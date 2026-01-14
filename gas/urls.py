from django.urls import path
from .views import GasTypeListCreateView, GasInventoryListCreateView

urlpatterns = [
    path('types/', GasTypeListCreateView.as_view()),
    path('inventory/', GasInventoryListCreateView.as_view()),
]
