from django.conf import settings


def demo_mode(request):
    return {"debug_demo": settings.DEBUG and request.META.get("REMOTE_ADDR") in {"127.0.0.1", "::1"}}
