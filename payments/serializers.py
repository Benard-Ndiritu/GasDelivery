from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'method', 'amount', 'status', 'mpesa_receipt',
            'phone_number', 'result_desc', 'paid_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class InitiatePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS, default='MPESA')
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=15)


class MpesaSTKSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=15)
