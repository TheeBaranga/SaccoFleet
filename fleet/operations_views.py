from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.permissions import manager_required

from .models import Assignment, Driver, OperationSession, Route, Vehicle
from .operations_forms import AssignmentForm, DriverForm, OperationSessionForm, RouteForm
from .operational_reporting import session_csv, sessions_for_period
from .presentation import reporting_period
from .services import lock_sacco


REGISTERS = {
    "drivers": (Driver, DriverForm, "driver", ("Name", "Phone", "Licence reference", "Status")),
    "routes": (Route, RouteForm, "route", ("Name", "Start point", "End point", "Status")),
}


@never_cache
@login_required
@require_GET
def register(request, section):
    model, _, label, headings = REGISTERS[section]
    records = model.objects.filter(fleet_id=request.user.sacco_id)
    return render(request, "fleet/register.html", {
        "records": records, "section": section, "heading": section.title(),
        "label": label, "headings": headings,
    })


def render_entry(request, form, heading, section, description=""):
    return render(request, "fleet/form.html", {
        "form": form, "heading": heading, "description": description,
        "button_label": "Save", "cancel_url": reverse(section), "back_label": "Back",
    })


@never_cache
@manager_required
@require_http_methods(["GET", "POST"])
def edit_register(request, section, pk=None):
    model, form_type, label, _ = REGISTERS[section]
    fleet_id = request.user.sacco_id
    instance = get_object_or_404(model, fleet_id=fleet_id, pk=pk) if pk else model(fleet_id=fleet_id)
    form = form_type(request.POST if request.method == "POST" else None, instance=instance)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        if pk:
            record.save(update_fields=form.Meta.fields)
        else:
            record.save()
        messages.success(request, f"{label.title()} saved.")
        return redirect(section)
    return render_entry(request, form, f"{'Edit' if pk else 'Add'} {label}", section)


@never_cache
@manager_required
@require_POST
@transaction.atomic
def deactivate_register(request, section, pk):
    model, _, label, _ = REGISTERS[section]
    fleet_id = request.user.sacco_id
    lock_sacco(fleet_id)
    record = get_object_or_404(model, fleet_id=fleet_id, pk=pk)
    record.is_active = False
    record.save(update_fields=["is_active"])
    messages.success(request, f"{label.title()} deactivated.")
    return redirect(section)


@never_cache
@login_required
@require_GET
def assignments(request):
    records = Assignment.objects.filter(fleet_id=request.user.sacco_id).select_related("driver", "vehicle")
    return render(request, "fleet/assignments.html", {"records": records})


@never_cache
@manager_required
@require_http_methods(["GET", "POST"])
def edit_assignment(request, pk=None):
    fleet_id = request.user.sacco_id
    if request.method == "POST":
        with transaction.atomic():
            lock_sacco(fleet_id)
            form = assignment_form(fleet_id, pk, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Assignment saved.")
                return redirect("assignments")
    else:
        form = assignment_form(fleet_id, pk)
    return render_entry(request, form, "Edit assignment" if pk else "Add assignment", "assignments",
                        "Enter dates and times in East Africa Time.")


def assignment_form(fleet_id, pk, data=None):
    instance = get_object_or_404(Assignment, fleet_id=fleet_id, pk=pk) if pk else Assignment(fleet_id=fleet_id)
    return AssignmentForm(data, instance=instance)


def session_records(fleet_id):
    records = OperationSession.objects.filter(fleet_id=fleet_id)
    previous = records.filter(
        assignment__vehicle_id=OuterRef("assignment__vehicle_id"), end__lte=OuterRef("start"),
    ).order_by("-end", "-pk")
    return records.select_related("assignment__vehicle", "assignment__driver", "route").annotate(
        previous_closing_km=Subquery(previous.values("closing_km")[:1])
    )


def requested_vehicle(request):
    value = request.GET.get("vehicle")
    if not value:
        return None
    if not value.isascii() or not value.isdecimal() or len(value) > 19 or int(value) > 2**63-1:
        raise Http404
    return get_object_or_404(Vehicle, fleet_id=request.user.sacco_id, pk=int(value))


@never_cache
@login_required
@require_GET
def daily_operations(request):
    fleet_id = request.user.sacco_id
    period = reporting_period(request.GET)
    vehicle = requested_vehicle(request)
    if vehicle:
        period["filter_vehicle"] = vehicle
    if period["period_valid"]:
        selected = sessions_for_period(fleet_id, period)
        if vehicle:
            selected = selected.filter(assignment__vehicle=vehicle)
        if request.GET.get("format") == "csv":
            return session_csv("daily-operations", selected)
        records = session_records(fleet_id).filter(pk__in=selected.order_by().values("pk"))
        period["page_obj"] = Paginator(records, 25).get_page(request.GET.get("page"))
    return render(request, "fleet/operations.html", period)


@never_cache
@login_required
@require_GET
def operation_detail(request, pk):
    records = session_records(request.user.sacco_id).select_related("created_by", "updated_by")
    return render(request, "fleet/operation_detail.html", {"record": get_object_or_404(records, pk=pk)})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def add_operation(request):
    return edit_operation_form(request)


@never_cache
@manager_required
@require_http_methods(["GET", "POST"])
def edit_operation(request, pk):
    return edit_operation_form(request, pk)


def edit_operation_form(request, pk=None):
    if request.method == "POST":
        with transaction.atomic():
            lock_sacco(request.user.sacco_id)
            form = operation_form(request.user, pk, request.POST)
            if form.is_valid():
                session = form.save()
                messages.success(request, "Operation session saved.")
                return redirect("operation_detail", pk=session.pk)
    else:
        form = operation_form(request.user, pk)
        if not pk and (vehicle := requested_vehicle(request)):
            assignment = form.fields["assignment"].queryset.filter(vehicle=vehicle).first()
            if assignment:
                form.initial["assignment"] = assignment.pk
    return render_entry(request, form, "Correct session" if pk else "Record daily operation", "daily_operations",
                        "Choose an assignment and route. Enter dates and times in East Africa Time.")


def operation_form(user, pk, data=None):
    instance = get_object_or_404(OperationSession, fleet_id=user.sacco_id, pk=pk) if pk else OperationSession(
        fleet_id=user.sacco_id, created_by=user,
    )
    instance.updated_by = user
    return OperationSessionForm(data, instance=instance)
