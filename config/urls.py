from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Profile Integration API",
        default_version='v1',
        description="""
        API for creating and managing user profiles with demographic data from external APIs.
        
        ## Features
        - Create profiles with automatic data fetching from Genderize, Agify, and Nationalize APIs
        - Idempotent profile creation (same name returns existing profile)
        - Retrieve single or multiple profiles with filtering
        - Delete profiles
        - Case-insensitive filtering by gender, country, and age group
        
        ## External APIs Used
        - Genderize API: Determines gender from name
        - Agify API: Predicts age from name
        - Nationalize API: Predicts nationality from name
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('profile_setup_api.urls')),
    
    # Swagger documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]