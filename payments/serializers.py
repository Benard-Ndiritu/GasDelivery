from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order_id', 'method', 'amount', 'status', 'mpesa_receipt', 'created_at']
        read_only_fields = ['status', 'mpesa_receipt', 'created_at']