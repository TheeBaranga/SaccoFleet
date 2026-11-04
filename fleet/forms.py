from datetime import timedelta
from django.utils import timezone
from django import forms
from .models import Collection, Expense, Vehicle, normalize_registration


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["registration", "make", "model", "driver", "route", "status", "capacity", "last_service", "next_service"]
        labels = {"driver": "Assigned driver", "last_service": "Last service", "next_service": "Next service"}
        widgets = {
            "registration": forms.TextInput(attrs={"placeholder": "e.g. KDA 284K", "autofocus": True}),
            "make": forms.TextInput(attrs={"placeholder": "e.g. Toyota"}),
            "model": forms.TextInput(attrs={"placeholder": "e.g. Hiace"}),
            "driver": forms.TextInput(attrs={"placeholder": "Driver name"}),
            "route": forms.TextInput(attrs={"placeholder": "e.g. Town – Westlands"}),
            "last_service": forms.DateInput(attrs={"type": "date"}),
            "next_service": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def clean_registration(self):
        registration = normalize_registration(self.cleaned_data["registration"])
        duplicates = Vehicle.objects.filter(fleet__owner=self.owner, registration__iexact=registration).exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("This registration is already in your fleet.")
        return registration


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["vehicle", "amount", "date"]
        labels = {"amount": "Amount (KSh)", "date": "Collection date"}
        widgets = {"amount": forms.NumberInput(attrs={"min": 1, "step": 1}), "date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.filter(fleet__owner=owner)
        self.fields["vehicle"].empty_label = "Choose a vehicle"


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["vehicle", "category", "amount", "date", "note"]
        labels = {"amount": "Amount (KSh)", "date": "Expense date"}
        widgets = {
            "amount": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "e.g. Brake pads"}),
        }

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = Vehicle.objects.filter(fleet__owner=owner)
        self.fields["vehicle"].empty_label = "Choose a vehicle"


class DateRangeForm(forms.Form):
    period = forms.ChoiceField(choices=[("today", "Today"), ("7", "Last 7 days"),
        ("month", "This month"), ("custom", "Custom range")], initial="7")
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        today = timezone.localdate()
        period = data.get("period")
        if period == "custom":
            for field in ("start", "end"):
                if not data.get(field) and field not in self.errors:
                    self.add_error(field, "Choose a date for your custom range.")
            start, end = data.get("start"), data.get("end")
            if start and end:
                if start > end:
                    self.add_error("end", "End date must be on or after the start date.")
                elif end > today:
                    self.add_error("end", "Choose today or an earlier date.")
                elif (end-start).days > 365:
                    self.add_error("end", "Choose a range of up to 366 days.")
        elif period:
            data["end"] = today
            data["start"] = {"today": today, "7": today-timedelta(days=6),
                             "month": today.replace(day=1)}[period]
        return data
