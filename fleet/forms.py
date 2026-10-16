from django import forms
from .models import Collection, Expense, Vehicle, normalize_registration


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["registration", "driver", "route", "status", "capacity", "last_service", "next_service"]
        labels = {"driver": "Assigned driver", "last_service": "Last service", "next_service": "Next service"}
        widgets = {
            "registration": forms.TextInput(attrs={"placeholder": "e.g. KDA 284K", "autofocus": True}),
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
