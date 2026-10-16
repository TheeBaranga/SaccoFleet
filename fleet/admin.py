from django.contrib import admin
from .models import Collection, Fleet, Vehicle


@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    search_fields = ("name", "owner__email")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration", "fleet", "driver", "route", "status")
    list_filter = ("status",)
    search_fields = ("registration", "driver", "route")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "amount", "date")
    list_filter = ("date",)
    autocomplete_fields = ("vehicle",)
