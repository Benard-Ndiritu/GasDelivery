import logging
import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from dealers.models import DealerProfile

from .models import PasswordResetOTP, User
from .permissions import IsAdmin
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    RequestOTPSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    VerifyOTPSerializer,
    check_password_strength,
)

logger = logging.getLogger(__name__)

INVALID_OTP = 'Invalid or expired OTP.'


def _error(message, code):
    return Response({'error': message}, status=code)


class RegisterUser(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'


class LoginUser(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number'].strip()
        password = serializer.validated_data['password']

        user = User.objects.filter(phone_number=phone).first()
        if user is None or not user.check_password(password):
            return _error('Invalid credentials', status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return _error('This account has been deactivated.', status.HTTP_403_FORBIDDEN)

        dealer_id = None
        if user.role == 'DEALER':
            dealer = DealerProfile.objects.filter(user=user).first()
            if dealer is None:
                return _error('No dealer application found for this account.', status.HTTP_403_FORBIDDEN)
            if dealer.status == 'PENDING':
                return _error('Your dealer application is still pending approval.', status.HTTP_403_FORBIDDEN)
            if dealer.status == 'REJECTED':
                return _error('Your dealer application has been rejected.', status.HTTP_403_FORBIDDEN)
            if not dealer.is_active:
                return _error('Your dealer account has been deactivated.', status.HTTP_403_FORBIDDEN)
            dealer_id = dealer.id

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': user.role,
            'phone_number': user.phone_number,
            'dealer_id': dealer_id,
        })


class RefreshTokenView(TokenRefreshView):
    """POST {"refresh": "..."} -> {"access": "...", "refresh": "..."} (refresh tokens rotate)."""

    throttle_scope = 'auth'


class LogoutUser(APIView):
    """Blacklist the given refresh token so it can no longer be used."""

    # Possessing the refresh token is the proof needed; the access token may have expired.
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        token = request.data.get('refresh')
        if not token:
            return _error('refresh token is required', status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            pass  # Already invalid or expired: the outcome is the same.
        return Response({'message': 'Logged out'})


class CurrentUser(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class RequestPasswordResetOTP(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'otp'

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # Same response whether or not the account exists, so emails can't be enumerated.
        response = Response({'message': 'If an account with that email exists, an OTP has been sent.'})

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            return response

        otp = f'{secrets.randbelow(1_000_000):06d}'
        with transaction.atomic():
            PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
            PasswordResetOTP.objects.create(user=user, otp=otp)

        try:
            send_mail(
                subject='Your password reset code',
                message=(
                    f'Your password reset code is: {otp}\n\n'
                    f'It expires in {settings.PASSWORD_RESET_OTP_MINUTES} minutes. '
                    'Do not share it with anyone. If you did not request this, ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except Exception:
            logger.exception('Failed to send password reset email')
            return _error('Could not send the email right now. Please try again later.',
                          status.HTTP_503_SERVICE_UNAVAILABLE)
        return response


def _check_otp(email, otp):
    """Return the matching active OTP record, or None. Counts failed attempts."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return None
    with transaction.atomic():
        record = (
            PasswordResetOTP.objects.select_for_update()
            .filter(user=user, is_used=False)
            .order_by('-created_at')
            .first()
        )
        if record is None or not record.is_valid():
            return None
        if not secrets.compare_digest(record.otp, otp):
            record.attempts += 1
            if record.attempts >= settings.PASSWORD_RESET_OTP_MAX_ATTEMPTS:
                record.is_used = True
            record.save(update_fields=['attempts', 'is_used'])
            return None
    return record


class VerifyPasswordResetOTP(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if _check_otp(serializer.validated_data['email'], serializer.validated_data['otp']) is None:
            return _error(INVALID_OTP, status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'OTP verified successfully'})


class ResetPassword(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record = _check_otp(data['email'], data['otp'])
        if record is None:
            return _error(INVALID_OTP, status.HTTP_400_BAD_REQUEST)

        user = record.user
        check_password_strength(data['new_password'], user, field='new_password')

        with transaction.atomic():
            user.set_password(data['new_password'])
            user.save(update_fields=['password'])
            record.is_used = True
            record.save(update_fields=['is_used'])

        return Response({'message': 'Password reset successfully'})


class ListUsers(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role.upper())
        return queryset
