"""Shared, owner-scoped summaries for dashboard and finance pages."""
from datetime import timedelta
from django.db.models import Count, Q, Sum
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


def cash_flow(owner, today):
    start = today - timedelta(days=6)
    def daily(model):
        return dict(model.objects.filter(vehicle__fleet__owner=owner, date__range=(start, today))
                    .order_by().values_list("date").annotate(total=Sum("amount")))
    incoming, outgoing = daily(Collection), daily(Expense)
    largest = max([*incoming.values(), *outgoing.values(), 1])
    return [{"day": start+timedelta(days=i),
             "collected": incoming.get(start+timedelta(days=i), 0),
             "spent": outgoing.get(start+timedelta(days=i), 0),
             "collected_pct": round(incoming.get(start+timedelta(days=i), 0)*100/largest),
             "spent_pct": round(outgoing.get(start+timedelta(days=i), 0)*100/largest)} for i in range(7)]
