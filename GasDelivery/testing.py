"""Shared helpers for the test suites."""

from django.core.cache import cache
from rest_framework.test import APITestCase

from dealers.models import DealerProfile
from gas.models import GasInventory, GasType
from users.models import User

PASSWORD = 'Str0ng-Test-Pass!'


class BaseAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttling counters between tests

    def make_user(self, phone, role='CUSTOMER', email=None):
        if role == 'ADMIN':
            return User.objects.create_superuser(phone_number=phone, password=PASSWORD, email=email)
        return User.objects.create_user(phone_number=phone, password=PASSWORD, role=role, email=email)

    def make_dealer(self, phone='0711000000', status='APPROVED', lat=-1.2921, lon=36.8219, radius=5, **kwargs):
        user = self.make_user(phone, role='DEALER')
        return DealerProfile.objects.create(
            user=user, name=f'Dealer {phone}', shop_name='Shop', phone_number=phone,
            latitude=lat, longitude=lon, delivery_radius=radius, status=status, **kwargs,
        )

    def make_gas_type(self, name='Total', size='13kg'):
        return GasType.objects.create(name=name, cylinder_size=size)

    def stock(self, dealer, gas_type, refill='2500.00', exchange='3000.00', available=True):
        return GasInventory.objects.create(
            dealer=dealer, gas_type=gas_type, price_refill=refill,
            price_exchange=exchange, stock_available=available,
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)
