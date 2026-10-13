"""
Ev işleri ve ev durumu testleri: haftalık plan, "yaptım", limit, yetki, durum adımları, çakışma.
"""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core import limits
from families import services as family_services

from . import services
from .models import Chore, ChoreLog, HomeStatus

PASSWORD = "papatya-cayir-42"


def make_user(name):
    return User.objects.create_user(f"{name.lower()}@example.com", name, PASSWORD)


class HomeTestBase(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.zeynep = make_user("Zeynep")  # aileye üye değil
        self.family = family_services.create_family(self.ayse, "Yılmazlar")
        family_services.join_family(self.can, self.family.invite_code)
        self.today = timezone.localdate()

    def login_family(self, user):
        self.client.force_login(user)
        self.client.post(reverse("switch_context"), {"family": self.family.pk, "next": "/"})


class StatusFlowTests(HomeTestBase):
    def test_initial_statuses(self):
        dish, laundry = sorted(services.get_statuses(self.family), key=lambda s: s.kind)
        self.assertEqual((dish.kind, dish.status), ("dishwasher", "idle"))
        self.assertEqual((laundry.kind, laundry.status), ("laundry", "done"))

    def test_dishwasher_full_cycle(self):
        expected = ["loaded", "running", "done", "needs_unloading", "idle"]
        current = "idle"
        for step in expected:
            card = services.change_status(self.family, "dishwasher", self.ayse, expected=current)
            self.assertEqual(card.status, step)
            current = step

    def test_laundry_cycle_restarts(self):
        card = services.change_status(self.family, "laundry", self.ayse, expected="done")
        self.assertEqual(card.status, "washing")
        for step in ["washed", "hanging", "dry", "done"]:
            card = services.change_status(self.family, "laundry", self.ayse, expected=card.status)
            self.assertEqual(card.status, step)

    def test_free_selection_and_undo(self):
        services.change_status(self.family, "dishwasher", self.ayse, expected="idle", new_status="running")
        card = services.change_status(self.family, "dishwasher", self.ayse, expected="running", new_status="loaded")
        self.assertEqual(card.status, "loaded")

    def test_invalid_status_rejected(self):
        with self.assertRaises(services.HomeError):
            services.change_status(self.family, "dishwasher", self.ayse, expected="idle", new_status="washing")
        with self.assertRaises(services.HomeError):
            services.change_status(self.family, "oven", self.ayse, expected="idle")

    def test_stale_click_does_not_double_advance(self):
        services.change_status(self.family, "dishwasher", self.ayse, expected="idle")
        with self.assertRaisesMessage(services.HomeError, "Ayse bu arada durumu"):
            services.change_status(self.family, "dishwasher", self.can, expected="idle")
        self.assertEqual(HomeStatus.objects.get(family=self.family, kind="dishwasher").status, "loaded")

    def test_two_users_see_each_others_updates(self):
        self.login_family(self.ayse)
        self.client.post(reverse("status_change", args=["laundry"]), {"expected": "done"})
        self.login_family(self.can)
        response = self.client.get(reverse("home_page"))
        self.assertContains(response, "Yıkanıyor")
        self.assertContains(response, "<strong>Ayse</strong>", html=False)
        self.client.post(reverse("status_change", args=["laundry"]), {"expected": "washing"})
        self.login_family(self.ayse)
        response = self.client.get(reverse("home_page"))
        self.assertContains(response, "Yıkandı, serilmeli")
        self.assertContains(response, "<strong>Can</strong>", html=False)

    def test_non_member_cannot_change_status(self):
        self.client.force_login(self.zeynep)
        self.client.post(reverse("switch_context"), {"family": self.family.pk, "next": "/"})
        self.client.post(reverse("status_change", args=["dishwasher"]), {"expected": "idle"})
        self.assertEqual(services.get_statuses(self.family)[0].status, "idle")


class ChoreTests(HomeTestBase):
    def chore(self, **kwargs):
        data = {"family": self.family, "title": "Bulaşık"}
        data.update(kwargs)
        return Chore.objects.create(**data)

    def test_create_via_page(self):
        self.login_family(self.ayse)
        response = self.client.post(reverse("chore_create"), {
            "title": "Çöpü at", "assigned_to": self.can.pk, "weekday": "2", "is_active": "on",
        })
        self.assertRedirects(response, reverse("home_page"))
        chore = Chore.objects.get(title="Çöpü at")
        self.assertEqual((chore.family, chore.assigned_to, chore.weekday), (self.family, self.can, 2))

    def test_cannot_assign_non_member(self):
        self.login_family(self.ayse)
        self.client.post(reverse("chore_create"), {"title": "Çöp", "assigned_to": self.zeynep.pk, "is_active": "on"})
        self.assertFalse(Chore.objects.exists())

    def test_title_limit(self):
        self.login_family(self.ayse)
        self.client.post(reverse("chore_create"), {"title": "A" * (limits.TITLE_MAX + 1), "is_active": "on"})
        self.assertFalse(Chore.objects.exists())

    def test_active_chore_limit(self):
        Chore.objects.bulk_create(
            [Chore(family=self.family, title=f"İş {i}") for i in range(limits.MAX_CHORES_PER_FAMILY)]
        )
        self.login_family(self.ayse)
        response = self.client.post(reverse("chore_create"), {"title": "Fazla", "is_active": "on"})
        self.assertContains(response, f"en fazla {limits.MAX_CHORES_PER_FAMILY} aktif ev işi")
        # Pasif iş limite takılmaz
        response = self.client.post(reverse("chore_create"), {"title": "Pasif"})
        self.assertEqual(response.status_code, 302)

    def test_weekly_schedule(self):
        monday = services.week_days(date(2026, 10, 14))[0]
        self.assertEqual(monday, date(2026, 10, 12))
        daily = self.chore(title="Her gün")
        wednesday = self.chore(title="Çarşamba", weekday=2)
        week = services.week_schedule(self.family, services.week_days(monday))
        self.assertEqual(len(week), 7)
        self.assertEqual([c for c, _ in week[0]["entries"]], [daily])
        self.assertEqual({c for c, _ in week[2]["entries"]}, {daily, wednesday})

    def test_toggle_done_and_undo(self):
        chore = self.chore()
        self.login_family(self.can)
        self.client.post(reverse("chore_toggle", args=[chore.pk]), {"date": self.today.isoformat()})
        log = ChoreLog.objects.get(chore=chore, date=self.today)
        self.assertEqual(log.done_by, self.can)
        self.client.post(reverse("chore_toggle", args=[chore.pk]), {"date": self.today.isoformat()})
        self.assertFalse(ChoreLog.objects.exists())

    def test_cannot_mark_future(self):
        chore = self.chore()
        with self.assertRaises(services.HomeError):
            services.toggle_done(chore, self.today + timedelta(days=1), self.ayse)

    def test_cannot_mark_unscheduled_day(self):
        other_day = (self.today.weekday() + 1) % 7
        chore = self.chore(weekday=other_day)
        with self.assertRaises(services.HomeError):
            services.toggle_done(chore, self.today, self.ayse)

    def test_non_member_blocked(self):
        chore = self.chore()
        self.client.force_login(self.zeynep)
        self.assertEqual(self.client.get(reverse("chore_edit", args=[chore.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("chore_delete", args=[chore.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("chore_toggle", args=[chore.pk])).status_code, 404)

    def test_leaving_member_chores_become_everyones(self):
        chore = self.chore(assigned_to=self.can)
        family_services.leave_family(family_services.get_membership(self.can, self.family.pk))
        chore.refresh_from_db()
        self.assertIsNone(chore.assigned_to)

    def test_removed_member_chores_become_everyones(self):
        chore = self.chore(assigned_to=self.can)
        owner = family_services.get_membership(self.ayse, self.family.pk)
        family_services.remove_member(owner, family_services.get_membership(self.can, self.family.pk).pk)
        chore.refresh_from_db()
        self.assertIsNone(chore.assigned_to)

    def test_personal_context_shows_hint(self):
        self.client.force_login(self.ayse)
        self.client.post(reverse("switch_context"), {"family": "", "next": "/"})
        response = self.client.get(reverse("home_page"))
        self.assertContains(response, "aileyle paylaşılır")

    def test_home_page_shows_today_chores_and_status(self):
        self.chore(title="Çiçekleri sula")
        self.login_family(self.ayse)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Çiçekleri sula")
        self.assertContains(response, "Bulaşık makinesi")
        response = self.client.post(reverse("chore_toggle", args=[Chore.objects.get().pk]),
                                    {"date": self.today.isoformat(), "next": "home"})
        self.assertRedirects(response, reverse("home"))
