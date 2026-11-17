import platform
import sqlite3
from statistics import median
from time import perf_counter

import django
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import User
from fleet.models import OperationSession
from fleet.operational_reporting import NAIROBI, sessions_for_period

RUNS = 30
LIMIT = 2


class Command(BaseCommand):
    help = "Time 30 authenticated requests each for Daily Operations and Reports on the fictional SQLite fixture."

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("Run this benchmark on the fictional SQLite database.")
        manager = User.objects.filter(email="manager.acacia@example.test", role=User.Role.MANAGER, is_active=True).first()
        if not manager:
            raise CommandError("Run seed_classroom on a separate demo database first.")
        scoped = OperationSession.objects.filter(fleet=manager.sacco)
        if scoped.count() < 1000:
            raise CommandError("The benchmark account needs at least 1,000 operation sessions.")
        start = scoped.earliest("start").start.astimezone(NAIROBI).date()
        end = scoped.latest("start").start.astimezone(NAIROBI).date()
        count = sessions_for_period(manager.sacco_id, {"range_start": start, "range_end": end}).count()
        self.stdout.write(f"{platform.system()} {platform.release()} ({platform.machine()})")
        self.stdout.write(f"Python {platform.python_version()} | Django {django.get_version()} | SQLite {sqlite3.sqlite_version}")
        self.stdout.write(f"File-backed SQLite | {OperationSession.objects.count()} total sessions | "
                          f"{count} sessions in scope | {start} through {end} (EAT)")
        self.stdout.write(f"{RUNS} in-process authenticated GETs per view after one warm-up; response rendering included.")
        params = {"period": "custom", "start": start, "end": end}
        passed = True
        with override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"], SESSION_ENGINE="django.contrib.sessions.backends.db"):
            client = Client()
            client.force_login(manager)
            for view in ("daily_operations", "reports"):
                url = reverse(view)
                def request():
                    response = client.get(url, params, secure=True)
                    if response.status_code != 200 or not response.content:
                        raise CommandError(f"{view} returned an unusable response (HTTP {response.status_code}).")
                request()
                timings = []
                for _ in range(RUNS):
                    begins = perf_counter()
                    request()
                    timings.append(perf_counter()-begins)
                under = sum(value < LIMIT for value in timings)
                passed &= under / RUNS >= .95
                self.stdout.write(f"{view}: {under}/{RUNS} under {LIMIT}s ({under/RUNS:.1%}); "
                                  f"median {median(timings):.3f}s; maximum {max(timings):.3f}s")
        if not passed:
            raise CommandError("Performance target missed.")
