from datetime import datetime

from django import forms
from django.db.models import Q

from .models import Assignment, Driver, OperationSession, Route, Vehicle


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ("name", "phone", "licence_reference")
        widgets = {"phone": forms.TextInput(attrs={"type": "tel"})}


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ("name", "start_point", "end_point")


class LocalDateTimeInput(forms.DateTimeInput):
    supports_microseconds = True

    def __init__(self):
        super().__init__(attrs={"type": "datetime-local", "step": "any"})

    def format_value(self, value):
        if isinstance(value, datetime):
            return value.isoformat(timespec="milliseconds")
        return value


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ("driver", "vehicle", "start", "end")
        widgets = {"start": LocalDateTimeInput(), "end": LocalDateTimeInput()}
        help_texts = {"end": "Leave blank for an ongoing assignment."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, model in (("driver", Driver), ("vehicle", Vehicle)):
            self.fields[name].queryset = model.objects.filter(fleet_id=self.instance.fleet_id).filter(
                Q(is_active=True) | Q(pk=getattr(self.instance, f"{name}_id"))
            )


class OperationSessionForm(forms.ModelForm):
    class Meta:
        model = OperationSession
        fields = ("assignment", "route", "start", "end", "trip_count", "opening_km", "closing_km", "reported_collections", "notes")
        widgets = {"start": LocalDateTimeInput(), "end": LocalDateTimeInput(), "notes": forms.Textarea(attrs={"rows": 3})}
        labels = {"opening_km": "Opening odometer (km)", "closing_km": "Closing odometer (km)",
                  "reported_collections": "Reported collections (KSh)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignment"].queryset = Assignment.objects.filter(
            fleet_id=self.instance.fleet_id
        ).select_related("driver", "vehicle")
        self.fields["route"].queryset = Route.objects.filter(fleet_id=self.instance.fleet_id).filter(
            Q(is_active=True) | Q(pk=self.instance.route_id)
        )
