from django.db import models

# Create your models here.
from dealers.models import DealerProfile

class GasType(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dealer', 'name')

class GasInventory(models.Model):
    CYLINDER_CHOICES = (('6kg','6kg'),('13kg','13kg'))
    gas_type = models.ForeignKey(GasType, on_delete=models.CASCADE)
    cylinder_size = models.CharField(max_length=5, choices=CYLINDER_CHOICES)
    price_refill = models.DecimalField(max_digits=10, decimal_places=2)
    price_exchange = models.DecimalField(max_digits=10, decimal_places=2)
    stock_available = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('gas_type','cylinder_size')

