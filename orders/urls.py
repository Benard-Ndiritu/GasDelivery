from django.urls import path
from .views import PlaceOrderView, ReorderView

urlpatterns = [
    path('place/', PlaceOrderView.as_view()),
    path('reorder/<int:order_id>/', ReorderView.as_view()),
]
