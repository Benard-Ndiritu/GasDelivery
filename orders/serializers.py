from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    dealer_id = serializers.IntegerField(read_only=True)
    dealer_name = serializers.CharField(source='dealer.name', read_only=True, default=None)
    shop_name = serializers.CharField(source='dealer.shop_name', read_only=True, default=None)
    dealer_phone = serializers.CharField(source='dealer.phone_number', read_only=True, default=None)
    gas_type_id = serializers.IntegerField(read_only=True)
    gas_type_name = serializers.CharField(source='gas_type.name', read_only=True, default=None)
    cylinder_size = serializers.CharField(source='gas_type.cylinder_size', read_only=True, default=None)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer_phone',
            'dealer_id', 'dealer_name', 'shop_name', 'dealer_phone',
            'gas_type_id', 'gas_type_name', 'cylinder_size',
            'order_type', 'status', 'price', 'delivery_fee', 'total',
            'payment_status', 'payment_method',
            'customer_latitude', 'customer_longitude',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    @staticmethod
    def _payment(order):
        return getattr(order, 'payment', None)

    def get_payment_status(self, order):
        payment = self._payment(order)
        return payment.status if payment else None

    def get_payment_method(self, order):
        payment = self._payment(order)
        return payment.method if payment else None


class PlaceOrderSerializer(serializers.Serializer):
    gas_type_id = serializers.IntegerField()
    order_type = serializers.ChoiceField(choices=Order.ORDER_TYPE_CHOICES)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
