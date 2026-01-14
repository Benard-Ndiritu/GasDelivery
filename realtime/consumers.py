from channels.generic.websocket import AsyncJsonWebsocketConsumer

class DealerConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.dealer_id = self.scope['url_route']['kwargs']['dealer_id']
        await self.channel_layer.group_add(f"dealer_{self.dealer_id}", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(f"dealer_{self.dealer_id}", self.channel_name)

    async def new_order(self, event):
        await self.send_json(event)
