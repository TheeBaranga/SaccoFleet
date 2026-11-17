from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import User
from fleet.models import Assignment, Collection, Driver, Expense, Fleet, OperationSession, Route, ServiceRecord, Vehicle
from fleet.operational_reporting import NAIROBI

DEMO_PASSWORD = "ClassroomFleet-2026!"
DEMO_SACCOS = (("Acacia Classroom SACCO", "acacia"), ("Baobab Classroom SACCO", "baobab"))


class Command(BaseCommand):
    help = "Seed two fictional SACCOs and 1,000 operation sessions per SACCO in an empty, explicitly named SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("--demo-db", type=Path, required=True)

    def handle(self, *args, **options):
        target = options["demo_db"].resolve()
        configured = Path(connection.settings_dict["NAME"]).resolve()
        if (connection.vendor != "sqlite" or target != configured or not target.is_file()
                or target == (settings.BASE_DIR / "db.sqlite3").resolve()):
            raise CommandError("Point DATABASE_URL and --demo-db at the same separate, migrated SQLite file.")
        today = timezone.localdate(timezone=NAIROBI)
        with transaction.atomic():
            # Acquire SQLite's write lock before checking emptiness.
            Fleet.objects.filter(pk__isnull=True).update(name="")
            if Fleet.objects.exists() or User.objects.exists():
                raise CommandError("The target already contains accounts or fleets. Use a fresh demo database.")
            for index, (name, slug) in enumerate(DEMO_SACCOS, start=1):
                seed_sacco(name, slug, today, index)
        self.stdout.write(self.style.SUCCESS(f"Seeded 2 fictional SACCOs and 2,000 sessions through {today}."))


def seed_sacco(name, slug, today, index):
    manager = User.objects.create_user(f"manager.{slug}@example.test", DEMO_PASSWORD, sacco_name=name)
    fleet = manager.sacco
    staff = User.objects.create_user(f"staff.{slug}@example.test", DEMO_PASSWORD, sacco=fleet, role=User.Role.OPERATIONS)
    route = Route.objects.create(fleet=fleet, name="Classroom Loop", start_point="Example Depot", end_point="Example Market")
    assignments = []
    for number in range(10):
        vehicle = Vehicle.objects.create(fleet=fleet, registration=f"DEMO{index}{number:02}", status=Vehicle.Status.ACTIVE)
        driver = Driver.objects.create(fleet=fleet, name=f"Fictional Driver {index}-{number + 1}",
                                       phone=f"000{index}{number:03}", licence_reference=f"FICTION-{index}-{number + 1}")
        assignment = Assignment(fleet=fleet, driver=driver, vehicle=vehicle,
                                start=datetime.combine(today-timedelta(days=100), time.min, NAIROBI))
        assignment.full_clean()
        assignment.save()
        assignments.append(assignment)

    sessions = []
    for number, assignment in enumerate(assignments):
        # Leave the current day for the two-session proposal fixture.
        count = 98 if number == 0 else 100
        reading = 80000 - count * 100
        for days_ago in range(count, 0, -1):
            start = datetime.combine(today-timedelta(days=days_ago), time(7), NAIROBI)
            sessions.append(session(assignment, route, staff, start, 3, reading, reading+100, 4500))
            reading += 100
    assignment = assignments[0]
    sessions += [
        session(assignment, route, staff, datetime.combine(today, time(7), NAIROBI), 3, 80000, 80140, 7500),
        session(assignment, route, staff, datetime.combine(today, time(10), NAIROBI), 2, 80150, 80210, 3000),
    ]
    # Each assignment has one vehicle and a unique day/time slot. Database checks run on insert.
    OperationSession.objects.bulk_create(sessions)
    expense = Expense.objects.create(vehicle=assignment.vehicle, category=Expense.Category.REPAIRS,
                                     amount=600, date=today, note="Fictional service")
    ServiceRecord.objects.create(expense=expense, service_type="Classroom inspection", next_service=today+timedelta(days=30))
    Collection.objects.create(vehicle=assignment.vehicle, amount=1000, date=today-timedelta(days=100))


def session(assignment, route, staff, start, trips, opening, closing, collected):
    return OperationSession(fleet=assignment.fleet, assignment=assignment, route=route,
                            start=start, end=start+timedelta(hours=2), trip_count=trips,
                            opening_km=opening, closing_km=closing, reported_collections=collected,
                            created_by=staff, updated_by=staff)
