"""Thin client for Safaricom Daraja's STK push (Lipa na M-Pesa Online)."""

import base64
import logging
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

BASE_URLS = {
    'sandbox': 'https://sandbox.safaricom.co.ke',
    'production': 'https://api.safaricom.co.ke',
}
TOKEN_CACHE_KEY = 'mpesa:access_token'
NAIROBI = ZoneInfo('Africa/Nairobi')


class MpesaError(Exception):
    pass


def _base_url():
    try:
        return BASE_URLS[settings.MPESA_ENV]
    except KeyError:
        raise MpesaError(f"MPESA_ENV must be 'sandbox' or 'production', not {settings.MPESA_ENV!r}")


def is_configured():
    return all([
        settings.MPESA_CONSUMER_KEY,
        settings.MPESA_CONSUMER_SECRET,
        settings.MPESA_SHORTCODE,
        settings.MPESA_PASSKEY,
        settings.MPESA_CALLBACK_URL,
    ])


def normalize_phone(phone_number):
    """Convert 07XXXXXXXX / 01XXXXXXXX / +2547XXXXXXXX to 2547XXXXXXXX."""
    phone = ''.join(ch for ch in str(phone_number) if ch.isdigit())
    if phone.startswith('0') and len(phone) == 10:
        phone = '254' + phone[1:]
    elif len(phone) == 9 and phone[0] in '17':
        phone = '254' + phone
    if not (phone.startswith('254') and len(phone) == 12):
        raise MpesaError('Phone number must be a valid Kenyan mobile number.')
    return phone


def mpesa_amount(amount):
    """M-Pesa only accepts whole shillings; round up so we never undercharge."""
    return int(math.ceil(amount))


def get_access_token():
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token

    credentials = base64.b64encode(
        f'{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}'.encode()
    ).decode()
    try:
        response = requests.get(
            f'{_base_url()}/oauth/v1/generate?grant_type=client_credentials',
            headers={'Authorization': f'Basic {credentials}'},
            timeout=settings.MPESA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        token = data['access_token']
        expires_in = int(data.get('expires_in', 3599))
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.exception('Could not obtain M-Pesa access token')
        raise MpesaError('Could not connect to M-Pesa. Please try again.') from exc

    cache.set(TOKEN_CACHE_KEY, token, max(expires_in - 60, 60))
    return token


def _password():
    timestamp = datetime.now(NAIROBI).strftime('%Y%m%d%H%M%S')
    raw = f'{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}'
    return base64.b64encode(raw.encode()).decode(), timestamp


def _post(path, payload):
    token = get_access_token()
    try:
        response = requests.post(
            f'{_base_url()}{path}',
            json=payload,
            headers={'Authorization': f'Bearer {token}'},
            timeout=settings.MPESA_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.exception('M-Pesa request to %s failed', path)
        raise MpesaError('Could not connect to M-Pesa. Please try again.') from exc

    if response.status_code in (401, 403):
        cache.delete(TOKEN_CACHE_KEY)
    try:
        return response.json()
    except ValueError as exc:
        logger.error('Non-JSON response from M-Pesa %s: %s %s', path, response.status_code, response.text[:500])
        raise MpesaError('Unexpected response from M-Pesa.') from exc


def stk_push(phone_number, amount, order_id):
    """Send an STK push prompt. Returns Daraja's JSON response."""
    if not is_configured():
        raise MpesaError('M-Pesa payments are not configured.')

    phone = normalize_phone(phone_number)
    password, timestamp = _password()
    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': settings.MPESA_TRANSACTION_TYPE,
        'Amount': mpesa_amount(amount),
        'PartyA': phone,
        'PartyB': settings.MPESA_PARTY_B,
        'PhoneNumber': phone,
        'CallBackURL': settings.MPESA_CALLBACK_URL,
        'AccountReference': f'Order{order_id}',
        'TransactionDesc': f'Payment for Order {order_id}',
    }
    return _post('/mpesa/stkpush/v1/processrequest', payload)


def stk_query(checkout_request_id):
    """Ask Daraja for the result of an earlier STK push."""
    if not is_configured():
        raise MpesaError('M-Pesa payments are not configured.')

    password, timestamp = _password()
    return _post('/mpesa/stkpushquery/v1/query', {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id,
    })
