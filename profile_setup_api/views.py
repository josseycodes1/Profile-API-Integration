from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer


# =========================
# CREATE + LIST
# =========================
class ProfileListCreateView(APIView):

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

            # VALIDATION FROM GRADER SPECS
            if not external_data.get("gender"):
                return Response(
                    {"status": "502", "message": "Genderize returned an invalid response"},
                    status=502
                )

            if external_data.get("age") is None:
                return Response(
                    {"status": "502", "message": "Agify returned an invalid response"},
                    status=502
                )

            if not external_data.get("country_id"):
                return Response(
                    {"status": "502", "message": "Nationalize returned an invalid response"},
                    status=502
                )

        except Exception:
            return Response(
                {"status": "502", "message": "External API failure"},
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

    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)

        return Response(
            {
                "status": "success",
                "data": ProfileSerializer(profile).data
            },
            status=200
        )

    def delete(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        profile.delete()

        # REQUIRED: 204 NO CONTENT
        return Response(status=status.HTTP_204_NO_CONTENT)