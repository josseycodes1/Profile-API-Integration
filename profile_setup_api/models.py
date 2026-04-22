import uuid
import time
from django.db import models

def generate_uuid7():
    """Generate UUID v7 compatible ID using timestamp and random bits"""
    timestamp_ms = int(time.time() * 1000)
    random_part = uuid.uuid4().int & ((1 << 80) - 1)
    uuid_int = (timestamp_ms << 80) | random_part
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
    country_name = models.CharField(max_length=100, default='')
    country_probability = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.age_group}"