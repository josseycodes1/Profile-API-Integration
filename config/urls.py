from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="MNC API",
        default_version='v1',
        description="Self-Paced Mentoring & Coaching Platform API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@mnc.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/learning/', include('learning.urls')),
    path('api/v1/progress/', include('progress.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    
    # ADD THIS LINE - Include your profile API
    path('api/', include('profile_setup_api.urls')),
    
    path('api/docs', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Only add static/media URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)