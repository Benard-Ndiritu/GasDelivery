import logging
import math

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from gas.models import GasInventory

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371
MAX_DELIVERY_RADIUS_KM = 10  # Largest DealerProfile.RADIUS_CHOICES value.


def haversine_distance(lat1, lon1, lat2, lon2):
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_available_dealer(customer_lat, customer_lon, gas_type_id):
    """
    Closest approved, active dealer who stocks the gas type and whose delivery
    radius covers the customer. Returns (dealer, inventory) or (None, None).
    """
    # Cheap bounding-box pre-filter in the database before the exact distance check.
    lat_delta = MAX_DELIVERY_RADIUS_KM / 111.0
    lon_delta = MAX_DELIVERY_RADIUS_KM / (111.0 * max(math.cos(math.radians(customer_lat)), 0.01))

    inventories = GasInventory.objects.filter(
        gas_type_id=gas_type_id,
        stock_available=True,
        dealer__status='APPROVED',
        dealer__is_active=True,
        dealer__user__is_active=True,
        dealer__latitude__range=(customer_lat - lat_delta, customer_lat + lat_delta),
        dealer__longitude__range=(customer_lon - lon_delta, customer_lon + lon_delta),
    ).select_related('dealer')

    best = (None, None)
    best_distance = float('inf')
    for inventory in inventories:
        dealer = inventory.dealer
        distance = haversine_distance(customer_lat, customer_lon, dealer.latitude, dealer.longitude)
        if distance <= dealer.delivery_radius and distance < best_distance:
            best_distance = distance
            best = (dealer, inventory)
    return best


def notify_dealer_new_order(order):
    """Push a new-order event to the dealer's WebSocket group. Never raises."""
    from realtime.consumers import dealer_group

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            dealer_group(order.dealer_id),
            {
                'type': 'order_notification',
                'order_id': order.id,
                'customer_phone': order.customer.phone_number,
                'gas_type': order.gas_type.name if order.gas_type else None,
                'order_type': order.order_type,
                'price': str(order.total),
            },
        )
    except Exception:
        logger.exception('Failed to send new-order notification for order %s', order.id)
