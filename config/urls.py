from django.contrib import admin
from django.urls import include, path
from core.views import dashboard, home, health

urlpatterns = [
    path("", home, name="home"),
    path("", include("accounts.urls")),
    path("dashboard/", dashboard, name="dashboard"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
]
admin.site.site_header = "Saccofleet administration"
admin.site.site_title = "Saccofleet"
