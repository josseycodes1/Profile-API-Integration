from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer


# =========================
# CREATE + LIST
# =========================
class ProfileListCreateView(APIView):

    @swagger_auto_schema(
        operation_id="create_profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={
                "name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Name of the user"
                )
            },
        ),
        responses={
            201: openapi.Response("Created"),
            200: openapi.Response("Already exists"),
            400: "Bad Request",
            422: "Invalid type",
            502: "External API failure"
        }
    )
    def post(self, request):
        name = request.data.get("name")

        # missing name
        if name is None:
            return Response(
                {"status": "error", "message": "Missing name"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # invalid type
        if not isinstance(name, str):
            return Response(
                {"status": "error", "message": "Invalid type"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        name = name.strip().lower()

        if name == "":
            return Response(
                {"status": "error", "message": "Empty name"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # idempotency
        existing = Profile.objects.filter(name=name).first()
        if existing:
            data = ProfileSerializer(existing).data
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": data
                },
                status=status.HTTP_200_OK
            )

        # external API
        try:
            external_data = ExternalAPIService.fetch_all_data(name)

            if not external_data.get("gender"):
                return Response(
                    {"status": "error", "message": "Genderize returned an invalid response"},
                    status=502
                )

            if external_data.get("age") is None:
                return Response(
                    {"status": "error", "message": "Agify returned an invalid response"},
                    status=502
                )

            if not external_data.get("country_id"):
                return Response(
                    {"status": "error", "message": "Nationalize returned an invalid response"},
                    status=502
                )

        except Exception:
            return Response(
                {"status": "error", "message": "External API failure"},
                status=502
            )

        profile = Profile.objects.create(name=name, **external_data)

        return Response(
            {
                "status": "success",
                "data": ProfileSerializer(profile).data
            },
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_id="get_all_profiles",
        manual_parameters=[
            openapi.Parameter("gender", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("country_id", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("age_group", openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        queryset = Profile.objects.all()

        gender = request.query_params.get("gender")
        country_id = request.query_params.get("country_id")
        age_group = request.query_params.get("age_group")

        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)

        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        return Response(
            {
                "status": "success",
                "count": queryset.count(),
                "data": ProfileListSerializer(queryset, many=True).data
            },
            status=200
        )


# =========================
# DETAIL + DELETE
# =========================
class ProfileDetailView(APIView):

    @swagger_auto_schema(operation_id="get_profile")
    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)

        return Response(
            {
                "status": "success",
                "data": ProfileSerializer(profile).data
            },
            status=200
        )

    @swagger_auto_schema(operation_id="delete_profile")
    def delete(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        profile.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)