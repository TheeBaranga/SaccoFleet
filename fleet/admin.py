from django.contrib import admin
from .models import Collection, Expense, Fleet, Vehicle


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ("name", "owner")
    search_fields = ("name", "owner__email")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return ("is_active", "fleet") if obj else ("is_active",)

    list_display = ("registration", "make", "model", "fleet", "driver", "route", "status")
    list_filter = ("status",)
    search_fields = ("registration", "make", "model", "driver", "route")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "amount", "date")
    list_filter = ("date",)
    autocomplete_fields = ("vehicle",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "category", "amount", "date")
    list_filter = ("category", "date")
    autocomplete_fields = ("vehicle",)
