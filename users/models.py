from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, role='CUSTOMER'):
        user = self.model(phone_number=phone_number, role=role)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone_number, password=None):
        user = self.create_user(phone_number, password, role='ADMIN')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user

class User(AbstractBaseUser):
    ROLE_CHOICES = (
        ('CUSTOMER', 'Customer'),
        ('DEALER', 'Dealer'),
        ('ADMIN', 'Admin'),
    )

    phone_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()