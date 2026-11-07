import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from orders.models import Order

from .models import Payment
from .mpesa import MpesaError, mpesa_amount, normalize_phone, stk_push, stk_query

logger = logging.getLogger(__name__)

PAYABLE_ORDER_STATUSES = ('pending', 'accepted', 'delivering')
STK_RETRY_COOLDOWN = timedelta(seconds=60)
STK_QUERY_MIN_AGE = timedelta(seconds=15)
# Daraja query result codes that mean "not finished yet".
STILL_PROCESSING_CODES = {'4999', '500.001.1001'}


class PaymentError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def start_mpesa_payment(order_id, customer, phone_number=None):
    """Create/reset the order's payment and send an STK push to the customer's phone."""
    try:
        phone = normalize_phone(phone_number or customer.phone_number)
    except MpesaError as exc:
        raise PaymentError(str(exc), 400)

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(id=order_id, customer=customer).first()
        if order is None:
            raise PaymentError('Order not found', 404)
        if order.status not in PAYABLE_ORDER_STATUSES:
            raise PaymentError('Order is not payable')

        payment = Payment.objects.filter(order=order).first()
        if payment and payment.status == 'PAID':
            raise PaymentError('This order has already been paid')
        if (
            payment
            and payment.method == 'MPESA'
            and payment.status == 'PENDING'
            and payment.checkout_request_id
            and timezone.now() - payment.updated_at < STK_RETRY_COOLDOWN
        ):
            raise PaymentError('A payment request was just sent to your phone. Please wait a minute before retrying.')

        payment = payment or Payment(order=order)
        payment.method = 'MPESA'
        payment.amount = order.total
        payment.status = 'PENDING'
        payment.phone_number = phone
        payment.checkout_request_id = None
        payment.merchant_request_id = None
        payment.result_code = ''
        payment.result_desc = ''
        payment.save()

    try:
        result = stk_push(payment.phone_number, payment.amount, order.id)
    except MpesaError as exc:
        _mark_failed(payment, str(exc))
        raise PaymentError(str(exc), 502)

    if str(result.get('ResponseCode')) == '0' and result.get('CheckoutRequestID'):
        payment.checkout_request_id = result['CheckoutRequestID']
        payment.merchant_request_id = result.get('MerchantRequestID')
        payment.result_desc = (result.get('ResponseDescription') or '')[:255]
        payment.save(update_fields=['checkout_request_id', 'merchant_request_id', 'result_desc', 'updated_at'])
        return payment, result

    message = result.get('errorMessage') or result.get('ResponseDescription') or 'STK push failed'
    logger.warning('STK push rejected for order %s: %s', order.id, result)
    _mark_failed(payment, message)
    raise PaymentError(f'M-Pesa request failed: {message}', 400)


def _mark_failed(payment, description, code=''):
    payment.status = 'FAILED'
    payment.result_code = str(code)[:20]
    payment.result_desc = str(description)[:255]
    payment.save(update_fields=['status', 'result_code', 'result_desc', 'updated_at'])


def handle_stk_callback(stk_callback):
    """Apply a Daraja STK callback (the `Body.stkCallback` object). Idempotent."""
    checkout_id = stk_callback.get('CheckoutRequestID')
    result_code = str(stk_callback.get('ResultCode', ''))
    result_desc = str(stk_callback.get('ResultDesc', ''))[:255]
    items = {
        item.get('Name'): item.get('Value')
        for item in (stk_callback.get('CallbackMetadata') or {}).get('Item', [])
    }

    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(checkout_request_id=checkout_id).first()
        if payment is None:
            logger.warning('M-Pesa callback for unknown CheckoutRequestID %s', checkout_id)
            return None

        payment.result_code = result_code
        payment.result_desc = result_desc

        if result_code == '0':
            try:
                paid = Decimal(str(items.get('Amount')))
            except (InvalidOperation, TypeError):
                paid = Decimal('0')
            if paid < mpesa_amount(payment.amount):
                logger.error('M-Pesa amount mismatch for payment %s: paid %s, expected %s',
                             payment.id, paid, payment.amount)
                if payment.status != 'PAID':
                    payment.status = 'FAILED'
                payment.result_desc = f'Amount mismatch: paid {paid}, expected {payment.amount}'
            else:
                payment.status = 'PAID'
                payment.mpesa_receipt = items.get('MpesaReceiptNumber') or payment.mpesa_receipt
                payment.paid_at = payment.paid_at or timezone.now()
        elif payment.status != 'PAID':
            payment.status = 'FAILED'

        payment.save()
        return payment


def refresh_mpesa_status(payment):
    """
    If an STK payment is still pending (e.g. the callback never arrived), ask
    Daraja for its result and update the record. Never raises.
    """
    if not (payment.method == 'MPESA' and payment.status == 'PENDING' and payment.checkout_request_id):
        return payment
    if timezone.now() - payment.updated_at < STK_QUERY_MIN_AGE:
        return payment

    try:
        result = stk_query(payment.checkout_request_id)
    except MpesaError:
        return payment

    code = result.get('ResultCode')
    if code is None or str(code) in STILL_PROCESSING_CODES:
        return payment

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != 'PENDING':
            return payment
        payment.result_code = str(code)
        payment.result_desc = str(result.get('ResultDesc', ''))[:255]
        if str(code) == '0':
            payment.status = 'PAID'
            payment.paid_at = timezone.now()
        else:
            payment.status = 'FAILED'
        payment.save()
    return payment


def confirm_cash_payment(order_id, dealer):
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(id=order_id, dealer=dealer).first()
        if order is None:
            raise PaymentError('Order not found', 404)
        if order.status in ('pending', 'cancelled'):
            raise PaymentError('Only accepted or delivered orders can be paid in cash')

        payment = Payment.objects.select_for_update().filter(order=order).first()
        if payment and payment.status == 'PAID':
            raise PaymentError('Payment has already been recorded for this order')

        payment = payment or Payment(order=order)
        payment.method = 'CASH'
        payment.amount = order.total
        payment.status = 'PAID'
        payment.paid_at = timezone.now()
        payment.save()

        order.status = 'completed'
        order.save(update_fields=['status', 'updated_at'])
    return payment
