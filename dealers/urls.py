from django.urls import path
from .views import (
    ApplyAsDealer,
    ListDealerApplications,
    ApproveDealerApplication,
    DealerApplicationStatus,
    ListDealers,
    DealerDetail,
    UpdateDealerProfile,
)

urlpatterns = [
    path('', ListDealers.as_view()),
    path('apply/', ApplyAsDealer.as_view()),
    path('applications/', ListDealerApplications.as_view()),
    path('applications/<int:pk>/action/', ApproveDealerApplication.as_view()),
    path('application/status/', DealerApplicationStatus.as_view()),
    path('<int:pk>/', DealerDetail.as_view()),
    path('update/', UpdateDealerProfile.as_view()),
]