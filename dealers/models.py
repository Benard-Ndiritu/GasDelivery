from django.db import models

class DealerProfile(models.Model):
    RADIUS_CHOICES = (
        (5, '5 km'),
        (7, '7 km'),
        (10, '10 km'),
    )

    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    delivery_radius = models.IntegerField(choices=RADIUS_CHOICES, default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name