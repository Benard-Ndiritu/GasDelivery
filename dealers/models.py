from django.db import models

class DealerProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    latitude = models.FloatField()
    longitude = models.FloatField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
