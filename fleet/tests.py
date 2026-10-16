from datetime import date, datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Collection, Fleet, Vehicle

User = get_user_model()


class FleetDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user("owner@example.com", "test-password")
        cls.other = User.objects.create_user("other@example.com", "test-password")
        cls.fleet = Fleet.objects.create(owner=cls.owner)
        cls.other_fleet = Fleet.objects.create(owner=cls.other)

    def setUp(self):
        self.client.force_login(self.owner)

    def vehicle(self, registration="KDA284K", **kwargs):
        return Vehicle.objects.create(fleet=self.fleet, registration=registration, **kwargs)

    def test_empty_fleet_has_zero_totals_and_real_empty_state(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_vehicles"], 0)
        self.assertEqual(response.context["active_vehicles"], 0)
        self.assertEqual(response.context["todays_collections"], "0")
        self.assertContains(response, "No vehicles yet")
        self.assertNotContains(response, "James Mwangi")
        self.assertIn("no-store", response["Cache-Control"])

    def test_dashboard_counts_and_table_are_scoped_to_owner(self):
        self.vehicle(status=Vehicle.Status.ACTIVE, driver="Own driver")
        self.vehicle("KCB719P", status=Vehicle.Status.IDLE)
        self.vehicle("KCF631R", status=Vehicle.Status.MAINTENANCE)
        Vehicle.objects.create(fleet=self.other_fleet, registration="OTHER999", status=Vehicle.Status.ACTIVE)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_vehicles"], 3)
        self.assertEqual(response.context["active_vehicles"], 1)
        self.assertContains(response, "Own driver")
        self.assertNotContains(response, "OTHER999")
        for status in ("Active", "Idle", "Maintenance"):
            self.assertContains(response, status)

    def test_todays_collections_use_nairobi_date_and_exclude_other_fleets(self):
        own = self.vehicle()
        other = Vehicle.objects.create(fleet=self.other_fleet, registration="OTHER999")
        Collection.objects.create(vehicle=own, amount=12500, date=date(2026, 10, 16))
        Collection.objects.create(vehicle=own, amount=3500, date=date(2026, 10, 16))
        Collection.objects.create(vehicle=own, amount=9999, date=date(2026, 10, 15))
        Collection.objects.create(vehicle=other, amount=77777, date=date(2026, 10, 16))
        # 21:30 UTC is 00:30 the next day in Kenya.
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 15, 21, 30, tzinfo=datetime_timezone.utc)):
            response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["today"], date(2026, 10, 16))
        self.assertEqual(response.context["todays_collections"], "16,000")
        self.assertContains(response, "KSh 16,000")

    def test_dashboard_preview_is_bounded_but_counts_include_all_vehicles(self):
        for number in range(6):
            self.vehicle(f"KDA{number:03}A")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["total_vehicles"], 6)
        self.assertEqual(len(response.context["vehicles"]), 5)
        self.assertNotContains(response, "KDA005A")
        self.assertContains(response, "Showing 5 of 6")
        self.assertContains(response, reverse("vehicles"))

    def test_search_is_scoped_and_understands_registration_spaces(self):
        self.vehicle(driver="Own driver", route="Town – Westlands")
        Vehicle.objects.create(fleet=self.other_fleet, registration="OTHER999", driver="Own driver")
        response = self.client.get(reverse("vehicles"), {"q": "kda 284k"})
        self.assertContains(response, "KDA284K")
        response = self.client.get(reverse("vehicles"), {"q": "Own driver"})
        self.assertContains(response, "KDA284K")
        self.assertNotContains(response, "OTHER999")
        self.assertContains(self.client.get(reverse("vehicles"), {"q": "missing"}), "No vehicles found")

    def test_vehicle_list_is_paginated(self):
        for number in range(21):
            self.vehicle(f"KDA{number:03}A")
        response = self.client.get(reverse("vehicles"))
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(self.client.get(reverse("vehicles"), {"page": 2}), "KDA020A")

    def test_anonymous_requests_cannot_read_or_write_fleet(self):
        client = Client()
        for name in ("vehicles", "add_vehicle", "record_collection", "dashboard"):
            self.assertEqual(client.get(reverse(name)).status_code, 302)
        for name in ("add_vehicle", "record_collection"):
            self.assertEqual(client.post(reverse(name), {}).status_code, 302)
        self.assertFalse(Vehicle.objects.exists())
        self.assertFalse(Collection.objects.exists())

    def test_creating_vehicle_ignores_forged_ownership(self):
        response = self.client.post(reverse("add_vehicle"), {
            "registration": "kda 284k", "driver": "Baranga", "route": "Town – Westlands",
            "status": "active", "capacity": 14, "fleet": self.other_fleet.pk, "owner": self.other.pk,
        })
        self.assertRedirects(response, reverse("dashboard"))
        vehicle = Vehicle.objects.get(registration="KDA284K")
        self.assertEqual(vehicle.fleet, self.fleet)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["active_vehicles"], 1)

    def test_duplicate_registration_is_a_friendly_form_error(self):
        self.vehicle()
        response = self.client.post(reverse("add_vehicle"), {"registration": "kda 284k", "capacity": 14, "status": "idle"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This registration is already in your fleet.")
        self.assertEqual(Vehicle.objects.count(), 1)

    def test_other_fleet_can_have_same_registration(self):
        self.vehicle()
        Vehicle.objects.create(fleet=self.other_fleet, registration="kda 284k")
        self.assertEqual(Vehicle.objects.count(), 2)

    def test_invalid_capacity_status_and_service_dates_are_rejected(self):
        response = self.client.post(reverse("add_vehicle"), {
            "registration": "KDA284K", "capacity": 0, "status": "flying",
            "last_service": "2026-10-16", "next_service": "2026-10-15",
        })
        self.assertEqual(response.status_code, 200)
        errors = response.context["form"].errors
        self.assertIn("capacity", errors)
        self.assertIn("status", errors)
        self.assertIn("next_service", errors)
        self.assertFalse(Vehicle.objects.exists())

    def test_own_collection_updates_dashboard(self):
        own = self.vehicle()
        response = self.client.post(reverse("record_collection"), {"vehicle": own.pk, "amount": "4500", "date": timezone.localdate().isoformat()})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Collection.objects.get().amount, 4500)
        self.assertEqual(self.client.get(reverse("dashboard")).context["todays_collections"], "4,500")

    def test_foreign_vehicle_is_neither_listed_nor_accepted(self):
        self.vehicle()
        other = Vehicle.objects.create(fleet=self.other_fleet, registration="OTHER999")
        self.assertNotContains(self.client.get(reverse("record_collection")), "OTHER999")
        response = self.client.post(reverse("record_collection"), {"vehicle": other.pk, "amount": 100, "date": timezone.localdate().isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertIn("vehicle", response.context["form"].errors)
        self.assertFalse(Collection.objects.exists())

    def test_invalid_collection_amounts_and_future_dates_are_rejected(self):
        own = self.vehicle()
        for amount in ("0", "-1", "12.50"):
            response = self.client.post(reverse("record_collection"), {"vehicle": own.pk, "amount": amount, "date": timezone.localdate().isoformat()})
            self.assertIn("amount", response.context["form"].errors)
        response = self.client.post(reverse("record_collection"), {"vehicle": own.pk, "amount": 100, "date": (timezone.localdate()+timedelta(days=1)).isoformat()})
        self.assertIn("date", response.context["form"].errors)
        self.assertFalse(Collection.objects.exists())

    def test_database_constraints_back_up_form_validation(self):
        own = self.vehicle()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vehicle.objects.create(fleet=self.fleet, registration="kda284k")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vehicle.objects.create(fleet=self.fleet, registration="KDA002A", capacity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Collection.objects.create(vehicle=own, amount=0)

    def test_csrf_is_required_for_fleet_writes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for name in ("add_vehicle", "record_collection"):
            self.assertEqual(client.post(reverse(name), {}).status_code, 403)

    def test_blank_submission_shows_required_fields(self):
        response = self.client.post(reverse("add_vehicle"), {})
        self.assertTrue(response.context["form"].is_bound)
        self.assertIn("registration", response.context["form"].errors)

    def edit_data(self, **overrides):
        data = {"registration": "KDA284K", "driver": "James Mwangi", "route": "Town – Westlands", "status": "active", "capacity": 14, "last_service": "2026-09-20", "next_service": "2026-11-20"}
        data.update(overrides)
        return data

    def test_vehicle_details_show_basic_information_and_maintenance(self):
        vehicle = self.vehicle(driver="James Mwangi", route="Town – Westlands", status=Vehicle.Status.ACTIVE, capacity=14, last_service=date(2026, 9, 20), next_service=date(2026, 11, 20))
        response = self.client.get(reverse("vehicle_detail", args=[vehicle.pk]))
        for text in ("KDA284K", "Active", "James Mwangi", "Town – Westlands", "14 passengers", "20 September 2026", "20 November 2026"):
            self.assertContains(response, text)
        self.assertContains(response, reverse("edit_vehicle", args=[vehicle.pk]))
        self.assertIn("no-store", response["Cache-Control"])

    def test_other_fleets_vehicles_cannot_be_read_or_edited(self):
        other = Vehicle.objects.create(fleet=self.other_fleet, registration="OTHER999", driver="Other driver")
        self.assertEqual(self.client.get(reverse("vehicle_detail", args=[other.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("edit_vehicle", args=[other.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("edit_vehicle", args=[other.pk]), self.edit_data(registration="STOLEN1")).status_code, 404)
        other.refresh_from_db()
        self.assertEqual((other.registration, other.driver, other.fleet), ("OTHER999", "Other driver", self.other_fleet))

    def test_editing_vehicle_saves_changes_and_keeps_ownership(self):
        vehicle = self.vehicle()
        response = self.client.post(reverse("edit_vehicle", args=[vehicle.pk]), self.edit_data(registration="kda 285k", status="maintenance", fleet=self.other_fleet.pk))
        self.assertRedirects(response, reverse("vehicle_detail", args=[vehicle.pk]))
        vehicle.refresh_from_db()
        self.assertEqual((vehicle.registration, vehicle.status, vehicle.driver, vehicle.fleet), ("KDA285K", "maintenance", "James Mwangi", self.fleet))
        self.assertEqual(vehicle.next_service, date(2026, 11, 20))

    def test_editing_to_existing_registration_is_rejected(self):
        self.vehicle("KCB719P")
        vehicle = self.vehicle()
        response = self.client.post(reverse("edit_vehicle", args=[vehicle.pk]), self.edit_data(registration="kcb 719p"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This registration is already in your fleet.")
        self.assertContains(response, "Edit KDA284K")
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.registration, "KDA284K")


class NewFleetTests(TestCase):
    def test_reading_dashboard_does_not_create_records_and_first_vehicle_sets_up_fleet(self):
        user = User.objects.create_user("new@example.com", "test-password")
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("dashboard")), "No vehicles yet")
        self.assertFalse(Fleet.objects.exists())
        self.assertContains(self.client.get(reverse("record_collection")), "Add a vehicle first")
        self.client.get(reverse("add_vehicle"))
        self.assertFalse(Fleet.objects.exists())
        response = self.client.post(reverse("add_vehicle"), {"registration": "KDA284K", "capacity": 14, "status": "idle"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Fleet.objects.get().owner, user)
        self.assertEqual(Vehicle.objects.count(), 1)
