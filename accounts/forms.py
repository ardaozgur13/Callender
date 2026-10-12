from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from core import limits

from .models import User, normalize_email


class RegisterForm(forms.ModelForm):
    """Kayıt: isim, e-posta, parola (iki kez)."""

    password1 = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=f"En az {limits.PASSWORD_MIN} karakter; sadece rakam ya da çok yaygın bir parola olmasın.",
    )
    password2 = forms.CharField(
        label="Parola (tekrar)",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("display_name", "email")
        labels = {"display_name": "İsim", "email": "E-posta"}
        widgets = {
            "display_name": forms.TextInput(attrs={"autocomplete": "name", "autofocus": True}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }
        error_messages = {
            "display_name": {
                "min_length": f"İsim en az {limits.USER_NAME_MIN} karakter olmalı.",
                "max_length": f"İsim en fazla {limits.USER_NAME_MAX} karakter olabilir.",
            },
        }

    def clean_email(self):
        email = normalize_email(self.cleaned_data.get("email"))
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta ile zaten bir hesap var. Giriş yapmayı dene.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Parolalar birbiriyle aynı değil.")
        elif p1:
            # Doğrulayıcılar isim/e-posta benzerliğine bakabilsin diye geçici kullanıcı bilgisi
            self.instance.email = cleaned.get("email", "")
            self.instance.display_name = cleaned.get("display_name", "")
            try:
                password_validation.validate_password(p1, self.instance)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-posta",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    password = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "E-posta veya parola hatalı. Tekrar dener misin?",
        "inactive": "Bu hesap etkin değil.",
    }


class DisplayNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name",)
        labels = {"display_name": "İsim"}
        widgets = {"display_name": forms.TextInput(attrs={"autocomplete": "name"})}
        error_messages = RegisterForm.Meta.error_messages


class DeleteAccountForm(forms.Form):
    """Hesap silme onayı: kullanıcı parolasını tekrar girer."""

    password = forms.CharField(
        label="Parolan",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Parola hatalı.")
        return password
