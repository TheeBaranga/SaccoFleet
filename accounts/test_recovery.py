import re
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings, Client
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RecoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('recovery@example.com', 'Old-password-123')

    def test_full_reset_flow_and_token_cannot_be_reused(self):
        response = self.client.post(reverse('password_reset'), {'email': self.user.email.upper()})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        url = re.search(r'https?://\S+', mail.outbox[0].body).group()
        path = urlsplit(url).path
        confirm = self.client.get(path)
        self.assertEqual(confirm.status_code, 302)
        response = self.client.post(confirm.url, {'new_password1': 'New-class-demo-123', 'new_password2': 'New-class-demo-123'})
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New-class-demo-123'))
        self.assertFalse(self.user.check_password('Old-password-123'))
        self.assertContains(self.client.get(path), 'invalid or expired')

    def test_unknown_and_inactive_accounts_have_same_response(self):
        inactive = get_user_model().objects.create_user('inactive-reset@example.com', 'test-password', is_active=False)
        for email in ['unknown@example.com', inactive.email]:
            response = self.client.post(reverse('password_reset'), {'email': email})
            self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_is_throttled_and_csrf_protected(self):
        for _ in range(6):
            response = self.client.post(reverse('password_reset'), {'email': self.user.email})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 5)
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('password_reset'), {'email': self.user.email}).status_code, 403)

    def test_local_inbox_works_without_external_email_and_is_local_only(self):
        with TemporaryDirectory() as folder, override_settings(DEBUG=True, EMAIL_FILE_PATH=folder,
                EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend'):
            self.client.post(reverse('password_reset'), {'email': self.user.email})
            response = self.client.get(reverse('demo_inbox'))
            self.assertContains(response, 'Open password reset')
            self.assertContains(response, self.user.email)
            self.assertEqual(self.client.get(reverse('demo_inbox'), REMOTE_ADDR='203.0.113.2').status_code, 404)
            with override_settings(DEBUG=False):
                self.assertEqual(self.client.get(reverse('demo_inbox')).status_code, 404)
