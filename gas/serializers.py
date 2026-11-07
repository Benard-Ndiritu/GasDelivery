from rest_framework import serializers

from .models import GasInventory, GasType


class GasTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GasType
        fields = ['id', 'name', 'cylinder_size', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        name = attrs.get('name', getattr(self.instance, 'name', None))
        size = attrs.get('cylinder_size', getattr(self.instance, 'cylinder_size', None))
        duplicates = GasType.objects.filter(name__iexact=name, cylinder_size=size)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(f'{name} {size} already exists.')
        return attrs


class GasInventorySerializer(serializers.ModelSerializer):
    gas_type_name = serializers.CharField(source='gas_type.name', read_only=True)
    cylinder_size = serializers.CharField(source='gas_type.cylinder_size', read_only=True)
    dealer_name = serializers.CharField(source='dealer.name', read_only=True)
    price_refill = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    price_exchange = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)

    class Meta:
        model = GasInventory
        fields = [
            'id', 'dealer', 'dealer_name', 'gas_type', 'gas_type_name', 'cylinder_size',
            'price_refill', 'price_exchange', 'stock_available', 'updated_at',
        ]
        read_only_fields = ['id', 'dealer', 'updated_at']

    def validate(self, attrs):
        dealer = self.context.get('dealer') or getattr(self.instance, 'dealer', None)
        gas_type = attrs.get('gas_type')
        if dealer and gas_type:
            duplicates = GasInventory.objects.filter(dealer=dealer, gas_type=gas_type)
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {'gas_type': 'You already list this gas type. Update the existing item instead.'}
                )
        return attrs
