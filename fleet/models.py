from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_registration(value):
    return "".join(value.upper().split())


class Fleet(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_fleet")
    name = models.CharField(max_length=100, default="Sacco Fleet")

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IDLE = "idle", "Idle"
        MAINTENANCE = "maintenance", "Maintenance"

    fleet = models.ForeignKey(Fleet, on_delete=models.CASCADE, related_name="vehicles")
    registration = models.CharField(max_length=20)
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    driver = models.CharField(max_length=100, blank=True)
    route = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IDLE)
    capacity = models.PositiveSmallIntegerField(default=14, validators=[MinValueValidator(1)])
    last_service = models.DateField(null=True, blank=True)
    next_service = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["registration"]
        constraints = [
            models.UniqueConstraint(Lower("registration"), "fleet", name="fleet_vehicle_registration_unique"),
            models.CheckConstraint(condition=models.Q(capacity__gte=1), name="fleet_vehicle_positive_capacity"),
            models.CheckConstraint(
                condition=models.Q(last_service__isnull=True) | models.Q(next_service__isnull=True) | models.Q(next_service__gte=models.F("last_service")),
                name="fleet_vehicle_service_dates_ordered",
            ),
            models.CheckConstraint(condition=models.Q(status__in=["active", "idle", "maintenance"]), name="fleet_vehicle_known_status"),
        ]

    def clean(self):
        super().clean()
        self.registration = normalize_registration(self.registration)
        if self.last_service and self.next_service and self.next_service < self.last_service:
            raise ValidationError({"next_service": "Next service must be on or after the last service date."})

    def save(self, *args, **kwargs):
        self.registration = normalize_registration(self.registration)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.registration


class Collection(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="collections")
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Amount in whole Kenyan shillings.")
    date = models.DateField(default=timezone.localdate, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=1), name="fleet_collection_positive_amount")]

    def clean(self):
        super().clean()
        if self.date and self.date > timezone.localdate():
            raise ValidationError({"date": "Collections cannot be recorded for a future date."})

    def __str__(self):
        return f"{self.vehicle} - KSh {self.amount}"


class Expense(models.Model):
    class Category(models.TextChoices):
        FUEL = "fuel", "Fuel"
        REPAIRS = "repairs", "Repairs"
        INSURANCE = "insurance", "Insurance"
        OTHER = "other", "Other"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.FUEL)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Amount in whole Kenyan shillings.")
    date = models.DateField(default=timezone.localdate, db_index=True)
    note = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def clean(self):
        super().clean()
        if self.date and self.date > timezone.localdate():
            raise ValidationError({"date": "Expenses cannot be recorded for a future date."})

    def __str__(self):
        return f"{self.vehicle} - {self.get_category_display()} KSh {self.amount}"


class ServiceRecord(models.Model):
    """Service history references its single accounting entry; never duplicate costs."""
    expense = models.OneToOneField(Expense, on_delete=models.CASCADE, related_name="service_record")
    service_type = models.CharField(max_length=100)
    notes = models.TextField(blank=True, max_length=2000)
    next_service = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-expense__date", "-pk"]

    def __str__(self):
        return f"{self.expense.vehicle} — {self.service_type}"


class Driver(models.Model):
    fleet = models.ForeignKey(Fleet, on_delete=models.PROTECT, related_name="drivers")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=32)
    licence_reference = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class Route(models.Model):
    fleet = models.ForeignKey(Fleet, on_delete=models.PROTECT, related_name="routes")
    name = models.CharField(max_length=100)
    start_point = models.CharField(max_length=100)
    end_point = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return f"{self.name} ({self.start_point} – {self.end_point})"


class Assignment(models.Model):
    fleet = models.ForeignKey(Fleet, on_delete=models.PROTECT, related_name="assignments")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="assignments")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="assignments")
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end__isnull=True) | models.Q(end__gt=models.F("start")),
                                   name="assignment_dates_ordered"),
        ]
        indexes = [
            models.Index(fields=["fleet", "driver", "start"]),
            models.Index(fields=["fleet", "vehicle", "start"]),
        ]

    def __str__(self):
        start = timezone.localtime(self.start).strftime("%d %b %Y %H:%M")
        end = timezone.localtime(self.end).strftime("%d %b %Y %H:%M") if self.end else "ongoing"
        return f"{self.vehicle} · {self.driver} · {start} to {end}"

    def clean(self):
        super().clean()
        errors = tenant_errors(self, ("driver", "vehicle"))
        previous = Assignment.objects.filter(pk=self.pk).first() if self.pk else None
        for field in ("driver", "vehicle"):
            reference = related_record(self, field)
            if reference and not reference.is_active and (not previous or reference.pk != getattr(previous, f"{field}_id")):
                errors[field] = "Choose an active record."
        if self.start and self.end and self.end <= self.start:
            errors["end"] = "End must be after the start."
        if self.start and not errors:
            candidates = Assignment.objects.filter(fleet_id=self.fleet_id).exclude(pk=self.pk)
            overlaps = candidates.filter(models.Q(end__isnull=True) | models.Q(end__gt=self.start))
            if self.end:
                overlaps = overlaps.filter(start__lt=self.end)
            if self.driver_id and overlaps.filter(driver_id=self.driver_id).exists():
                errors["driver"] = "This driver already has an overlapping assignment."
            if self.vehicle_id and overlaps.filter(vehicle_id=self.vehicle_id).exists():
                errors["vehicle"] = "This vehicle already has an overlapping assignment."
            if previous:
                if (self.driver_id, self.vehicle_id, self.start) != (previous.driver_id, previous.vehicle_id, previous.start):
                    if self.sessions.exists():
                        errors["start"] = "An assignment with saved sessions keeps its original driver, vehicle and start."
                if self.end and self.sessions.filter(end__gt=self.end).exists():
                    errors["end"] = "End must be on or after the last saved session ends."
        if errors:
            raise ValidationError(errors)


def related_record(instance, field):
    try:
        return getattr(instance, field)
    except ObjectDoesNotExist:
        return None


def tenant_errors(instance, fields):
    return {
        field: "Choose a record from your SACCO."
        for field in fields
        if (record := related_record(instance, field))
        and getattr(record, "fleet_id", getattr(record, "sacco_id", None)) != instance.fleet_id
    }


class OperationSession(models.Model):
    fleet = models.ForeignKey(Fleet, on_delete=models.PROTECT, related_name="operation_sessions")
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="sessions")
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="sessions")
    start = models.DateTimeField()
    end = models.DateTimeField()
    trip_count = models.PositiveIntegerField()
    opening_km = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    closing_km = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    reported_collections = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True, max_length=2000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_sessions")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "route", "start"], name="operation_unique_submission"),
            models.CheckConstraint(condition=models.Q(end__gt=models.F("start")), name="operation_dates_ordered"),
            models.CheckConstraint(
                condition=models.Q(opening_km__gte=0, closing_km__gte=models.F("opening_km"),
                                   trip_count__gte=0, reported_collections__gte=0),
                name="operation_valid_amounts",
            ),
        ]
        indexes = [models.Index(fields=["fleet", "start"])]

    @property
    def distance_km(self):
        return self.closing_km - self.opening_km

    def clean(self):
        super().clean()
        errors = tenant_errors(self, ("assignment", "route", "created_by", "updated_by"))
        assignment = related_record(self, "assignment")
        route = related_record(self, "route")
        if route and not route.is_active:
            original_route = OperationSession.objects.filter(pk=self.pk).values_list("route_id", flat=True).first() if self.pk else None
            if original_route != route.pk:
                errors["route"] = "Choose an active route."
        if self.opening_km is not None and self.closing_km is not None and self.closing_km < self.opening_km:
            errors["closing_km"] = "Closing odometer must be at least the opening odometer."
        if self.start and self.end:
            if self.end <= self.start:
                errors["end"] = "End must be after the start."
            if assignment and not errors:
                if self.start < assignment.start:
                    errors["start"] = "Start must be within the assignment period."
                if assignment.end and self.end > assignment.end:
                    errors["end"] = "End must be within the assignment period."
                candidates = OperationSession.objects.filter(fleet_id=self.fleet_id).exclude(pk=self.pk)
                if candidates.filter(assignment_id=self.assignment_id, route_id=self.route_id, start=self.start).exists():
                    errors["start"] = "A session already exists for this assignment, route and start."
                elif candidates.filter(assignment__vehicle_id=assignment.vehicle_id, start__lt=self.end, end__gt=self.start).exists():
                    errors["start"] = "This vehicle already has an overlapping session."
        if errors:
            raise ValidationError(errors)
