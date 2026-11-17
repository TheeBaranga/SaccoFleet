import csv
from decimal import Decimal
from urllib.parse import urlsplit
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .forms import DateRangeForm
from .models import Collection, Expense, Vehicle
from .reporting_test_data import make_session
from .presentation import cash_flow


class ReportingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('reports@example.com', 'test-password')
        other = get_user_model().objects.create_user('foreign@example.com', 'test-password')
        fleet = cls.owner.sacco
        cls.vehicle = Vehicle.objects.create(fleet=fleet, registration='KDA100A')
        cls.second = Vehicle.objects.create(fleet=fleet, registration='KDA200A')
        cls.foreign = Vehicle.objects.create(fleet=other.sacco, registration='PRIVATE999')

    def setUp(self):
        self.client.force_login(self.owner)
        self.today = timezone.localdate()

    def custom(self, start, end):
        return {'period': 'custom', 'start': start.isoformat(), 'end': end.isoformat()}

    def test_custom_range_is_inclusive_and_consistent_across_views(self):
        start = self.today-timedelta(days=35)
        end = self.today-timedelta(days=20)
        make_session(self.vehicle, start, 4000)
        make_session(self.vehicle, end, 6000)
        make_session(self.vehicle, start-timedelta(days=1), 50000)
        make_session(self.vehicle, end+timedelta(days=1), 50000)
        make_session(self.second, end, 2000)
        make_session(self.foreign, end, 999999)
        Expense.objects.create(vehicle=self.vehicle, date=end, amount=1000)
        params = self.custom(start, end)
        for name, args, expected in [('dashboard', [], 12000), ('reports', [], 12000),
                                     ('vehicle_detail', [self.vehicle.pk], 10000)]:
            with self.subTest(view=name):
                response = self.client.get(reverse(name, args=args), params)
                self.assertEqual(response.status_code, 200)
                key = 'total_in' if name == 'vehicle_detail' else 'reported'
                self.assertEqual(response.context[key], expected)
                self.assertEqual(response.context['difference'], expected-1000)
                self.assertEqual(sum(day['collected'] for day in response.context['chart']), expected)
                self.assertEqual(sum(day['spent'] for day in response.context['chart']), 1000)
                self.assertEqual(response.context['chart_granularity'], 'Weekly')
                self.assertNotContains(response, 'PRIVATE999')

    def test_date_validation_and_invalid_view_states(self):
        cases = [self.custom(self.today, self.today-timedelta(days=1)),
                 self.custom(self.today, self.today+timedelta(days=1)),
                 self.custom(self.today-timedelta(days=366), self.today),
                 {'period': 'custom', 'start': 'invalid', 'end': ''},
                 {'period': 'custom'}, {'period': 'unknown'}]
        for params in cases:
            with self.subTest(params=params):
                self.assertFalse(DateRangeForm(params).is_valid())
                for name, args in [('dashboard', []), ('reports', []), ('vehicle_detail', [self.vehicle.pk])]:
                    response = self.client.get(reverse(name, args=args), params)
                    self.assertEqual(response.status_code, 200)
                    self.assertFalse(response.context['period_valid'])
                    self.assertContains(response, 'Please correct the date range')
                    self.assertNotContains(response, 'Selected period totals')

    def test_presets_use_local_dates(self):
        for period, start in [('today', self.today), ('7', self.today-timedelta(days=6)),
                               ('month', self.today.replace(day=1))]:
            form = DateRangeForm({'period': period})
            self.assertTrue(form.is_valid())
            self.assertEqual((form.cleaned_data['start'], form.cleaned_data['end']), (start, self.today))

    def test_empty_chart_and_expense_only_activity(self):
        response = self.client.get(reverse('reports'))
        self.assertContains(response, 'No transactions in this period')
        Expense.objects.create(vehicle=self.vehicle, amount=700, date=self.today)
        response = self.client.get(reverse('reports'))
        self.assertNotContains(response, 'No transactions in this period')
        self.assertEqual(response.context['difference'], -700)
        self.assertEqual(response.context['chart'][-1]['spent'], 700)

    def test_year_chart_is_bounded_and_uses_two_queries(self):
        start = self.today-timedelta(days=365)
        make_session(self.vehicle, start, 1200)
        make_session(self.vehicle, self.today, 1800)
        with self.assertNumQueries(2):
            chart = cash_flow(self.owner, self.today, start)
        self.assertLessEqual(len(chart), 13)
        self.assertEqual(sum(day['collected'] for day in chart), 3000)

    def test_vehicle_history_is_scoped_bounded_and_newest_first(self):
        for i in range(8):
            make_session(self.vehicle, self.today-timedelta(days=i), i+1)
        make_session(self.second, self.today, 444444)
        Expense.objects.create(vehicle=self.foreign, amount=999999, date=self.today)
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        records = list(response.context['recent_vehicle_sessions'])
        self.assertEqual(len(records), 5)
        self.assertEqual([r.reported_collections for r in records], [1, 2, 3, 4, 5])
        self.assertEqual(response.context['total_in'], 28)
        self.assertNotContains(response, '444,444')
        self.assertNotContains(response, '999,999')

    def test_quick_entry_preselects_vehicle_but_post_and_ownership_win(self):
        url = reverse("add_expense")
        response = self.client.get(url, {"vehicle": self.vehicle.pk})
        self.assertEqual(str(response.context["form"]["vehicle"].value()), str(self.vehicle.pk))
        payload = {"vehicle": self.second.pk, "amount": 500, "date": self.today.isoformat(), "category": "fuel"}
        response = self.client.post(f"{url}?vehicle={self.vehicle.pk}", payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Expense.objects.filter(vehicle=self.second, amount=500).exists())
        payload["vehicle"] = self.foreign.pk
        response = self.client.post(f"{url}?vehicle={self.vehicle.pk}", payload)
        self.assertIn("vehicle", response.context["form"].errors)

    def test_operation_quick_entry_selects_assignment_from_vehicle(self):
        session = make_session(self.vehicle, self.today, 0)
        url = reverse("add_operation")
        response = self.client.get(url, {"vehicle": self.vehicle.pk})
        self.assertEqual(response.context["form"]["assignment"].value(), session.assignment_id)
        self.assertEqual(self.client.get(url, {"vehicle": self.foreign.pk}).status_code, 404)


    def test_fr6_totals_drilldown_and_all_csvs_match_the_same_sessions(self):
        first = make_session(self.vehicle, self.today, 7500, hour=0, trips=3, opening=80000, closing=80140)
        second = make_session(self.vehicle, self.today, 3000, trips=2, opening=80140, closing=80200)
        make_session(self.vehicle, self.today-timedelta(days=1), 999, hour=23)
        make_session(self.foreign, self.today, 99999, trips=99)
        Collection.objects.create(vehicle=self.vehicle, date=self.today, amount=999999)
        expected = {str(first.pk), str(second.pk)}
        for name in ("dashboard", "reports", "collections"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name), {"period": "today"})
                self.assertEqual((response.context["trips"], response.context["distance"], response.context["reported"]),
                                 (5, Decimal("200"), Decimal("10500")))
                source = self.client.get(response.context["source_url"])
                self.assertEqual({str(record.pk) for record in source.context["page_obj"]}, expected)
                self.assertNotContains(response, "999,999")
        for name in ("dashboard", "reports", "collections", "daily_operations"):
            with self.subTest(export=name):
                response = self.client.get(reverse(name), {"period": "today", "format": "csv"})
                rows = list(csv.DictReader(b"".join(response.streaming_content).decode().splitlines()))
                self.assertEqual({row["Session ID"] for row in rows}, expected)
                self.assertEqual(sum(int(row["Trips"]) for row in rows), 5)
                self.assertEqual(sum(Decimal(row["Distance (km)"]) for row in rows), 200)
                self.assertEqual(sum(Decimal(row["Reported collections (KSh)"]) for row in rows), 10500)
                self.assertTrue(all(row["Start (EAT)"].endswith("+03:00") for row in rows))
        reports = self.client.get(reverse("reports"), {"period": "today"})
        vehicle_link = reports.context["rows"][0]["source_url"]
        self.assertIn(f"vehicle={self.vehicle.pk}", urlsplit(vehicle_link).query)
        self.assertEqual(len(self.client.get(vehicle_link).context["page_obj"]), 2)
        self.assertEqual(self.client.get(reverse("daily_operations"), {"vehicle": self.foreign.pk}).status_code, 404)

    def test_fr6_empty_period_has_zero_totals_and_explicit_empty_state(self):
        make_session(self.vehicle, self.today-timedelta(days=1), 7500)
        for name in ("dashboard", "reports", "collections"):
            response = self.client.get(reverse(name), {"period": "today"})
            self.assertEqual((response.context["trips"], response.context["distance"], response.context["reported"]), (0, 0, 0))
            self.assertContains(response, "No operation sessions found for this period.")
