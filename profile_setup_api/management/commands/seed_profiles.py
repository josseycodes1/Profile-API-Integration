import random

import requests
from django.core.management.base import BaseCommand

from profile_setup_api.models import Profile


class Command(BaseCommand):
    help = "Seed database with profiles from deployed API or deterministic sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            help="Source to fetch profiles from: deployed or sample",
            default="sample",
        )
        parser.add_argument(
            "--url",
            type=str,
            help="Custom API URL to fetch profiles from",
            default="https://rofile--ntegration-adewumijosephine3516-kodp7ruz.leapcell.dev",
        )
        parser.add_argument(
            "--count",
            type=int,
            help="Number of sample profiles to ensure in the database",
            default=100,
        )

    def handle(self, *args, **options):
        source = options["source"]
        base_url = options["url"]
        count = options["count"]

        self.stdout.write(f"Seeding profiles from source: {source}")

        if source == "deployed":
            self.seed_from_deployed_api(base_url)
        elif source == "sample":
            self.seed_sample_data(count)
        else:
            self.stdout.write(self.style.ERROR('Invalid source. Use "deployed" or "sample"'))

    def seed_from_deployed_api(self, base_url):
        """Fetch profiles from deployed API."""
        self.stdout.write(f"Fetching profiles from {base_url}...")

        try:
            response = requests.get(
                f"{base_url}/api/profiles/?limit=100",
                headers={"X-API-Version": "1"},
                timeout=30,
            )
            response.raise_for_status()
            profiles_data = response.json().get("data", [])

            created_count = 0
            updated_count = 0

            for profile_data in profiles_data:
                age = profile_data.get("age", 30)
                _, created = Profile.objects.update_or_create(
                    name=profile_data["name"].lower(),
                    defaults={
                        "gender": profile_data.get("gender", "unknown"),
                        "gender_probability": profile_data.get("gender_probability", 0.5),
                        "sample_size": profile_data.get("sample_size", 1000),
                        "age": age,
                        "age_group": self.age_group_for(age),
                        "country_id": profile_data.get("country_id", "XX"),
                        "country_name": profile_data.get("country_name", "Unknown"),
                        "country_probability": profile_data.get("country_probability", 0.5),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Seeded from deployed API: {created_count} created, {updated_count} updated"
                )
            )
            self.stdout.write(f"Total profiles in database: {Profile.objects.count()}")
        except requests.exceptions.RequestException as exc:
            self.stdout.write(self.style.ERROR(f"Error fetching from deployed API: {exc}"))
            self.stdout.write("Falling back to sample data...")
            self.seed_sample_data(100)

    def seed_sample_data(self, count=100):
        """Create deterministic sample profiles for NLP search demos."""
        random.seed(2026)
        self.stdout.write(f"Creating {count} sample profiles...")

        countries = [
            ("NG", "Nigeria"),
            ("KE", "Kenya"),
            ("ZA", "South Africa"),
            ("GH", "Ghana"),
            ("EG", "Egypt"),
            ("MA", "Morocco"),
            ("US", "United States"),
            ("GB", "United Kingdom"),
            ("CA", "Canada"),
            ("IN", "India"),
            ("BR", "Brazil"),
            ("FR", "France"),
            ("DE", "Germany"),
            ("IT", "Italy"),
            ("ES", "Spain"),
            ("AO", "Angola"),
            ("CM", "Cameroon"),
            ("SN", "Senegal"),
            ("TZ", "Tanzania"),
            ("UG", "Uganda"),
            ("ET", "Ethiopia"),
            ("RW", "Rwanda"),
            ("JP", "Japan"),
            ("CN", "China"),
            ("AU", "Australia"),
        ]

        male_names = [
            "emmanuel", "james", "john", "michael", "david", "joseph",
            "peter", "paul", "george", "daniel", "samuel", "benjamin",
            "oliver", "henry", "jack", "alex", "chris", "jordan",
            "taylor", "morgan", "riley", "casey", "victor", "felix",
            "isaac", "gabriel", "noah", "liam", "ethan", "mason",
            "logan", "lucas", "owen", "caleb", "aaron", "brian",
            "kevin", "mark", "stephen", "thomas", "andrew", "francis",
            "kofi", "kwame", "ade", "tunde", "kamau", "kojo", "sipho",
            "hassan",
        ]
        female_names = [
            "mary", "sarah", "elizabeth", "jane", "emily", "lisa",
            "anna", "maria", "grace", "joy", "faith", "hope",
            "chiamaka", "bose", "nneka", "adeola", "amina", "zainab",
            "fatima", "aisha", "sophia", "olivia", "emma", "ava",
            "mia", "isabella", "charlotte", "amelia", "harper", "ella",
            "abena", "akosua", "nyambura", "wambui", "thandi", "lerato",
            "nandi", "lindiwe", "yara", "lucia", "claire", "camille",
            "sofia", "giulia", "ines", "hana", "mei", "priya",
            "anika", "maya",
        ]
        age_bands = [8, 17, 21, 28, 37, 48, 64]

        curated_profiles = [
            ("young_ng_male_01", "male", 21, "NG", "Nigeria", 0.96, 0.91),
            ("young_ng_male_02", "male", 23, "NG", "Nigeria", 0.94, 0.88),
            ("young_ng_female_01", "female", 22, "NG", "Nigeria", 0.97, 0.90),
            ("adult_ke_male_01", "male", 34, "KE", "Kenya", 0.95, 0.87),
            ("adult_ke_male_02", "male", 45, "KE", "Kenya", 0.91, 0.84),
            ("senior_gh_female_01", "female", 66, "GH", "Ghana", 0.93, 0.83),
            ("child_us_female_01", "female", 8, "US", "United States", 0.90, 0.80),
            ("teen_za_male_01", "male", 17, "ZA", "South Africa", 0.92, 0.86),
            ("confident_fr_female_01", "female", 31, "FR", "France", 0.89, 0.86),
            ("low_confidence_br_male_01", "male", 29, "BR", "Brazil", 0.55, 0.52),
        ]

        desired_profiles = []

        def save_profile(name, gender, age, country_code, country_name, gender_probability, country_probability):
            desired_profiles.append(
                {
                    "name": name,
                    "gender": gender,
                    "gender_probability": round(gender_probability, 2),
                    "sample_size": random.randint(500, 5000),
                    "age": age,
                    "age_group": self.age_group_for(age),
                    "country_id": country_code,
                    "country_name": country_name,
                    "country_probability": round(country_probability, 2),
                }
            )

        for profile in curated_profiles[:count]:
            save_profile(*profile)

        generated = len(curated_profiles)
        while generated < count:
            gender = "male" if generated % 2 == 0 else "female"
            names = male_names if gender == "male" else female_names
            base_name = names[generated % len(names)]
            country_code, country_name = countries[generated % len(countries)]
            age = age_bands[generated % len(age_bands)]
            name = f"{base_name}_{country_code.lower()}_{generated + 1:03d}"

            save_profile(
                name,
                gender,
                age,
                country_code,
                country_name,
                random.uniform(0.72, 0.99),
                random.uniform(0.62, 0.96),
            )
            generated += 1

        names = [profile["name"] for profile in desired_profiles]
        existing = Profile.objects.in_bulk(names, field_name="name")
        to_create = []
        to_update = []

        for data in desired_profiles:
            profile = existing.get(data["name"])
            if profile:
                for field, value in data.items():
                    if field != "name":
                        setattr(profile, field, value)
                to_update.append(profile)
            else:
                to_create.append(Profile(**data))

        if to_create:
            Profile.objects.bulk_create(to_create, batch_size=100)
        if to_update:
            Profile.objects.bulk_update(
                to_update,
                [
                    "gender",
                    "gender_probability",
                    "sample_size",
                    "age",
                    "age_group",
                    "country_id",
                    "country_name",
                    "country_probability",
                ],
                batch_size=100,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded sample data: {len(to_create)} created, {len(to_update)} updated"
            )
        )
        self.stdout.write(f"Total profiles in database: {Profile.objects.count()}")

    def age_group_for(self, age):
        if age <= 12:
            return "child"
        if age <= 19:
            return "teenager"
        if age <= 59:
            return "adult"
        return "senior"
