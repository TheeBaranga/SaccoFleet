from django import forms
from django.contrib.auth.forms import AuthenticationForm


class EmailAuthenticationForm(AuthenticationForm):
    """Keep Django's password verification, with an email-specific input."""

    username = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={
            "autocomplete": "username", "autofocus": True,
            "placeholder": "Enter your email address", "spellcheck": "false",
        }),
    )
    password = forms.CharField(
        label="Password", strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password", "placeholder": "Enter your password",
        }),
    )
    error_messages = {
        "invalid_login": "The email or password is incorrect. Please try again.",
        "inactive": "The email or password is incorrect. Please try again.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
