import logging
import sqlite3
from django.conf import settings
from django.utils import timezone
from .backups import backup_demo

logger = logging.getLogger(__name__)


class DemoBackupMiddleware:
    """One local snapshot on the first signed-in request of each demo day."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_backup = None

    def __call__(self, request):
        today = timezone.localdate()
        if settings.DEBUG and request.user.is_authenticated and self.last_backup != today:
            try:
                if backup_demo():
                    self.last_backup = today
            except (OSError, RuntimeError, sqlite3.Error):
                logger.exception("Local demo backup failed; run backup_demo before continuing")
        return self.get_response(request)
