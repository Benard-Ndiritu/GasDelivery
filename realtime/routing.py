from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/dealer/(?P<dealer_id>\d+)/$', consumers.DealerConsumer.as_asgi()),
]
