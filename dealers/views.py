from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin, IsApprovedDealer, IsDealer

from .models import DealerProfile
from .serializers import DealerApplicationSerializer, DealerProfileSerializer


class ApplyAsDealer(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = DealerApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dealer = serializer.save()
        return Response(
            {
                'message': 'Application submitted successfully! You will be notified once approved.',
                'dealer_id': dealer.id,
            },
            status=status.HTTP_201_CREATED,
        )


class ListDealerApplications(generics.ListAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = DealerProfile.objects.select_related('user').order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset


class ApproveDealerApplication(APIView):
    """Admin action: {"action": "approve" | "reject" | "deactivate" | "activate"}."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        dealer = DealerProfile.objects.filter(id=pk).first()
        if dealer is None:
            return Response({'error': 'Dealer not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action == 'approve':
            dealer.status, dealer.is_active = 'APPROVED', True
            message = f'{dealer.name} has been approved.'
        elif action == 'reject':
            dealer.status, dealer.is_active = 'REJECTED', False
            message = f'{dealer.name} has been rejected.'
        elif action == 'deactivate':
            dealer.is_active = False
            message = f'{dealer.name} has been deactivated.'
        elif action == 'activate':
            if dealer.status != 'APPROVED':
                return Response({'error': 'Only approved dealers can be activated.'},
                                status=status.HTTP_400_BAD_REQUEST)
            dealer.is_active = True
            message = f'{dealer.name} has been activated.'
        else:
            return Response(
                {'error': "Action must be 'approve', 'reject', 'activate' or 'deactivate'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dealer.save(update_fields=['status', 'is_active', 'updated_at'])
        return Response({'message': message, 'dealer': DealerProfileSerializer(dealer).data})


class DealerApplicationStatus(APIView):
    """The logged-in dealer's own profile, including application status."""

    permission_classes = [IsDealer]

    def get(self, request):
        dealer = DealerProfile.objects.filter(user=request.user).select_related('user').first()
        if dealer is None:
            return Response({'error': 'No application found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DealerProfileSerializer(dealer).data)


class ListDealers(generics.ListAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            DealerProfile.objects.filter(is_active=True, status='APPROVED')
            .select_related('user')
            .order_by('shop_name')
        )


class DealerDetail(generics.RetrieveAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = DealerProfile.objects.select_related('user')
        if self.request.user.role == 'ADMIN':
            return queryset
        return queryset.filter(is_active=True, status='APPROVED')


class UpdateDealerProfile(generics.RetrieveUpdateAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsApprovedDealer]

    def get_object(self):
        dealer = DealerProfile.objects.filter(user=self.request.user).first()
        if dealer is None:
            raise NotFound("You don't have a dealer profile.")
        return dealer
