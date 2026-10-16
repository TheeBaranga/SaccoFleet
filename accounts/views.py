from django.contrib.auth.views import LoginView, LogoutView
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
