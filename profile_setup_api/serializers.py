from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            'id', 'name', 'gender', 'gender_probability', 
            'sample_size', 'age', 'age_group', 'country_id', 
            'country_probability', 'created_at'
        ]
        read_only_fields = fields

class ProfileListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    gender = serializers.CharField()
    age = serializers.IntegerField()
    age_group = serializers.CharField()
    country_id = serializers.CharField()