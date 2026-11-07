"""ASGI entrypoint: serves HTTP (Django) and WebSockets (Channels)."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GasDelivery.settings')

# Initialise Django before importing anything that touches models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

import realtime.routing  # noqa: E402
from realtime.middleware import JWTAuthMiddleware  # noqa: E402

# WebSockets authenticate with a JWT (not cookies), so no Origin check is needed;
# native mobile clients usually send no Origin header at all.
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        URLRouter(realtime.routing.websocket_urlpatterns)
    ),
})
