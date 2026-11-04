from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from fleet.models import Collection, Expense, Vehicle
from fleet.presentation import cash_flow, vehicle_summary
from datetime import timedelta
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
    vehicles = Vehicle.objects.filter(fleet__owner=request.user)
    summary = vehicle_summary(request.user)
    collections = Collection.objects.filter(vehicle__fleet__owner=request.user, date=today)
    amount = collections.aggregate(total=Sum("amount"))["total"] or 0
    spent = Expense.objects.filter(vehicle__fleet__owner=request.user, date=today).aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "core/dashboard.html", {
        "today": today, "total_vehicles": summary["total"], "active_vehicles": summary["active"],
        "todays_collections": f"{amount:,}", "vehicles": vehicles[:5],
        "todays_expenses": spent, "profit": amount-spent, "summary": summary,
        "chart": cash_flow(request.user, today),
        "recent_collections": Collection.objects.filter(vehicle__fleet__owner=request.user).select_related("vehicle")[:4],
        "reminders": vehicles.filter(next_service__lte=today+timedelta(days=7)).order_by("next_service")[:4],
    })


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
