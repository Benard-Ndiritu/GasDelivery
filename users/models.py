from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, role='CUSTOMER', email=None, **extra_fields):
        if not phone_number:
            raise ValueError('A phone number is required.')
        user = self.model(
            phone_number=phone_number,
            role=role,
            email=self.normalize_email(email) or None,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.pop('role', None)
        return self.create_user(phone_number, password, role='ADMIN', **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('CUSTOMER', 'Customer'),
        ('DEALER', 'Dealer'),
        ('ADMIN', 'Admin'),
    )

    phone_number = models.CharField(max_length=15, unique=True, primary_key=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f'{self.phone_number} ({self.role})'


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    def is_expired(self):
        return timezone.now() >= self.created_at + timedelta(minutes=settings.PASSWORD_RESET_OTP_MINUTES)

    def is_valid(self):
        return not self.is_used and not self.is_expired()

    def __str__(self):
        return f'OTP for {self.user.phone_number}'
