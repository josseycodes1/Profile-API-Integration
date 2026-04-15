import uuid
import time
from django.db import models

def generate_uuid7():
    """Generate UUID v7 compatible ID using timestamp and random bits"""
    # Get current timestamp in milliseconds (48 bits for UUID v7)
    timestamp_ms = int(time.time() * 1000)
    
    # Generate random 80 bits (UUID v7 uses 74-80 bits of randomness)
    random_part = uuid.uuid4().int & ((1 << 80) - 1)
    
    # Combine: timestamp in first 48 bits, random in remaining 80 bits
    # Shift timestamp left by 80 bits, then OR with random part
    uuid_int = (timestamp_ms << 80) | random_part
    
    # Ensure we don't exceed 128 bits (max for UUID)
    uuid_int &= (1 << 128) - 1
    
    return uuid.UUID(int=uuid_int)

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=generate_uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    gender = models.CharField(max_length=20)
    gender_probability = models.FloatField()
    sample_size = models.IntegerField()
    age = models.IntegerField()
    age_group = models.CharField(max_length=20)
    country_id = models.CharField(max_length=10)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.age_group}"