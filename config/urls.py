from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from accounts.auth_views import (
    CurrentUserView,
    GitHubCallbackRedirectView,
    GitHubCLIExchangeView,
    GitHubOnlyLoginView,
    GitHubOAuthCallbackView,
    GitHubOAuthStartView,
    LogoutTokenView,
    RefreshTokenView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="Profile Integration API",
        default_version='v1',
        description="API for creating and managing user profiles with demographic data from external APIs.",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@profileapi.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
)

def health_check(request):
    return JsonResponse({"status": "ok", "message": "Profile Integration API is running"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('accounts/', include('allauth.urls')),          # allauth (once, not twice)
    path('github/callback/', GitHubCallbackRedirectView.as_view(), name='github_callback_redirect'),

    # TRD-compatible auth endpoints
    path('auth/github', GitHubOAuthStartView.as_view(), name='auth_github'),
    path('auth/github/', GitHubOAuthStartView.as_view(), name='auth_github_slash'),
    path('auth/github/callback', GitHubOAuthCallbackView.as_view(), name='auth_github_callback'),
    path('auth/github/callback/', GitHubOAuthCallbackView.as_view(), name='auth_github_callback_slash'),
    path('auth/refresh', RefreshTokenView.as_view(), name='auth_refresh'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth_refresh_slash'),
    path('auth/logout', LogoutTokenView.as_view(), name='auth_logout'),
    path('auth/logout/', LogoutTokenView.as_view(), name='auth_logout_slash'),
    path('api/users/me', CurrentUserView.as_view(), name='users_me'),
    path('api/users/me/', CurrentUserView.as_view(), name='users_me_slash'),

    # Auth endpoints
    path('api/v1/auth/login/', GitHubOnlyLoginView.as_view(), name='auth_login_disabled'),
    path('api/v1/auth/', include('dj_rest_auth.urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/github/cli/', GitHubCLIExchangeView.as_view(), name='github_cli_exchange'),

    # Profile API
    path('api/', include('profile_setup_api.urls')),

    # Docs
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
