from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()

class EmailAccountTests(TestCase):
    def test_email_is_normalized_and_password_hashed(self):
        user = User.objects.create_user(" Admin@Example.COM ", "A-long-test-password-495!")
        self.assertEqual(user.email, "admin@example.com")
        self.assertNotEqual(user.password, "A-long-test-password-495!")
        self.assertTrue(user.check_password("A-long-test-password-495!"))
        self.assertIsNotNone(authenticate(email=user.email, password="A-long-test-password-495!"))
        self.assertIsNone(authenticate(email=user.email, password="incorrect"))

    def test_duplicate_email_cannot_bypass_database_constraint(self):
        User.objects.create_user("admin@example.com", "password")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="ADMIN@EXAMPLE.COM")])

    def test_blank_email_is_rejected(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("   ")

    def test_inactive_user_cannot_sign_in(self):
        user = User.objects.create_user("inactive@example.com", "password", is_active=False)
        self.assertIsNone(authenticate(email=user.email, password="password"))

    def test_superuser_flags_are_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", "password", is_staff=False)
        user = User.objects.create_superuser("owner@example.com", "password")
        self.assertTrue(user.is_staff and user.is_superuser)


from datetime import timedelta
from unittest.mock import patch
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from .models import LoginBucket
from .rate_limit import reserve_attempt, IP_LIMIT, WINDOW_SECONDS


class LoginFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("driver@example.com", "A-long-test-password-495!")

    def credentials(self, **changes):
        data = {"username": self.user.email, "password": "A-long-test-password-495!"}
        return {**data, **changes}

    def test_login_page_has_real_form_and_password_autocomplete(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Welcome back")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertContains(response, "Email address")
        self.assertContains(response, "Contact your Sacco administrator")

    def test_login_creates_session_and_opens_dashboard(self):
        old_session = self.client.session
        old_session["before_login"] = True
        old_session.save()
        response = self.client.post(reverse("login"), self.credentials())
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertNotEqual(self.client.session.session_key, old_session.session_key)
        self.assertContains(self.client.get(reverse("dashboard")), self.user.email)
        self.assertTrue(response.cookies["sessionid"]["httponly"])

    def test_mixed_case_email_can_sign_in(self):
        response = self.client.post(reverse("login"), self.credentials(username=" DRIVER@EXAMPLE.COM "))
        self.assertRedirects(response, reverse("dashboard"))

    def test_bad_password_does_not_create_authenticated_session_or_echo_password(self):
        response = self.client.post(reverse("login"), self.credentials(password="secret-wrong-password"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "The email or password is incorrect.")
        self.assertNotContains(response, "secret-wrong-password")

    def test_unknown_and_inactive_accounts_have_same_error(self):
        unknown = self.client.post(reverse("login"), self.credentials(username="unknown@example.com"))
        self.user.is_active = False
        self.user.save()
        inactive = self.client.post(reverse("login"), self.credentials())
        self.assertEqual(unknown.context["form"].non_field_errors(), inactive.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_email_has_accessible_error(self):
        response = self.client.post(reverse("login"), self.credentials(username="not-an-email"))
        self.assertContains(response, "Enter a valid email address.")
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'id="id_username_error"')

    def test_external_next_url_cannot_redirect_off_site(self):
        response = self.client.post(reverse("login"), self.credentials(next="https://attacker.example/"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_local_next_url_is_preserved(self):
        response = self.client.post(reverse("login"), self.credentials(next="/dashboard/?view=all"))
        self.assertRedirects(response, "/dashboard/?view=all")

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("login")), reverse("dashboard"))

    def test_sign_out_rejects_get_and_clears_the_server_session(self):
        self.client.force_login(self.user)
        old_cookie = self.client.cookies["sessionid"].value
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        replay = Client()
        replay.cookies["sessionid"] = old_cookie
        self.assertRedirects(replay.get(reverse("dashboard")), "/login/?next=/dashboard/", fetch_redirect_response=False)

    def test_login_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("login"), self.credentials()).status_code, 403)
        response = client.get(reverse("login"))
        token = response.cookies["csrftoken"].value
        response = client.post(reverse("login"), {**self.credentials(), "csrfmiddlewaretoken": token})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        client.get(reverse("dashboard"))
        token = client.cookies["csrftoken"].value
        self.assertRedirects(client.post(reverse("logout"), {"csrfmiddlewaretoken": token}), reverse("login"))

    def test_sensitive_pages_are_not_cached(self):
        self.assertIn("no-store", self.client.get(reverse("login"))["Cache-Control"])
        self.client.force_login(self.user)
        self.assertIn("no-store", self.client.get(reverse("dashboard"))["Cache-Control"])


class LoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("driver@example.com", "A-long-test-password-495!")

    def test_email_limit_applies_across_ip_addresses_and_expires(self):
        for number in range(5):
            response = self.client.post(reverse("login"), {"username": "DRIVER@example.com", "password": "wrong"}, REMOTE_ADDR=f"192.0.2.{number}")
            self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": "A-long-test-password-495!"}, REMOTE_ADDR="192.0.2.99")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "600")
        self.assertNotIn("_auth_user_id", self.client.session)
        later = timezone.now() + timedelta(seconds=WINDOW_SECONDS + 1)
        with patch("accounts.rate_limit.timezone.now", return_value=later):
            response = self.client.post(reverse("login"), {"username": self.user.email, "password": "A-long-test-password-495!"})
        self.assertRedirects(response, reverse("dashboard"))

    def test_ip_limit_covers_different_emails(self):
        for number in range(IP_LIMIT):
            self.assertIsNotNone(reserve_attempt(f"person{number}@example.com", "192.0.2.1"))
        response = self.client.post(reverse("login"), {"username": "fresh@example.com", "password": "wrong"}, REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="198.51.100.7")
        self.assertEqual(response.status_code, 429)

    def test_successful_login_does_not_consume_failure_allowance(self):
        response = self.client.post(reverse("login"), {"username": self.user.email, "password": "A-long-test-password-495!"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(all(bucket.attempts == 0 for bucket in LoginBucket.objects.all()))

    def test_counters_do_not_store_raw_identifiers(self):
        reserve_attempt("private@example.com", "192.0.2.1")
        for bucket in LoginBucket.objects.all():
            self.assertEqual(len(bucket.key), 64)
            self.assertNotIn("@", bucket.key)
            self.assertNotIn("192.0.2.1", bucket.key)

    def test_cleanup_preserves_current_counters(self):
        LoginBucket.objects.create(key="old", started_at=timezone.now()-timedelta(days=2))
        LoginBucket.objects.create(key="current", started_at=timezone.now())
        call_command("prune_login_buckets", verbosity=0)
        self.assertFalse(LoginBucket.objects.filter(key="old").exists())
        self.assertTrue(LoginBucket.objects.filter(key="current").exists())
