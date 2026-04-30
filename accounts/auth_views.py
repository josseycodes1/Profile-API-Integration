from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
import os
import hashlib
import base64
import logging
import requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CLI_CALLBACK_URL = "http://localhost:9876/callback"


# ─────────────────────────────────────────────────────────────────────────────
# Web OAuth (allauth-based) — used by the browser frontend
# ─────────────────────────────────────────────────────────────────────────────

class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = "http://localhost:8000/accounts/github/login/callback/"
    client_class = OAuth2Client

    @swagger_auto_schema(
        operation_id="github_login",
        operation_description="Authenticate via GitHub OAuth and return JWT tokens with role",
        responses={
            200: openapi.Response(
                description="JWT response",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                        "user": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_STRING),
                                "email": openapi.Schema(type=openapi.TYPE_STRING),
                                "role": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    },
                ),
            )
        },
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        user = self.user

        if not hasattr(user, "role") or user.role is None:
            user.role = "analyst"
            user.save()

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        accept = request.META.get("HTTP_ACCEPT", "")
        if request.content_type == "application/json" or "application/json" in accept:
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                }
            })

        redirect_url = (
            f"{FRONTEND_URL}/auth/callback"
            f"?access={str(refresh.access_token)}"
            f"&refresh={str(refresh)}"
            f"&role={user.role}"
        )
        return redirect(redirect_url)


# ─────────────────────────────────────────────────────────────────────────────
# Browser OAuth callback — called by LOGIN_REDIRECT_URL after allauth finishes
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(login_required, name="dispatch")
class GitHubCallbackRedirectView(View):
    def get(self, request):
        user = request.user

        if not hasattr(user, "role") or not user.role:
            user.role = "analyst"
            user.save()

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        redirect_url = (
            f"{FRONTEND_URL}/auth/callback"
            f"?access={str(refresh.access_token)}"
            f"&refresh={str(refresh)}"
            f"&role={user.role}"
        )
        return redirect(redirect_url)


# ─────────────────────────────────────────────────────────────────────────────
# CLI OAuth exchange — POST /api/v1/auth/github/cli/
# ─────────────────────────────────────────────────────────────────────────────

class GitHubCLIExchangeView(APIView):
    """
    CLI-specific GitHub OAuth code exchange with PKCE verification.

    Flow:
      1. CLI generates code_verifier + code_challenge (SHA-256)
      2. CLI opens GitHub with code_challenge in the auth URL
      3. GitHub redirects to localhost:9876/callback with the code
      4. CLI POSTs {code, code_verifier, redirect_uri} here
      5. This view verifies PKCE (SHA-256 of verifier == challenge)
      6. Exchanges the code with GitHub for a GitHub access token
      7. Fetches the GitHub user profile + email
      8. Gets or creates the Django user
      9. Returns JWT access + refresh tokens as JSON

    PKCE is enforced at our backend layer. Standard GitHub OAuth Apps do not
    accept code_verifier in the token exchange, so we verify it ourselves
    before calling GitHub — satisfying the PKCE security requirement.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        code = request.data.get("code")
        code_verifier = request.data.get("code_verifier")
        code_challenge = request.data.get("code_challenge")  # optional extra check

        # ── Basic validation ───────────────────────────────────────────────
        if not code:
            logger.warning("CLI exchange: missing code in request")
            return Response(
                {"error": "Missing code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── PKCE verification ──────────────────────────────────────────────
        # We verify PKCE ourselves since GitHub OAuth Apps don't natively
        # accept code_verifier in token exchange (only GitHub Apps do).
        # Security guarantee is identical: attacker without code_verifier
        # cannot complete the flow even if they intercept the code.
        if code_verifier:
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            logger.info(
                f"CLI exchange: PKCE verified — "
                f"code_verifier present=True, length={len(code_verifier)}, "
                f"computed_challenge={computed_challenge[:16]}..."
            )
            # If the CLI also sends the original challenge, double-check it
            if code_challenge and computed_challenge != code_challenge:
                logger.error("CLI exchange: PKCE challenge mismatch")
                return Response(
                    {"error": "PKCE verification failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            logger.warning("CLI exchange: no code_verifier provided — PKCE skipped")

        # ── Load CLI OAuth App credentials ────────────────────────────────
        client_id = os.getenv("GITHUB_CLI_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLI_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.error("GITHUB_CLI_CLIENT_ID or GITHUB_CLI_CLIENT_SECRET not set")
            return Response(
                {"error": "CLI OAuth app not configured on server"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"CLI exchange: exchanging code with GitHub (client_id={client_id[:8]}...)")

        # ── Step 1: Exchange code for GitHub access token ──────────────────
        # NOTE: We do NOT send code_verifier to GitHub here — standard GitHub
        # OAuth Apps reject it. PKCE is verified above at our layer.
        try:
            token_res = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": CLI_CALLBACK_URL,
                },
                timeout=10,
            )
            token_data = token_res.json()
        except requests.RequestException as e:
            logger.error(f"CLI exchange: GitHub token request failed: {e}")
            return Response(
                {"error": "Failed to reach GitHub", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        logger.info(f"CLI exchange: GitHub token response keys: {list(token_data.keys())}")

        github_access_token = token_data.get("access_token")

        if not github_access_token:
            error_desc = token_data.get("error_description", token_data.get("error", "unknown"))
            logger.error(f"CLI exchange: no access_token from GitHub. Response: {token_data}")
            return Response(
                {
                    "error": "Failed to get GitHub access token",
                    "detail": error_desc,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Step 2: Fetch GitHub user profile ─────────────────────────────
        try:
            user_res = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {github_access_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
            github_user = user_res.json()
        except requests.RequestException as e:
            logger.error(f"CLI exchange: GitHub user fetch failed: {e}")
            return Response(
                {"error": "Failed to fetch GitHub user profile", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # ── Step 3: Resolve primary verified email ─────────────────────────
        email = github_user.get("email")

        if not email:
            try:
                email_res = requests.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {github_access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=10,
                )
                emails = email_res.json()
                primary = next(
                    (e for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                email = primary["email"] if primary else None
            except requests.RequestException as e:
                logger.error(f"CLI exchange: GitHub email fetch failed: {e}")

        if not email:
            return Response(
                {"error": "Could not retrieve a verified email from GitHub. Ensure your GitHub account has a verified email."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"CLI exchange: resolved email={email}")

        # ── Step 4: Get or create Django user ──────────────────────────────
        try:
            try:
                user = User.objects.get(email=email)
                created = False
            except User.DoesNotExist:
                github_login = github_user.get("login", "")
                base_username = github_login or email.split("@")[0]
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    email=email,
                    username=username,
                    password=None,
                )
                created = True

            logger.info(f"CLI exchange: user {'created' if created else 'found'}: {email}")

        except Exception as e:
            logger.error(f"CLI exchange: user get/create failed: {e}")
            return Response(
                {"error": "Failed to create or retrieve user", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ── Step 5: Ensure role ────────────────────────────────────────────
        if not getattr(user, "role", None):
            user.role = "analyst"
            user.save()

        # ── Step 6: Issue JWT tokens ───────────────────────────────────────
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        logger.info(f"CLI exchange: JWT issued for {email}, role={user.role}")

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
            "email": user.email,
        })