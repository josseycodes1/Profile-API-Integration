from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView

urlpatterns = [
    path('profiles/', ProfileListCreateView.as_view(), name='profiles'),
    path('profiles/<uuid:profile_id>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles', ProfileListCreateView.as_view(), name='profiles'),
    path('profiles/<uuid:profile_id>', ProfileDetailView.as_view(), name='profile-detail'),
]