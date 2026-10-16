from django.contrib import admin
from django.urls import path
from core.views import home, health

urlpatterns = [path("", home, name="home"), path("health/", health, name="health"), path("admin/", admin.site.urls)]
admin.site.site_header = "Saccofleet administration"
admin.site.site_title = "Saccofleet"
