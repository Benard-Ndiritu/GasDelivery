from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from GasDelivery.testing import PASSWORD, BaseAPITestCase
from users.models import PasswordResetOTP, User


class RegistrationTests(BaseAPITestCase):
    def test_register_always_creates_customer(self):
        response = self.client.post('/api/users/register/', {
            'phone_number': '0722000001', 'password': PASSWORD, 'role': 'ADMIN',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['role'], 'CUSTOMER')
        user = User.objects.get(phone_number='0722000001')
        self.assertEqual(user.role, 'CUSTOMER')
        self.assertFalse(user.is_staff)
        self.assertNotIn('password', response.data)

    def test_register_with_email(self):
        response = self.client.post('/api/users/register/', {
            'phone_number': '0722000002', 'password': PASSWORD, 'email': 'A@Example.com',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(User.objects.get(pk='0722000002').email, 'a@example.com')

    def test_duplicate_phone_rejected_with_error_key(self):
        self.make_user('0722000003')
        response = self.client.post('/api/users/register/', {
            'phone_number': '0722000003', 'password': PASSWORD,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.data['phone_number'], list)
        self.assertIn('error', response.data)

    def test_weak_password_rejected(self):
        response = self.client.post('/api/users/register/', {
            'phone_number': '0722000004', 'password': '123',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)


class LoginTests(BaseAPITestCase):
    def login(self, phone, password=PASSWORD):
        return self.client.post('/api/users/login/', {'phone_number': phone, 'password': password}, format='json')

    def test_customer_login_returns_tokens(self):
        self.make_user('0733000001')
        response = self.login('0733000001')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'CUSTOMER')
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_wrong_password(self):
        self.make_user('0733000002')
        response = self.login('0733000002', 'wrong')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error'], 'Invalid credentials')

    def test_inactive_user_blocked(self):
        user = self.make_user('0733000003')
        user.is_active = False
        user.save()
        self.assertEqual(self.login('0733000003').status_code, 403)

    def test_pending_and_profileless_dealers_blocked(self):
        self.make_dealer('0733000004', status='PENDING')
        self.assertEqual(self.login('0733000004').status_code, 403)
        self.make_user('0733000005', role='DEALER')
        self.assertEqual(self.login('0733000005').status_code, 403)

    def test_approved_dealer_gets_dealer_id(self):
        dealer = self.make_dealer('0733000006')
        response = self.login('0733000006')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['dealer_id'], dealer.id)

    def test_refresh_and_logout(self):
        self.make_user('0733000007')
        refresh = self.login('0733000007').data['refresh']
        response = self.client.post('/api/users/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        new_refresh = response.data['refresh']

        # The rotated-out token is blacklisted.
        self.assertEqual(self.client.post('/api/users/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)

        self.assertEqual(self.client.post('/api/users/logout/', {'refresh': new_refresh}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/users/token/refresh/', {'refresh': new_refresh}, format='json').status_code, 401)

    def test_me(self):
        user = self.make_user('0733000008')
        self.auth(user)
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.data['phone_number'], '0733000008')


class PasswordResetTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user('0744000001', email='reset@example.com')

    def request_otp(self, email='reset@example.com'):
        return self.client.post('/api/users/request-otp/', {'email': email}, format='json')

    def test_unknown_email_gets_same_response(self):
        known = self.request_otp()
        unknown = self.request_otp('nobody@example.com')
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_full_reset_flow(self):
        self.request_otp()
        otp = PasswordResetOTP.objects.get(user=self.user, is_used=False).otp
        self.assertIn(otp, mail.outbox[0].body)

        verify = self.client.post('/api/users/verify-otp/', {'email': 'reset@example.com', 'otp': otp}, format='json')
        self.assertEqual(verify.status_code, 200)

        new_password = 'An0ther-Strong-Pass!'
        reset = self.client.post('/api/users/reset-password/', {
            'email': 'reset@example.com', 'otp': otp, 'new_password': new_password,
        }, format='json')
        self.assertEqual(reset.status_code, 200, reset.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # The OTP cannot be reused.
        again = self.client.post('/api/users/reset-password/', {
            'email': 'reset@example.com', 'otp': otp, 'new_password': 'Yet-An0ther-Pass!',
        }, format='json')
        self.assertEqual(again.status_code, 400)

    def test_otp_locks_after_max_attempts(self):
        self.request_otp()
        record = PasswordResetOTP.objects.get(user=self.user, is_used=False)
        wrong = '000000' if record.otp != '000000' else '111111'
        for _ in range(5):
            self.client.post('/api/users/verify-otp/', {'email': 'reset@example.com', 'otp': wrong}, format='json')
        record.refresh_from_db()
        self.assertTrue(record.is_used)
        response = self.client.post('/api/users/verify-otp/', {'email': 'reset@example.com', 'otp': record.otp}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_expired_otp_rejected(self):
        self.request_otp()
        record = PasswordResetOTP.objects.get(user=self.user, is_used=False)
        PasswordResetOTP.objects.filter(pk=record.pk).update(created_at=timezone.now() - timedelta(minutes=11))
        response = self.client.post('/api/users/verify-otp/', {'email': 'reset@example.com', 'otp': record.otp}, format='json')
        self.assertEqual(response.status_code, 400)


class AdminAccessTests(BaseAPITestCase):
    def test_list_users_admin_only(self):
        self.auth(self.make_user('0755000001'))
        self.assertEqual(self.client.get('/api/users/list/').status_code, 403)
        self.auth(self.make_user('0755000002', role='ADMIN'))
        self.assertEqual(self.client.get('/api/users/list/').status_code, 200)


class CreateAdminCommandTests(BaseAPITestCase):
    def test_creates_admin_from_env(self):
        env = {'ADMIN_PHONE': '0700000001', 'ADMIN_PASSWORD': 'a-very-long-admin-pass'}
        with mock.patch.dict('os.environ', env):
            call_command('create_admin', stdout=StringIO())
        user = User.objects.get(pk='0700000001')
        self.assertEqual(user.role, 'ADMIN')
        self.assertTrue(user.is_superuser)

    def test_skips_without_env(self):
        with mock.patch.dict('os.environ', {'ADMIN_PHONE': '', 'ADMIN_PASSWORD': ''}):
            call_command('create_admin', stdout=StringIO())
        self.assertFalse(User.objects.filter(role='ADMIN').exists())
