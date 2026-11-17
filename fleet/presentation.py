"""Shared, owner-scoped summaries for dashboard and finance pages."""
from datetime import timedelta
from django.db.models import Count, F, Q, Sum
from .models import Expense, Vehicle
from .operational_reporting import NAIROBI, sessions_for_period


def vehicle_summary(owner):
    return Vehicle.objects.filter(fleet_id=owner.sacco_id).aggregate(
        total=Count("pk"), active=Count("pk", filter=Q(is_active=True, status="active")),
        idle=Count("pk", filter=Q(is_active=True, status="idle")), maintenance=Count("pk", filter=Q(is_active=True, status="maintenance")))


def money_summary(records, today):
    result = records.aggregate(total=Sum("amount"), today=Sum("amount", filter=Q(date=today)),
        week=Sum("amount", filter=Q(date__gte=today-timedelta(days=today.weekday()), date__lte=today)),
        month=Sum("amount", filter=Q(date__gte=today.replace(day=1), date__lte=today)))
    return {key: value or 0 for key, value in result.items()}


def reporting_period(params):
    """Validate once; views never query a guessed or invalid period."""
    from .forms import DateRangeForm
    data = params.copy()
    data.setdefault("period", "7")
    form = DateRangeForm(data)
    if not form.is_valid():
        return {"date_form": form, "period_valid": False}
    start, end = form.cleaned_data["start"], form.cleaned_data["end"]
    return {"date_form": form, "period_valid": True, "range_start": start,
            "range_end": end, "range_label": f"{start:%d %b %Y} – {end:%d %b %Y}"}


def cash_flow(owner, today, start=None, vehicle=None):
    """At most 14 daily/weekly/monthly buckets, using two grouped queries."""
    from django.db.models.functions import TruncWeek, TruncMonth, TruncDate
    start = start or today - timedelta(days=6)
    days = (today-start).days + 1
    trunc = None if days <= 14 else TruncWeek if days <= 90 else TruncMonth

    def bucket(day):
        if days <= 14:
            return day
        if days <= 90:
            return day - timedelta(days=day.weekday())
        return day.replace(day=1)

    sessions = sessions_for_period(owner.sacco_id, {"range_start": start, "range_end": today})
    expenses = Expense.objects.filter(vehicle__fleet_id=owner.sacco_id, date__range=(start, today))
    if vehicle is not None:
        sessions = sessions.filter(assignment__vehicle=vehicle)
        expenses = expenses.filter(vehicle=vehicle)
    session_bucket = TruncDate("start", tzinfo=NAIROBI)
    expense_bucket = F("date")
    if trunc:
        session_bucket = trunc(session_bucket)
        expense_bucket = trunc(expense_bucket)

    def grouped(records, grouping, field):
        return dict(records.order_by().annotate(bucket=grouping).values_list("bucket").annotate(total=Sum(field)))

    incoming = grouped(sessions, session_bucket, "reported_collections")
    outgoing = grouped(expenses, expense_bucket, "amount")
    largest = max([*incoming.values(), *outgoing.values(), 1])
    buckets = sorted({bucket(start+timedelta(days=i)) for i in range(days)})
    return [{"day": day, "label": max(day, start).strftime("%d %b") if days <= 90 else day.strftime("%b %Y"),
             "collected": incoming.get(day, 0), "spent": outgoing.get(day, 0),
             "collected_pct": round(incoming.get(day, 0)*100/largest),
             "spent_pct": round(outgoing.get(day, 0)*100/largest)} for day in buckets]


def chart_context(owner, period, vehicle=None):
    chart = cash_flow(owner, period["range_end"], period["range_start"], vehicle)
    days = (period["range_end"]-period["range_start"]).days + 1
    return {"chart": chart, "chart_has_activity": any(day["collected"] or day["spent"] for day in chart),
            "chart_granularity": "Daily" if days <= 14 else "Weekly" if days <= 90 else "Monthly"}
