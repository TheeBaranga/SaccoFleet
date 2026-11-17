from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Assignment, Driver, OperationSession, Route, Vehicle


def time_at(hour):
    return datetime(2026, 11, 16, hour, tzinfo=ZoneInfo("Africa/Nairobi"))


class OperationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("manager@example.test")
        cls.staff = User.objects.create_user("staff@example.test", sacco=cls.manager.sacco, role=User.Role.OPERATIONS)
        cls.other = User.objects.create_user("other@example.test")
        cls.driver = Driver.objects.create(fleet=cls.manager.sacco, name="Example Driver", phone="000000", licence_reference="DEMO-123")
        cls.route = Route.objects.create(fleet=cls.manager.sacco, name="Example Route", start_point="Start", end_point="End")
        cls.vehicle = Vehicle.objects.create(fleet=cls.manager.sacco, registration="EX001")
        cls.other_vehicle = Vehicle.objects.create(fleet=cls.manager.sacco, registration="EX002")
        cls.other_driver = Driver.objects.create(fleet=cls.manager.sacco, name="Second Driver")
        cls.foreign_driver = Driver.objects.create(fleet=cls.other.sacco, name="Private Driver")
        cls.foreign_vehicle = Vehicle.objects.create(fleet=cls.other.sacco, registration="PRIVATE001")
        cls.foreign_route = Route.objects.create(fleet=cls.other.sacco, name="Private Route")
        cls.assignment = Assignment.objects.create(
            fleet=cls.manager.sacco, driver=cls.driver, vehicle=cls.vehicle, start=time_at(7), end=time_at(17),
        )
        cls.foreign_assignment = Assignment.objects.create(
            fleet=cls.other.sacco, driver=cls.foreign_driver, vehicle=cls.foreign_vehicle, start=time_at(7),
        )

    def setUp(self):
        self.client.force_login(self.manager)

    def assignment_data(self, **overrides):
        return {"driver": self.driver.pk, "vehicle": self.vehicle.pk, "start": "2026-11-16T17:00", "end": "", **overrides}

    def session_data(self, **overrides):
        return {
            "assignment": self.assignment.pk, "route": self.route.pk, "start": "2026-11-16T08:00",
            "end": "2026-11-16T10:00", "trip_count": "3", "opening_km": "80000", "closing_km": "80140",
            "reported_collections": "7500", "notes": "Fictional return", **overrides,
        }

    def record_session(self, **overrides):
        return self.client.post(reverse("add_operation"), self.session_data(**overrides))

    def test_fr2_registers_allow_managers_to_create_edit_and_list(self):
        for section, data in (
            ("drivers", {"name": "New Example Driver", "phone": "000111", "licence_reference": "DEMO-456"}),
            ("routes", {"name": "New Example Route", "start_point": "First", "end_point": "Second"}),
        ):
            with self.subTest(section=section):
                data["fleet"] = self.other.sacco_id
                self.assertRedirects(self.client.post(reverse(f"add_{section}"), data), reverse(section))
                response = self.client.get(reverse(section))
                self.assertContains(response, data["name"])
                saved = next(record for record in response.context["records"] if record.name == data["name"])
                self.assertEqual(saved.fleet_id, self.manager.sacco_id)
                self.assertRedirects(self.client.post(reverse(f"edit_{section}", args=[saved.pk]),
                                                      {**data, "name": "Edited Example"}), reverse(section))

    def test_fr3_assignments_reject_driver_and_vehicle_conflicts_and_allow_boundary(self):
        url = reverse("add_assignment")
        for overrides, field in (
            ({"vehicle": self.other_vehicle.pk}, "driver"), ({"driver": self.other_driver.pk}, "vehicle"),
        ):
            with self.subTest(field=field):
                response = self.client.post(url, self.assignment_data(start="2026-11-16T16:00", **overrides))
                self.assertFormError(response.context["form"], field, f"This {field} already has an overlapping assignment.")
        self.assertRedirects(self.client.post(url, self.assignment_data(), follow=False), reverse("assignments"))
        self.assertEqual(Assignment.objects.filter(fleet=self.manager.sacco).count(), 2)
        response = self.client.post(url, self.assignment_data(start="2026-11-16T18:00"))
        self.assertFormError(response.context["form"], "vehicle", "This vehicle already has an overlapping assignment.")

    def test_fr4_daily_operation_saves_distance_and_audit_metadata(self):
        self.client.force_login(self.staff)
        response = self.record_session(fleet=self.other.sacco_id, created_by=self.other.pk)
        record = OperationSession.objects.get()
        self.assertRedirects(response, reverse("operation_detail", args=[record.pk]))
        self.assertEqual((record.distance_km, record.trip_count, record.reported_collections),
                         (Decimal("140"), 3, Decimal("7500")))
        self.assertEqual((record.fleet_id, record.created_by, record.updated_by),
                         (self.manager.sacco_id, self.staff, self.staff))
        self.assertEqual(record.start, time_at(8))
        self.assertContains(self.client.get(reverse("daily_operations"), {"period": "custom", "start": "2026-11-16", "end": "2026-11-16"}), "140.00 km")

    def test_fr5_rejects_invalid_sessions_and_preserves_input(self):
        for changes, field, message in (
            ({"opening_km": "80141"}, "closing_km", "Closing odometer must be at least the opening odometer."),
            ({"trip_count": "-1"}, "trip_count", "Ensure this value is greater than or equal to 0."),
            ({"reported_collections": "-1"}, "reported_collections", "Ensure this value is greater than or equal to 0."),
            ({"opening_km": "-1"}, "opening_km", "Ensure this value is greater than or equal to 0."),
            ({"start": "2026-11-16T06:00"}, "start", "Start must be within the assignment period."),
            ({"end": "2026-11-16T18:00"}, "end", "End must be within the assignment period."),
            ({"end": "2026-11-16T08:00"}, "end", "End must be after the start."),
        ):
            with self.subTest(field=field, changes=changes):
                response = self.record_session(**changes)
                self.assertFormError(response.context["form"], field, message)
                self.assertContains(response, "Fictional return")
                self.assertFalse(OperationSession.objects.exists())

    def test_fr5_duplicate_overlap_and_visible_odometer_gap(self):
        self.assertEqual(self.record_session().status_code, 302)
        response = self.record_session()
        self.assertFormError(response.context["form"], "start", "A session already exists for this assignment, route and start.")
        response = self.record_session(start="2026-11-16T09:00")
        self.assertFormError(response.context["form"], "start", "This vehicle already has an overlapping session.")
        self.assertEqual(self.record_session(start="2026-11-16T10:00", end="2026-11-16T12:00",
                                            opening_km="80150", closing_km="80210").status_code, 302)
        self.assertContains(self.client.get(reverse("daily_operations"), {"period": "custom", "start": "2026-11-16", "end": "2026-11-16"}), "Gap to review")
        latest = OperationSession.objects.first()
        self.assertContains(self.client.get(reverse("operation_detail", args=[latest.pk])), "Odometer gap to review")
        self.assertEqual(latest.opening_km, Decimal("80150"))
        self.assertEqual(OperationSession.objects.count(), 2)

    def test_fr2_deactivation_preserves_history_and_blocks_new_references(self):
        self.record_session()
        for endpoint, record in (
            ("deactivate_drivers", self.driver), ("deactivate_routes", self.route), ("delete_vehicle", self.vehicle),
        ):
            self.assertEqual(self.client.post(reverse(endpoint, args=[record.pk])).status_code, 302)
            record.refresh_from_db()
            self.assertFalse(record.is_active)
        self.assertEqual(OperationSession.objects.get().assignment, self.assignment)
        self.assertEqual(self.record_session(start="2026-11-16T10:00", end="2026-11-16T11:00").status_code, 200)
        response = self.client.post(reverse("add_assignment"), self.assignment_data())
        self.assertIn("vehicle", response.context["form"].errors)
        self.assertEqual(OperationSession.objects.count(), 1)

    def test_fr3_assignment_edits_cannot_invalidate_existing_sessions(self):
        self.record_session()
        url = reverse("edit_assignment", args=[self.assignment.pk])
        for data, field in (
            ({"start": "2026-11-16T07:00", "end": "2026-11-16T09:00"}, "end"),
            ({"start": "2026-11-16T06:00"}, "start"),
        ):
            response = self.client.post(url, self.assignment_data(**data))
            self.assertIn(field, response.context["form"].errors)
            self.assignment.refresh_from_db()
            self.assertEqual((self.assignment.start, self.assignment.end), (time_at(7), time_at(17)))

    def test_fr7_staff_cannot_correct_and_manager_updates_audit_metadata(self):
        self.client.force_login(self.staff)
        self.record_session()
        record = OperationSession.objects.get()
        url = reverse("edit_operation", args=[record.pk])
        data = self.session_data(trip_count=4, updated_by=self.other.pk)
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.client.force_login(self.manager)
        self.assertRedirects(self.client.post(url, data), reverse("operation_detail", args=[record.pk]))
        record.refresh_from_db()
        self.assertEqual((record.trip_count, record.created_by, record.updated_by), (4, self.staff, self.manager))
        self.assertGreater(record.updated_at, record.created_at)

    def test_fr1_direct_foreign_ids_and_staff_register_writes_are_rejected(self):
        self.client.force_login(self.other)
        self.record_session(assignment=self.foreign_assignment.pk, route=self.foreign_route.pk)
        private_session = OperationSession.objects.get()
        self.client.force_login(self.manager)
        for endpoint, pk in (
            ("edit_drivers", self.foreign_driver.pk), ("edit_routes", self.foreign_route.pk),
            ("edit_assignment", self.foreign_assignment.pk), ("operation_detail", private_session.pk),
            ("edit_operation", private_session.pk),
        ):
            self.assertEqual(self.client.get(reverse(endpoint, args=[pk])).status_code, 404)
        for field, pk in (("assignment", self.foreign_assignment.pk), ("route", self.foreign_route.pk)):
            response = self.record_session(**{field: pk})
            self.assertIn(field, response.context["form"].errors)
        self.assertNotContains(self.client.get(reverse("daily_operations"), {"period": "custom", "start": "2026-11-16", "end": "2026-11-16"}), self.foreign_vehicle.registration)
        self.client.force_login(self.staff)
        for endpoint in ("add_drivers", "add_routes", "add_assignment"):
            self.assertEqual(self.client.post(reverse(endpoint), {}).status_code, 403)
        self.assertEqual(OperationSession.objects.count(), 1)
