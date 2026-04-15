from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'age', 'age_group', 'country_id', 'created_at']
    search_fields = ['name']
    list_filter = ['age_group', 'gender', 'country_id']