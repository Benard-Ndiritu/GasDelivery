import math
from dealers.models import DealerProfile
from gas.models import GasInventory

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_available_dealer(customer_lat, customer_lon, gas_type_id):
    inventories = GasInventory.objects.filter(
        gas_type_id=gas_type_id,
        stock_available=True,
        dealer__is_active=True
    ).select_related('dealer')

    for inventory in inventories:
        dealer = inventory.dealer
        distance = haversine_distance(customer_lat, customer_lon, dealer.latitude, dealer.longitude)
        if distance <= dealer.delivery_radius:
            return dealer, inventory
    return None, None