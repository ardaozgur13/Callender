"""
Güvenlik testleri (docs/callender.md bölüm 12): deneme sınırları, tek tip hata mesajı,
günlük aile sınırı, güvenlik başlıkları, kapalı admin, satır içi JS yokluğu.
"""
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core import attempts, limits
from core.models import AuthAttempt
from families import services as family_services
from families.models import Family, FamilyMember
from home.models import Chore

PASSWORD = "papatya-cayir-42"


def make_user(name):
    return User.objects.create_user(f"{name.lower()}@example.com", name, PASSWORD)


class LoginRateLimitTests(TestCase):
    def setUp(self):
        self.user = make_user("Ayse")

    def login(self, email="ayse@example.com", password=PASSWORD):
        return self.client.post(reverse("login"), {"username": email, "password": password})

    def test_lockout_after_max_failures_even_with_correct_password(self):
        for _ in range(limits.LOGIN_MAX_ATTEMPTS):
            self.assertContains(self.login(password="yanlis-parola"), "E-posta veya parola hatalı")
        response = self.login()
        self.assertContains(response, "Çok fazla hatalı deneme")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lockout_is_case_insensitive_on_email(self):
        for _ in range(limits.LOGIN_MAX_ATTEMPTS):
            self.login(email="AYSE@Example.com", password="yanlis")
        self.assertContains(self.login(), "Çok fazla hatalı deneme")

    def test_success_clears_counter(self):
        for _ in range(limits.LOGIN_MAX_ATTEMPTS - 1):
            self.login(password="yanlis")
        self.assertEqual(self.login().status_code, 302)
        self.assertFalse(AuthAttempt.objects.filter(kind="login", key="ayse@example.com").exists())

    def test_lock_expires_after_window(self):
        for _ in range(limits.LOGIN_MAX_ATTEMPTS):
            self.login(password="yanlis")
        old = timezone.now() - timedelta(minutes=limits.LOGIN_LOCKOUT_MINUTES + 1)
        AuthAttempt.objects.update(created_at=old)
        self.assertEqual(self.login().status_code, 302)

    def test_unknown_email_locks_the_same_way(self):
        # Kayıtlı olmayan e-posta da aynı davranır (hesap var/yok sızmaz)
        for _ in range(limits.LOGIN_MAX_ATTEMPTS):
            self.login(email="yok@example.com", password="x")
        self.assertContains(self.login(email="yok@example.com", password="x"), "Çok fazla hatalı deneme")


class JoinRateLimitTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.family = family_services.create_family(self.ayse, "Yılmazlar")

    def test_lockout_after_wrong_codes(self):
        for _ in range(limits.JOIN_MAX_ATTEMPTS):
            with self.assertRaisesMessage(family_services.FamilyError, "Kod geçersiz"):
                family_services.join_family(self.can, "YANLIS99")
        with self.assertRaisesMessage(family_services.FamilyError, "Çok fazla hatalı deneme"):
            family_services.join_family(self.can, self.family.invite_code)
        self.assertFalse(FamilyMember.objects.filter(family=self.family, user=self.can).exists())

    def test_attempts_are_recorded_despite_transaction_rollback(self):
        with self.assertRaises(family_services.FamilyError):
            family_services.join_family(self.can, "YANLIS99")
        self.assertEqual(AuthAttempt.objects.filter(kind="join", key=str(self.can.pk)).count(), 1)

    def test_success_clears_counter(self):
        with self.assertRaises(family_services.FamilyError):
            family_services.join_family(self.can, "YANLIS99")
        family_services.join_family(self.can, self.family.invite_code)
        self.assertFalse(AuthAttempt.objects.filter(kind="join", key=str(self.can.pk)).exists())

    def test_full_family_gives_same_message_as_wrong_code(self):
        for i in range(limits.MAX_FAMILY_MEMBERS - 1):
            family_services.join_family(make_user(f"Uye{i}"), self.family.invite_code)
        with self.assertRaises(family_services.FamilyError) as full:
            family_services.join_family(self.can, self.family.invite_code)
        with self.assertRaises(family_services.FamilyError) as wrong:
            family_services.join_family(self.can, "YANLIS99")
        self.assertEqual(str(full.exception), str(wrong.exception))

    def test_lockout_is_per_user(self):
        for _ in range(limits.JOIN_MAX_ATTEMPTS):
            with self.assertRaises(family_services.FamilyError):
                family_services.join_family(self.can, "YANLIS99")
        zeynep = make_user("Zeynep")
        family_services.join_family(zeynep, self.family.invite_code)


class FamilyCreateDailyLimitTests(TestCase):
    def test_daily_family_creation_limit(self):
        user = make_user("Ayse")
        # 2 aile üyelik sınırına takılmadan günlük sınırı denemek için kurup ayrılıyoruz
        for i in range(limits.FAMILY_CREATE_PER_DAY):
            family = family_services.create_family(user, f"Aile {i}")
            family_services.leave_family(family_services.get_membership(user, family.pk))
        with self.assertRaisesMessage(family_services.FamilyError, "Bir günde en fazla"):
            family_services.create_family(user, "Bir tane daha")
        self.assertFalse(Family.objects.filter(name="Bir tane daha").exists())


class HeadersAndSurfaceTests(TestCase):
    def test_security_headers_present(self):
        response = self.client.get(reverse("login"))
        csp = response["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertIn("camera=()", response["Permissions-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "same-origin")

    def test_admin_is_not_exposed(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)
        self.assertEqual(self.client.get("/admin/login/").status_code, 404)

    def test_upload_size_limited(self):
        self.assertLessEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 100_000)

    def test_no_inline_javascript_in_templates(self):
        # CSP script-src 'self' satır içi JS'i engeller; şablonlarda hiç olmamalı
        import re

        pattern = re.compile(r"\son[a-z]+=|<script>(?!\s*$)|<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>")
        offenders = []
        for path in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [])

    def test_password_help_renders_as_list_without_safe_filter(self):
        self.client.force_login(make_user("Ayse"))
        response = self.client.get(reverse("settings"))
        self.assertContains(response, "<li>")
        self.assertNotContains(response, "&lt;li&gt;")


class InactiveChoreTests(TestCase):
    def test_inactive_chore_cannot_be_marked(self):
        user = make_user("Ayse")
        family = family_services.create_family(user, "Yılmazlar")
        chore = Chore.objects.create(family=family, title="Eski iş", is_active=False)
        self.client.force_login(user)
        self.client.post(reverse("chore_toggle", args=[chore.pk]), {"date": timezone.localdate().isoformat()})
        self.assertFalse(chore.logs.exists())


class AttemptHelperTests(TestCase):
    def test_old_attempts_cleaned_lazily(self):
        old = timezone.now() - timedelta(days=1)
        AuthAttempt.objects.create(kind="login", key="eski@example.com")
        AuthAttempt.objects.update(created_at=old)
        attempts.record_failure(AuthAttempt.Kind.LOGIN, "yeni@example.com")
        self.assertFalse(AuthAttempt.objects.filter(key="eski@example.com").exists())
