import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.models import User
from fleet.models import Collection, Expense, ServiceRecord, Vehicle
from fleet.reporting_test_data import make_session

from .backups import backup_demo, restore_demo
from .middleware import DemoBackupMiddleware


class BackupTests(SimpleTestCase):
    def test_snapshot_is_valid_and_daily_snapshot_is_not_overwritten(self):
        with TemporaryDirectory() as folder:
            source = Path(folder)/'demo.sqlite3'
            with sqlite3.connect(source) as db:
                db.execute('CREATE TABLE records (value INTEGER)')
                db.execute('INSERT INTO records VALUES (42)')
            config = SimpleNamespace(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(source)}}, DEMO_BACKUP_DIR=Path(folder)/'backups')
            with patch('core.backups.settings', config):
                path = backup_demo()
                with sqlite3.connect(source) as db:
                    db.execute('INSERT INTO records VALUES (99)')
                self.assertEqual(backup_demo(), path)
                with sqlite3.connect(path) as copy:
                    self.assertEqual(copy.execute('SELECT value FROM records').fetchall(), [(42,)])
                fresh = backup_demo(force=True)
                with sqlite3.connect(fresh) as copy:
                    self.assertEqual(copy.execute('SELECT count(*) FROM records').fetchone()[0], 2)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @override_settings(DEBUG=True)
    def test_middleware_runs_once_per_day_for_signed_in_users_only(self):
        request = RequestFactory().get('/')
        request.user = SimpleNamespace(is_authenticated=False)
        middleware = DemoBackupMiddleware(lambda request: HttpResponse('ok'))
        with patch('core.middleware.backup_demo', return_value=Path('backup.sqlite3')) as backup:
            middleware(request)
            backup.assert_not_called()
            request.user.is_authenticated = True
            middleware(request)
            middleware(request)
            backup.assert_called_once()


class RestoreTests(TransactionTestCase):
    def test_restore_matches_counts_relationships_and_refuses_overwrite(self):
        if connection.vendor != "sqlite":
            self.skipTest("Classroom backup and restore use SQLite.")
        user = User.objects.create_user("restore@example.test")
        vehicle = Vehicle.objects.create(fleet=user.sacco, registration="RESTORE1")
        make_session(vehicle, timezone.localdate(), 100)
        expense = Expense.objects.create(vehicle=vehicle, amount=50)
        ServiceRecord.objects.create(expense=expense, service_type="Test service")
        Collection.objects.create(vehicle=vehicle, amount=25)
        with TemporaryDirectory() as folder:
            backup = Path(folder) / "backup.sqlite3"
            target = Path(folder) / "restored.sqlite3"
            with closing(sqlite3.connect(backup)) as snapshot:
                connection.connection.backup(snapshot)
            counts, samples = restore_demo(backup, target)
            self.assertEqual(counts["fleet_operationsession"], 1)
            self.assertEqual(counts["fleet_servicerecord"], 1)
            self.assertEqual(list(samples.values()), [1, 1, 1])
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                restore_demo(backup, target)
            self.assertEqual(target.read_bytes(), original)
