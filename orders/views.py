from django.shortcuts import render

# Create your views here.
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order, OrderItem
from dealers.models import DealerProfile
from gas.models import GasInventory
# from django.contrib.gis.geos import Point
from django.db import transaction
from .services import dispatch_order  # uses your 5/7km/10km logic

# Place Order
class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        customer = request.user
        data = request.data
        latitude = models.FloatField()
        longitude = models.FloatField()
        gas_inventory = GasInventory.objects.get(id=data['inventory_id'])
        order_type = data['order_type']

        dealer = dispatch_order(location, gas_inventory.gas_type.name, gas_inventory.cylinder_size)
        if not dealer:
            return Response({"error": "No dealer available"}, status=400)

        delivery_fee = data.get('delivery_fee', 0)  # system-calculated
        total = gas_inventory.price_refill + delivery_fee if order_type=='REFILL' else gas_inventory.price_exchange + delivery_fee

        order = Order.objects.create(
            customer=customer,
            dealer=dealer,
            delivery_location=location,
            delivery_fee=delivery_fee,
            total_amount=total,
            payment_method=data['payment_method']
        )

        OrderItem.objects.create(
            order=order,
            gas_inventory=gas_inventory,
            order_type=order_type,
            quantity=1,
            price=gas_inventory.price_refill if order_type=='REFILL' else gas_inventory.price_exchange
        )

        return Response({"order_id": order.id, "dealer": dealer.user.phone_number})

# Reorder previous
class ReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        previous_order = Order.objects.get(id=order_id, customer=request.user)
        data = {
            "inventory_id": previous_order.orderitem_set.first().gas_inventory.id,
            "order_type": previous_order.orderitem_set.first().order_type,
            "latitude": previous_order.delivery_location.y,
            "longitude": previous_order.delivery_location.x,
            "payment_method": previous_order.payment_method,
        }
        # Calls PlaceOrder logic
        view = PlaceOrderView()
        view.request = request
        return view.post(request=data)

