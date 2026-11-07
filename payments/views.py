import logging

from django.conf import settings
from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from users.permissions import IsAdmin, IsApprovedDealer, IsCustomer

from .models import Payment
from .serializers import InitiatePaymentSerializer, MpesaSTKSerializer, PaymentSerializer
from .services import (
    PAYABLE_ORDER_STATUSES,
    PaymentError,
    confirm_cash_payment,
    handle_stk_callback,
    refresh_mpesa_status,
    start_mpesa_payment,
)

logger = logging.getLogger(__name__)

STK_SENT_MESSAGE = 'STK Push sent to your phone. Enter M-Pesa PIN to complete payment.'


def _error(exc):
    return Response({'error': exc.message}, status=exc.status_code)


class MpesaSTKPushView(APIView):
    """Customer pays an order with M-Pesa: sends the STK prompt to their phone."""

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = MpesaSTKSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, result = start_mpesa_payment(
                serializer.validated_data['order_id'],
                request.user,
                serializer.validated_data.get('phone_number') or None,
            )
        except PaymentError as exc:
            return _error(exc)
        return Response({
            'message': STK_SENT_MESSAGE,
            'checkout_request_id': payment.checkout_request_id,
            'payment': PaymentSerializer(payment).data,
        })


class InitiatePaymentView(APIView):
    """
    Customer chooses how to pay. MPESA sends an STK push; CASH records a pending
    cash payment that the dealer confirms on delivery.
    """

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data['method'] == 'MPESA':
            try:
                payment, _ = start_mpesa_payment(data['order_id'], request.user, data.get('phone_number') or None)
            except PaymentError as exc:
                return _error(exc)
            return Response({'message': STK_SENT_MESSAGE, **PaymentSerializer(payment).data},
                            status=status.HTTP_201_CREATED)

        with transaction.atomic():
            order = Order.objects.select_for_update().filter(id=data['order_id'], customer=request.user).first()
            if order is None:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
            if order.status not in PAYABLE_ORDER_STATUSES:
                return Response({'error': 'Order is not payable'}, status=status.HTTP_400_BAD_REQUEST)
            payment = Payment.objects.filter(order=order).first()
            if payment and payment.status == 'PAID':
                return Response({'error': 'This order has already been paid'}, status=status.HTTP_400_BAD_REQUEST)
            payment = payment or Payment(order=order)
            payment.method, payment.status, payment.amount = 'CASH', 'PENDING', order.total
            payment.checkout_request_id = None
            payment.save()

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class MpesaPaymentCallback(APIView):
    """Called by Safaricom. Always acknowledges, so Daraja doesn't retry forever."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request, token=None):
        expected = settings.MPESA_CALLBACK_TOKEN
        if expected and not constant_time_compare(token or '', expected):
            logger.warning('Rejected M-Pesa callback with a bad token')
            return Response({'ResultCode': 1, 'ResultDesc': 'Rejected'}, status=status.HTTP_403_FORBIDDEN)

        try:
            stk_callback = request.data['Body']['stkCallback']
        except (KeyError, TypeError):
            logger.warning('Malformed M-Pesa callback: %s', request.data)
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        try:
            handle_stk_callback(stk_callback)
        except Exception:
            logger.exception('Error processing M-Pesa callback')
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


class CashPaymentConfirm(APIView):
    """Dealer confirms cash was received; this also completes the order."""

    permission_classes = [IsApprovedDealer]

    def post(self, request, order_id):
        try:
            payment = confirm_cash_payment(order_id, request.user.dealerprofile)
        except PaymentError as exc:
            return _error(exc)
        return Response(PaymentSerializer(payment).data)


class PaymentStatusView(APIView):
    """Payment for an order, visible to its customer, its dealer, or an admin."""

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        user = request.user
        payments = Payment.objects.select_related('order')
        if user.role == 'CUSTOMER':
            payments = payments.filter(order__customer=user)
        elif user.role == 'DEALER':
            payments = payments.filter(order__dealer__user=user)
        elif user.role != 'ADMIN':
            payments = payments.none()

        payment = payments.filter(order_id=order_id).first()
        if payment is None:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        payment = refresh_mpesa_status(payment)
        return Response(PaymentSerializer(payment).data)


class ListAllPayments(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Payment.objects.select_related('order').order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset
