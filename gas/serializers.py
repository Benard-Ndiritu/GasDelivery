from rest_framework import serializers
from .models import GasType, GasInventory

class GasTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GasType
        fields = '__all__'
        read_only_fields = ['created_at']

class GasInventorySerializer(serializers.ModelSerializer):
    gas_type_name = serializers.CharField(source='gas_type.name', read_only=True)
    cylinder_size = serializers.CharField(source='gas_type.cylinder_size', read_only=True)
    dealer_name = serializers.CharField(source='dealer.name', read_only=True)

    class Meta:
        model = GasInventory
        fields = '__all__'
        read_only_fields = ['dealer', 'updated_at']