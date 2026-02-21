from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from .models import Order
from .serializers import OrderSerializer
from .services import find_available_dealer
from gas.models import GasType
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class IsCustomer(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'CUSTOMER'

class IsDealer(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'DEALER'

# Customer places an order
class PlaceOrderView(APIView):
    permission_classes = [IsCustomer]

    @transaction.atomic
    def post(self, request):
        data = request.data
        gas_type_id = data.get('gas_type_id')
        order_type = data.get('order_type')  # 'refill' or 'exchange'
        customer_lat = data.get('latitude')
        customer_lon = data.get('longitude')

        if not all([gas_type_id, order_type, customer_lat, customer_lon]):
            return Response({"error": "gas_type_id, order_type, latitude, longitude are required"}, status=400)

        try:
            gas_type = GasType.objects.get(id=gas_type_id)
        except GasType.DoesNotExist:
            return Response({"error": "Gas type not found"}, status=404)

        dealer, inventory = find_available_dealer(customer_lat, customer_lon, gas_type_id)
        if not dealer:
            return Response({"error": "No dealer available in your area"}, status=404)

        price = inventory.price_refill if order_type == 'refill' else inventory.price_exchange

        order = Order.objects.create(
            customer=request.user,
            dealer=dealer,
            gas_type=gas_type,
            order_type=order_type,
            price=price,
            delivery_fee=0,
            customer_latitude=customer_lat,
            customer_longitude=customer_lon,
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'dealer_{dealer.id}',
            {
                'type': 'order_notification',
                'order_id': order.id,
                'customer_phone': request.user.phone_number,
                'gas_type': gas_type.name,
                'price': str(order.price),
            }
        )

        return Response(OrderSerializer(order).data, status=201)

# Customer views their orders
class CustomerOrderListView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
        return Response(OrderSerializer(orders, many=True).data)

# Dealer views incoming orders
class DealerOrderListView(APIView):
    permission_classes = [IsDealer]

    def get(self, request):
        try:
            orders = Order.objects.filter(dealer=request.user.dealerprofile).order_by('-created_at')
            return Response(OrderSerializer(orders, many=True).data)
        except Exception:
            return Response({"error": "Dealer profile not found"}, status=404)
# Dealer updates order status
class UpdateOrderStatusView(APIView):
    permission_classes = [IsDealer]

    def put(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, dealer=request.user.dealerprofile)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        new_status = request.data.get('status')
        valid_transitions = {
            'pending': ['accepted', 'cancelled'],
            'accepted': ['delivering', 'cancelled'],
            'delivering': ['completed'],
        }

        if new_status not in valid_transitions.get(order.status, []):
            return Response({"error": f"Cannot move from {order.status} to {new_status}"}, status=400)

        order.status = new_status
        order.save()
        return Response(OrderSerializer(order).data)

# Customer cancels their order
class CancelOrderView(APIView):
    permission_classes = [IsCustomer]

    def put(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.status != 'pending':
            return Response({"error": "Only pending orders can be cancelled"}, status=400)

        order.status = 'cancelled'
        order.save()
        return Response(OrderSerializer(order).data)