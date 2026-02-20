from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import GasType, GasInventory
from .serializers import GasTypeSerializer, GasInventorySerializer
from dealers.models import DealerProfile


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsDealer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'DEALER'


# Gas Types — admin creates, anyone authenticated can view
class GasTypeListCreateView(generics.ListCreateAPIView):
    queryset = GasType.objects.all()
    serializer_class = GasTypeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]


# Dealer's own inventory — list and add
class GasInventoryListCreateView(generics.ListCreateAPIView):
    serializer_class = GasInventorySerializer
    permission_classes = [IsDealer]

    def get_queryset(self):
        try:
            dealer = DealerProfile.objects.get(user=self.request.user)
        except DealerProfile.DoesNotExist:
            raise PermissionDenied("You don't have a dealer profile.")
        return GasInventory.objects.filter(dealer=dealer)

    def perform_create(self, serializer):
        try:
            dealer = DealerProfile.objects.get(user=self.request.user)
        except DealerProfile.DoesNotExist:
            raise PermissionDenied("You don't have a dealer profile.")
        serializer.save(dealer=dealer)


# Update inventory item (price, stock)
class GasInventoryUpdateView(generics.UpdateAPIView):
    serializer_class = GasInventorySerializer
    permission_classes = [IsDealer]

    def get_queryset(self):
        try:
            dealer = DealerProfile.objects.get(user=self.request.user)
        except DealerProfile.DoesNotExist:
            raise PermissionDenied("You don't have a dealer profile.")
        return GasInventory.objects.filter(dealer=dealer)


# Public view — customers see available inventory for a dealer
class DealerInventoryView(generics.ListAPIView):
    serializer_class = GasInventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        dealer_id = self.kwargs['dealer_id']
        return GasInventory.objects.filter(dealer__id=dealer_id, stock_available=True)