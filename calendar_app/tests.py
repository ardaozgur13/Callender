"""
Kişisel takvim testleri: tekrar hesabı, günlük limit, yetki, sayfalar.
"""
from datetime import date, time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core import limits

from . import services
from .models import CalendarItem

PASSWORD = "papatya-cayir-42"


def make_item(owner, **kwargs):
    data = {"title": "Deneme", "date": date(2026, 10, 13), "kind": CalendarItem.Kind.EVENT}
    data.update(kwargs)
    return CalendarItem.objects.create(owner=owner, **data)


class OccurrenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)

    def test_yearly_item_repeats_in_later_years_only(self):
        item = make_item(self.user, kind="birthday", repeat="yearly", date=date(1990, 5, 4))
        self.assertEqual(item.occurs_in_year(2026), date(2026, 5, 4))
        self.assertIsNone(item.occurs_in_year(1989))

    def test_feb_29_falls_back_to_feb_28(self):
        item = make_item(self.user, kind="birthday", repeat="yearly", date=date(2000, 2, 29))
        self.assertEqual(item.occurs_in_year(2027), date(2027, 2, 28))
        self.assertEqual(item.occurs_in_year(2028), date(2028, 2, 29))

    def test_occurrences_between_includes_yearly_and_one_off(self):
        make_item(self.user, title="Doğum günü", kind="birthday", repeat="yearly", date=date(1990, 10, 20))
        make_item(self.user, title="Toplantı", date=date(2026, 10, 21))
        make_item(self.user, title="Geçen yıl", date=date(2025, 10, 21))
        by_date = services.occurrences_between(self.user, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual([o.item.title for o in by_date[date(2026, 10, 20)]], ["Doğum günü"])
        self.assertEqual(by_date[date(2026, 10, 20)][0].years, 36)
        self.assertEqual([o.item.title for o in by_date[date(2026, 10, 21)]], ["Toplantı"])

    def test_range_spanning_new_year(self):
        make_item(self.user, title="Yılbaşı", kind="anniversary", repeat="yearly", date=date(2020, 1, 1))
        by_date = services.occurrences_between(self.user, date(2026, 12, 28), date(2027, 1, 3))
        self.assertIn(date(2027, 1, 1), by_date)

    def test_day_ordering_all_day_first_then_time(self):
        make_item(self.user, title="Öğlen", all_day=False, start_time=time(12, 0))
        make_item(self.user, title="Sabah", all_day=False, start_time=time(8, 0))
        make_item(self.user, title="Tüm gün")
        titles = [o.item.title for o in services.occurrences_on(self.user, date(2026, 10, 13))]
        self.assertEqual(titles, ["Tüm gün", "Sabah", "Öğlen"])


class DailyLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.client.force_login(self.user)
        self.day = date(2026, 10, 13)
        for i in range(limits.MAX_ITEMS_PER_DAY):
            make_item(self.user, title=f"Kayıt {i}", date=self.day)

    def post_new(self, day):
        return self.client.post(reverse("item_create"), {
            "kind": "event", "title": "Bir tane daha", "date": day.isoformat(),
            "all_day": "on", "repeat": "none", "description": "",
        })

    def test_limit_blocks_new_item_with_friendly_message(self):
        response = self.post_new(self.day)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Bu güne en fazla {limits.MAX_ITEMS_PER_DAY} kayıt ekleyebilirsin.")
        self.assertEqual(CalendarItem.objects.filter(date=self.day).count(), limits.MAX_ITEMS_PER_DAY)

    def test_other_day_still_allowed(self):
        response = self.post_new(date(2026, 10, 14))
        self.assertEqual(response.status_code, 302)

    def test_moving_item_into_full_day_blocked(self):
        other = make_item(self.user, title="Yarın", date=date(2026, 10, 14))
        self.client.post(reverse("item_edit", args=[other.pk]), {
            "kind": "event", "title": "Yarın", "date": self.day.isoformat(),
            "all_day": "on", "repeat": "none",
        })
        other.refresh_from_db()
        self.assertEqual(other.date, date(2026, 10, 14))

    def test_editing_item_on_full_day_is_allowed(self):
        item = CalendarItem.objects.filter(date=self.day).first()
        response = self.client.post(reverse("item_edit", args=[item.pk]), {
            "kind": "event", "title": "Yeni başlık", "date": self.day.isoformat(),
            "all_day": "on", "repeat": "none",
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.title, "Yeni başlık")

    def test_limit_is_per_user(self):
        other = User.objects.create_user("can@example.com", "Can", PASSWORD)
        self.client.force_login(other)
        self.assertEqual(self.post_new(self.day).status_code, 302)


class ItemFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.client.force_login(self.user)

    def post(self, **overrides):
        data = {"kind": "event", "title": "Kahvaltı", "date": "2026-10-13", "repeat": "none", "description": ""}
        data.update(overrides)
        return self.client.post(reverse("item_create"), data)

    def test_create_timed_item(self):
        response = self.post(start_time="09:00", end_time="10:30")
        self.assertRedirects(response, reverse("calendar_day", args=[2026, 10, 13]))
        item = CalendarItem.objects.get()
        self.assertEqual(item.owner, self.user)
        self.assertFalse(item.all_day)
        self.assertEqual(item.start_time, time(9, 0))

    def test_all_day_clears_times(self):
        self.post(all_day="on", start_time="09:00")
        self.assertIsNone(CalendarItem.objects.get().start_time)

    def test_timed_item_needs_start(self):
        response = self.post()
        self.assertContains(response, "Saat seç")
        self.assertFalse(CalendarItem.objects.exists())

    def test_end_before_start_rejected(self):
        response = self.post(start_time="10:00", end_time="09:00")
        self.assertContains(response, "Bitiş saati başlangıçtan sonra olmalı")

    def test_title_limit(self):
        response = self.post(all_day="on", title="A" * (limits.TITLE_MAX + 1))
        self.assertContains(response, f"en fazla {limits.TITLE_MAX} karakter")
        self.assertFalse(CalendarItem.objects.exists())

    def test_description_limit(self):
        response = self.post(all_day="on", description="A" * (limits.DESCRIPTION_MAX + 1))
        self.assertContains(response, f"en fazla {limits.DESCRIPTION_MAX} karakter")
        self.assertFalse(CalendarItem.objects.exists())

    def test_blank_title_rejected(self):
        self.post(all_day="on", title="   ")
        self.assertFalse(CalendarItem.objects.exists())

    def test_create_prefills_date_from_query(self):
        response = self.client.get(reverse("item_create") + "?tarih=2026-12-24")
        self.assertContains(response, 'value="2026-12-24"')


class AuthorizationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.other = User.objects.create_user("can@example.com", "Can", PASSWORD)
        self.item = make_item(self.owner, title="Gizli plan", kind="task")
        self.client.force_login(self.other)

    def test_other_user_cannot_edit(self):
        self.assertEqual(self.client.get(reverse("item_edit", args=[self.item.pk])).status_code, 404)

    def test_other_user_cannot_delete(self):
        self.assertEqual(self.client.post(reverse("item_delete", args=[self.item.pk])).status_code, 404)
        self.assertTrue(CalendarItem.objects.filter(pk=self.item.pk).exists())

    def test_other_user_cannot_toggle(self):
        self.assertEqual(self.client.post(reverse("item_toggle_done", args=[self.item.pk])).status_code, 404)

    def test_other_user_does_not_see_item(self):
        response = self.client.get(reverse("calendar_month", args=[2026, 10]))
        self.assertNotContains(response, "Gizli plan")
        response = self.client.get(reverse("calendar_day", args=[2026, 10, 13]))
        self.assertNotContains(response, "Gizli plan")

    def test_calendar_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class PageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayse@example.com", "Ayşe", PASSWORD)
        self.client.force_login(self.user)

    def test_month_view_shows_items(self):
        make_item(self.user, title="Annemin doğum günü", kind="birthday", repeat="yearly", date=date(1960, 10, 20))
        response = self.client.get(reverse("calendar_month", args=[2026, 10]))
        self.assertContains(response, "Ekim 2026")
        self.assertContains(response, "Annemin doğum günü")

    def test_invalid_month_is_404(self):
        self.assertEqual(self.client.get("/takvim/2026/13/").status_code, 404)
        self.assertEqual(self.client.get("/takvim/2026/2/30/").status_code, 404)

    def test_toggle_done_only_for_tasks(self):
        task = make_item(self.user, kind="task")
        event = make_item(self.user, kind="event")
        self.client.post(reverse("item_toggle_done", args=[task.pk]))
        self.client.post(reverse("item_toggle_done", args=[event.pk]))
        task.refresh_from_db()
        event.refresh_from_db()
        self.assertTrue(task.is_done)
        self.assertFalse(event.is_done)

    def test_toggle_ignores_external_next(self):
        task = make_item(self.user, kind="task")
        response = self.client.post(reverse("item_toggle_done", args=[task.pk]), {"next": "https://evil.example.com/"})
        self.assertEqual(response["Location"], reverse("calendar_day", args=[2026, 10, 13]))

    def test_delete(self):
        item = make_item(self.user)
        self.client.post(reverse("item_delete", args=[item.pk]))
        self.assertFalse(CalendarItem.objects.filter(pk=item.pk).exists())

    def test_home_shows_today_items(self):
        make_item(self.user, title="Bugünkü plan", date=timezone.localdate())
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Bugünkü plan")
