import re

from rest_framework import serializers

PHONE_RE = re.compile(r'^\+?\d{9,14}$')


def validate_phone_number(value):
    value = (value or '').strip().replace(' ', '')
    if not PHONE_RE.match(value):
        raise serializers.ValidationError('Enter a valid phone number, e.g. 0712345678 or +254712345678.')
    return value
