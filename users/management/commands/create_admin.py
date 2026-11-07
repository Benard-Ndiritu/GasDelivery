import os

from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    help = (
        'Create the admin account from the ADMIN_PHONE, ADMIN_PASSWORD and (optional) '
        'ADMIN_EMAIL environment variables. Safe to run on every deploy.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-password',
            action='store_true',
            help='If the admin already exists, reset its password to ADMIN_PASSWORD.',
        )

    def handle(self, *args, **options):
        phone = os.environ.get('ADMIN_PHONE')
        password = os.environ.get('ADMIN_PASSWORD')
        email = os.environ.get('ADMIN_EMAIL') or None

        if not phone or not password:
            self.stdout.write('ADMIN_PHONE / ADMIN_PASSWORD not set; skipping admin creation.')
            return
        if len(password) < 12:
            raise CommandError('ADMIN_PASSWORD must be at least 12 characters.')

        user = User.objects.filter(phone_number=phone).first()
        if user is None:
            User.objects.create_superuser(phone_number=phone, password=password, email=email)
            self.stdout.write(self.style.SUCCESS(f'Admin {phone} created.'))
            return

        changed = []
        if user.role != 'ADMIN' or not user.is_staff or not user.is_superuser:
            user.role, user.is_staff, user.is_superuser = 'ADMIN', True, True
            changed.append('role')
        if options['update_password']:
            user.set_password(password)
            changed.append('password')
        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin {phone} updated ({", ".join(changed)}).'))
        else:
            self.stdout.write(f'Admin {phone} already exists.')
