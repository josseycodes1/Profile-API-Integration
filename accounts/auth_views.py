from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import hashlib
import base64
import secrets
import logging
import requests
from urllib.parse import urlencode, urlparse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from profile_setup_api.throttles import AuthThrottle

User = get_user_model()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://insighta-web-azure.vercel.app/").rstrip("/")
CLI_CALLBACK_URL = "http://localhost:9876/callback"
GITHUB_ALLAUTH_CALLBACK_URL = os.getenv(
    "GITHUB_CALLBACK_URL",
    "https://rofile--ntegration-queenjossey2882-3fiaqj4k.leapcell.dev/accounts/github/login/callback/",
)
GITHUB_WEB_CALLBACK_URL = os.getenv(
    "GITHUB_WEB_CALLBACK_URL",
    "https://rofile--ntegration-queenjossey2882-3fiaqj4k.leapcell.dev/auth/github/callback",
)
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _frontend_origins():
    origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
    if FRONTEND_URL:
        parsed = urlparse(FRONTEND_URL)
        if parsed.scheme and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")
    return origins


def _is_web_client(request):
    if request.headers.get("X-Client-Type", "").lower() == "cli":
        return False
    if request.query_params.get("client") == "cli":
        return False

    data = getattr(request, "data", None)
    if hasattr(data, "get") and str(data.get("client", "")).lower() == "cli":
        return False

    origin = request.headers.get("Origin")
    if origin and origin in _frontend_origins():
        return True

    referer = request.headers.get("Referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin in _frontend_origins():
                return True

    return False


def _cookie_options(request, max_age):
    host = request.get_host().split(":")[0]
    is_local = host in {"localhost", "127.0.0.1"}
    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", "").strip() or None

    if is_local and settings.DEBUG:
        options = {
            "max_age": max_age,
            "httponly": True,
            "secure": False,
            "samesite": "Lax",
            "path": "/",
        }
        if cookie_domain:
            options["domain"] = cookie_domain
        return options

    options = {
        "max_age": max_age,
        "httponly": True,
        "secure": True,
        "samesite": "None",
        "path": "/",
    }
    if cookie_domain:
        options["domain"] = cookie_domain
    return options


def _oauth_cookie_options(request):
    host = request.get_host().split(":")[0]
    is_local = host in {"localhost", "127.0.0.1"}
    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN", "").strip() or None

    options = {
        "max_age": 5 * 60,
        "httponly": True,
        "secure": not is_local,
        "samesite": "Lax",
        "path": "/",
    }
    if cookie_domain:
        options["domain"] = cookie_domain
    return options


def _base64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _token_payload(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email
    return {
        "status": "success",
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": str(user.id),
            "github_id": user.github_id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
        },
        "role": user.role,
        "email": user.email,
    }


def _public_auth_payload(payload):
    return {
        "status": payload["status"],
        "user": payload["user"],
        "role": payload["role"],
        "email": payload["email"],
    }


def _set_token_cookies(request, response, payload):
    response.set_cookie(
        "access_token",
        payload["access_token"],
        **_cookie_options(request, 3 * 60),
    )
    response.set_cookie(
        "refresh_token",
        payload["refresh_token"],
        **_cookie_options(request, 5 * 60),
    )


def _log_response_cookies(context, response):
    cookie_debug = []
    for name, morsel in response.cookies.items():
        cookie_debug.append(
            {
                "name": name,
                "domain": morsel["domain"] or None,
                "path": morsel["path"] or None,
                "secure": bool(morsel["secure"]),
                "httponly": bool(morsel["httponly"]),
                "samesite": morsel["samesite"] or None,
                "max_age": morsel["max-age"] or None,
                "expires": morsel["expires"] or None,
            }
        )

    logger.info("%s cookies=%s", context, cookie_debug)


def _clear_token_cookies(request, response):
    cookie_options = _cookie_options(request, 0)
    delete_options = {
        "path": cookie_options["path"],
        "samesite": cookie_options["samesite"],
    }
    if "domain" in cookie_options:
        delete_options["domain"] = cookie_options["domain"]

    response.delete_cookie("access_token", **delete_options)
    response.delete_cookie("refresh_token", **delete_options)


def _clear_oauth_cookies(request, response):
    cookie_options = _oauth_cookie_options(request)
    delete_options = {
        "path": cookie_options["path"],
        "samesite": cookie_options["samesite"],
    }
    if "domain" in cookie_options:
        delete_options["domain"] = cookie_options["domain"]

    response.delete_cookie("oauth_state", **delete_options)
    response.delete_cookie("code_verifier", **delete_options)
    response.delete_cookie("code_challenge", **delete_options)


def _build_auth_response(request, payload):
    if _is_web_client(request):
        response = Response(_public_auth_payload(payload))
        _set_token_cookies(request, response, payload)
        return response

    return Response(payload)


def _github_request_json(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(str(exc)) from exc


def _get_or_create_github_user(github_access_token):
    github_user = _github_request_json(
        "GET",
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {github_access_token}",
            "Accept": "application/vnd.github+json",
        },
    )

    github_id = str(github_user.get("id") or "")
    username = github_user.get("login") or ""
    email = github_user.get("email")

    if not email:
        emails = _github_request_json(
            "GET",
            GITHUB_EMAILS_URL,
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        primary = next(
            (item for item in emails if item.get("primary") and item.get("verified")),
            None,
        )
        email = primary["email"] if primary else None

    if not github_id or not email:
        raise ValueError("Could not retrieve GitHub id and verified email")

    user = User.objects.filter(github_id=github_id).first()
    if not user:
        user = User.objects.filter(email=email).first()

    if not user:
        base_username = username or email.split("@")[0]
        candidate = base_username
        counter = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base_username}{counter}"
            counter += 1
        user = User.objects.create_user(
            email=email,
            username=candidate,
            password=None,
        )

    user.github_id = github_id
    user.username = user.username or username
    user.avatar_url = github_user.get("avatar_url") or user.avatar_url
    user.last_login_at = timezone.now()
    if not user.role:
        user.role = "analyst"
    user.save()
    return user


class GitHubOAuthStartView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AuthThrottle]

    def get(self, request):
        client_id = os.getenv("GITHUB_CLIENT_ID")
        if not client_id:
            return Response(
                {"status": "error", "message": "GitHub OAuth is not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = _base64url_sha256(code_verifier)
        callback_url = GITHUB_WEB_CALLBACK_URL or request.build_absolute_uri("/auth/github/callback")
        auth_params = {
            'client_id': client_id,
            'redirect_uri': callback_url,
            'scope': 'user:email',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        auth_url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(auth_params)}"

        response = redirect(auth_url)
        cookie_kwargs = _oauth_cookie_options(request)
        response.set_cookie("oauth_state", state, **cookie_kwargs)
        response.set_cookie("code_verifier", code_verifier, **cookie_kwargs)
        response.set_cookie("code_challenge", code_challenge, **cookie_kwargs)
        return response


class GitHubOAuthCallbackView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AuthThrottle]

    def get(self, request):
        logger.info(
            "GitHubOAuthCallbackView start host=%s origin=%s referer=%s frontend=%s callback=%s has_state=%s has_verifier=%s",
            request.get_host(),
            request.headers.get("Origin"),
            request.headers.get("Referer"),
            FRONTEND_URL,
            GITHUB_WEB_CALLBACK_URL,
            bool(request.COOKIES.get("oauth_state")),
            bool(request.COOKIES.get("code_verifier")),
        )
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        saved_state = request.COOKIES.get("oauth_state")
        code_verifier = request.COOKIES.get("code_verifier")

        if not code or not state:
            return Response(
                {"status": "error", "message": "Missing OAuth code or state"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not saved_state or state != saved_state:
            return Response(
                {"status": "error", "message": "Invalid OAuth state"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not code_verifier:
            return Response(
                {"status": "error", "message": "Missing PKCE code verifier"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token_data = _github_request_json(
                "POST",
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                json={
                    "client_id": os.getenv("GITHUB_CLIENT_ID"),
                    "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                    "code": code,
                    "redirect_uri": GITHUB_WEB_CALLBACK_URL or request.build_absolute_uri("/auth/github/callback"),
                    "code_verifier": code_verifier,
                },
            )
        except RuntimeError as exc:
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        github_access_token = token_data.get("access_token")
        if not github_access_token:
            return Response(
                {
                    "status": "error",
                    "message": token_data.get("error_description", "GitHub token exchange failed"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = _get_or_create_github_user(github_access_token)
        except (RuntimeError, ValueError) as exc:
            return Response(
                {"status": "error", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"status": "error", "message": "User account is inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = _token_payload(user)
        logger.info(
            "GitHubOAuthCallbackView payload created user_id=%s role=%s",
            user.id,
            user.role,
        )

        # Tokens are delivered ONLY via httpOnly cookies — never in the redirect
        # URL. This keeps them out of browser history, server logs, and JS.
        response = redirect(f"{FRONTEND_URL}/auth/callback")
        logger.info(
            "GitHubOAuthCallbackView redirect prepared status=%s location=%s",
            response.status_code,
            response.get("Location"),
        )
        _set_token_cookies(request, response, payload)
        _log_response_cookies("GitHubOAuthCallbackView after _set_token_cookies", response)
        _clear_oauth_cookies(request, response)
        _log_response_cookies("GitHubOAuthCallbackView before return", response)
        return response


class GitHubOnlyLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return Response(
            {"status": "error", "message": "Password login is disabled. Use GitHub OAuth."},
            status=status.HTTP_404_NOT_FOUND,
        )


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        raw_refresh = (
            request.data.get("refresh_token")
            or request.data.get("refresh")
            or request.COOKIES.get("refresh_token")
        )
        if not raw_refresh:
            return Response(
                {"status": "error", "message": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_refresh = RefreshToken(raw_refresh)
            user = User.objects.get(id=old_refresh["user_id"])
            old_refresh.blacklist()
        except (TokenError, User.DoesNotExist):
            return Response(
                {"status": "error", "message": "Invalid refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"status": "error", "message": "User account is inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = _token_payload(user)
        return _build_auth_response(request, payload)


class LogoutTokenView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        raw_refresh = (
            request.data.get("refresh_token")
            or request.data.get("refresh")
            or request.COOKIES.get("refresh_token")
        )
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass

        response = Response({"status": "success", "message": "Logged out"})
        _clear_token_cookies(request, response)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "status": "success",
            "data": {
                "id": str(user.id),
                "github_id": user.github_id,
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "role": user.role,
                "is_active": user.is_active,
                "last_login_at": user.last_login_at,
                "created_at": user.date_joined,
            }
        })


# ─────────────────────────────────────────────────────────────────────────────
# Web OAuth (allauth-based) — used by the browser frontend
# ─────────────────────────────────────────────────────────────────────────────

class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = GITHUB_ALLAUTH_CALLBACK_URL
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

        payload = _token_payload(user)
        response = redirect(f"{FRONTEND_URL}/auth/callback")
        _set_token_cookies(request, response, payload)
        _log_response_cookies("GitHubLogin before return", response)
        return response


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

        payload = _token_payload(user)

        # Tokens in cookies only — no query params in redirect URL
        response = redirect(f"{FRONTEND_URL}/auth/callback")
        _set_token_cookies(request, response, payload)
        _log_response_cookies("GitHubCallbackRedirectView before return", response)
        return response


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
      9. Returns JWT access + refresh tokens as JSON (no cookies — CLI reads body)

    PKCE is enforced at our backend layer. Standard GitHub OAuth Apps do not
    accept code_verifier in the token exchange, so we verify it ourselves
    before calling GitHub — satisfying the PKCE security requirement.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        code = request.data.get("code")
        code_verifier = request.data.get("code_verifier")
        code_challenge = request.data.get("code_challenge")  

        if not code:
            logger.warning("CLI exchange: missing code in request")
            return Response(
                {"error": "Missing code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if code_verifier:
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            logger.info(
                f"CLI exchange: PKCE verified — "
                f"code_verifier present=True, length={len(code_verifier)}, "
                f"computed_challenge={computed_challenge[:16]}..."
            )
            if code_challenge and computed_challenge != code_challenge:
                logger.error("CLI exchange: PKCE challenge mismatch")
                return Response(
                    {"error": "PKCE verification failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            logger.warning("CLI exchange: no code_verifier provided — PKCE skipped")

        client_id = os.getenv("GITHUB_CLI_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLI_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.error("GITHUB_CLI_CLIENT_ID or GITHUB_CLI_CLIENT_SECRET not set")
            return Response(
                {"error": "CLI OAuth app not configured on server"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        logger.info(f"CLI exchange: exchanging code with GitHub (client_id={client_id[:8]}...)")

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

        if not getattr(user, "role", None):
            user.role = "analyst"
            user.save()

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
