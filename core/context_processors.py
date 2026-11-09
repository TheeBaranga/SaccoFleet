from django.conf import settings


def can_read_demo_inbox(request):
    return (
        settings.DEBUG
        and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}
        and request.user.is_authenticated
        and request.user.is_superuser
    )


def demo_mode(request):
    return {"debug_demo": can_read_demo_inbox(request)}
