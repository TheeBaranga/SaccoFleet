from django.urls import path
from . import operations_views as operations, views

urlpatterns = [
    path("maintenance/record/", views.record_service, name="record_service"),
    path("maintenance/<int:pk>/edit/", views.record_service, name="edit_service"),
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

for section in operations.REGISTERS:
    options = {"section": section}
    urlpatterns += [
        path(f"{section}/", operations.register, options, name=section),
        path(f"{section}/add/", operations.edit_register, options, name=f"add_{section}"),
        path(f"{section}/<int:pk>/edit/", operations.edit_register, options, name=f"edit_{section}"),
        path(f"{section}/<int:pk>/deactivate/", operations.deactivate_register, options, name=f"deactivate_{section}"),
    ]

urlpatterns += [
    path("assignments/", operations.assignments, name="assignments"),
    path("assignments/add/", operations.edit_assignment, name="add_assignment"),
    path("assignments/<int:pk>/edit/", operations.edit_assignment, name="edit_assignment"),
    path("daily-operations/", operations.daily_operations, name="daily_operations"),
    path("daily-operations/add/", operations.add_operation, name="add_operation"),
    path("daily-operations/<int:pk>/", operations.operation_detail, name="operation_detail"),
    path("daily-operations/<int:pk>/edit/", operations.edit_operation, name="edit_operation"),
]
