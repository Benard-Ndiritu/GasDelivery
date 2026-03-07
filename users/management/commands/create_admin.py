from django.core.management.base import BaseCommand
from users.models import User

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not User.objects.filter(phone_number='0700000000').exists():
            user = User.objects.create_superuser(phone_number='0700000000', password='admin1234')
            user.role = 'ADMIN'
            user.save()
            self.stdout.write('Admin created successfully')
        else:
            self.stdout.write('Admin already exists')