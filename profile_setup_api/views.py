from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Profile
from .services import ExternalAPIService
from .serializers import ProfileSerializer, ProfileListSerializer
from .query_parser import NaturalLanguageParser

import logging
logger = logging.getLogger(__name__)


class ProfileListCreateView(APIView):
    """Handle POST and GET for profiles with filtering, sorting, pagination"""
    
    @swagger_auto_schema(
        operation_id="create_profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={201: "Created", 200: "Exists", 400: "Bad Request", 422: "Invalid", 502: "API Error"}
    )
    def post(self, request):
        name = request.data.get("name")
        
        if name is None:
            return Response(
                {"status": "error", "message": "Missing name"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        # Idempotency
        existing = Profile.objects.filter(name=name).first()
        if existing:
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": ProfileSerializer(existing).data
                },
                status=status.HTTP_200_OK
            )
        
        # External API
        try:
            external_data = ExternalAPIService.fetch_all_data(name)
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        
        profile = Profile.objects.create(name=name, **external_data)
        
        return Response(
            {"status": "success", "data": ProfileSerializer(profile).data},
            status=status.HTTP_201_CREATED
        )
    
    @swagger_auto_schema(
        operation_id="get_all_profiles",
        manual_parameters=[
            openapi.Parameter("gender", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("age_group", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("country_id", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("min_age", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("max_age", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("min_gender_probability", openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter("min_country_probability", openapi.IN_QUERY, type=openapi.TYPE_NUMBER),
            openapi.Parameter("sort_by", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=['age', 'created_at', 'gender_probability']),
            openapi.Parameter("order", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=['asc', 'desc']),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request):
        try:
            queryset = Profile.objects.all()
            
            # Apply filters
            gender = request.query_params.get("gender")
            if gender:
                queryset = queryset.filter(gender__iexact=gender)
            
            age_group = request.query_params.get("age_group")
            if age_group:
                queryset = queryset.filter(age_group__iexact=age_group)
            
            country_id = request.query_params.get("country_id")
            if country_id:
                queryset = queryset.filter(country_id__iexact=country_id.upper())
            
            min_age = request.query_params.get("min_age")
            if min_age:
                try:
                    queryset = queryset.filter(age__gte=int(min_age))
                except ValueError:
                    return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
            
            max_age = request.query_params.get("max_age")
            if max_age:
                try:
                    queryset = queryset.filter(age__lte=int(max_age))
                except ValueError:
                    return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
            
            min_gender_prob = request.query_params.get("min_gender_probability")
            if min_gender_prob:
                try:
                    queryset = queryset.filter(gender_probability__gte=float(min_gender_prob))
                except ValueError:
                    return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
            
            min_country_prob = request.query_params.get("min_country_probability")
            if min_country_prob:
                try:
                    queryset = queryset.filter(country_probability__gte=float(min_country_prob))
                except ValueError:
                    return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
            
            # Apply sorting
            sort_by = request.query_params.get("sort_by", "created_at")
            order = request.query_params.get("order", "desc")
            
            allowed_sort_fields = ['age', 'created_at', 'gender_probability']
            if sort_by not in allowed_sort_fields:
                sort_by = 'created_at'
            
            if order == 'asc':
                queryset = queryset.order_by(sort_by)
            else:
                queryset = queryset.order_by(f'-{sort_by}')
            
            # Apply pagination
            page = request.query_params.get("page", 1)
            limit = request.query_params.get("limit", 10)
            
            try:
                page = int(page)
                limit = int(limit)
                if limit > 50:
                    limit = 50
                if limit < 1:
                    limit = 10
            except ValueError:
                return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
            
            paginator = Paginator(queryset, limit)
            
            try:
                page_obj = paginator.page(page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
            
            # Serialize data
            data = ProfileListSerializer(page_obj, many=True).data
            
            return Response(
                {
                    "status": "success",
                    "page": page,
                    "limit": limit,
                    "total": paginator.count,
                    "data": data
                },
                status=200
            )
            
        except Exception as e:
            logger.error(f"Error in get all profiles: {str(e)}")
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=500
            )


class ProfileDetailView(APIView):
    """Handle GET and DELETE for single profile"""
    
    @swagger_auto_schema(operation_id="get_profile")
    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        return Response(
            {"status": "success", "data": ProfileSerializer(profile).data},
            status=200
        )
    
    @swagger_auto_schema(operation_id="delete_profile")
    def delete(self, request, profile_id):
        profile = get_object_or_404(Profile, id=profile_id)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NaturalLanguageSearchView(APIView):
    """Handle natural language search queries"""
    
    @swagger_auto_schema(
        operation_id="natural_language_search",
        manual_parameters=[
            openapi.Parameter("q", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True, description="Natural language query"),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("limit", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Success", 400: "Bad Request", 422: "Unable to interpret query"}
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        
        if not query:
            return Response(
                {"status": "error", "message": "Missing query parameter 'q'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse the natural language query
        filters = NaturalLanguageParser.parse(query)
        
        if 'error' in filters:
            return Response(
                {"status": "error", "message": filters['error']},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        # Build queryset based on parsed filters
        queryset = Profile.objects.all()
        
        if 'gender' in filters:
            queryset = queryset.filter(gender__iexact=filters['gender'])
        
        if 'age_group' in filters:
            queryset = queryset.filter(age_group__iexact=filters['age_group'])
        
        if 'country_id' in filters:
            queryset = queryset.filter(country_id__iexact=filters['country_id'])
        
        if 'min_age' in filters:
            queryset = queryset.filter(age__gte=filters['min_age'])
        
        if 'max_age' in filters:
            queryset = queryset.filter(age__lte=filters['max_age'])
        
        if 'min_gender_probability' in filters:
            queryset = queryset.filter(gender_probability__gte=filters['min_gender_probability'])
        
        if 'min_country_probability' in filters:
            queryset = queryset.filter(country_probability__gte=filters['min_country_probability'])
        
        # Apply pagination
        page = request.query_params.get("page", 1)
        limit = request.query_params.get("limit", 10)
        
        try:
            page = int(page)
            limit = int(limit)
            if limit > 50:
                limit = 50
        except ValueError:
            return Response({"status": "error", "message": "Invalid query parameters"}, status=422)
        
        paginator = Paginator(queryset, limit)
        
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        data = ProfileListSerializer(page_obj, many=True).data
        
        return Response(
            {
                "status": "success",
                "page": page,
                "limit": limit,
                "total": paginator.count,
                "data": data
            },
            status=200
        )