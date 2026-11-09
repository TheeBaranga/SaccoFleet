from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm


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

class SignUpForm(BaseUserCreationForm):
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Email address"}),
    )
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={"autocomplete": "given-name", "placeholder": "First name"},
    ))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={"autocomplete": "family-name", "placeholder": "Last name"},
    ))

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if self._meta.model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email
