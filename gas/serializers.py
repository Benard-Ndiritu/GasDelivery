# gas/serializers.py
from rest_framework import serializers
from .models import GasType, GasInventory  # make sure these models exist

class GasTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GasType
        fields = '__all__'

class GasInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GasInventory
        fields = '__all__'
