from django.db import models

class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("delivering", "Delivering"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    customer = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="orders")
    dealer = models.ForeignKey("dealers.DealerProfile", on_delete=models.SET_NULL, null=True, blank=True)

    gas_type = models.CharField(max_length=100)
    cylinder_size = models.IntegerField()  # 6 or 13
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)

    customer_latitude = models.FloatField()
    customer_longitude = models.FloatField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} ({self.quantity})"