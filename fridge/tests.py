"""
Buzdolabı testleri: use_by hesabı, durumlar, tohum verisi, öneri, limit, yetki, Bugün sayfası.
"""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core import limits
from families import services as family_services

from . import services
from .models import FoodItem, ShelfLifeRule
from .seed_shelf_life import SHELF_LIFE_RULES

PASSWORD = "papatya-cayir-42"


def make_user(name):
    return User.objects.create_user(f"{name.lower()}@example.com", name, PASSWORD)


def make_food(owner, **kwargs):
    data = {"name": "Süt"}
    data.update(kwargs)
    return FoodItem.objects.create(owner=owner, **data)


class UseByTests(TestCase):
    def setUp(self):
        self.user = make_user("Ayse")

    def test_opened_only(self):
        food = make_food(self.user, opened_on=date(2026, 10, 1), suggested_days=5)
        self.assertEqual(food.use_by, date(2026, 10, 6))

    def test_package_only(self):
        food = make_food(self.user, package_expiry=date(2026, 11, 1), suggested_days=5)
        self.assertEqual(food.use_by, date(2026, 11, 1))

    def test_earlier_of_both(self):
        food = make_food(self.user, opened_on=date(2026, 10, 1), suggested_days=5, package_expiry=date(2026, 10, 3))
        self.assertEqual(food.use_by, date(2026, 10, 3))
        food.package_expiry = date(2026, 12, 1)
        food.save()
        self.assertEqual(food.use_by, date(2026, 10, 6))

    def test_nothing(self):
        self.assertIsNone(make_food(self.user).use_by)
        self.assertIsNone(make_food(self.user, opened_on=date(2026, 10, 1)).use_by)

    def test_update_fields_recalculates(self):
        food = make_food(self.user, suggested_days=5)
        food.opened_on = date(2026, 10, 1)
        food.save(update_fields=["opened_on"])
        food.refresh_from_db()
        self.assertEqual(food.use_by, date(2026, 10, 6))

    def test_status_and_labels(self):
        today = timezone.localdate()
        cases = [
            (today + timedelta(days=10), FoodItem.Status.FRESH, "10 gün kaldı"),
            (today + timedelta(days=limits.EXPIRY_WARNING_DAYS), FoodItem.Status.SOON, None),
            (today + timedelta(days=1), FoodItem.Status.SOON, "Yarın son gün"),
            (today, FoodItem.Status.SOON, "Bugün son gün"),
            (today - timedelta(days=2), FoodItem.Status.LATE, "2 gün geçti"),
        ]
        for expiry, status, label in cases:
            food = make_food(self.user, package_expiry=expiry)
            self.assertEqual(food.status, status)
            if label:
                self.assertEqual(food.days_left_label, label)
        self.assertEqual(make_food(self.user).status, FoodItem.Status.UNKNOWN)


class SeedTests(TestCase):
    def test_all_rules_seeded_with_sources(self):
        self.assertEqual(ShelfLifeRule.objects.filter(key__in=[r[0] for r in SHELF_LIFE_RULES]).count(),
                         len(SHELF_LIFE_RULES))
        milk = ShelfLifeRule.objects.get(key="sut-pastorize")
        self.assertEqual((milk.opened_days, milk.source), (5, "usda"))
        lactose_free = ShelfLifeRule.objects.get(key="sut-laktozsuz")
        self.assertEqual((lactose_free.opened_days, lactose_free.source), (3, "estimate"))
        self.assertEqual(ShelfLifeRule.objects.get(key="recel-bal").storage, "room")
        self.assertTrue(all(r.source in ("usda", "estimate") for r in ShelfLifeRule.objects.all()))


class FoodFormTests(TestCase):
    def setUp(self):
        self.user = make_user("Ayse")
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    def post(self, **overrides):
        data = {"name": "Süt (pastörize, laktozlu)", "storage": "fridge", "opened_on": "", "suggested_days": "",
                "package_expiry": "", "note": ""}
        data.update(overrides)
        return self.client.post(reverse("food_create"), data)

    def test_rule_suggestion_fills_days(self):
        self.post(opened_on=self.today.isoformat())
        food = FoodItem.objects.get()
        self.assertEqual(food.rule.key, "sut-pastorize")
        self.assertEqual(food.suggested_days, 5)
        self.assertEqual(food.use_by, self.today + timedelta(days=5))

    def test_rule_match_is_case_insensitive(self):
        self.post(name="  SÜT (PASTÖRIZE, LAKTOZLU) ")
        self.assertEqual(FoodItem.objects.get().rule.key, "sut-pastorize")

    def test_user_days_override_suggestion(self):
        self.post(opened_on=self.today.isoformat(), suggested_days="2")
        self.assertEqual(FoodItem.objects.get().suggested_days, 2)

    def test_earlier_package_expiry_wins(self):
        expiry = self.today + timedelta(days=2)
        self.post(opened_on=self.today.isoformat(), package_expiry=expiry.isoformat())
        self.assertEqual(FoodItem.objects.get().use_by, expiry)

    def test_unknown_product_without_rule(self):
        self.post(name="Ev yapımı turşu", package_expiry=(self.today + timedelta(days=30)).isoformat())
        food = FoodItem.objects.get()
        self.assertIsNone(food.rule)
        self.assertIsNone(food.suggested_days)

    def test_future_opened_date_rejected(self):
        response = self.post(opened_on=(self.today + timedelta(days=1)).isoformat())
        self.assertContains(response, "Açılma tarihi ileri bir tarih olamaz")
        self.assertFalse(FoodItem.objects.exists())

    def test_name_and_note_limits(self):
        self.post(name="A" * (limits.FOOD_NAME_MAX + 1))
        self.post(name="Süt", note="A" * (limits.FOOD_NOTE_MAX + 1))
        self.assertFalse(FoodItem.objects.exists())

    def test_form_shows_safety_notice_and_suggestions(self):
        response = self.client.get(reverse("food_create"))
        self.assertContains(response, "Şüpheliysen at.")
        self.assertContains(response, "Süt (laktozsuz)")


class FridgeActionTests(TestCase):
    def setUp(self):
        self.user = make_user("Ayse")
        self.client.force_login(self.user)

    def test_list_sorted_by_use_by_and_hides_consumed(self):
        today = timezone.localdate()
        make_food(self.user, name="Geç", package_expiry=today + timedelta(days=20))
        make_food(self.user, name="Erken", package_expiry=today + timedelta(days=1))
        make_food(self.user, name="Tarihsiz")
        make_food(self.user, name="Bitti", is_consumed=True)
        response = self.client.get(reverse("fridge"))
        names = [f.name for f in response.context["items"]]
        self.assertEqual(names, ["Erken", "Geç", "Tarihsiz"])
        self.assertContains(response, "Şüpheliysen at.")

    def test_consume(self):
        food = make_food(self.user)
        self.client.post(reverse("food_consume", args=[food.pk]))
        food.refresh_from_db()
        self.assertTrue(food.is_consumed)
        self.assertIsNotNone(food.consumed_at)

    def test_open_today_uses_rule_days(self):
        rule = ShelfLifeRule.objects.get(key="yogurt")
        food = make_food(self.user, name=rule.name_tr, rule=rule)
        self.client.post(reverse("food_open_today", args=[food.pk]))
        food.refresh_from_db()
        self.assertEqual(food.opened_on, timezone.localdate())
        self.assertEqual(food.use_by, timezone.localdate() + timedelta(days=rule.opened_days))

    def test_limit(self):
        FoodItem.objects.bulk_create(
            [FoodItem(owner=self.user, name=f"Ürün {i}") for i in range(limits.MAX_FRIDGE_ITEMS_PER_FAMILY)]
        )
        response = self.client.post(reverse("food_create"), {"name": "Bir tane daha", "storage": "fridge"})
        self.assertContains(response, f"en fazla {limits.MAX_FRIDGE_ITEMS_PER_FAMILY} aktif ürün")
        # Tüketilen ürün limitten düşer
        FoodItem.objects.filter(pk=FoodItem.objects.filter(owner=self.user).first().pk).update(is_consumed=True)
        response = self.client.post(reverse("food_create"), {"name": "Bir tane daha", "storage": "fridge"})
        self.assertEqual(response.status_code, 302)

    def test_home_shows_expiring(self):
        today = timezone.localdate()
        make_food(self.user, name="Kefir yarın", package_expiry=today + timedelta(days=1))
        make_food(self.user, name="Bozulmuş", package_expiry=today - timedelta(days=1))
        make_food(self.user, name="Uzak", package_expiry=today + timedelta(days=30))
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Kefir yarın")
        self.assertContains(response, "Bozulmuş")
        self.assertNotContains(response, "Uzak")


class FridgeAuthorizationTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.zeynep = make_user("Zeynep")
        self.family = family_services.create_family(self.ayse, "Yılmazlar")
        family_services.join_family(self.can, self.family.invite_code)
        self.shared = make_food(self.ayse, name="Ortak süt", family=self.family)
        self.personal = make_food(self.ayse, name="Ayşe'nin yoğurdu")

    def switch(self, family_id):
        self.client.post(reverse("switch_context"), {"family": family_id or "", "next": "/"})

    def test_member_sees_family_fridge(self):
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        response = self.client.get(reverse("fridge"))
        self.assertContains(response, "Ortak süt")
        self.assertNotContains(response, "Ayşe&#x27;nin yoğurdu")
        self.client.post(reverse("food_consume", args=[self.shared.pk]))
        self.shared.refresh_from_db()
        self.assertTrue(self.shared.is_consumed)

    def test_member_cannot_touch_personal_item(self):
        self.client.force_login(self.can)
        self.assertEqual(self.client.get(reverse("food_edit", args=[self.personal.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("food_delete", args=[self.personal.pk])).status_code, 404)

    def test_non_member_blocked(self):
        self.client.force_login(self.zeynep)
        self.switch(self.family.pk)
        self.assertNotContains(self.client.get(reverse("fridge")), "Ortak süt")
        for name in ("food_consume", "food_open_today", "food_delete"):
            self.assertEqual(self.client.post(reverse(name, args=[self.shared.pk])).status_code, 404)
        self.shared.refresh_from_db()
        self.assertFalse(self.shared.is_consumed)

    def test_new_item_goes_to_active_context(self):
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        self.client.post(reverse("food_create"), {"name": "Yumurta (kırılmamış)", "storage": "fridge"})
        self.assertEqual(FoodItem.objects.get(name="Yumurta (kırılmamış)").family, self.family)

    def test_expiring_scope_follows_context(self):
        today = timezone.localdate()
        FoodItem.objects.filter(pk=self.shared.pk).update(use_by=today)
        self.assertEqual(list(services.expiring_items(self.can, self.family)), [self.shared])
        self.assertEqual(list(services.expiring_items(self.zeynep, self.family)), [])
