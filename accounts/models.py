from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models.functions import Lower

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("An email address is required.")
        return self._create_account(email, password, **extra_fields)

    def _create_account(self, email, password, *, sacco_name=None, **fields):
        from fleet.models import Fleet

        with transaction.atomic(using=self.db):
            if "sacco" not in fields and "sacco_id" not in fields:
                fields["sacco"] = Fleet.objects.using(self.db).create(name=sacco_name or "Sacco Fleet")
            user = self.model(email=email.strip().lower(), **fields)
            user.set_password(password)
            user.save(using=self.db)
            return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers require is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        OPERATIONS = "operations", "Operations staff"

    sacco = models.ForeignKey("fleet.Fleet", on_delete=models.PROTECT, related_name="members")
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.MANAGER)
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_insensitive_unique"),
            models.CheckConstraint(
                condition=models.Q(role="manager") | models.Q(role="operations", is_staff=False, is_superuser=False),
                name="accounts_valid_sacco_role",
            ),
        ]

    @property
    def is_sacco_manager(self):
        return self.is_active and self.role == self.Role.MANAGER

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class LoginBucket(models.Model):
    """Short-lived login counters shared by all application processes."""

    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
