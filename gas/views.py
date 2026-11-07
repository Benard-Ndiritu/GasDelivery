from rest_framework import generics, permissions

from users.permissions import IsAdmin, IsApprovedDealer

from .models import GasInventory, GasType
from .serializers import GasInventorySerializer, GasTypeSerializer


class GasTypeListCreateView(generics.ListCreateAPIView):
    """Admin creates gas types; any authenticated user can list them."""

    queryset = GasType.objects.all().order_by('name', 'cylinder_size')
    serializer_class = GasTypeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]


class GasTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GasType.objects.all()
    serializer_class = GasTypeSerializer
    permission_classes = [IsAdmin]


class DealerInventoryMixin:
    serializer_class = GasInventorySerializer
    permission_classes = [IsApprovedDealer]

    def get_dealer(self):
        return self.request.user.dealerprofile

    def get_queryset(self):
        return (
            GasInventory.objects.filter(dealer=self.get_dealer())
            .select_related('gas_type', 'dealer')
            .order_by('gas_type__name')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['dealer'] = getattr(self.request.user, 'dealerprofile', None)
        return context


class GasInventoryListCreateView(DealerInventoryMixin, generics.ListCreateAPIView):
    """The logged-in dealer's inventory: list and add items."""

    def perform_create(self, serializer):
        serializer.save(dealer=self.get_dealer())


class GasInventoryDetailView(DealerInventoryMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update (price, stock) or remove one of the dealer's inventory items."""


class DealerInventoryView(generics.ListAPIView):
    """Customers browse a dealer's in-stock items."""

    serializer_class = GasInventorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GasInventory.objects.filter(
            dealer__id=self.kwargs['dealer_id'],
            dealer__status='APPROVED',
            dealer__is_active=True,
            stock_available=True,
        ).select_related('gas_type', 'dealer')
