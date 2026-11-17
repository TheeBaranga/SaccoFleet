from datetime import datetime, time, timedelta

from .models import Assignment, Driver, OperationSession, Route
from .operational_reporting import NAIROBI


def make_session(vehicle, day, amount, *, hour=8, minute=0, trips=1, opening=0, closing=10, creator=None):
    fleet = vehicle.fleet
    start = datetime.combine(day, time(hour, minute), NAIROBI)
    driver, _ = Driver.objects.get_or_create(fleet=fleet, name=f"Fictional driver {vehicle.pk}")
    route, _ = Route.objects.get_or_create(fleet=fleet, name="Fictional route")
    assignment, _ = Assignment.objects.get_or_create(
        fleet=fleet, vehicle=vehicle, driver=driver, defaults={"start": start-timedelta(days=366)},
    )
    creator = creator or fleet.members.get()
    return OperationSession.objects.create(
        fleet=fleet, assignment=assignment, route=route, start=start, end=start+timedelta(minutes=20),
        trip_count=trips, opening_km=opening, closing_km=closing, reported_collections=amount,
        created_by=creator, updated_by=creator,
    )
