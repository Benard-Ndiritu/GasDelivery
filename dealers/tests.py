from GasDelivery.testing import PASSWORD, BaseAPITestCase
from dealers.models import DealerProfile


class DealerApplicationTests(BaseAPITestCase):
    def test_apply_creates_pending_dealer(self):
        response = self.client.post('/api/dealers/apply/', {
            'phone_number': '0711111111', 'password': PASSWORD, 'name': 'Jane',
            'shop_name': 'Jane Gas', 'delivery_radius': 7,
            'latitude': -1.29, 'longitude': 36.82, 'email': 'jane@example.com',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        dealer = DealerProfile.objects.get(user__phone_number='0711111111')
        self.assertEqual(dealer.status, 'PENDING')
        self.assertEqual(dealer.user.role, 'DEALER')
        self.assertEqual(dealer.user.email, 'jane@example.com')
        self.assertEqual(dealer.delivery_radius, 7)

    def test_apply_validates_input(self):
        response = self.client.post('/api/dealers/apply/', {
            'phone_number': '0711111112', 'password': PASSWORD, 'name': 'X',
            'shop_name': 'Y', 'delivery_radius': 50,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
        self.assertFalse(DealerProfile.objects.exists())

    def test_dealer_cannot_self_approve(self):
        dealer = self.make_dealer(status='APPROVED')
        dealer.is_active = True
        dealer.save()
        self.auth(dealer.user)
        response = self.client.patch('/api/dealers/update/', {
            'status': 'APPROVED', 'is_active': True, 'shop_name': 'Renamed',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        dealer.refresh_from_db()
        self.assertEqual(dealer.shop_name, 'Renamed')

        pending = self.make_dealer('0711000002', status='PENDING')
        self.auth(pending.user)
        self.assertEqual(self.client.patch('/api/dealers/update/', {'status': 'APPROVED'}, format='json').status_code, 403)
        pending.refresh_from_db()
        self.assertEqual(pending.status, 'PENDING')

    def test_admin_approves_and_rejects(self):
        dealer = self.make_dealer(status='PENDING')
        self.auth(self.make_user('0700000009', role='ADMIN'))
        url = f'/api/dealers/applications/{dealer.id}/action/'
        self.assertEqual(self.client.post(url, {'action': 'approve'}, format='json').status_code, 200)
        dealer.refresh_from_db()
        self.assertEqual(dealer.status, 'APPROVED')
        self.assertEqual(self.client.post(url, {'action': 'nonsense'}, format='json').status_code, 400)

    def test_non_admin_cannot_approve(self):
        dealer = self.make_dealer(status='PENDING')
        self.auth(self.make_user('0722222222'))
        response = self.client.post(f'/api/dealers/applications/{dealer.id}/action/', {'action': 'approve'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_customers_only_see_approved_dealers(self):
        approved = self.make_dealer('0711000003')
        pending = self.make_dealer('0711000004', status='PENDING')
        self.auth(self.make_user('0722222223'))
        ids = [d['id'] for d in self.client.get('/api/dealers/').data]
        self.assertEqual(ids, [approved.id])
        self.assertEqual(self.client.get(f'/api/dealers/{pending.id}/').status_code, 404)

    def test_status_endpoint_returns_full_profile(self):
        dealer = self.make_dealer()
        self.auth(dealer.user)
        data = self.client.get('/api/dealers/application/status/').data
        for key in ('status', 'name', 'shop_name', 'phone_number', 'delivery_radius'):
            self.assertIn(key, data)
