from . import views
from django.urls import path
from .views import RegisterUser, LoginUser, RequestPasswordResetOTP, VerifyPasswordResetOTP, ResetPassword



urlpatterns = [
    path("register/", RegisterUser.as_view(), name="register"),
    path("login/", LoginUser.as_view(), name="login"),
    path("request-otp/", RequestPasswordResetOTP.as_view(), name="request-otp"),
    path("verify-otp/", VerifyPasswordResetOTP.as_view(), name="verify-otp"),
    path("reset-password/", ResetPassword.as_view(), name="reset-password"),
]