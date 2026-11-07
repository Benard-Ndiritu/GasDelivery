from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User
from .validators import validate_phone_number


def check_password_strength(password, user=None, field='password'):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({field: list(exc.messages)})


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of a user (admin listings, /me)."""

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'role', 'is_active', 'created_at']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public customer sign-up. The role is always CUSTOMER; dealers apply through
    /api/dealers/apply/ and admins are created with the create_admin command.
    """

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'password', 'role', 'created_at']
        read_only_fields = ['role', 'created_at']
        # Uniqueness is checked in validate_phone_number with a clearer message.
        extra_kwargs = {'phone_number': {'validators': []}}

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
        check_password_strength(attrs['password'], User(phone_number=attrs.get('phone_number'), email=attrs.get('email')))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            email=validated_data.get('email'),
            role='CUSTOMER',
        )


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.RegexField(r'^\d{6}$', error_messages={'invalid': 'OTP must be 6 digits.'})


class ResetPasswordSerializer(VerifyOTPSerializer):
    new_password = serializers.CharField(trim_whitespace=False)
