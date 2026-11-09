from django.urls import path
from .views import SignInView, SignUpView, SignOutView, DemoPasswordResetView, demo_inbox
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("demo-inbox/", demo_inbox, name="demo_inbox"),
    path("password-reset/", DemoPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/recovery.html", extra_context={"heading": "Check the demo inbox", "description": "If an active account matches that email, a reset link has been sent to the local demo inbox."}), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/recovery.html", extra_context={"heading": "Choose a new password", "description": "Use the form below. If this link has expired or was already used, request another reset.", "button_label": "Save new password"}), name="password_reset_confirm"),
    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/recovery.html", extra_context={"heading": "Password updated", "description": "You can now sign in with your new password."}), name="password_reset_complete"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", SignInView.as_view(), name="login"),
    path("logout/", SignOutView.as_view(), name="logout"),
]
