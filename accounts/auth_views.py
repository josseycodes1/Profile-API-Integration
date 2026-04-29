from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.shortcuts import redirect
from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = "https://rofile--ntegration-adewumijosephine3516-kodp7ruz.leapcell.dev/accounts/github/login/callback/"
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

        # Ensure role exists
        if not hasattr(user, "role") or user.role is None:
            user.role = "analyst"
            user.save()

        # Generate JWT
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email

        # For direct API access (Swagger/CLI), return JSON
        if request.content_type == 'application/json' or request.META.get('HTTP_ACCEPT', '').find('application/json') != -1:
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                }
            })
        
        # For browser OAuth flow, redirect to frontend with tokens
        frontend_url = "https://insighta-web-azure.vercel.app/auth/callback"
        redirect_url = f"{frontend_url}?access={refresh.access_token}&refresh={refresh}&role={user.role}"
        
        return redirect(redirect_url)