from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Payment
from orders.models import Order

class MpesaPaymentCallback(APIView):
    def post(self, request):
        data = request.data
        payment = Payment.objects.get(order_id=data['order_id'])
        payment.status = 'PAID'
        payment.mpesa_receipt = data['receipt']
        payment.save()
        return Response({"status": "success"})

class CashPaymentConfirm(APIView):
    def post(self, request, order_id):
        order = Order.objects.get(id=order_id)
        order.payment_method = 'CASH'
        order.save()
        Payment.objects.create(order=order, method='CASH', amount=order.total_amount, status='PAID')
        return Response({"status": "payment confirmed"})

