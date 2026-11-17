from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError

from accounts.models import User


class Command(BaseCommand):
    help = "Create a SACCO and its first manager. Prompts for the manager password."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        name = options["name"].strip()
        email = options["email"].strip().lower()
        if not name or len(name) > 100:
            raise CommandError("Enter a SACCO name between 1 and 100 characters.")
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("Enter a valid manager email.") from exc
        if len(email) > 254 or User.objects.filter(email__iexact=email).exists():
            raise CommandError("Enter an unused manager email of at most 254 characters.")
        password = getpass("Manager password: ")
        if password != getpass("Confirm password: "):
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, User(email=email))
            User.objects.create_user(email, password, sacco_name=name)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        except IntegrityError as exc:
            if not User.objects.filter(email__iexact=email).exists():
                raise
            raise CommandError("An account already uses this email address.") from exc
        self.stdout.write(self.style.SUCCESS(f"Created {name} and its first manager."))
