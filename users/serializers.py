from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'role', 'created_at']
        extra_kwargs = {
            'role': {'default': 'CUSTOMER'}
        }

    def create(self, validated_data):
        return User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            role=validated_data.get('role', 'CUSTOMER')
        )

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField()