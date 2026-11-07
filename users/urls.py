from django.urls import path

from .views import (
    CurrentUser,
    ListUsers,
    LoginUser,
    LogoutUser,
    RefreshTokenView,
    RegisterUser,
    RequestPasswordResetOTP,
    ResetPassword,
    VerifyPasswordResetOTP,
)

urlpatterns = [
    path('register/', RegisterUser.as_view(), name='register'),
    path('login/', LoginUser.as_view(), name='login'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('logout/', LogoutUser.as_view(), name='logout'),
    path('me/', CurrentUser.as_view(), name='me'),
    path('request-otp/', RequestPasswordResetOTP.as_view(), name='request-otp'),
    path('verify-otp/', VerifyPasswordResetOTP.as_view(), name='verify-otp'),
    path('reset-password/', ResetPassword.as_view(), name='reset-password'),
    path('list/', ListUsers.as_view(), name='list-users'),
]
