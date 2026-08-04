from django.urls import path
from .views import (
    GasTypeListCreateView,
    GasInventoryListCreateView,
    GasInventoryUpdateView,
    DealerInventoryView,
    GasTypeDetailView,
)

urlpatterns = [
    path('types/', GasTypeListCreateView.as_view()),
    path('types/<int:pk>/', GasTypeDetailView.as_view()),
    path('inventory/', GasInventoryListCreateView.as_view()),
    path('inventory/<int:pk>/update/', GasInventoryUpdateView.as_view()),
    path('dealer/<int:dealer_id>/inventory/', DealerInventoryView.as_view()),
]