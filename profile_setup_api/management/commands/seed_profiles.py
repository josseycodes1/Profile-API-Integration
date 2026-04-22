import json
import random
import requests
from django.core.management.base import BaseCommand
from profile_setup_api.models import Profile

class Command(BaseCommand):
    help = 'Seed database with profiles from deployed API or create sample data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Source to fetch profiles from (deployed, sample, or local)',
            default='sample'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='Custom API URL to fetch profiles from',
            default='https://rofile--ntegration-adewumijosephine3516-kodp7ruz.leapcell.dev'
        )
    
    def handle(self, *args, **options):
        source = options['source']
        base_url = options['url']
        
        self.stdout.write(f"Seeding profiles from source: {source}")
        
        if source == 'deployed':
            self.seed_from_deployed_api(base_url)
        elif source == 'sample':
            self.seed_sample_data()
        else:
            self.stdout.write(self.style.ERROR('Invalid source. Use "deployed" or "sample"'))
    
    def seed_from_deployed_api(self, base_url):
        """Fetch profiles from deployed API"""
        self.stdout.write(f"Fetching profiles from {base_url}...")
        
        try:
            # Fetch all profiles from deployed API (with large limit)
            response = requests.get(f"{base_url}/api/profiles/?limit=100", timeout=30)
            response.raise_for_status()
            
            data = response.json()
            profiles_data = data.get('data', [])
            
            self.stdout.write(f"Found {len(profiles_data)} profiles in deployed API")
            
            created_count = 0
            skipped_count = 0
            
            for profile_data in profiles_data:
                # Check if profile already exists locally
                if Profile.objects.filter(name=profile_data['name'].lower()).exists():
                    skipped_count += 1
                    continue
                
                # Determine age group if not provided
                age = profile_data.get('age', 30)
                if age <= 12:
                    age_group = "child"
                elif age <= 19:
                    age_group = "teenager"
                elif age <= 59:
                    age_group = "adult"
                else:
                    age_group = "senior"
                
                # Create profile locally
                Profile.objects.create(
                    name=profile_data['name'].lower(),
                    gender=profile_data.get('gender', 'unknown'),
                    gender_probability=profile_data.get('gender_probability', 0.5),
                    sample_size=profile_data.get('sample_size', 1000),
                    age=age,
                    age_group=age_group,
                    country_id=profile_data.get('country_id', 'XX'),
                    country_name=profile_data.get('country_name', 'Unknown'),
                    country_probability=profile_data.get('country_probability', 0.5),
                )
                created_count += 1
                self.stdout.write(f"Created profile for {profile_data['name']}")
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Successfully seeded: {created_count} created, {skipped_count} skipped'
            ))
            self.stdout.write(f'Total profiles in local database: {Profile.objects.count()}')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching from deployed API: {str(e)}'))
            self.stdout.write('Falling back to sample data...')
            self.seed_sample_data()
    
    def seed_sample_data(self):
        """Create sample profiles for local testing"""
        self.stdout.write("Creating sample profiles...")
        
        # Sample countries with their codes and names
        countries = [
            ('NG', 'Nigeria'), ('KE', 'Kenya'), ('ZA', 'South Africa'), 
            ('GH', 'Ghana'), ('EG', 'Egypt'), ('MA', 'Morocco'),
            ('US', 'United States'), ('GB', 'United Kingdom'), ('CA', 'Canada'),
            ('IN', 'India'), ('BR', 'Brazil'), ('FR', 'France'),
            ('DE', 'Germany'), ('IT', 'Italy'), ('ES', 'Spain'),
            ('AO', 'Angola'), ('CM', 'Cameroon'), ('SN', 'Senegal'),
            ('TZ', 'Tanzania'), ('UG', 'Uganda')
        ]
        
        # Sample names with their typical gender mappings
        names_data = [
            # Male names
            ('emmanuel', 'male', 0.95, 1500), ('james', 'male', 0.98, 2000), ('john', 'male', 0.99, 5000),
            ('michael', 'male', 0.97, 4500), ('david', 'male', 0.96, 3800), ('joseph', 'male', 0.94, 3200),
            ('peter', 'male', 0.95, 2800), ('paul', 'male', 0.93, 2500), ('george', 'male', 0.92, 2100),
            ('daniel', 'male', 0.96, 3500), ('samuel', 'male', 0.94, 2900), ('benjamin', 'male', 0.93, 2600),
            ('oliver', 'male', 0.95, 3100), ('henry', 'male', 0.94, 2700), ('jack', 'male', 0.96, 3300),
            # Female names
            ('mary', 'female', 0.97, 4200), ('sarah', 'female', 0.98, 3900), ('elizabeth', 'female', 0.96, 4800),
            ('jane', 'female', 0.95, 3400), ('emily', 'female', 0.97, 4100), ('lisa', 'female', 0.94, 2900),
            ('anna', 'female', 0.96, 3700), ('maria', 'female', 0.95, 5600), ('grace', 'female', 0.97, 3100),
            ('joy', 'female', 0.94, 2400), ('faith', 'female', 0.96, 2800), ('hope', 'female', 0.93, 2200),
            ('chiamaka', 'female', 0.98, 3500), ('bose', 'female', 0.95, 3100), ('nneka', 'female', 0.96, 2700),
        ]
        
        created_count = 0
        skipped_count = 0
        
        for name, gender, gender_prob, sample_size in names_data:
            # Check if profile already exists
            if Profile.objects.filter(name=name).exists():
                skipped_count += 1
                continue
            
            # Random age based on distribution
            age_choices = list(range(18, 65)) + list(range(25, 50)) * 3
            age = random.choice(age_choices)
            
            # Determine age group
            if age <= 12:
                age_group = "child"
            elif age <= 19:
                age_group = "teenager"
            elif age <= 59:
                age_group = "adult"
            else:
                age_group = "senior"
            
            # Random country
            country_code, country_name = random.choice(countries)
            
            # Random probabilities
            gender_probability = random.uniform(0.7, 0.99)
            country_probability = random.uniform(0.6, 0.95)
            
            # Create profile with sample_size
            Profile.objects.create(
                name=name,
                gender=gender,
                gender_probability=gender_probability,
                sample_size=sample_size,
                age=age,
                age_group=age_group,
                country_id=country_code,
                country_name=country_name,
                country_probability=country_probability,
            )
            created_count += 1
            self.stdout.write(f"Created profile for {name} - {age} years, {gender}, from {country_name}")
        
        # Generate additional random profiles
        additional_count = 50
        first_names = ['Alex', 'Chris', 'Pat', 'Jordan', 'Taylor', 'Morgan', 'Riley', 'Casey']
        last_names = ['Smith', 'Jones', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore']
        
        for i in range(additional_count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            name = f"{first}{last}".lower()
            
            if Profile.objects.filter(name=name).exists():
                continue
            
            gender = random.choice(['male', 'female'])
            age = random.randint(16, 70)
            
            if age <= 12:
                age_group = "child"
            elif age <= 19:
                age_group = "teenager"
            elif age <= 59:
                age_group = "adult"
            else:
                age_group = "senior"
            
            country_code, country_name = random.choice(countries)
            
            Profile.objects.create(
                name=name,
                gender=gender,
                gender_probability=random.uniform(0.6, 0.99),
                sample_size=random.randint(100, 5000),
                age=age,
                age_group=age_group,
                country_id=country_code,
                country_name=country_name,
                country_probability=random.uniform(0.5, 0.95),
            )
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully seeded sample data: {created_count} created, {skipped_count} skipped'
        ))
        self.stdout.write(f'Total profiles in database: {Profile.objects.count()}')