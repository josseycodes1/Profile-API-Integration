import json
import requests
from .models import Profile

def seed_profiles_from_json(json_url):
    """Seed database with profiles from JSON file"""
    try:
        # Download JSON data
        response = requests.get(json_url)
        response.raise_for_status()
        profiles_data = response.json()
        
        created_count = 0
        updated_count = 0
        
        for profile_data in profiles_data:
            # Check if profile exists
            profile, created = Profile.objects.update_or_create(
                name=profile_data['name'].lower(),
                defaults={
                    'gender': profile_data['gender'],
                    'gender_probability': profile_data['gender_probability'],
                    'age': profile_data['age'],
                    'age_group': profile_data['age_group'],
                    'country_id': profile_data['country_id'],
                    'country_name': profile_data.get('country_name', ''),
                    'country_probability': profile_data['country_probability'],
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return {
            'created': created_count,
            'updated': updated_count,
            'total': created_count + updated_count
        }
    except Exception as e:
        raise Exception(f"Failed to seed profiles: {str(e)}")