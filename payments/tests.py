from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from GasDelivery.testing import BaseAPITestCase
from orders.models import Order
from payments.models import Payment
from payments.mpesa import MpesaError, normalize_phone

MPESA_SETTINGS = dict(
    MPESA_CONSUMER_KEY='key', MPESA_CONSUMER_SECRET='secret',
    MPESA_SHORTCODE='174379', MPESA_PASSKEY='pass',
    MPESA_CALLBACK_URL='https://example.com/api/payments/mpesa-callback/',
    MPESA_CALLBACK_TOKEN='',
)


def stk_ok(checkout_id):
    return {'ResponseCode': '0', 'CheckoutRequestID': checkout_id,
            'MerchantRequestID': 'm-1', 'ResponseDescription': 'Success'}


def callback(checkout_id, result_code=0, amount=2500, receipt='QWE123'):
    stk = {'MerchantRequestID': 'm-1', 'CheckoutRequestID': checkout_id,
           'ResultCode': result_code, 'ResultDesc': 'done'}
    if result_code == 0:
        stk['CallbackMetadata'] = {'Item': [
            {'Name': 'Amount', 'Value': amount},
            {'Name': 'MpesaReceiptNumber', 'Value': receipt},
            {'Name': 'PhoneNumber', 'Value': 254722000001},
        ]}
    return {'Body': {'stkCallback': stk}}


@override_settings(**MPESA_SETTINGS)
class MpesaTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.customer = self.make_user('0722000001')
        self.dealer = self.make_dealer()
        gas = self.make_gas_type()
        self.order = Order.objects.create(
            customer=self.customer, dealer=self.dealer, gas_type=gas, order_type='refill',
            price='2500.00', customer_latitude=0, customer_longitude=0,
        )

    def push(self, order=None, checkout_id='ws_CO_1'):
        self.auth(self.customer)
        with mock.patch('payments.services.stk_push', return_value=stk_ok(checkout_id)) as push:
            response = self.client.post('/api/payments/mpesa-stk/', {'order_id': (order or self.order).id}, format='json')
        return response, push

    def test_phone_normalisation(self):
        self.assertEqual(normalize_phone('0722000001'), '254722000001')
        self.assertEqual(normalize_phone('+254 722 000 001'), '254722000001')
        self.assertEqual(normalize_phone('722000001'), '254722000001')
        with self.assertRaises(MpesaError):
            normalize_phone('12345')

    def test_stk_push_creates_pending_payment(self):
        response, push = self.push()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('message', response.data)
        push.assert_called_once()
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.checkout_request_id, 'ws_CO_1')

    def test_callback_marks_only_the_matching_payment_paid(self):
        self.push()
        other_customer = self.make_user('0722000002')
        other_order = Order.objects.create(
            customer=other_customer, dealer=self.dealer, order_type='refill',
            price='2500.00', customer_latitude=0, customer_longitude=0,
        )
        other = Payment.objects.create(order=other_order, method='MPESA', amount='2500.00',
                                       status='PENDING', checkout_request_id='ws_CO_OTHER')

        self.client.force_authenticate(user=None)
        response = self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_1'), format='json')
        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.status, 'PAID')
        self.assertEqual(payment.mpesa_receipt, 'QWE123')
        other.refresh_from_db()
        self.assertEqual(other.status, 'PENDING')
        # Payment alone does not complete the delivery.
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')

    def test_callback_unknown_checkout_id_changes_nothing(self):
        self.push()
        self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_FAKE'), format='json')
        self.assertEqual(Payment.objects.get(order=self.order).status, 'PENDING')

    def test_callback_amount_mismatch_not_paid(self):
        self.push()
        self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_1', amount=1), format='json')
        self.assertEqual(Payment.objects.get(order=self.order).status, 'FAILED')

    def test_failed_callback_then_retry(self):
        self.push()
        self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_1', result_code=1032), format='json')
        self.assertEqual(Payment.objects.get(order=self.order).status, 'FAILED')
        response, _ = self.push(checkout_id='ws_CO_2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.get(order=self.order).checkout_request_id, 'ws_CO_2')

    def test_cannot_pay_twice(self):
        self.push()
        self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_1'), format='json')
        response, push = self.push(checkout_id='ws_CO_3')
        self.assertEqual(response.status_code, 400)
        push.assert_not_called()

    def test_rapid_retry_blocked(self):
        self.push()
        response, push = self.push(checkout_id='ws_CO_4')
        self.assertEqual(response.status_code, 400)
        push.assert_not_called()

    def test_mpesa_error_reported(self):
        self.auth(self.customer)
        with mock.patch('payments.services.stk_push', side_effect=MpesaError('down')):
            response = self.client.post('/api/payments/mpesa-stk/', {'order_id': self.order.id}, format='json')
        self.assertEqual(response.status_code, 502)
        self.assertEqual(Payment.objects.get(order=self.order).status, 'FAILED')

    @override_settings(MPESA_CALLBACK_TOKEN='s3cret')
    def test_callback_token_enforced(self):
        self.push()
        bad = self.client.post('/api/payments/mpesa-callback/', callback('ws_CO_1'), format='json')
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(Payment.objects.get(order=self.order).status, 'PENDING')
        good = self.client.post('/api/payments/mpesa-callback/s3cret/', callback('ws_CO_1'), format='json')
        self.assertEqual(good.status_code, 200)
        self.assertEqual(Payment.objects.get(order=self.order).status, 'PAID')

    def test_status_visibility(self):
        self.push()
        self.assertEqual(self.client.get(f'/api/payments/status/{self.order.id}/').status_code, 200)
        self.auth(self.dealer.user)
        self.assertEqual(self.client.get(f'/api/payments/status/{self.order.id}/').status_code, 200)
        self.auth(self.make_user('0722000099'))
        self.assertEqual(self.client.get(f'/api/payments/status/{self.order.id}/').status_code, 404)

    def test_status_reconciles_with_daraja(self):
        self.push()
        Payment.objects.filter(order=self.order).update(updated_at=timezone.now() - timedelta(minutes=1))
        with mock.patch('payments.services.stk_query', return_value={'ResultCode': '0', 'ResultDesc': 'ok'}):
            response = self.client.get(f'/api/payments/status/{self.order.id}/')
        self.assertEqual(response.data['status'], 'PAID')


class CashPaymentTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.customer = self.make_user('0722000001')
        self.dealer = self.make_dealer()
        self.order = Order.objects.create(
            customer=self.customer, dealer=self.dealer, order_type='refill', status='delivering',
            price='2500.00', customer_latitude=0, customer_longitude=0,
        )

    def test_customer_chooses_cash_then_dealer_confirms(self):
        self.auth(self.customer)
        response = self.client.post('/api/payments/initiate/', {'order_id': self.order.id, 'method': 'CASH'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)

        self.auth(self.dealer.user)
        response = self.client.post(f'/api/payments/cash-confirm/{self.order.id}/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'PAID')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')

        again = self.client.post(f'/api/payments/cash-confirm/{self.order.id}/')
        self.assertEqual(again.status_code, 400)

    def test_cannot_confirm_pending_order(self):
        Order.objects.filter(pk=self.order.pk).update(status='pending')
        self.auth(self.dealer.user)
        self.assertEqual(self.client.post(f'/api/payments/cash-confirm/{self.order.id}/').status_code, 400)

    def test_invalid_method(self):
        self.auth(self.customer)
        response = self.client.post('/api/payments/initiate/', {'order_id': self.order.id, 'method': 'BITCOIN'}, format='json')
        self.assertEqual(response.status_code, 400)
