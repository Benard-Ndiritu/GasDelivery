from django.db import models

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('delivering', 'Delivering'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    ORDER_TYPE_CHOICES = (
        ('refill', 'Refill'),
        ('exchange', 'Exchange'),
    )

    customer = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='orders')
    dealer = models.ForeignKey('dealers.DealerProfile', on_delete=models.SET_NULL, null=True, blank=True)
    gas_type = models.ForeignKey('gas.GasType', on_delete=models.SET_NULL, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default='refill')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_latitude = models.FloatField()
    customer_longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)