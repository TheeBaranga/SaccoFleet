"""Free local SQLite snapshots for the classroom demo; no cloud traffic."""
import os
import sqlite3
import tempfile
from contextlib import closing
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


def restore_demo(backup, destination):
    """Restore to a new file so the current database can never be overwritten."""
    backup = backup.resolve(strict=True)
    destination = destination.resolve()
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)) as original, \
             closing(sqlite3.connect(destination)) as restored:
            original.backup(restored)
            if restored.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Restored database failed its integrity check.")
            if restored.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("Restored database has broken foreign keys.")
            expected, old_samples = database_evidence(original)
            counts, samples = database_evidence(restored)
            if (expected, old_samples) != (counts, samples):
                raise RuntimeError("Restored counts or sampled relationships differ from the backup.")
    except sqlite3.Error as exc:
        destination.unlink()
        raise RuntimeError(f"SQLite restore failed: {exc}") from exc
    except BaseException:
        destination.unlink()
        raise
    return counts, {name: len(rows) for name, rows in samples.items()}


def database_evidence(db):
    tables = ("accounts_user", "fleet_fleet", "fleet_vehicle", "fleet_driver", "fleet_route",
              "fleet_assignment", "fleet_operationsession", "fleet_collection", "fleet_expense", "fleet_servicerecord")
    counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    joins = {
        "session to assignment, vehicle, driver, route and creator": """
            SELECT s.id, a.id, v.id, d.id, r.id, u.id, modifier.id, s.fleet_id
            FROM fleet_operationsession s
            JOIN fleet_assignment a ON a.id = s.assignment_id AND a.fleet_id = s.fleet_id
            JOIN fleet_vehicle v ON v.id = a.vehicle_id AND v.fleet_id = s.fleet_id
            JOIN fleet_driver d ON d.id = a.driver_id AND d.fleet_id = s.fleet_id
            JOIN fleet_route r ON r.id = s.route_id AND r.fleet_id = s.fleet_id
            JOIN accounts_user u ON u.id = s.created_by_id AND u.sacco_id = s.fleet_id
            JOIN accounts_user modifier ON modifier.id = s.updated_by_id AND modifier.sacco_id = s.fleet_id
            ORDER BY s.id LIMIT 5
        """,
        "service to expense, vehicle and SACCO": """
            SELECT s.id, e.id, v.id, v.fleet_id FROM fleet_servicerecord s
            JOIN fleet_expense e ON e.id = s.expense_id JOIN fleet_vehicle v ON v.id = e.vehicle_id
            ORDER BY s.id LIMIT 5
        """,
        "legacy collection to vehicle and SACCO": """
            SELECT c.id, v.id, v.fleet_id FROM fleet_collection c
            JOIN fleet_vehicle v ON v.id = c.vehicle_id ORDER BY c.id LIMIT 5
        """,
    }
    samples = {name: db.execute(query).fetchall() for name, query in joins.items()}
    for rows, table in zip(samples.values(), ("fleet_operationsession", "fleet_servicerecord", "fleet_collection")):
        if len(rows) != min(counts[table], 5):
            raise RuntimeError(f"Could not verify sampled relationships for {table}.")
    return counts, samples
