from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import DealerProfile
from .serializers import DealerProfileSerializer

class IsDealer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'DEALER'

class CreateDealerProfile(generics.CreateAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsDealer]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ListDealers(generics.ListAPIView):
    queryset = DealerProfile.objects.filter(is_active=True)
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class DealerDetail(generics.RetrieveAPIView):
    queryset = DealerProfile.objects.all()
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class UpdateDealerProfile(generics.UpdateAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsDealer]

    def get_object(self):
        try:
            profile = DealerProfile.objects.get(user=self.request.user)
        except DealerProfile.DoesNotExist:
            raise PermissionDenied("You don't have a dealer profile.")
        return profile