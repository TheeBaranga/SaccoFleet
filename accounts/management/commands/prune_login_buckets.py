from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import LoginBucket


class Command(BaseCommand):
    help = "Remove login counters older than one day. Run daily in production."

    def handle(self, *args, **options):
        count, _ = LoginBucket.objects.filter(
            started_at__lt=timezone.now() - timedelta(days=1),
        ).delete()
        self.stdout.write(f"Removed {count} expired login counters.")
