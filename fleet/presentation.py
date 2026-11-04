"""Shared, owner-scoped summaries for dashboard and finance pages."""
from datetime import timedelta
from django.db.models import Count, F, Q, Sum
from .models import Collection, Expense, Vehicle


def vehicle_summary(owner):
    return Vehicle.objects.filter(fleet__owner=owner).aggregate(
        total=Count("pk"), active=Count("pk", filter=Q(status="active")),
        idle=Count("pk", filter=Q(status="idle")), maintenance=Count("pk", filter=Q(status="maintenance")))


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
    from django.db.models.functions import TruncWeek, TruncMonth
    start = start or today - timedelta(days=6)
    days = (today-start).days + 1
    trunc = None if days <= 14 else TruncWeek if days <= 90 else TruncMonth

    def bucket(day):
        if days <= 14:
            return day
        if days <= 90:
            return day - timedelta(days=day.weekday())
        return day.replace(day=1)

    def daily(model):
        records = model.objects.filter(vehicle__fleet__owner=owner, date__range=(start, today))
        if vehicle is not None:
            records = records.filter(vehicle=vehicle)
        return dict(records.order_by().annotate(bucket=trunc("date") if trunc else F("date"))
                    .values_list("bucket").annotate(total=Sum("amount")))

    incoming, outgoing = daily(Collection), daily(Expense)
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
