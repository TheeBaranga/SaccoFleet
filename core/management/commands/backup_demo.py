from pathlib import Path

from django.test import override_settings
from django.core.management.base import BaseCommand, CommandError
from core.backups import backup_demo


class Command(BaseCommand):
    help = "Create an integrity-checked local SQLite backup for the classroom demo."

    def add_arguments(self, parser):
        parser.add_argument("--directory", type=Path, default=None)

    def handle(self, *args, **options):
        if options["directory"]:
            with override_settings(DEMO_BACKUP_DIR=options["directory"]):
                path = backup_demo(force=True)
        else:
            path = backup_demo(force=True)
        if not path:
            raise CommandError("This command requires an existing local SQLite demo database.")
        self.stdout.write(self.style.SUCCESS(f"Backup saved: {path}"))
