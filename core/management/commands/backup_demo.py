from django.core.management.base import BaseCommand, CommandError
from core.backups import backup_demo


class Command(BaseCommand):
    help = "Create an integrity-checked local SQLite backup for the classroom demo."

    def handle(self, *args, **options):
        path = backup_demo(force=True)
        if not path:
            raise CommandError("This command requires an existing local SQLite demo database.")
        self.stdout.write(self.style.SUCCESS(f"Backup saved: {path}"))
