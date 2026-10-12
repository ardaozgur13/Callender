"""
Kimlik doğrulama testleri: kayıt, giriş, çıkış, ayarlar, hesap silme.
"""
from django.test import TestCase
from django.urls import reverse

from core import limits

from .models import User

PASSWORD = "papatya-cayir-42"


class UserModelTests(TestCase):
    def test_email_is_lowercased(self):
        user = User.objects.create_user("  Ayse@Example.COM ", "Ayşe", PASSWORD)
        self.assertEqual(user.email, "ayse@example.com")

    def test_login_is_case_insensitive(self):
        User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.assertTrue(self.client.login(username="AYSE@example.com", password=PASSWORD))

    def test_superuser(self):
        admin = User.objects.create_superuser("admin@example.com", "Yönetici", PASSWORD)
        self.assertTrue(admin.is_staff and admin.is_superuser)


class RegisterTests(TestCase):
    url = reverse("register")

    def post(self, **overrides):
        data = {
            "display_name": "Ayşe",
            "email": "Ayse@Example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_register_logs_in_and_redirects_home(self):
        response = self.post()
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get()
        self.assertEqual(user.email, "ayse@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_email_rejected_case_insensitive(self):
        User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        response = self.post(email="AYSE@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "zaten bir hesap var")
        self.assertEqual(User.objects.count(), 1)

    def test_name_length_limits(self):
        response = self.post(display_name="A")
        self.assertContains(response, f"en az {limits.USER_NAME_MIN} karakter")
        response = self.post(display_name="A" * (limits.USER_NAME_MAX + 1))
        self.assertContains(response, f"en fazla {limits.USER_NAME_MAX} karakter")
        self.assertFalse(User.objects.exists())

    def test_short_password_rejected(self):
        response = self.post(password1="kisa1", password2="kisa1")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_password_mismatch_rejected(self):
        response = self.post(password2=PASSWORD + "x")
        self.assertContains(response, "Parolalar birbiriyle aynı değil")
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_redirected(self):
        user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse("home"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)

    def test_login_page_is_public(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse("login"), {"username": "ayse@example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("home"))

    def test_login_wrong_password_shows_friendly_error(self):
        response = self.client.post(reverse("login"), {"username": "ayse@example.com", "password": "yanlis-parola"})
        self.assertContains(response, "E-posta veya parola hatalı")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.client.force_login(self.user)
        self.url = reverse("settings")

    def test_settings_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_change_name(self):
        response = self.client.post(self.url, {"action": "name", "name-display_name": "Ayşe Nur"})
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Ayşe Nur")

    def test_change_name_validates_length(self):
        self.client.post(self.url, {"action": "name", "name-display_name": "A"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Ayşe")

    def test_change_password_keeps_session(self):
        new_password = "lale-bahar-2026"
        response = self.client.post(self.url, {
            "action": "password",
            "pw-old_password": PASSWORD,
            "pw-new_password1": new_password,
            "pw-new_password2": new_password,
        })
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        # Oturum hâlâ açık
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_change_password_wrong_old_password(self):
        self.client.post(self.url, {
            "action": "password",
            "pw-old_password": "yanlis",
            "pw-new_password1": "lale-bahar-2026",
            "pw-new_password2": "lale-bahar-2026",
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_delete_account_needs_correct_password(self):
        self.client.post(reverse("delete_account"), {"del-password": "yanlis"})
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_delete_account(self):
        response = self.client.post(reverse("delete_account"), {"del-password": PASSWORD})
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
