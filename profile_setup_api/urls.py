from django.urls import path
from .views import ProfileListCreateView, ProfileDetailView, NaturalLanguageSearchView

urlpatterns = [
    path('profiles/', ProfileListCreateView.as_view(), name='profiles'),
    path('profiles', ProfileListCreateView.as_view(), name='profiles-no-slash'),
    path('profiles/<uuid:profile_id>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/<uuid:profile_id>', ProfileDetailView.as_view(), name='profile-detail-no-slash'),
    path('profiles/search/', NaturalLanguageSearchView.as_view(), name='natural-search'),
    path('profiles/search', NaturalLanguageSearchView.as_view(), name='natural-search-no-slash'),
]