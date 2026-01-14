from django.db import models

# Create your models here.
from orders.models import Order

class Payment(models.Model):
    PAYMENT_METHODS = (('MPESA','Mpesa'),('CASH','Cash'))
    STATUS_CHOICES = (('PENDING','Pending'),('PAID','Paid'),('FAILED','Failed'))
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    mpesa_receipt = models.CharField(max_length=50,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

