from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, F, Q, Sum
from django.urls import reverse
from django.utils import timezone

from .exports import csv_response
from .models import Assignment, Driver, OperationSession


NAIROBI = ZoneInfo("Africa/Nairobi")
DISTANCE = F("closing_km") - F("opening_km")


def sessions_for_period(fleet_id, period):
    start = datetime.combine(period["range_start"], time.min, tzinfo=NAIROBI)
    end = datetime.combine(period["range_end"] + timedelta(days=1), time.min, tzinfo=NAIROBI)
    return OperationSession.objects.filter(fleet_id=fleet_id, start__gte=start, start__lt=end)


def operation_totals():
    return {"trips": Sum("trip_count", default=0), "distance": Sum(DISTANCE, default=0),
            "reported": Sum("reported_collections", default=0)}


def operational_context(owner, period):
    sessions = sessions_for_period(owner.sacco_id, period)
    query = {"period": "custom", "start": period["range_start"], "end": period["range_end"]}
    totals = sessions.aggregate(**operation_totals(), session_count=Count("pk"))
    return {
        **totals,
        "has_sessions": bool(totals["session_count"]),
        "source_url": reverse("daily_operations", query=query),
    }


def fleet_activity(fleet_id):
    now = timezone.now()
    ongoing = Assignment.objects.filter(fleet_id=fleet_id, start__lte=now).filter(
        Q(end__isnull=True) | Q(end__gt=now)
    )
    return {
        "active_drivers": Driver.objects.filter(fleet_id=fleet_id, is_active=True).count(),
        "current_assignments": ongoing.count(),
    }


def session_csv(filename, sessions):
    records = sessions.select_related("assignment__vehicle", "assignment__driver", "route")
    rows = (
        (record.pk, record.start.astimezone(NAIROBI).isoformat(), record.end.astimezone(NAIROBI).isoformat(),
         record.assignment.vehicle.registration, record.assignment.driver.name, record.route.name,
         record.trip_count, format(record.distance_km, ".2f"), format(record.reported_collections, ".2f"))
        for record in records.iterator()
    )
    return csv_response(filename, ["Session ID", "Start (EAT)", "End (EAT)", "Vehicle", "Driver", "Route",
                                   "Trips", "Distance (km)", "Reported collections (KSh)"], rows)
