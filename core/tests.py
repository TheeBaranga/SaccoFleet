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


class PremiumDashboardTests(TestCase):
    def test_financial_summaries_and_chart_exclude_other_owners(self):
        from datetime import timedelta
        from django.utils import timezone
        from fleet.models import Fleet, Vehicle, Collection, Expense
        today = timezone.localdate()
        owner = get_user_model().objects.create_user('design@example.com', 'test-password')
        other = get_user_model().objects.create_user('other@example.com', 'test-password')
        vehicle = Vehicle.objects.create(fleet=Fleet.objects.create(owner=owner), registration='KDA284K', status='active', next_service=today-timedelta(days=1))
        foreign = Vehicle.objects.create(fleet=Fleet.objects.create(owner=other), registration='OTHER')
        Collection.objects.create(vehicle=vehicle, date=today, amount=5000)
        Expense.objects.create(vehicle=vehicle, date=today, amount=1200)
        Collection.objects.create(vehicle=foreign, date=today, amount=999999)
        Expense.objects.create(vehicle=foreign, date=today, amount=999999)
        self.client.force_login(owner)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['profit'], 3800)
        self.assertEqual(response.context['todays_expenses'], 1200)
        self.assertEqual(response.context['summary']['active'], 1)
        self.assertEqual(response.context['chart'][-1]['collected'], 5000)
        self.assertEqual(list(response.context['reminders']), [vehicle])
        for name in ('vehicles', 'collections', 'expenses', 'maintenance', 'reports'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '999,999')
        response = self.client.get(reverse('expenses'), {'q': 'OTHER', 'period': 'today'})
        self.assertEqual(response.context['money']['total'], 0)
        self.assertEqual(list(response.context['page_obj']), [])
