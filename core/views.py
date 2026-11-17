from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from fleet.models import Expense, Vehicle
from fleet.operational_reporting import fleet_activity, operational_context, session_csv, sessions_for_period
from fleet.presentation import chart_context, reporting_period, vehicle_summary, vehicles_with_current_driver
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")


@never_cache
@login_required
@require_GET
def dashboard(request):
    today = timezone.localdate()
    fleet_id = request.user.sacco_id
    vehicles = vehicles_with_current_driver(fleet_id)
    summary = vehicle_summary(request.user)
    context = {"today": today, "vehicles": vehicles[:5], "summary": summary,
               "total_vehicles": summary["total"], "active_vehicles": summary["active"],
               **fleet_activity(fleet_id)}
    if request.user.is_sacco_manager:
        period = reporting_period(request.GET)
        context.update(period, reminders=vehicles.filter(is_active=True, next_service__lte=today+timedelta(days=7)).order_by("next_service")[:4])
        if period["period_valid"]:
            if request.GET.get("format") == "csv":
                return session_csv("dashboard-sessions", sessions_for_period(fleet_id, period))
            operational = operational_context(request.user, period)
            expenses = Expense.objects.filter(
                vehicle__fleet_id=fleet_id, date__range=(period["range_start"], period["range_end"])
            ).aggregate(total=Sum("amount", default=0))["total"]
            context.update(operational, period_out=expenses, difference=operational["reported"]-expenses,
                           **chart_context(request.user, period))
    return render(request, "core/dashboard.html", context)



@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
