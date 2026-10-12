from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from families.services import leave_all_families

from .forms import DeleteAccountForm, DisplayNameForm, LoginForm, RegisterForm


@login_not_required
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Hoş geldin {user.display_name}! Çayıra adım attın 🌼")
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Çıkış yaptın. Görüşmek üzere!")
    return redirect("login")


def account_settings(request):
    """Ayarlar: isim değiştirme ve parola değiştirme. Hangi formun gönderildiği `action` alanından anlaşılır."""
    user = request.user
    action = request.POST.get("action") if request.method == "POST" else None

    name_form = DisplayNameForm(request.POST if action == "name" else None, instance=user, prefix="name")
    password_form = PasswordChangeForm(user, request.POST if action == "password" else None, prefix="pw")
    delete_form = DeleteAccountForm(user, prefix="del")

    if action == "name" and name_form.is_valid():
        name_form.save()
        messages.success(request, "İsmin güncellendi.")
        return redirect("settings")

    if action == "password" and password_form.is_valid():
        password_form.save()
        update_session_auth_hash(request, password_form.user)  # Oturum açık kalsın
        messages.success(request, "Parolan değiştirildi.")
        return redirect("settings")

    return render(request, "accounts/settings.html", {
        "name_form": name_form,
        "password_form": password_form,
        "delete_form": delete_form,
        "active_nav": "settings",
    })


@require_POST
def delete_account(request):
    user = request.user
    form = DeleteAccountForm(user, request.POST, prefix="del")
    if form.is_valid():
        # Ailelerden kurallara uygun ayrıl (kurucu devri / son üyede aile silme)
        leave_all_families(user)
        logout(request)
        user.delete()
        messages.info(request, "Hesabın silindi. Yolun açık olsun 🌿")
        return redirect("login")
    return render(request, "accounts/settings.html", {
        "name_form": DisplayNameForm(instance=user, prefix="name"),
        "password_form": PasswordChangeForm(user, prefix="pw"),
        "delete_form": form,
        "active_nav": "settings",
    })
