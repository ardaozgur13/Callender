"""
Ortak testler: ana sayfa, ayarlar, limitler.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core import limits


class HomePageTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")

    def test_home_renders_for_user(self):
        user = get_user_model().objects.create_user("ayse@example.com", "Ayşe", "papatya-cayir-42")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Merhaba Ayşe")
        self.assertContains(response, 'lang="tr"')
        self.assertContains(response, "css/theme.css")


class SettingsTests(SimpleTestCase):
    def test_locale_and_timezone(self):
        self.assertEqual(settings.LANGUAGE_CODE, "tr")
        self.assertEqual(settings.TIME_ZONE, "Europe/Istanbul")
        self.assertTrue(settings.USE_TZ)

    def test_database_is_postgres_pooler_safe(self):
        db = settings.DATABASES["default"]
        self.assertIn("postgresql", db["ENGINE"])
        self.assertEqual(db["CONN_MAX_AGE"], 0)
        self.assertTrue(db["DISABLE_SERVER_SIDE_CURSORS"])


class LimitsTests(SimpleTestCase):
    def test_core_limits(self):
        self.assertEqual(limits.MAX_FAMILIES_PER_USER, 2)
        self.assertEqual(limits.MAX_ITEMS_PER_DAY, 20)
        self.assertEqual(limits.TITLE_MAX, 80)

    def test_invite_alphabet_excludes_ambiguous(self):
        for ch in "0O1I":
            self.assertNotIn(ch, limits.INVITE_CODE_ALPHABET)
