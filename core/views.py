from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from fleet.models import Collection, Vehicle
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
    totals = vehicles.aggregate(total=Count("id"), active=Count("id", filter=Q(status=Vehicle.Status.ACTIVE)))
    collections = Collection.objects.filter(vehicle__fleet__owner=request.user, date=today)
    amount = collections.aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "core/dashboard.html", {
        "today": today, "total_vehicles": totals["total"], "active_vehicles": totals["active"],
        "todays_collections": f"{amount:,}", "vehicles": vehicles[:5],
    })


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
