from rest_framework import serializers
from .models import DealerProfile

class DealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
