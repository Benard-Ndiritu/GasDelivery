from django.db import transaction
from rest_framework import serializers

from users.models import User
from users.serializers import check_password_strength
from users.validators import validate_phone_number

from .models import DealerProfile


class DealerProfileSerializer(serializers.ModelSerializer):
    """
    Dealer profile as seen by the dealer and the admin. `status` and `is_active`
    can only be changed by an admin through the application action endpoint.
    """

    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = DealerProfile
        fields = [
            'id', 'user', 'email', 'name', 'shop_name', 'phone_number',
            'latitude', 'longitude', 'delivery_radius', 'status', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'email', 'status', 'is_active', 'created_at', 'updated_at']
        extra_kwargs = {
            'latitude': {'min_value': -90, 'max_value': 90},
            'longitude': {'min_value': -180, 'max_value': 180},
        }


class DealerApplicationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    name = serializers.CharField(max_length=255)
    shop_name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    latitude = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    longitude = serializers.FloatField(min_value=-180, max_value=180, required=False, allow_null=True)
    delivery_radius = serializers.ChoiceField(choices=DealerProfile.RADIUS_CHOICES, default=5)

    def validate_phone_number(self, value):
        value = validate_phone_number(value)
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value

    def validate_email(self, value):
        if not value:
            return None
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, attrs):
        check_password_strength(
            attrs['password'],
            User(phone_number=attrs['phone_number'], email=attrs.get('email')),
        )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data.get('email'),
            role='DEALER',
        )
        return DealerProfile.objects.create(
            user=user,
            name=validated_data['name'],
            shop_name=validated_data['shop_name'],
            phone_number=validated_data['phone_number'],
            latitude=validated_data.get('latitude') or 0.0,
            longitude=validated_data.get('longitude') or 0.0,
            delivery_radius=validated_data['delivery_radius'],
            status='PENDING',
        )
