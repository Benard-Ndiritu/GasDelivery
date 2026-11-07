from GasDelivery.testing import BaseAPITestCase


class GasTypeTests(BaseAPITestCase):
    def test_only_admin_creates_gas_types(self):
        self.auth(self.make_user('0722000001'))
        self.assertEqual(self.client.post('/api/gas/types/', {'name': 'K-Gas', 'cylinder_size': '6kg'}).status_code, 403)
        self.auth(self.make_user('0700000001', role='ADMIN'))
        self.assertEqual(self.client.post('/api/gas/types/', {'name': 'K-Gas', 'cylinder_size': '6kg'}).status_code, 201)
        duplicate = self.client.post('/api/gas/types/', {'name': 'k-gas', 'cylinder_size': '6kg'})
        self.assertEqual(duplicate.status_code, 400)


class InventoryTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.dealer = self.make_dealer()
        self.gas = self.make_gas_type()
        self.auth(self.dealer.user)

    def test_dealer_adds_and_updates_inventory(self):
        response = self.client.post('/api/gas/inventory/', {
            'gas_type': self.gas.id, 'price_refill': '2400', 'price_exchange': '2900',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['dealer'], self.dealer.id)

        item_id = response.data['id']
        response = self.client.patch(f'/api/gas/inventory/{item_id}/update/', {'stock_available': False}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['stock_available'])

        self.assertEqual(self.client.delete(f'/api/gas/inventory/{item_id}/').status_code, 204)

    def test_duplicate_gas_type_is_a_validation_error(self):
        self.stock(self.dealer, self.gas)
        response = self.client.post('/api/gas/inventory/', {
            'gas_type': self.gas.id, 'price_refill': '2400', 'price_exchange': '2900',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('gas_type', response.data)

    def test_negative_price_rejected(self):
        response = self.client.post('/api/gas/inventory/', {
            'gas_type': self.gas.id, 'price_refill': '-5', 'price_exchange': '2900',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_dealer_cannot_edit_another_dealers_item(self):
        other = self.make_dealer('0711000099')
        item = self.stock(other, self.gas)
        response = self.client.patch(f'/api/gas/inventory/{item.id}/', {'price_refill': '1'}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_pending_dealer_cannot_manage_inventory(self):
        pending = self.make_dealer('0711000098', status='PENDING')
        self.auth(pending.user)
        self.assertEqual(self.client.get('/api/gas/inventory/').status_code, 403)
