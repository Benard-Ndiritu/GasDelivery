from django.urls import path
from .views import MpesaPaymentCallback, CashPaymentConfirm

urlpatterns = [
    path('mpesa-callback/', MpesaPaymentCallback.as_view()),
    path('cash-confirm/<int:order_id>/', CashPaymentConfirm.as_view()),
]
