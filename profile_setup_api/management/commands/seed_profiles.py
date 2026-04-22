import os
import json
import requests
from django.core.management.base import BaseCommand
from profile_setup_api.models import Profile

class Command(BaseCommand):
    help = 'Seed database with profiles from JSON file'
    
    def handle(self, *args, **options):
        json_url = "https://drive.google.com/uc?export=download&id=YOUR_FILE_ID"  # Update with actual URL
        
        self.stdout.write("Seeding profiles...")
        
        try:
            response = requests.get(json_url)
            response.raise_for_status()
            profiles_data = response.json()
            
            created_count = 0
            updated_count = 0
            
            for profile_data in profiles_data:
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
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully seeded database: {created_count} created, {updated_count} updated'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding database: {str(e)}'))