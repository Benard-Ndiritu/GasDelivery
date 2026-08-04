from django.urls import path
from .views import (
    PlaceOrderView,
    CustomerOrderListView,
    DealerOrderListView,
    UpdateOrderStatusView,
    CancelOrderView,
    ListAllOrders,
)

urlpatterns = [
    path('place/', PlaceOrderView.as_view()),
    path('my/', CustomerOrderListView.as_view()),
    path('dealer/', DealerOrderListView.as_view()),
    path('<int:order_id>/status/', UpdateOrderStatusView.as_view()),
    path('<int:order_id>/cancel/', CancelOrderView.as_view()),
    path('all/', ListAllOrders.as_view()),
]