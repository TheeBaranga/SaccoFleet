from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_registration(value):
    return "".join(value.upper().split())


class Fleet(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fleet")
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
    driver = models.CharField(max_length=100, blank=True)
    route = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IDLE)
    capacity = models.PositiveSmallIntegerField(default=14, validators=[MinValueValidator(1)])
    last_service = models.DateField(null=True, blank=True)
    next_service = models.DateField(null=True, blank=True)
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
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="collections")
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
