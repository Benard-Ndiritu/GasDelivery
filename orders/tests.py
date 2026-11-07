from GasDelivery.testing import BaseAPITestCase
from orders.models import Order
from orders.services import find_available_dealer, haversine_distance

NAIROBI = (-1.2921, 36.8219)


class DealerMatchingTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.gas = self.make_gas_type()

    def test_haversine(self):
        # Roughly 1.1 km per 0.01 degree of latitude.
        self.assertAlmostEqual(haversine_distance(0, 0, 0.01, 0), 1.11, places=1)

    def test_picks_closest_approved_in_range(self):
        far = self.make_dealer('0711000001', lat=NAIROBI[0] + 0.03, lon=NAIROBI[1], radius=5)
        near = self.make_dealer('0711000002', lat=NAIROBI[0] + 0.01, lon=NAIROBI[1], radius=5)
        self.stock(far, self.gas)
        self.stock(near, self.gas)
        dealer, _ = find_available_dealer(*NAIROBI, self.gas.id)
        self.assertEqual(dealer, near)

    def test_ignores_unapproved_inactive_out_of_stock_and_out_of_range(self):
        pending = self.make_dealer('0711000003', status='PENDING')
        inactive = self.make_dealer('0711000004', is_active=False)
        no_stock = self.make_dealer('0711000005')
        out_of_range = self.make_dealer('0711000006', lat=NAIROBI[0] + 0.08, radius=5)
        for dealer in (pending, inactive, out_of_range):
            self.stock(dealer, self.gas)
        self.stock(no_stock, self.gas, available=False)
        self.assertEqual(find_available_dealer(*NAIROBI, self.gas.id), (None, None))


class OrderFlowTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.gas = self.make_gas_type()
        self.dealer = self.make_dealer()
        self.stock(self.dealer, self.gas, refill='2500.00', exchange='3200.00')
        self.customer = self.make_user('0722000001')

    def place(self, **overrides):
        payload = {'gas_type_id': self.gas.id, 'order_type': 'exchange',
                   'latitude': NAIROBI[0], 'longitude': NAIROBI[1], **overrides}
        return self.client.post('/api/orders/place/', payload, format='json')

    def test_place_order(self):
        self.auth(self.customer)
        response = self.place()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['price'], '3200.00')
        self.assertEqual(response.data['dealer_id'], self.dealer.id)
        self.assertEqual(response.data['status'], 'pending')
        self.assertIsNone(response.data['payment_status'])

    def test_place_order_validation(self):
        self.auth(self.customer)
        self.assertEqual(self.place(order_type='free').status_code, 400)
        self.assertEqual(self.place(latitude='abc').status_code, 400)
        self.assertEqual(self.place(gas_type_id=9999).status_code, 404)

    def test_only_customers_place_orders(self):
        self.auth(self.dealer.user)
        self.assertEqual(self.place().status_code, 403)

    def test_dealer_status_transitions(self):
        self.auth(self.customer)
        order_id = self.place().data['id']
        self.auth(self.dealer.user)
        url = f'/api/orders/{order_id}/status/'
        self.assertEqual(self.client.put(url, {'status': 'completed'}, format='json').status_code, 400)
        for new_status in ('accepted', 'delivering', 'completed'):
            response = self.client.put(url, {'status': new_status}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Order.objects.get(pk=order_id).status, 'completed')

    def test_other_dealer_cannot_touch_order(self):
        self.auth(self.customer)
        order_id = self.place().data['id']
        other = self.make_dealer('0711000077')
        self.auth(other.user)
        self.assertEqual(self.client.put(f'/api/orders/{order_id}/status/', {'status': 'accepted'}, format='json').status_code, 404)
        self.assertEqual(self.client.get(f'/api/orders/{order_id}/').status_code, 404)

    def test_customer_cancel(self):
        self.auth(self.customer)
        order_id = self.place().data['id']
        response = self.client.put(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(self.client.put(f'/api/orders/{order_id}/cancel/').status_code, 400)

    def test_lists_and_stats(self):
        self.auth(self.customer)
        self.place()
        self.assertEqual(len(self.client.get('/api/orders/my/').data), 1)
        self.auth(self.dealer.user)
        self.assertEqual(len(self.client.get('/api/orders/dealer/').data), 1)
        self.assertEqual(self.client.get('/api/orders/stats/').status_code, 403)
        self.auth(self.make_user('0700000001', role='ADMIN'))
        stats = self.client.get('/api/orders/stats/').data
        self.assertEqual(stats['total'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(len(self.client.get('/api/orders/all/').data), 1)
