from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterUser(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginUser(APIView):
    def post(self, request):
        # Placeholder for JWT login logic
        return Response({"message": "JWT login placeholder"})
    


# Customer & Dealer Registration
class RegisterUser(generics.CreateAPIView):
    serializer_class = UserSerializer

# JWT Login
class LoginUser(generics.GenericAPIView):
    serializer_class = UserSerializer

    def post(self, request):
        phone = request.data.get("phone_number")
        password = request.data.get("password")
        try:
            user = User.objects.get(phone_number=phone)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "role": user.role
                })
        except User.DoesNotExist:
            pass
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

