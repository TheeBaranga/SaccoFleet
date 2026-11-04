"""Transactional service recording and schedule synchronization."""
from django.db import transaction
from .models import Expense, ServiceRecord, Vehicle


@transaction.atomic
def save_service(form, owner, record=None):
    vehicle = Vehicle.objects.select_for_update().get(pk=form.cleaned_data["vehicle"].pk, fleet__owner=owner)
    expense = form.save(commit=False)
    expense.category = Expense.Category.REPAIRS
    expense.note = form.cleaned_data["service_type"]
    expense.save()
    record = record or ServiceRecord(expense=expense)
    record.service_type = form.cleaned_data["service_type"]
    record.notes = form.cleaned_data["notes"]
    record.next_service = form.cleaned_data["next_service"]
    record.save()
    latest = ServiceRecord.objects.filter(expense__vehicle=vehicle).select_related("expense").first()
    vehicle.last_service = latest.expense.date
    vehicle.next_service = latest.next_service
    vehicle.save(update_fields=["last_service", "next_service"])
    return record
