import csv
import io
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Collection, Expense, Fleet, ServiceRecord, Vehicle


class DemoFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('demo@example.com', 'test-password')
        other = get_user_model().objects.create_user('other-demo@example.com', 'test-password')
        cls.vehicle = Vehicle.objects.create(fleet=Fleet.objects.create(owner=cls.owner), registration='KDA123A')
        cls.foreign = Vehicle.objects.create(fleet=Fleet.objects.create(owner=other), registration='PRIVATE')

    def setUp(self):
        self.client.force_login(self.owner)
        self.today = timezone.localdate()

    def payload(self, **changes):
        data = {'vehicle': self.vehicle.pk, 'date': self.today.isoformat(), 'service_type': 'Oil change',
                'amount': 2500, 'notes': 'New filter fitted', 'next_service': (self.today+timedelta(days=60)).isoformat()}
        return {**data, **changes}

    def test_service_has_one_expense_and_edit_does_not_duplicate_it(self):
        response = self.client.post(reverse('record_service'), self.payload())
        self.assertRedirects(response, reverse('vehicle_detail', args=[self.vehicle.pk]))
        record = ServiceRecord.objects.get()
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual((record.expense.amount, record.expense.category), (2500, 'repairs'))
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service, self.today)
        self.assertEqual(self.vehicle.next_service, self.today+timedelta(days=60))
        self.client.post(reverse('edit_service', args=[record.pk]), self.payload(amount=3000, notes='Corrected cost'))
        record.refresh_from_db()
        self.assertEqual(record.notes, 'Corrected cost')
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(Expense.objects.get().amount, 3000)
        self.assertEqual(self.client.get(reverse('reports')).context['total_out'], 3000)
        self.assertRedirects(self.client.get(reverse('edit_expense', args=[record.expense_id])), reverse('edit_service', args=[record.pk]))
        self.client.post(reverse('delete_expense', args=[record.expense_id]))
        self.assertTrue(Expense.objects.filter(pk=record.expense_id).exists())
        self.assertTrue(ServiceRecord.objects.filter(pk=record.pk).exists())

    def test_service_rejects_foreign_vehicle_bad_dates_and_nonpositive_costs(self):
        for changes in [{'vehicle': self.foreign.pk}, {'amount': 0}, {'amount': -1},
                        {'date': (self.today+timedelta(days=1)).isoformat()},
                        {'next_service': (self.today-timedelta(days=1)).isoformat()}]:
            response = self.client.post(reverse('record_service'), self.payload(**changes))
            self.assertTrue(response.context['form'].errors)
        self.assertFalse(ServiceRecord.objects.exists())
        self.assertFalse(Expense.objects.exists())

    def test_older_service_does_not_replace_latest_schedule(self):
        self.client.post(reverse('record_service'), self.payload())
        self.client.post(reverse('record_service'), self.payload(date=(self.today-timedelta(days=30)).isoformat(), next_service=''))
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.last_service, self.today)
        self.assertEqual(self.vehicle.next_service, self.today+timedelta(days=60))

    def test_service_transaction_rolls_back_on_history_failure(self):
        with patch('fleet.services.ServiceRecord.save', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('record_service'), self.payload())
        self.assertFalse(Expense.objects.exists())
        self.vehicle.refresh_from_db()
        self.assertIsNone(self.vehicle.last_service)

    def test_foreign_history_is_inaccessible_and_vehicle_delete_cascades(self):
        expense = Expense.objects.create(vehicle=self.foreign, amount=500)
        foreign = ServiceRecord.objects.create(expense=expense, service_type='Private')
        self.assertEqual(self.client.get(reverse('edit_service', args=[foreign.pk])).status_code, 404)
        self.client.post(reverse('record_service'), self.payload())
        self.client.post(reverse('delete_vehicle', args=[self.vehicle.pk]))
        self.assertEqual(ServiceRecord.objects.count(), 1)
        self.assertEqual(Expense.objects.count(), 1)

    def read_csv(self, name, params):
        response = self.client.get(reverse(name), {**params, 'format': 'csv'})
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        return list(csv.reader(io.StringIO(b''.join(response.streaming_content).decode())))

    def test_csv_contains_all_matching_records_and_escapes_formula_text(self):
        self.vehicle.driver = '=HYPERLINK("bad")'
        self.vehicle.save()
        for i in range(23):
            Collection.objects.create(vehicle=self.vehicle, date=self.today, amount=i+1)
        Collection.objects.create(vehicle=self.vehicle, date=self.today-timedelta(days=1), amount=888888)
        Collection.objects.create(vehicle=self.foreign, date=self.today, amount=999999)
        rows = self.read_csv('collections', {'q': 'KDA123A', 'period': 'today', 'page': 2})
        self.assertEqual(len(rows), 24)
        self.assertEqual(rows[1][2], '\'=HYPERLINK("bad")')
        self.assertNotIn('999999', str(rows))
        self.assertNotIn('888888', str(rows))
        Expense.objects.create(vehicle=self.vehicle, amount=150, note=' @SUM(1,2)')
        rows = self.read_csv('expenses', {'period': 'today'})
        self.assertEqual(rows[1][3], "' @SUM(1,2)")
        self.assertEqual(rows[1][4], '150')

    def test_report_export_matches_filtered_summary_and_requires_login(self):
        Collection.objects.create(vehicle=self.vehicle, amount=2000)
        Expense.objects.create(vehicle=self.vehicle, amount=500)
        Collection.objects.create(vehicle=self.vehicle, amount=10000, date=self.today-timedelta(days=30))
        self.assertEqual(len(self.read_csv('reports', {})), 2)
        rows = self.read_csv('reports', {'period': 'today'})
        self.assertEqual(rows[1][2:], ['KDA123A', '2000', '500', '1500'])
        response = self.client.get(reverse('reports'), {'format': 'csv', 'period': 'custom', 'start': 'bad'})
        self.assertFalse(response.context['period_valid'])
        self.assertNotIn('Content-Disposition', response)
        self.client.logout()
        for name in ['collections', 'expenses', 'reports', 'record_service']:
            self.assertEqual(self.client.get(reverse(name), {'format': 'csv'}).status_code, 302)
