"""Free local SQLite snapshots for the classroom demo; no cloud traffic."""
import os
import sqlite3
import tempfile
from pathlib import Path
from threading import Lock
from django.conf import settings
from django.utils import timezone

_lock = Lock()


def backup_demo(force=False):
    database = settings.DATABASES["default"]
    source = Path(database["NAME"])
    if database["ENGINE"] != "django.db.backends.sqlite3" or not source.is_file():
        return None
    with _lock:
        folder = Path(settings.DEMO_BACKUP_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = timezone.localtime().strftime("%Y-%m-%d-%H%M%S-%f") if force else timezone.localdate().isoformat()
        destination = folder / f"saccofleet-{stamp}.sqlite3"
        if destination.exists():
            return destination
        fd, temporary = tempfile.mkstemp(suffix=".sqlite3", dir=folder)
        os.close(fd)
        try:
            with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original, sqlite3.connect(temporary) as copy:
                original.backup(copy)
                if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return destination
