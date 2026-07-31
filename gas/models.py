from django.db import models
from dealers.models import DealerProfile

class GasType(models.Model):
    CYLINDER_CHOICES = (
        ('6kg', '6kg'),
        ('13kg', '13kg'),
    )
    name = models.CharField(max_length=100, unique=True)
    cylinder_size = models.CharField(max_length=5, choices=CYLINDER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.cylinder_size}"


class GasInventory(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='inventory')
    gas_type = models.ForeignKey(GasType, on_delete=models.CASCADE)
    price_refill = models.DecimalField(max_digits=10, decimal_places=2)
    price_exchange = models.DecimalField(max_digits=10, decimal_places=2)
    stock_available = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('dealer', 'gas_type')

    def __str__(self):
        return f"{self.dealer.name} - {self.gas_type.name}"