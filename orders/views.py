from django.db import transaction
from django.db.models import Count, Q, Sum
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gas.models import GasType
from users.permissions import IsAdmin, IsApprovedDealer, IsCustomer

from .models import Order
from .serializers import OrderSerializer, PlaceOrderSerializer, UpdateOrderStatusSerializer
from .services import find_available_dealer, notify_dealer_new_order


def order_queryset():
    return Order.objects.select_related('customer', 'dealer', 'gas_type', 'payment')


class PlaceOrderView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        gas_type = GasType.objects.filter(id=data['gas_type_id']).first()
        if gas_type is None:
            return Response({'error': 'Gas type not found'}, status=status.HTTP_404_NOT_FOUND)

        dealer, inventory = find_available_dealer(data['latitude'], data['longitude'], gas_type.id)
        if dealer is None:
            return Response({'error': 'No dealer available in your area'}, status=status.HTTP_404_NOT_FOUND)

        price = inventory.price_refill if data['order_type'] == 'refill' else inventory.price_exchange

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user,
                dealer=dealer,
                gas_type=gas_type,
                order_type=data['order_type'],
                price=price,
                delivery_fee=0,
                customer_latitude=data['latitude'],
                customer_longitude=data['longitude'],
            )
            transaction.on_commit(lambda: notify_dealer_new_order(order))

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CustomerOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsCustomer]

    def get_queryset(self):
        return order_queryset().filter(customer=self.request.user)


class DealerOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsApprovedDealer]

    def get_queryset(self):
        queryset = order_queryset().filter(dealer=self.request.user.dealerprofile)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.lower())
        return queryset


class OrderDetailView(generics.RetrieveAPIView):
    """An order visible to its customer, its dealer, or an admin."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'order_id'

    def get_queryset(self):
        user = self.request.user
        queryset = order_queryset()
        if user.role == 'ADMIN':
            return queryset
        if user.role == 'DEALER':
            return queryset.filter(dealer__user=user)
        return queryset.filter(customer=user)


class UpdateOrderStatusView(APIView):
    permission_classes = [IsApprovedDealer]

    def put(self, request, order_id):
        serializer = UpdateOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']

        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(id=order_id, dealer=request.user.dealerprofile)
                .first()
            )
            if order is None:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

            if new_status not in Order.DEALER_TRANSITIONS.get(order.status, []):
                return Response(
                    {'error': f'Cannot move from {order.status} to {new_status}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])

        return Response(OrderSerializer(order_queryset().get(pk=order.pk)).data)

    patch = put


class CancelOrderView(APIView):
    permission_classes = [IsCustomer]

    def put(self, request, order_id):
        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(id=order_id, customer=request.user)
                .first()
            )
            if order is None:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
            if order.status != 'pending':
                return Response({'error': 'Only pending orders can be cancelled'},
                                status=status.HTTP_400_BAD_REQUEST)
            payment = getattr(order, 'payment', None)
            if payment and payment.status == 'PAID':
                return Response(
                    {'error': 'This order has already been paid. Please contact support to cancel it.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.status = 'cancelled'
            order.save(update_fields=['status', 'updated_at'])

        return Response(OrderSerializer(order_queryset().get(pk=order.pk)).data)

    post = put


class ListAllOrders(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = order_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.lower())
        return queryset


class OrderStats(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        stats = Order.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            accepted=Count('id', filter=Q(status='accepted')),
            delivering=Count('id', filter=Q(status='delivering')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            revenue=Sum('price', filter=Q(status='completed')),
        )
        stats['revenue'] = str(stats['revenue'] or 0)
        return Response(stats)
