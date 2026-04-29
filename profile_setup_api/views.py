from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import csv
import logging

from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer
from .query_parser import NaturalLanguageParser

from accounts.permissions import IsAdmin, IsAnalyst
from .throttles import ProfileCreateThrottle

logger = logging.getLogger(__name__)


# =========================
# PROFILE LIST + CREATE
# =========================
class ProfileListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAnalyst]
    throttle_classes = [ProfileCreateThrottle]

    @swagger_auto_schema(
        operation_id="create_profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={"name": openapi.Schema(type=openapi.TYPE_STRING)},
        )
    )
    def post(self, request):
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
        queryset = Profile.objects.all()

        gender = request.query_params.get("gender")
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        page = int(request.query_params.get("page", 1))
        limit = min(int(request.query_params.get("limit", 10)), 50)

        paginator = Paginator(queryset, limit)

        try:
            page_obj = paginator.page(page)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        return Response({
            "status": "success",
            "data": ProfileListSerializer(page_obj, many=True).data,
            "total": paginator.count
        })


# =========================
# PROFILE DETAIL
# =========================
class ProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        return Response(ProfileSerializer(profile).data)

    def delete(self, request, profile_id):
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
        query = request.query_params.get("q", "")

        if not query:
            return Response({"error": "Missing query"}, status=400)

        filters = NaturalLanguageParser.parse(query)

        queryset = Profile.objects.all()

        if "gender" in filters:
            queryset = queryset.filter(gender__iexact=filters["gender"])

        page = int(request.query_params.get("page", 1))
        limit = min(int(request.query_params.get("limit", 10)), 50)

        paginator = Paginator(queryset, limit)

        page_obj = paginator.get_page(page)

        return Response({
            "status": "success",
            "data": ProfileListSerializer(page_obj, many=True).data
        })


# =========================
# CSV EXPORT (ADMIN ONLY)
# =========================
class ProfileCSVExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="profiles.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'id', 'name', 'gender', 'age',
            'age_group', 'country_id', 'created_at'
        ])

        for profile in Profile.objects.all():
            writer.writerow([
                profile.id,
                profile.name,
                profile.gender,
                profile.age,
                profile.age_group,
                profile.country_id,
                profile.created_at,
            ])

        return response
    
class LogoutView(APIView):
    def post(self, request):
        response = Response({"status": "logged out"})

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response