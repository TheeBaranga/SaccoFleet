from django.urls import path
from . import views

urlpatterns = [
    path("vehicles/", views.vehicles, name="vehicles"),
    path("vehicles/add/", views.add_vehicle, name="add_vehicle"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.edit_vehicle, name="edit_vehicle"),
    path("collections/add/", views.record_collection, name="record_collection"),
]
