from django.db import models

class DealerProfile(models.Model):
    RADIUS_CHOICES = (
        (5, '5 km'),
        (7, '7 km'),
        (10, '10 km'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    shop_name = models.CharField(max_length=255, default='My Shop')
    phone_number = models.CharField(max_length=15, default='0000000000')
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    delivery_radius = models.IntegerField(choices=RADIUS_CHOICES, default=5)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.status})"