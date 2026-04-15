from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer

class ProfileListCreateView(APIView):

    @swagger_auto_schema(
        operation_id="create_profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING)
            },
        )
    )
    def post(self, request):
        name = request.data.get("name")

        # ✅ Validate type FIRST
        if not isinstance(name, str):
            return Response(
                {"status": "error", "message": "Invalid type"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        name = name.strip().lower()

        if not name:
            return Response(
                {"status": "error", "message": "Missing or empty name"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Idempotency check
        existing = Profile.objects.filter(name=name).first()
        if existing:
            serializer = ProfileSerializer(existing)
            data = serializer.data
            data["created_at"] = existing.created_at.isoformat().replace("+00:00", "Z")

            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": data
                },
                status=status.HTTP_200_OK
            )

        # ✅ External API
        try:
            external_data = ExternalAPIService.fetch_all_data(name)
        except ValueError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        profile = Profile.objects.create(
            name=name,
            **external_data
        )

        serializer = ProfileSerializer(profile)
        data = serializer.data
        data["created_at"] = profile.created_at.isoformat().replace("+00:00", "Z")

        return Response(
            {"status": "success", "data": data},
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

        # ✅ Filters
        gender = request.query_params.get("gender")
        if gender:
            queryset = queryset.filter(gender__iexact=gender)

        country_id = request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id.upper())

        age_group = request.query_params.get("age_group")
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        serializer = ProfileListSerializer(queryset, many=True)

        return Response(
            {
                "status": "success",
                "count": len(serializer.data),
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

class ProfileDetailView(APIView):

    @swagger_auto_schema(operation_id="get_profile")
    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)

        serializer = ProfileSerializer(profile)
        data = serializer.data
        data["created_at"] = profile.created_at.isoformat().replace("+00:00", "Z")

        return Response(
            {"status": "success", "data": data},
            status=status.HTTP_200_OK
        )


    @swagger_auto_schema(operation_id="delete_profile")
    def delete(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        profile.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)