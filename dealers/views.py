from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from .models import DealerProfile
from .serializers import DealerProfileSerializer
from users.models import User


class IsDealer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'DEALER'


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class ApplyAsDealer(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        name = request.data.get('name')
        shop_name = request.data.get('shop_name')
        password = request.data.get('password')
        latitude = request.data.get('latitude', 0.0)
        longitude = request.data.get('longitude', 0.0)
        delivery_radius = request.data.get('delivery_radius', 5)

        if not all([phone_number, name, shop_name, password]):
            return Response(
                {"error": "phone_number, name, shop_name and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"error": "An account with this phone number already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            phone_number=phone_number,
            password=password,
            role='DEALER'
        )

        DealerProfile.objects.create(
            user=user,
            name=name,
            shop_name=shop_name,
            phone_number=phone_number,
            latitude=latitude,
            longitude=longitude,
            delivery_radius=delivery_radius,
            status='PENDING'
        )

        return Response(
            {"message": "Application submitted successfully! You will be notified once approved."},
            status=status.HTTP_201_CREATED
        )


class ListDealerApplications(generics.ListAPIView):
    serializer_class = DealerProfileSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            return DealerProfile.objects.filter(status=status_filter)
        return DealerProfile.objects.all()


class ApproveDealerApplication(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            dealer = DealerProfile.objects.get(id=pk)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer not found"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action == 'approve':
            dealer.status = 'APPROVED'
            dealer.is_active = True
            dealer.save()
            return Response({"message": f"{dealer.name} has been approved."})
        elif action == 'reject':
            dealer.status = 'REJECTED'
            dealer.is_active = False
            dealer.save()
            return Response({"message": f"{dealer.name} has been rejected."})
        else:
            return Response({"error": "Action must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)


class DealerApplicationStatus(APIView):
    permission_classes = [IsDealer]

    def get(self, request):
        try:
            dealer = DealerProfile.objects.get(user=request.user)
            return Response({
                "status": dealer.status,
                "name": dealer.name,
                "shop_name": dealer.shop_name,
            })
        except DealerProfile.DoesNotExist:
            return Response({"error": "No application found"}, status=status.HTTP_404_NOT_FOUND)


class ListDealers(generics.ListAPIView):
    queryset = DealerProfile.objects.filter(is_active=True, status='APPROVED')
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
            return DealerProfile.objects.get(user=self.request.user)
        except DealerProfile.DoesNotExist:
            raise PermissionDenied("You don't have a dealer profile.")