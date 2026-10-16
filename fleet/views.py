from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .forms import CollectionForm, VehicleForm
from .models import Fleet, Vehicle


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
    return render(request, "fleet/form.html", {"form": form, "heading": "Add vehicle", "description": "Add a vehicle to your fleet.", "button_label": "Save vehicle", "nav_section": "vehicles"})


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
    return render(request, "fleet/form.html", {"form": form, "heading": "Record collection", "description": "Record a vehicle’s collections in whole Kenyan shillings.", "button_label": "Save collection", "no_vehicles": not has_vehicles})
