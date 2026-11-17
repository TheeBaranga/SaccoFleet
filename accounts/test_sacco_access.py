from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from fleet.models import Vehicle
from .models import User


class FR1SaccoAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user("manager@example.test")
        cls.other = User.objects.create_user("other@example.test")
        cls.staff = User.objects.create_user(
            "staff@example.test", "Example-passphrase-53",
            sacco=cls.manager.sacco, role=User.Role.OPERATIONS,
        )
        cls.vehicle = Vehicle.objects.create(fleet=cls.manager.sacco, registration="SACCO01")
        cls.foreign = Vehicle.objects.create(fleet=cls.other.sacco, registration="SACCO02")

    def staff_data(self):
        return {
            "email": "new@example.test", "first_name": "Sample", "last_name": "Staff",
            "password1": "Example-passphrase-91", "password2": "Example-passphrase-91",
            "sacco": self.other.sacco_id, "role": User.Role.MANAGER, "is_staff": "true",
        }

    def test_fr1_manager_creates_staff_in_own_sacco_and_staff_can_sign_in(self):
        self.client.force_login(self.manager)
        self.assertRedirects(self.client.post(reverse("manage_staff"), self.staff_data()), reverse("manage_staff"))
        staff = User.objects.get(email="new@example.test")
        self.assertEqual((staff.sacco_id, staff.role, staff.is_staff), (self.manager.sacco_id, User.Role.OPERATIONS, False))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.manager.pk))
        self.client.post(reverse("logout"))
        response = self.client.post(reverse("login"), {"username": staff.email, "password": "Example-passphrase-91"})
        self.assertRedirects(response, reverse("dashboard"))

    def test_fr1_public_signup_is_closed_and_staff_cannot_manage_accounts(self):
        self.assertEqual(self.client.post("/signup/", self.staff_data()).status_code, 404)
        self.assertRedirects(self.client.get(reverse("manage_staff")), "/login/?next=/staff/")
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("manage_staff")).status_code, 403)
        self.assertEqual(self.client.post(reverse("manage_staff"), self.staff_data()).status_code, 403)
        self.assertFalse(User.objects.filter(email="new@example.test").exists())

    def test_fr1_staff_can_read_own_register_but_cannot_write_or_access_finances(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("vehicles"))
        self.assertContains(response, self.vehicle.registration)
        self.assertNotContains(response, self.foreign.registration)
        self.assertEqual(self.client.get(reverse("vehicle_detail", args=[self.foreign.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("vehicle_detail", args=[self.vehicle.pk])), "Financial performance")
        for route, args in (("add_vehicle", []), ("edit_vehicle", [self.vehicle.pk]), ("delete_vehicle", [self.vehicle.pk]), ("record_collection", []), ("add_expense", []), ("record_service", [])):
            with self.subTest(route=route):
                self.assertEqual(self.client.post(reverse(route, args=args), {"registration": "FORGED"}).status_code, 403)
        for route in ("collections", "expenses", "maintenance", "reports"):
            self.assertEqual(self.client.get(reverse(route), {"export": "csv"}).status_code, 403)

    def test_fr1_manager_can_deactivate_only_own_operations_staff(self):
        url = reverse("deactivate_staff", args=[self.staff.pk])
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("manage_staff")), self.staff.email)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(reverse("deactivate_staff", args=[self.manager.pk])).status_code, 404)
        self.assertRedirects(self.client.post(url), reverse("manage_staff"))
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertFalse(self.client.login(username=self.staff.email, password="Example-passphrase-53"))

    @patch("accounts.management.commands.bootstrap_sacco.getpass", return_value="Example-passphrase-25")
    def test_fr1_bootstrap_creates_manager_and_new_sacco(self, prompt):
        call_command("bootstrap_sacco", name="Fictional SACCO", email="bootstrap@example.test", stdout=StringIO())
        manager = User.objects.get(email="bootstrap@example.test")
        self.assertTrue(manager.is_sacco_manager)
        self.assertTrue(manager.check_password("Example-passphrase-25"))
        self.assertEqual(manager.sacco.name, "Fictional SACCO")
        self.assertFalse(manager.is_superuser)
