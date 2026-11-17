from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.backups import restore_demo


class Command(BaseCommand):
    help = "Restore a SQLite snapshot to a new file and verify counts and relationships."

    def add_arguments(self, parser):
        parser.add_argument("backup", type=Path)
        parser.add_argument("destination", type=Path)

    def handle(self, *args, **options):
        try:
            counts, samples = restore_demo(options["backup"], options["destination"])
        except (OSError, ValueError, RuntimeError) as exc:
            raise CommandError(str(exc)) from exc
        for table, count in counts.items():
            self.stdout.write(f"{table}: {count} rows matched")
        for name, count in samples.items():
            self.stdout.write(f"{name}: {count} relationship samples matched")
        self.stdout.write(self.style.SUCCESS("Restore verified. SQLite integrity and foreign keys passed."))
