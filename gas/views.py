from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import GasType, GasInventory
from .serializers import GasTypeSerializer, GasInventorySerializer

# Add/Edit Gas Types
class GasTypeListCreateView(generics.ListCreateAPIView):
        queryset = GasType.objects.all()
        serializer_class = GasTypeSerializer

# Manage Inventory
class GasInventoryListCreateView(generics.ListCreateAPIView):
    serializer_class = GasInventorySerializer
    queryset = GasInventory.objects.all()
    def get_queryset(self):
        return GasInventory.objects.filter(gas_type__dealer__user=self.request.user)

