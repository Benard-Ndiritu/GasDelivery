from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order
from .mpesa import stk_push

class IsCustomer(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'CUSTOMER'

class IsDealer(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'DEALER'

# Customer initiates payment
class InitiatePaymentView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        order_id = request.data.get('order_id')
        method = request.data.get('method')  # 'MPESA' or 'CASH'

        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if hasattr(order, 'payment'):
            return Response({"error": "Payment already exists for this order"}, status=400)

        if order.status not in ['pending', 'accepted']:
            return Response({"error": "Order is not payable"}, status=400)

        payment = Payment.objects.create(
            order=order,
            method=method,
            amount=order.price + order.delivery_fee,
            status='PENDING'
        )

        return Response(PaymentSerializer(payment).data, status=201)

# M-Pesa callback (called by Safaricom, no auth)
class MpesaPaymentCallback(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data = request.data
        try:
            payment = Payment.objects.get(order_id=data['order_id'])
            payment.status = 'PAID'
            payment.mpesa_receipt = data['receipt']
            payment.save()

            # Mark order as completed
            payment.order.status = 'completed'
            payment.order.save()

            return Response({"status": "success"})
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

# Dealer confirms cash payment
class CashPaymentConfirm(APIView):
    permission_classes = [IsDealer]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, dealer=request.user.dealerprofile)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if hasattr(order, 'payment'):
            return Response({"error": "Payment already exists"}, status=400)

        payment = Payment.objects.create(
            order=order,
            method='CASH',
            amount=order.price + order.delivery_fee,
            status='PAID'
        )

        order.status = 'completed'
        order.save()

        return Response(PaymentSerializer(payment).data)

# Get payment status
class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            payment = Payment.objects.get(order_id=order_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        return Response(PaymentSerializer(payment).data)
    

class MpesaSTKPushView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        order_id = request.data.get('order_id')
        phone_number = request.user.phone_number

        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if hasattr(order, 'payment'):
            return Response({"error": "Payment already exists"}, status=400)

        amount = order.price + order.delivery_fee

        # Create pending payment
        payment = Payment.objects.create(
            order=order,
            method='MPESA',
            amount=amount,
            status='PENDING'
        )

        # Trigger STK Push
        result = stk_push(phone_number, amount, order_id)

        if result.get('ResponseCode') == '0':
            return Response({
                "message": "STK Push sent to your phone. Enter M-Pesa PIN to complete payment.",
                "checkout_request_id": result.get('CheckoutRequestID')
            })
        else:
            payment.status = 'FAILED'
            payment.save()
            return Response({"error": "STK Push failed", "details": result}, status=400)