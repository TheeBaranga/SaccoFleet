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
from .forms import CollectionForm, VehicleForm
from .models import Collection, Fleet, Vehicle


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
