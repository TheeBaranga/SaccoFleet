from django.urls import path
from . import views

urlpatterns = [
    path("vehicles/", views.vehicles, name="vehicles"),
    path("vehicles/add/", views.add_vehicle, name="add_vehicle"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.edit_vehicle, name="edit_vehicle"),
    path("collections/", views.collections, name="collections"),
    path("maintenance/", views.maintenance, name="maintenance"),
    path("collections/add/", views.record_collection, name="record_collection"),
    path("vehicles/<int:pk>/delete/", views.delete_vehicle, name="delete_vehicle"),
    path("collections/<int:pk>/edit/", views.edit_collection, name="edit_collection"),
    path("collections/<int:pk>/delete/", views.delete_collection, name="delete_collection"),
    path("expenses/", views.expenses, name="expenses"),
    path("expenses/add/", views.add_expense, name="add_expense"),
    path("expenses/<int:pk>/edit/", views.edit_expense, name="edit_expense"),
    path("expenses/<int:pk>/delete/", views.delete_expense, name="delete_expense"),
    path("reports/", views.reports, name="reports"),
]
