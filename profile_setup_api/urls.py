from django.urls import path

from accounts.auth_views import GitHubLogin
from .views import ProfileCSVExportView, ProfileListCreateView, ProfileDetailView, NaturalLanguageSearchView

urlpatterns = [
    path('profiles/', ProfileListCreateView.as_view(), name='profiles'),
    path('profiles', ProfileListCreateView.as_view(), name='profiles-no-slash'),
    path('profiles/<uuid:profile_id>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/<uuid:profile_id>', ProfileDetailView.as_view(), name='profile-detail-no-slash'),
    path('profiles/search/', NaturalLanguageSearchView.as_view(), name='natural-search'),
    path('profiles/search', NaturalLanguageSearchView.as_view(), name='natural-search-no-slash'),
    path('v1/auth/github/', GitHubLogin.as_view(), name='github_login'),
    path('profiles/export/', ProfileCSVExportView.as_view(), name='profiles-export'),
    path('profiles/export/csv/', ProfileCSVExportView.as_view(), name='profiles-export-csv'),
]
