from django.core.management.base import BaseCommand
from investments.models import Investment

class Command(BaseCommand):
    help = 'Delete all investments with status cancelled.'

    def handle(self, *args, **options):
        cancelled = Investment.objects.filter(status='cancelled')
        count = cancelled.count()
        cancelled.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} cancelled investments.')) 