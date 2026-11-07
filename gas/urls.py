from django.urls import path

from .views import (
    DealerInventoryView,
    GasInventoryDetailView,
    GasInventoryListCreateView,
    GasTypeDetailView,
    GasTypeListCreateView,
)

urlpatterns = [
    path('types/', GasTypeListCreateView.as_view()),
    path('types/<int:pk>/', GasTypeDetailView.as_view()),
    path('inventory/', GasInventoryListCreateView.as_view()),
    path('inventory/<int:pk>/', GasInventoryDetailView.as_view()),
    # Kept for backwards compatibility with existing clients.
    path('inventory/<int:pk>/update/', GasInventoryDetailView.as_view()),
    path('dealer/<int:dealer_id>/inventory/', DealerInventoryView.as_view()),
]
