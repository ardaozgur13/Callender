"""
KVKK ve hesap yaşam döngüsü testleri: kayıt onayı, e-posta kısıtı, hesap silme sonrası veri durumu,
JSON dışa aktarma, hukuki sayfalar.
"""
import json
from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from calendar_app.models import CalendarItem
from families import services as family_services
from families.models import Family, FamilyMember
from fridge.models import FoodItem
from home.models import Chore, ChoreLog, HomeStatus

from .models import User

PASSWORD = "papatya-cayir-42"


def make_user(name):
    return User.objects.create_user(f"{name.lower()}@example.com", name, PASSWORD)


class ConsentTests(TestCase):
    def post(self, **overrides):
        data = {"display_name": "Ayşe", "email": "ayse@example.com", "password1": PASSWORD, "password2": PASSWORD}
        data.update(overrides)
        return self.client.post(reverse("register"), data)

    def test_register_requires_terms(self):
        response = self.post()
        self.assertContains(response, "aydınlatma metnini okuduğunu onaylaman gerekiyor")
        self.assertFalse(User.objects.exists())

    def test_register_records_acceptance_time(self):
        self.post(accept_terms="on")
        self.assertIsNotNone(User.objects.get().accepted_terms_at)

    def test_register_page_links_legal_texts(self):
        response = self.client.get(reverse("register"))
        for name in ("privacy_notice", "privacy_policy", "terms"):
            self.assertContains(response, reverse(name))

    def test_legal_pages_are_public_and_marked_draft(self):
        for name in ("privacy_notice", "privacy_policy", "terms"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, "Taslak metin")
            self.assertContains(response, "hukuki bir metin değildir")


class EmailConstraintTests(TestCase):
    def test_db_rejects_case_variant_email(self):
        make_user("Ayse")
        # save() küçük harfe çevirdiği için kısıtı bulk_create ile (save atlanarak) deniyoruz
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="AYSE@example.com", display_name="Kopya")])


class AccountDeletionTests(TestCase):
    """Bölüm 7: kişisel veri silinir, aile verisi SET_NULL ile kalır, kurucu devredilir."""

    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.family = family_services.create_family(self.ayse, "Yılmazlar")  # Ayşe kurucu
        family_services.join_family(self.can, self.family.invite_code)
        self.solo_family = family_services.create_family(self.ayse, "Tek başıma")  # sadece Ayşe
        day = date(2026, 10, 13)

        self.personal_item = CalendarItem.objects.create(owner=self.ayse, title="Kişisel", date=day)
        self.family_item = CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile", date=day)
        self.solo_item = CalendarItem.objects.create(owner=self.ayse, family=self.solo_family, title="Tek", date=day)
        self.personal_food = FoodItem.objects.create(owner=self.ayse, name="Kişisel süt")
        self.family_food = FoodItem.objects.create(owner=self.ayse, family=self.family, name="Ortak süt")
        self.chore = Chore.objects.create(family=self.family, title="Bulaşık", assigned_to=self.ayse)
        self.log = ChoreLog.objects.create(chore=self.chore, date=day, done_by=self.ayse)
        self.status = HomeStatus.objects.create(family=self.family, kind="dishwasher", status="loaded",
                                                updated_by=self.ayse)
        self.other_item = CalendarItem.objects.create(owner=self.can, family=self.family, title="Can'in", date=day)

    def delete_ayse(self, password=PASSWORD):
        self.client.force_login(self.ayse)
        return self.client.post(reverse("delete_account"), {"del-password": password})

    def test_wrong_password_keeps_everything(self):
        self.delete_ayse("yanlis-parola")
        self.assertTrue(User.objects.filter(pk=self.ayse.pk).exists())
        self.assertTrue(CalendarItem.objects.filter(pk=self.personal_item.pk).exists())

    def test_data_state_after_deletion(self):
        response = self.delete_ayse()
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(User.objects.filter(pk=self.ayse.pk).exists())

        # Kişisel veri gerçekten silindi
        self.assertFalse(CalendarItem.objects.filter(pk=self.personal_item.pk).exists())
        self.assertFalse(FoodItem.objects.filter(pk=self.personal_food.pk).exists())

        # Aile verisi kaldı, sahibi boşaldı
        self.family_item.refresh_from_db()
        self.family_food.refresh_from_db()
        self.assertIsNone(self.family_item.owner)
        self.assertIsNone(self.family_food.owner)
        self.chore.refresh_from_db()
        self.log.refresh_from_db()
        self.status.refresh_from_db()
        self.assertIsNone(self.chore.assigned_to)
        self.assertIsNone(self.log.done_by)
        self.assertIsNone(self.status.updated_by)

        # Kuruculuk Can'e geçti; tek üyeli aile ve kayıtları silindi
        self.assertTrue(FamilyMember.objects.get(family=self.family, user=self.can).is_owner)
        self.assertFalse(Family.objects.filter(pk=self.solo_family.pk).exists())
        self.assertFalse(CalendarItem.objects.filter(pk=self.solo_item.pk).exists())

        # Başkasının kaydına dokunulmadı
        self.assertTrue(CalendarItem.objects.filter(pk=self.other_item.pk, owner=self.can).exists())

    def test_remaining_member_sees_deleted_user_label_and_family_owner_can_manage(self):
        self.delete_ayse()
        self.client.force_login(self.can)
        self.client.post(reverse("switch_context"), {"family": self.family.pk, "next": "/"})
        response = self.client.get(reverse("calendar_day", args=[2026, 10, 13]))
        self.assertContains(response, "Silinmiş kullanıcı ekledi")
        # Can artık kurucu: sahipsiz kaydı düzenleyebilir (limit kontrolü sahipsiz kayıtta atlanır)
        response = self.client.post(reverse("item_edit", args=[self.family_item.pk]), {
            "kind": "event", "title": "Devralındı", "date": "2026-10-13", "all_day": "on", "repeat": "none",
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("fridge"))
        self.assertContains(response, "Silinmiş kullanıcı ekledi")

    def test_food_must_have_family_or_owner(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            FoodItem.objects.create(owner=None, family=None, name="Sahipsiz")


class ExportTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.family = family_services.create_family(self.ayse, "Yılmazlar")
        family_services.join_family(self.can, self.family.invite_code)
        CalendarItem.objects.create(owner=self.ayse, title="Kişisel plan", date=date(2026, 10, 13))
        CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile planı", date=date(2026, 10, 14))
        CalendarItem.objects.create(owner=self.can, family=self.family, title="Can'in planı", date=date(2026, 10, 14))
        FoodItem.objects.create(owner=self.ayse, name="Süt")

    def test_requires_login(self):
        response = self.client.get(reverse("export_data"))
        self.assertEqual(response.status_code, 302)

    def test_export_contains_only_own_data(self):
        self.client.force_login(self.ayse)
        response = self.client.get(reverse("export_data"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        data = json.loads(response.content)
        self.assertEqual(data["hesap"]["e_posta"], "ayse@example.com")
        titles = {i["baslik"] for i in data["takvim"]}
        self.assertEqual(titles, {"Kişisel plan", "Aile planı"})
        self.assertEqual([f["urun"] for f in data["buzdolabi"]], ["Süt"])
        self.assertEqual(data["aile_uyelikleri"][0]["aile"], "Yılmazlar")
        raw = response.content.decode()
        self.assertNotIn("can@example.com", raw)
        self.assertNotIn(self.family.invite_code, raw)


class ErrorPageTests(TestCase):
    def test_404_is_friendly_and_generic(self):
        response = self.client.get("/boyle-bir-sayfa-yok/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Bu sayfayı bulamadık", status_code=404)
        self.assertNotContains(response, "Traceback", status_code=404)
        self.assertNotContains(response, "urlpatterns", status_code=404)

    def test_404_for_logged_in_user(self):
        self.client.force_login(make_user("Ayse"))
        response = self.client.get("/takvim/oge/999999/duzenle/")
        self.assertContains(response, "Bu sayfayı bulamadık", status_code=404)

    def test_500_template_is_standalone(self):
        from django.template import loader

        html = loader.get_template("500.html").render({})
        self.assertIn("Bir şeyler ters gitti", html)
