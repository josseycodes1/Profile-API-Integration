import logging
import requests
from typing import Dict, Any, Tuple
from django.core.cache import cache

logger = logging.getLogger(__name__)

class ExternalAPIService:
    """Service to handle external API calls with error handling"""
    
    GENDERIZE_URL = "https://api.genderize.io"
    AGIFY_URL = "https://api.agify.io"
    NATIONALIZE_URL = "https://api.nationalize.io"
    
    @staticmethod
    def get_age_group(age: int) -> str:
        """Determine age group based on age"""
        if age <= 12:
            return "child"
        elif age <= 19:
            return "teenager"
        elif age <= 59:
            return "adult"
        else:
            return "senior"
    
    @staticmethod
    def fetch_gender_data(name: str) -> Tuple[Dict[str, Any], bool]:
        """Fetch gender data from Genderize API"""
        try:
            logger.info(f"Fetching gender data for name: {name}")
            response = requests.get(
                f"{ExternalAPIService.GENDERIZE_URL}",
                params={"name": name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('gender') is None or data.get('count', 0) == 0:
                logger.error(f"Invalid gender response for {name}: {data}")
                return None, False
            
            logger.info(f"Successfully fetched gender data for {name}")
            return {
                'gender': data['gender'],
                'gender_probability': data.get('probability', 0),
                'sample_size': data.get('count', 0)
            }, True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Genderize API error for {name}: {str(e)}")
            return None, False
        except Exception as e:
            logger.error(f"Unexpected error in gender fetch for {name}: {str(e)}")
            return None, False
    
    @staticmethod
    def fetch_age_data(name: str) -> Tuple[Dict[str, Any], bool]:
        """Fetch age data from Agify API"""
        try:
            logger.info(f"Fetching age data for name: {name}")
            response = requests.get(
                f"{ExternalAPIService.AGIFY_URL}",
                params={"name": name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('age') is None:
                logger.error(f"Invalid age response for {name}: {data}")
                return None, False
            
            age = data['age']
            age_group = ExternalAPIService.get_age_group(age)
            
            logger.info(f"Successfully fetched age data for {name}: age={age}, group={age_group}")
            return {
                'age': age,
                'age_group': age_group
            }, True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Agify API error for {name}: {str(e)}")
            return None, False
        except Exception as e:
            logger.error(f"Unexpected error in age fetch for {name}: {str(e)}")
            return None, False
    
    @staticmethod
    def fetch_nationality_data(name: str) -> Tuple[Dict[str, Any], bool]:
        """Fetch nationality data from Nationalize API"""
        try:
            logger.info(f"Fetching nationality data for name: {name}")
            response = requests.get(
                f"{ExternalAPIService.NATIONALIZE_URL}",
                params={"name": name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            country_data = data.get('country', [])
            if not country_data or len(country_data) == 0:
                logger.error(f"Invalid nationality response for {name}: No country data")
                return None, False
            
            top_country = max(country_data, key=lambda x: x.get('probability', 0))
            
            logger.info(f"Successfully fetched nationality data for {name}: country={top_country['country_id']}")
            return {
                'country_id': top_country['country_id'],
                'country_probability': top_country.get('probability', 0)
            }, True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Nationalize API error for {name}: {str(e)}")
            return None, False
        except Exception as e:
            logger.error(f"Unexpected error in nationality fetch for {name}: {str(e)}")
            return None, False
    
    @staticmethod
    def fetch_all_data(name: str) -> Dict[str, Any]:
        """Fetch data from all three APIs"""
        logger.info(f"Starting external API calls for name: {name}")
       
        gender_data, gender_success = ExternalAPIService.fetch_gender_data(name)
        if not gender_success:
            logger.error(f"Gender API failed for {name}")
            raise ValueError("Genderize returned an invalid response")
        
        age_data, age_success = ExternalAPIService.fetch_age_data(name)
        if not age_success:
            logger.error(f"Age API failed for {name}")
            raise ValueError("Agify returned an invalid response")
        
        nationality_data, nationality_success = ExternalAPIService.fetch_nationality_data(name)
        if not nationality_success:
            logger.error(f"Nationality API failed for {name}")
            raise ValueError("Nationalize returned an invalid response")
        
        combined_data = {
            **gender_data,
            **age_data,
            **nationality_data
        }
        
        logger.info(f"Successfully fetched all data for {name}: {combined_data}")
        return combined_data