from rest_framework import serializers
from .models import Order

class OrderSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    dealer_name = serializers.CharField(source='dealer.name', read_only=True)
    gas_type_name = serializers.CharField(source='gas_type.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_phone', 'dealer_name', 'gas_type_name',
            'order_type', 'status', 'price', 'delivery_fee',
            'customer_latitude', 'customer_longitude',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'price', 'delivery_fee', 'created_at', 'updated_at']