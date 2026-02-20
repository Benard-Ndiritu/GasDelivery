from django.urls import path
from .views import (
    PlaceOrderView,
    CustomerOrderListView,
    DealerOrderListView,
    UpdateOrderStatusView,
    CancelOrderView,
)

urlpatterns = [
    path('place/', PlaceOrderView.as_view()),
    path('my/', CustomerOrderListView.as_view()),
    path('dealer/', DealerOrderListView.as_view()),
    path('<int:order_id>/status/', UpdateOrderStatusView.as_view()),
    path('<int:order_id>/cancel/', CancelOrderView.as_view()),
]