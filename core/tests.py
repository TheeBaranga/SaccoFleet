from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class FoundationTests(TestCase):
    def test_home_redirects_to_login_when_signed_out(self):
        self.assertRedirects(self.client.get(reverse("home")), reverse("login"))

    def test_home_redirects_to_dashboard_when_signed_in(self):
        user = get_user_model().objects.create_user("owner@example.com", "test-password")
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("home")), reverse("dashboard"))

    def test_dashboard_requires_login(self):
        self.assertRedirects(self.client.get(reverse("dashboard")), "/login/?next=/dashboard/", fetch_redirect_response=False)

    def test_health_reports_only_status(self):
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})

    def test_admin_requires_login(self):
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/", fetch_redirect_response=False)
