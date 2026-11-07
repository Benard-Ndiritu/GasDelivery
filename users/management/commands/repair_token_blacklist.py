from django.core.management.base import BaseCommand
from django.db import connection, transaction

APP = 'token_blacklist'
# Child table first: blacklistedtoken references outstandingtoken.
TABLES = ['token_blacklist_blacklistedtoken', 'token_blacklist_outstandingtoken']


class Command(BaseCommand):
    help = (
        "Repair a half-applied simplejwt token_blacklist migration: if its tables exist but "
        "no token_blacklist migration is recorded, drop the (empty) tables so `migrate` can "
        "recreate them. Does nothing in any other situation, so it is safe to run on every deploy."
    )

    def handle(self, *args, **options):
        existing = set(connection.introspection.table_names())
        present = [table for table in TABLES if table in existing]
        if not present or 'django_migrations' not in existing:
            self.stdout.write('token_blacklist: nothing to repair.')
            return

        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM django_migrations WHERE app = %s', [APP])
            if cursor.fetchone()[0]:
                self.stdout.write('token_blacklist: migrations recorded, nothing to repair.')
                return

            # Only remove tables that hold no data. In the half-applied state they were
            # created moments before the connection dropped, so they are always empty.
            for table in present:
                cursor.execute(f'SELECT COUNT(*) FROM {quote(table)}')
                if cursor.fetchone()[0]:
                    self.stderr.write(
                        f'token_blacklist: {table} contains rows but no migration is recorded; '
                        'refusing to drop it. Repair manually.'
                    )
                    return

        cascade = ' CASCADE' if connection.vendor == 'postgresql' else ''
        with transaction.atomic(), connection.cursor() as cursor:
            for table in present:
                cursor.execute(f'DROP TABLE IF EXISTS {quote(table)}{cascade}')
        self.stdout.write(self.style.SUCCESS(
            f'token_blacklist: dropped unrecorded empty tables ({", ".join(present)}); '
            'migrate will recreate them.'
        ))
