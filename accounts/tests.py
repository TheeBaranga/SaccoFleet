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
