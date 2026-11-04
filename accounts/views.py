from pathlib import Path
from email import policy
from email.parser import BytesParser
from urllib.parse import urlsplit
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from .forms import EmailAuthenticationForm
from .rate_limit import reserve_attempt, release_attempt, WINDOW_SECONDS


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        self.reservations = reserve_attempt(
            request.POST.get("username", ""), request.META.get("REMOTE_ADDR", "unknown"),
        )
        if self.reservations is None:
            # Do not bind the submitted password into the throttled response.
            context = self.get_context_data(form=self.get_form_class()(request=request))
            context["throttled"] = True
            response = self.render_to_response(context, status=429)
            response["Retry-After"] = str(WINDOW_SECONDS)
            return response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        release_attempt(self.reservations)
        return response


class SignOutView(LogoutView):
    # Django only permits POST, and its CSRF middleware validates the token.
    next_page = "login"


class DemoPasswordResetView(PasswordResetView):
    template_name = "accounts/recovery.html"
    email_template_name = "accounts/reset_email.txt"
    subject_template_name = "accounts/reset_subject.txt"
    extra_context = {"heading": "Reset your password", "description": "Enter your account email to receive a reset link in the local demo inbox.", "button_label": "Send reset link"}

    def post(self, request, *args, **kwargs):
        if reserve_attempt(request.POST.get("email", ""), request.META.get("REMOTE_ADDR", "unknown"), namespace="reset") is None:
            return redirect("password_reset_done")
        return super().post(request, *args, **kwargs)


@never_cache
@require_GET
def demo_inbox(request):
    # The inbox intentionally exposes demo reset links, so keep it local and DEBUG-only.
    if not settings.DEBUG or request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
        raise Http404
    messages = []
    for path in sorted(Path(settings.EMAIL_FILE_PATH).glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=("plain",))
        text = body.get_content() if body else ""
        links = [line.strip() for line in text.splitlines() if line.strip().startswith(("http://", "https://"))]
        link = next((url for url in links if urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1", "testserver"}), None)
        messages.append({"recipient": message.get("To"), "subject": message.get("Subject"), "body": text, "link": link})
    return render(request, "accounts/demo_inbox.html", {"emails": messages})
