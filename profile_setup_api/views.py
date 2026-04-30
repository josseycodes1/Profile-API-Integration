from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import csv
import logging
from urllib.parse import urlencode

from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer
from .query_parser import NaturalLanguageParser

from accounts.permissions import IsAdmin, IsAnalyst
from .throttles import ProfileCreateThrottle

logger = logging.getLogger(__name__)

REQUIRED_API_VERSION = "1"


def require_api_version(request):
    if request.headers.get("X-API-Version") != REQUIRED_API_VERSION:
        return Response(
            {"status": "error", "message": "API version header required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def filtered_profiles(request):
    queryset = Profile.objects.all()

    filters = {
        "gender": "gender__iexact",
        "age_group": "age_group__iexact",
        "country_id": "country_id__iexact",
        "country": "country_id__iexact",
        "min_age": "age__gte",
        "max_age": "age__lte",
        "min_gender_probability": "gender_probability__gte",
        "min_country_probability": "country_probability__gte",
    }

    for param, lookup in filters.items():
        value = request.query_params.get(param)
        if value not in (None, ""):
            queryset = queryset.filter(**{lookup: value})

    sort_by = request.query_params.get("sort_by")
    order = request.query_params.get("order", "asc")
    if sort_by in {"age", "created_at", "gender_probability"}:
        prefix = "-" if order == "desc" else ""
        queryset = queryset.order_by(f"{prefix}{sort_by}")

    return queryset


def paginated_response(request, queryset):
    page = max(int(request.query_params.get("page", 1)), 1)
    limit = min(max(int(request.query_params.get("limit", 10)), 1), 50)
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page)
    current_page = page_obj.number

    def page_link(page_number):
        if page_number is None:
            return None
        params = request.query_params.copy()
        params["page"] = page_number
        params["limit"] = limit
        return f"{request.path}?{urlencode(params, doseq=True)}"

    return Response({
        "status": "success",
        "page": current_page,
        "limit": limit,
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "links": {
            "self": page_link(current_page),
            "next": page_link(page_obj.next_page_number()) if page_obj.has_next() else None,
            "prev": page_link(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        },
        "data": ProfileListSerializer(page_obj, many=True).data,
    })


# =========================
# PROFILE LIST + CREATE
# =========================
class ProfileListCreateView(APIView):
    throttle_classes = [ProfileCreateThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated(), IsAnalyst()]

    def get_throttles(self):
        if self.request.method == "POST":
            return [ProfileCreateThrottle()]
        return [throttle() for throttle in api_settings.DEFAULT_THROTTLE_CLASSES]

    @swagger_auto_schema(
        operation_id="create_profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={"name": openapi.Schema(type=openapi.TYPE_STRING)},
        )
    )
    def post(self, request):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        name = request.data.get("name")

        if not name:
            return Response({"status": "error", "message": "Missing name"}, status=400)

        name = name.strip().lower()

        existing = Profile.objects.filter(name=name).first()
        if existing:
            return Response(
                {"status": "success", "data": ProfileSerializer(existing).data},
                status=200
            )

        try:
            external_data = ExternalAPIService.fetch_all_data(name)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=502)

        profile = Profile.objects.create(name=name, **external_data)

        return Response(
            {"status": "success", "data": ProfileSerializer(profile).data},
            status=201
        )

    @swagger_auto_schema(
        operation_id="get_profiles",
        manual_parameters=[
            openapi.Parameter("gender", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        return paginated_response(request, filtered_profiles(request))


# =========================
# PROFILE DETAIL
# =========================
class ProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        profile = get_object_or_404(Profile, id=profile_id)
        return Response(ProfileSerializer(profile).data)

    def delete(self, request, profile_id):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        self.permission_classes = [IsAuthenticated, IsAdmin]
        self.check_permissions(request)

        profile = get_object_or_404(Profile, id=profile_id)
        profile.delete()
        return Response(status=204)


# =========================
# NATURAL LANGUAGE SEARCH
# =========================
class NaturalLanguageSearchView(APIView):
    permission_classes = [IsAuthenticated, IsAnalyst]

    def get(self, request):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        query = request.query_params.get("q", "")

        if not query:
            return Response({"status": "error", "message": "Missing query"}, status=400)

        filters = NaturalLanguageParser.parse(query)
        if "error" in filters:
            return Response({"status": "error", "message": filters["error"]}, status=422)

        queryset = Profile.objects.all()

        for key, value in filters.items():
            if key == "gender":
                queryset = queryset.filter(gender__iexact=value)
            elif key == "age_group":
                queryset = queryset.filter(age_group__iexact=value)
            elif key == "country_id":
                queryset = queryset.filter(country_id__iexact=value)
            elif key == "min_age":
                queryset = queryset.filter(age__gte=value)
            elif key == "max_age":
                queryset = queryset.filter(age__lte=value)
            elif key == "min_gender_probability":
                queryset = queryset.filter(gender_probability__gte=value)
            elif key == "min_country_probability":
                queryset = queryset.filter(country_probability__gte=value)

        return paginated_response(request, queryset)


# =========================
# CSV EXPORT (ADMIN ONLY)
# =========================
class ProfileCSVExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        version_error = require_api_version(request)
        if version_error:
            return version_error

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="profiles_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'id', 'name', 'gender', 'gender_probability', 'age',
            'age_group', 'country_id', 'country_name',
            'country_probability', 'created_at'
        ])

        for profile in filtered_profiles(request):
            writer.writerow([
                profile.id,
                profile.name,
                profile.gender,
                profile.gender_probability,
                profile.age,
                profile.age_group,
                profile.country_id,
                profile.country_name,
                profile.country_probability,
                profile.created_at,
            ])

        return response
    
class LogoutView(APIView):
    def post(self, request):
        response = Response({"status": "logged out"})

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
