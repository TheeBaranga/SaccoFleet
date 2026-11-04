from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .forms import DateRangeForm
from .models import Collection, Expense, Fleet, Vehicle
from .presentation import cash_flow


class ReportingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('reports@example.com', 'test-password')
        other = get_user_model().objects.create_user('foreign@example.com', 'test-password')
        fleet = Fleet.objects.create(owner=cls.owner)
        cls.vehicle = Vehicle.objects.create(fleet=fleet, registration='KDA100A')
        cls.second = Vehicle.objects.create(fleet=fleet, registration='KDA200A')
        cls.foreign = Vehicle.objects.create(fleet=Fleet.objects.create(owner=other), registration='PRIVATE999')

    def setUp(self):
        self.client.force_login(self.owner)
        self.today = timezone.localdate()

    def custom(self, start, end):
        return {'period': 'custom', 'start': start.isoformat(), 'end': end.isoformat()}

    def test_custom_range_is_inclusive_and_consistent_across_views(self):
        start = self.today-timedelta(days=35)
        end = self.today-timedelta(days=20)
        Collection.objects.create(vehicle=self.vehicle, date=start, amount=4000)
        Collection.objects.create(vehicle=self.vehicle, date=end, amount=6000)
        Collection.objects.create(vehicle=self.vehicle, date=start-timedelta(days=1), amount=50000)
        Collection.objects.create(vehicle=self.vehicle, date=end+timedelta(days=1), amount=50000)
        Collection.objects.create(vehicle=self.second, date=end, amount=2000)
        Collection.objects.create(vehicle=self.foreign, date=end, amount=999999)
        Expense.objects.create(vehicle=self.vehicle, date=end, amount=1000)
        params = self.custom(start, end)
        for name, args, expected in [('dashboard', [], 12000), ('reports', [], 12000),
                                     ('vehicle_detail', [self.vehicle.pk], 10000)]:
            with self.subTest(view=name):
                response = self.client.get(reverse(name, args=args), params)
                self.assertEqual(response.status_code, 200)
                key = 'period_in' if name == 'dashboard' else 'total_in'
                self.assertEqual(response.context[key], expected)
                self.assertEqual(response.context['profit'], expected-1000)
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
        self.assertEqual(response.context['profit'], -700)
        self.assertEqual(response.context['chart'][-1]['spent'], 700)

    def test_year_chart_is_bounded_and_uses_two_queries(self):
        start = self.today-timedelta(days=365)
        Collection.objects.create(vehicle=self.vehicle, amount=1200, date=start)
        Collection.objects.create(vehicle=self.vehicle, amount=1800, date=self.today)
        with self.assertNumQueries(2):
            chart = cash_flow(self.owner, self.today, start)
        self.assertLessEqual(len(chart), 13)
        self.assertEqual(sum(day['collected'] for day in chart), 3000)

    def test_vehicle_history_is_scoped_bounded_and_newest_first(self):
        for i in range(8):
            Collection.objects.create(vehicle=self.vehicle, amount=i+1, date=self.today-timedelta(days=i))
        Collection.objects.create(vehicle=self.second, amount=444444, date=self.today)
        Expense.objects.create(vehicle=self.foreign, amount=999999, date=self.today)
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        records = list(response.context['recent_vehicle_collections'])
        self.assertEqual(len(records), 5)
        self.assertEqual([r.amount for r in records], [1, 2, 3, 4, 5])
        self.assertEqual(response.context['total_in'], 28)
        self.assertNotContains(response, '444,444')
        self.assertNotContains(response, '999,999')

    def test_quick_entry_preselects_vehicle_but_post_and_ownership_win(self):
        for name in ['record_collection', 'add_expense']:
            url = reverse(name)
            response = self.client.get(url, {'vehicle': self.vehicle.pk})
            self.assertEqual(str(response.context['form']['vehicle'].value()), str(self.vehicle.pk))
            response = self.client.get(url, {'vehicle': self.foreign.pk})
            self.assertNotContains(response, self.foreign.registration)
            payload = {'vehicle': self.second.pk, 'amount': 500, 'date': self.today.isoformat(), 'category': 'fuel'}
            response = self.client.post(f'{url}?vehicle={self.vehicle.pk}', payload)
            self.assertEqual(response.status_code, 302)
            model = Collection if name == 'record_collection' else Expense
            self.assertTrue(model.objects.filter(vehicle=self.second, amount=500).exists())
            payload['vehicle'] = self.foreign.pk
            response = self.client.post(f'{url}?vehicle={self.vehicle.pk}', payload)
            self.assertIn('vehicle', response.context['form'].errors)
            self.assertFalse(model.objects.filter(vehicle=self.foreign).exists())
