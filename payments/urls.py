from django.urls import path

from .views import (
    CashPaymentConfirm,
    InitiatePaymentView,
    ListAllPayments,
    MpesaPaymentCallback,
    MpesaSTKPushView,
    PaymentStatusView,
)

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view()),
    path('mpesa-stk/', MpesaSTKPushView.as_view()),
    path('mpesa-callback/', MpesaPaymentCallback.as_view()),
    path('mpesa-callback/<str:token>/', MpesaPaymentCallback.as_view()),
    path('cash-confirm/<int:order_id>/', CashPaymentConfirm.as_view()),
    path('status/<int:order_id>/', PaymentStatusView.as_view()),
    path('all/', ListAllPayments.as_view()),
]
