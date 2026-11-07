from django.contrib import admin

from .models import PasswordResetOTP, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'email', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('phone_number', 'email')
    readonly_fields = ('password', 'last_login', 'created_at')
    ordering = ('-created_at',)


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'is_used', 'attempts')
    exclude = ('otp',)
    readonly_fields = ('user', 'created_at', 'is_used', 'attempts')
