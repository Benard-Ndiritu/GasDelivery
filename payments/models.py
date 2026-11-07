from django.db import models

from orders.models import Order


class Payment(models.Model):
    PAYMENT_METHODS = (('MPESA', 'Mpesa'), ('CASH', 'Cash'))
    STATUS_CHOICES = (('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'))

    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    mpesa_receipt = models.CharField(max_length=50, null=True, blank=True)

    # M-Pesa STK push bookkeeping. CheckoutRequestID is how callbacks are matched.
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, default='')
    result_code = models.CharField(max_length=20, blank=True, default='')
    result_desc = models.CharField(max_length=255, blank=True, default='')

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment for order #{self.order_id} ({self.method} {self.status})'
