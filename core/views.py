from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from fleet.models import Collection, Expense, Vehicle
from fleet.presentation import chart_context, reporting_period, vehicle_summary
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
    period = reporting_period(request.GET)
    context = {"today": today, "total_vehicles": summary["total"], "active_vehicles": summary["active"],
               "vehicles": vehicles[:5], "summary": summary, **period,
               "reminders": vehicles.filter(next_service__lte=today+timedelta(days=7)).order_by("next_service")[:4]}
    if period["period_valid"]:
        selected = Q(date__range=(period["range_start"], period["range_end"]))
        def totals(model):
            return model.objects.filter(vehicle__fleet__owner=request.user).aggregate(
                selected=Sum("amount", filter=selected), today=Sum("amount", filter=Q(date=today)))
        incoming, outgoing = totals(Collection), totals(Expense)
        context.update({"todays_collections": f"{incoming['today'] or 0:,}",
                        "todays_expenses": outgoing["today"] or 0,
                        "period_in": incoming["selected"] or 0, "period_out": outgoing["selected"] or 0,
                        "profit": (incoming["selected"] or 0)-(outgoing["selected"] or 0),
                        "recent_collections": Collection.objects.filter(vehicle__fleet__owner=request.user)
                            .filter(selected).select_related("vehicle")[:4],
                        **chart_context(request.user, period)})
    return render(request, "core/dashboard.html", context)



@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
