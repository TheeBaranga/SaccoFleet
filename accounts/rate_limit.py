from datetime import timedelta
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import LoginBucket

WINDOW_SECONDS = 600
EMAIL_LIMIT = 5
IP_LIMIT = 20


def bucket_keys(email, remote_address):
    # Never trust a client-supplied forwarding header for the IP address.
    values = [(f"email:{email.strip().lower()[:254]}", EMAIL_LIMIT),
              (f"ip:{remote_address}", IP_LIMIT)]
    return sorted((salted_hmac("saccofleet.login", value, algorithm="sha256").hexdigest(), limit)
                  for value, limit in values)


@transaction.atomic
def reserve_attempt(email, remote_address):
    """Reserve before checking a password so concurrent requests count too."""
    now = timezone.now()
    rows = []
    for key, limit in bucket_keys(email, remote_address):
        bucket, _ = LoginBucket.objects.select_for_update().get_or_create(
            key=key, defaults={"started_at": now},
        )
        if bucket.started_at <= now - timedelta(seconds=WINDOW_SECONDS):
            bucket.attempts = 0
            bucket.started_at = now
            bucket.save(update_fields=["attempts", "started_at"])
        if bucket.attempts >= limit:
            return None
        rows.append(bucket)
    for bucket in rows:
        bucket.attempts += 1
        bucket.save(update_fields=["attempts"])
    return [(bucket.key, bucket.started_at) for bucket in rows]


def release_attempt(reservations):
    """A successful sign-in does not consume the failed-attempt allowance."""
    for key, started_at in reservations:
        LoginBucket.objects.filter(key=key, started_at=started_at, attempts__gt=0).update(
            attempts=F("attempts") - 1,
        )
