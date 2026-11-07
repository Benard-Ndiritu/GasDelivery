from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from dealers.models import DealerProfile
from GasDelivery.asgi import application
from users.models import User

PASSWORD = 'Str0ng-Test-Pass!'


class OrderSocketTests(TransactionTestCase):
    def setUp(self):
        user = User.objects.create_user(phone_number='0711000000', password=PASSWORD, role='DEALER')
        self.dealer = DealerProfile.objects.create(user=user, name='D', shop_name='S', status='APPROVED')
        self.dealer_token = str(AccessToken.for_user(user))
        other = User.objects.create_user(phone_number='0722000000', password=PASSWORD)
        self.customer_token = str(AccessToken.for_user(other))

    async def connect(self, token=None):
        path = f'/ws/orders/{self.dealer.id}/' + (f'?token={token}' if token else '')
        communicator = WebsocketCommunicator(application, path)
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_anonymous_rejected(self):
        communicator, connected = await self.connect()
        self.assertFalse(connected)

    async def test_other_user_rejected(self):
        communicator, connected = await self.connect(self.customer_token)
        self.assertFalse(connected)

    async def test_dealer_receives_notification(self):
        communicator, connected = await self.connect(self.dealer_token)
        self.assertTrue(connected)
        await get_channel_layer().group_send(f'dealer_{self.dealer.id}', {
            'type': 'order_notification', 'order_id': 1, 'customer_phone': '0722',
            'gas_type': 'Total', 'order_type': 'refill', 'price': '2500.00',
        })
        message = await communicator.receive_json_from()
        self.assertEqual(message['type'], 'new_order')
        self.assertEqual(message['order_id'], 1)
        await communicator.disconnect()
