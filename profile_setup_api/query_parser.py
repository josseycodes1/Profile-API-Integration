import re
import logging

logger = logging.getLogger(__name__)

class NaturalLanguageParser:
    """Parse natural language queries into filter parameters"""
    
    # Age group mappings
    AGE_GROUPS = {
        'child': (0, 12),
        'teenager': (13, 19),
        'teen': (13, 19),
        'teens': (13, 19),
        'adult': (20, 59),
        'adults': (20, 59),
        'senior': (60, 150),
        'seniors': (60, 150),
        'elderly': (60, 150),
        'old': (60, 150),
        'young': (16, 24),  # Special mapping for "young"
        'youth': (15, 25),
        'middle aged': (35, 55),
        'middle-aged': (35, 55),
    }
    
    # Gender keywords
    GENDER_KEYWORDS = {
        'male': ['male', 'man', 'men', 'boy', 'boys', 'gentleman', 'gentlemen', 'males'],
        'female': ['female', 'woman', 'women', 'girl', 'girls', 'lady', 'ladies', 'females'],
    }
    
    # Age comparison operators
    AGE_OPERATORS = {
        'above': ('min_age', lambda x: x),
        'over': ('min_age', lambda x: x),
        'greater than': ('min_age', lambda x: x),
        'older than': ('min_age', lambda x: x),
        'below': ('max_age', lambda x: x),
        'under': ('max_age', lambda x: x),
        'less than': ('max_age', lambda x: x),
        'younger than': ('max_age', lambda x: x),
    }
    
    @classmethod
    def parse(cls, query: str) -> dict:
        """
        Parse natural language query and return filter parameters
        Returns: dict with filters or error
        """
        if not query or not query.strip():
            return {'error': 'Empty query'}
        
        query = query.lower().strip()
        filters = {}
        
        # Extract gender
        gender = cls._extract_gender(query)
        if gender:
            filters['gender'] = gender
        
        # Extract age group
        age_group = cls._extract_age_group(query)
        if age_group:
            filters['age_group'] = age_group
        
        # Extract age range
        age_range = cls._extract_age_range(query)
        if age_range:
            if 'min_age' in age_range:
                filters['min_age'] = age_range['min_age']
            if 'max_age' in age_range:
                filters['max_age'] = age_range['max_age']
        
        # Extract country
        country = cls._extract_country(query)
        if country:
            filters['country_id'] = country.upper()
        
        # Extract probability filters
        prob_filters = cls._extract_probability(query)
        filters.update(prob_filters)
        
        # If no filters extracted, return error
        if not filters:
            return {'error': 'Unable to interpret query'}
        
        return filters
    
    @classmethod
    def _extract_gender(cls, query: str) -> str:
        """Extract gender from query"""
        for gender, keywords in cls.GENDER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query:
                    return gender
        return None
    
    @classmethod
    def _extract_age_group(cls, query: str) -> str:
        """Extract age group from query"""
        # First check for specific age group keywords
        for group, (min_age, max_age) in cls.AGE_GROUPS.items():
            if group in query:
                # Don't return 'young' as age_group (it's not a stored group)
                if group == 'young':
                    continue
                return group
        
        # Check for "teen" related terms
        if 'teen' in query or 'adolescent' in query:
            return 'teenager'
        
        # Check for "child" related terms
        if 'child' in query or 'kid' in query or 'children' in query:
            return 'child'
        
        return None
    
    @classmethod
    def _extract_age_range(cls, query: str) -> dict:
        """Extract age range from query"""
        filters = {}
        
        # Check for "young" which maps to 16-24
        if 'young' in query and not 'younger' in query:
            filters['min_age'] = 16
            filters['max_age'] = 24
        
        # Pattern: above X, over X, older than X
        above_pattern = r'(?:above|over|older than|greater than)\s+(\d{1,3})'
        match = re.search(above_pattern, query)
        if match:
            filters['min_age'] = int(match.group(1))
        
        # Pattern: below X, under X, younger than X
        below_pattern = r'(?:below|under|younger than|less than)\s+(\d{1,3})'
        match = re.search(below_pattern, query)
        if match:
            filters['max_age'] = int(match.group(1))
        
        # Pattern: between X and Y
        between_pattern = r'between\s+(\d{1,3})\s+and\s+(\d{1,3})'
        match = re.search(between_pattern, query)
        if match:
            filters['min_age'] = int(match.group(1))
            filters['max_age'] = int(match.group(2))
        
        # Pattern: ages X to Y
        to_pattern = r'(\d{1,3})\s+to\s+(\d{1,3})'
        match = re.search(to_pattern, query)
        if match:
            filters['min_age'] = int(match.group(1))
            filters['max_age'] = int(match.group(2))
        
        # If age group was detected, apply its range (unless specific ages were given)
        if not filters:
            for group, (min_age, max_age) in cls.AGE_GROUPS.items():
                if group in query and group != 'young':
                    filters['min_age'] = min_age
                    filters['max_age'] = max_age
                    break
        
        return filters
    
    @classmethod
    def _extract_country(cls, query: str) -> str:
        """Extract country from query"""
        # Common country mappings
        country_map = {
            'nigeria': 'NG',
            'ghana': 'GH',
            'kenya': 'KE',
            'south africa': 'ZA',
            'egypt': 'EG',
            'morocco': 'MA',
            'algeria': 'DZ',
            'ethiopia': 'ET',
            'tanzania': 'TZ',
            'uganda': 'UG',
            'sudan': 'SD',
            'angola': 'AO',
            'mozambique': 'MZ',
            'zambia': 'ZM',
            'zimbabwe': 'ZW',
            'rwanda': 'RW',
            'cameroon': 'CM',
            'ivory coast': 'CI',
            'senegal': 'SN',
            'tunisia': 'TN',
            'united states': 'US',
            'usa': 'US',
            'uk': 'GB',
            'united kingdom': 'GB',
            'canada': 'CA',
            'australia': 'AU',
            'germany': 'DE',
            'france': 'FR',
            'spain': 'ES',
            'italy': 'IT',
            'japan': 'JP',
            'china': 'CN',
            'india': 'IN',
            'brazil': 'BR',
        }
        
        for country_name, country_code in country_map.items():
            if country_name in query:
                return country_code
        
        return None
    
    @classmethod
    def _extract_probability(cls, query: str) -> dict:
        """Extract probability filters from query"""
        filters = {}
        
        # High confidence
        if 'high confidence' in query or 'very confident' in query:
            filters['min_gender_probability'] = 0.8
            filters['min_country_probability'] = 0.8
        elif 'low confidence' in query or 'not confident' in query:
            filters['min_gender_probability'] = 0.0
            filters['min_country_probability'] = 0.0
        elif 'confident' in query:
            filters['min_gender_probability'] = 0.7
            filters['min_country_probability'] = 0.7
        
        # Specific probability patterns
        prob_pattern = r'probability\s+above\s+(\d+(?:\.\d+)?)'
        match = re.search(prob_pattern, query)
        if match:
            prob = float(match.group(1))
            filters['min_gender_probability'] = prob
            filters['min_country_probability'] = prob
        
        return filters