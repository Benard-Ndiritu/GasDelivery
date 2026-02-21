import math
from dealers.models import DealerProfile
from gas.models import GasInventory

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_available_dealer(customer_lat, customer_lon, gas_type_id):
    inventories = GasInventory.objects.filter(
        gas_type_id=gas_type_id,
        stock_available=True,
    ).select_related('dealer')

    closest_dealer = None
    closest_inventory = None
    closest_distance = float('inf')

    for inventory in inventories:
        dealer = inventory.dealer
        distance = haversine_distance(customer_lat, customer_lon, dealer.latitude, dealer.longitude)
        if distance <= dealer.delivery_radius and distance < closest_distance:
            closest_distance = distance
            closest_dealer = dealer
            closest_inventory = inventory

    return closest_dealer, closest_inventory