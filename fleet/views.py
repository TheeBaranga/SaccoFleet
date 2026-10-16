from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from datetime import timedelta
from django.db.models import Q, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .forms import CollectionForm, ExpenseForm, VehicleForm
from .models import Collection, Expense, Fleet, Vehicle


@never_cache
@login_required
@require_http_methods(["GET"])
def vehicles(request):
    query = request.GET.get("q", "").strip()[:100]
    records = Vehicle.objects.filter(fleet__owner=request.user)
    if query:
        records = records.filter(Q(registration__icontains="".join(query.split())) | Q(driver__icontains=query) | Q(route__icontains=query))
    page = Paginator(records, 20).get_page(request.GET.get("page"))
    return render(request, "fleet/vehicles.html", {"page_obj": page, "query": query})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def add_vehicle(request):
    form = VehicleForm(request.POST if request.method == "POST" else None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                fleet, _ = Fleet.objects.get_or_create(owner=request.user)
                vehicle = form.save(commit=False)
                vehicle.fleet = fleet
                vehicle.save()
        except IntegrityError:
            if Vehicle.objects.filter(fleet__owner=request.user, registration__iexact=form.cleaned_data["registration"]).exists():
                form.add_error("registration", "This registration is already in your fleet.")
            else:
                raise
        else:
            messages.success(request, f"{vehicle.registration} was added to your fleet.")
            return redirect("dashboard")
    return render(request, "fleet/form.html", {"form": form, "heading": "Add vehicle", "description": "Add a vehicle to your fleet.", "button_label": "Save vehicle", "nav_section": "vehicles", "cancel_url": reverse("vehicles"), "back_label": "Back to vehicles"})


@never_cache
@login_required
@require_http_methods(["GET"])
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, fleet__owner=request.user)
    return render(request, "fleet/vehicle_detail.html", {"vehicle": vehicle})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, fleet__owner=request.user)
    registration = vehicle.registration
    form = VehicleForm(request.POST if request.method == "POST" else None, instance=vehicle, owner=request.user)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        messages.success(request, f"{vehicle.registration} was updated.")
        return redirect("vehicle_detail", pk=pk)
    return render(request, "fleet/form.html", {"form": form, "heading": f"Edit {registration}", "description": "Update this vehicle’s details.", "button_label": "Save changes", "cancel_url": reverse("vehicle_detail", args=[pk]), "back_label": "Back to vehicle"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_collection(request):
    form = CollectionForm(request.POST if request.method == "POST" else None, owner=request.user)
    has_vehicles = Vehicle.objects.filter(fleet__owner=request.user).exists()
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Collection recorded.")
        return redirect("dashboard")
    return render(request, "fleet/form.html", {"form": form, "heading": "Record collection", "description": "Record a vehicle’s collections in whole Kenyan shillings.", "button_label": "Save collection", "no_vehicles": not has_vehicles, "cancel_url": reverse("dashboard"), "back_label": "Back to dashboard"})


@never_cache
@login_required
@require_http_methods(["GET"])
def collections(request):
    records = Collection.objects.filter(vehicle__fleet__owner=request.user).select_related("vehicle")
    total = records.aggregate(total=Sum("amount"))["total"] or 0
    page = Paginator(records, 20).get_page(request.GET.get("page"))
    return render(request, "fleet/collections.html", {"page_obj": page, "total": f"{total:,}"})


@never_cache
@login_required
@require_http_methods(["GET"])
def maintenance(request):
    today = timezone.localdate()
    vehicles = Vehicle.objects.filter(fleet__owner=request.user, next_service__isnull=False).order_by("next_service")
    return render(request, "fleet/maintenance.html", {"vehicles": vehicles, "today": today, "soon": today + timedelta(days=7)})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def delete_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, fleet__owner=request.user)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, f"{vehicle.registration} was deleted.")
        return redirect("vehicles")
    warning = f"This also deletes its {vehicle.collections.count()} collection(s) and {vehicle.expenses.count()} expense(s)."
    return render(request, "fleet/confirm_delete.html", {"heading": f"Delete {vehicle.registration}?", "warning": warning, "cancel_url": reverse("vehicle_detail", args=[pk])})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk, vehicle__fleet__owner=request.user)
    form = CollectionForm(request.POST if request.method == "POST" else None, instance=collection, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Collection updated.")
        return redirect("collections")
    return render(request, "fleet/form.html", {"form": form, "heading": "Edit collection", "description": "Correct this collection.", "button_label": "Save changes", "cancel_url": reverse("collections"), "back_label": "Back to collections"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def delete_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk, vehicle__fleet__owner=request.user)
    if request.method == "POST":
        collection.delete()
        messages.success(request, "Collection deleted.")
        return redirect("collections")
    return render(request, "fleet/confirm_delete.html", {"heading": "Delete this collection?", "warning": f"KSh {collection.amount:,} for {collection.vehicle} on {collection.date:%d %b %Y}.", "cancel_url": reverse("collections")})


@never_cache
@login_required
@require_http_methods(["GET"])
def expenses(request):
    records = Expense.objects.filter(vehicle__fleet__owner=request.user).select_related("vehicle")
    total = records.aggregate(total=Sum("amount"))["total"] or 0
    page = Paginator(records, 20).get_page(request.GET.get("page"))
    return render(request, "fleet/expenses.html", {"page_obj": page, "total": f"{total:,}"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def add_expense(request):
    form = ExpenseForm(request.POST if request.method == "POST" else None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense recorded.")
        return redirect("expenses")
    has_vehicles = Vehicle.objects.filter(fleet__owner=request.user).exists()
    return render(request, "fleet/form.html", {"form": form, "heading": "Record expense", "description": "Record fuel, repairs and other costs in whole Kenyan shillings.", "button_label": "Save expense", "no_vehicles": not has_vehicles, "cancel_url": reverse("expenses"), "back_label": "Back to expenses"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, vehicle__fleet__owner=request.user)
    form = ExpenseForm(request.POST if request.method == "POST" else None, instance=expense, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense updated.")
        return redirect("expenses")
    return render(request, "fleet/form.html", {"form": form, "heading": "Edit expense", "description": "Correct this expense.", "button_label": "Save changes", "cancel_url": reverse("expenses"), "back_label": "Back to expenses"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, vehicle__fleet__owner=request.user)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("expenses")
    return render(request, "fleet/confirm_delete.html", {"heading": "Delete this expense?", "warning": f"{expense.get_category_display()}: KSh {expense.amount:,} for {expense.vehicle} on {expense.date:%d %b %Y}.", "cancel_url": reverse("expenses")})


@never_cache
@login_required
@require_http_methods(["GET"])
def reports(request):
    today = timezone.localdate()
    collections = Collection.objects.filter(vehicle__fleet__owner=request.user)
    expenses = Expense.objects.filter(vehicle__fleet__owner=request.user)

    # Last 7 days, oldest first, for the chart.
    start = today - timedelta(days=6)
    daily_in = dict(collections.filter(date__gte=start).values_list("date").annotate(total=Sum("amount")))
    daily_out = dict(expenses.filter(date__gte=start).values_list("date").annotate(total=Sum("amount")))
    days = [start + timedelta(days=i) for i in range(7)]
    largest = max([daily_in.get(d, 0) for d in days] + [daily_out.get(d, 0) for d in days] + [1])
    chart = [{"day": d, "collected": daily_in.get(d, 0), "spent": daily_out.get(d, 0),
              "collected_pct": round(daily_in.get(d, 0) * 100 / largest), "spent_pct": round(daily_out.get(d, 0) * 100 / largest)} for d in days]

    # All-time totals per vehicle.
    per_in = dict(collections.values_list("vehicle").annotate(total=Sum("amount")))
    per_out = dict(expenses.values_list("vehicle").annotate(total=Sum("amount")))
    rows = []
    for vehicle in Vehicle.objects.filter(fleet__owner=request.user):
        collected, spent = per_in.get(vehicle.pk, 0), per_out.get(vehicle.pk, 0)
        rows.append({"vehicle": vehicle, "collected": collected, "spent": spent, "profit": collected - spent})
    rows.sort(key=lambda row: row["profit"], reverse=True)

    total_in, total_out = sum(per_in.values()), sum(per_out.values())
    return render(request, "fleet/reports.html", {"chart": chart, "rows": rows, "total_in": total_in, "total_out": total_out, "profit": total_in - total_out})
