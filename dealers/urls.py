from django.urls import path
from .views import CreateDealerProfile, ListDealers, DealerDetail, UpdateDealerProfile

urlpatterns = [
    path('', ListDealers.as_view()),
    path('create/', CreateDealerProfile.as_view()),
    path('<int:pk>/', DealerDetail.as_view()),
    path('update/', UpdateDealerProfile.as_view()),
]