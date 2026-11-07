import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


def dealer_group(dealer_id):
    return f'dealer_{dealer_id}'


@database_sync_to_async
def _can_listen(user, dealer_id):
    if not user or not user.is_authenticated:
        return False
    if user.role == 'ADMIN':
        return True
    if user.role != 'DEALER':
        return False
    from dealers.models import DealerProfile
    return DealerProfile.objects.filter(
        id=dealer_id, user=user, status='APPROVED', is_active=True,
    ).exists()


class OrderConsumer(AsyncWebsocketConsumer):
    """
    Pushes new-order notifications to a dealer.

    Connect to `ws/orders/<dealer_id>/?token=<access_token>`. Only the dealer who
    owns that profile (or an admin) may subscribe.
    """

    group_name = None

    async def connect(self):
        dealer_id = int(self.scope['url_route']['kwargs']['dealer_id'])
        if not await _can_listen(self.scope.get('user'), dealer_id):
            await self.close(code=4403)
            return

        self.group_name = dealer_group(dealer_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'order_id': event['order_id'],
            'customer_phone': event['customer_phone'],
            'gas_type': event['gas_type'],
            'order_type': event.get('order_type'),
            'price': event['price'],
        }))
