"""
Aile testleri: davet kodu, limitler, roller, ayrılma, bağlam seçici, ortak takvim yetkisi.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from calendar_app.models import CalendarItem
from core import limits

from . import services
from .context import SESSION_KEY
from .models import Family, FamilyMember

PASSWORD = "papatya-cayir-42"


def make_user(name):
    return User.objects.create_user(f"{name.lower()}@example.com", name, PASSWORD)


class InviteCodeTests(TestCase):
    def test_code_format(self):
        for _ in range(50):
            code = services.generate_invite_code()
            self.assertEqual(len(code), limits.INVITE_CODE_LENGTH)
            self.assertTrue(set(code) <= set(limits.INVITE_CODE_ALPHABET))

    def test_normalize_code(self):
        self.assertEqual(services.normalize_code(" k7mp-2rtv "), "K7MP2RTV")


class FamilyServiceTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")

    def test_create_makes_owner(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        membership = FamilyMember.objects.get(family=family, user=self.ayse)
        self.assertTrue(membership.is_owner)
        self.assertEqual(family.created_by, self.ayse)

    def test_join_with_code_case_insensitive(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        services.join_family(self.can, family.invite_code.lower())
        member = FamilyMember.objects.get(family=family, user=self.can)
        self.assertEqual(member.role, FamilyMember.Role.MEMBER)

    def test_wrong_code(self):
        with self.assertRaisesMessage(services.FamilyError, "Bu kodla bir aile bulamadık"):
            services.join_family(self.can, "ZZZZZZZZ")

    def test_already_member(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        with self.assertRaisesMessage(services.FamilyError, "Zaten"):
            services.join_family(self.ayse, family.invite_code)

    def test_two_family_limit_on_create_and_join(self):
        services.create_family(self.ayse, "Bir")
        services.create_family(self.ayse, "İki")
        with self.assertRaisesMessage(services.FamilyError, f"En fazla {limits.MAX_FAMILIES_PER_USER} aileye"):
            services.create_family(self.ayse, "Üç")
        other = services.create_family(self.can, "Canlar")
        with self.assertRaises(services.FamilyError):
            services.join_family(self.ayse, other.invite_code)
        self.assertEqual(FamilyMember.objects.filter(user=self.ayse).count(), limits.MAX_FAMILIES_PER_USER)

    def test_member_limit(self):
        family = services.create_family(self.ayse, "Kalabalık")
        for i in range(limits.MAX_FAMILY_MEMBERS - 1):
            services.join_family(make_user(f"Uye{i}"), family.invite_code)
        with self.assertRaisesMessage(services.FamilyError, "Bu aile dolu"):
            services.join_family(self.can, family.invite_code)

    def test_regenerate_invalidates_old_code(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        old = family.invite_code
        owner = services.get_membership(self.ayse, family.pk)
        new = services.regenerate_code(owner)
        self.assertNotEqual(old, new)
        with self.assertRaises(services.FamilyError):
            services.join_family(self.can, old)
        services.join_family(self.can, new)

    def test_owner_leaves_oldest_member_becomes_owner(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        services.join_family(self.can, family.invite_code)
        deniz = make_user("Deniz")
        services.join_family(deniz, family.invite_code)
        deleted = services.leave_family(services.get_membership(self.ayse, family.pk))
        self.assertFalse(deleted)
        self.assertTrue(services.get_membership(self.can, family.pk).is_owner)
        self.assertFalse(services.get_membership(deniz, family.pk).is_owner)

    def test_last_member_leaving_deletes_family_and_items(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        CalendarItem.objects.create(owner=self.ayse, family=family, title="Aile yemeği", date=date(2026, 10, 13))
        self.assertTrue(services.leave_family(services.get_membership(self.ayse, family.pk)))
        self.assertFalse(Family.objects.filter(pk=family.pk).exists())
        self.assertFalse(CalendarItem.objects.filter(title="Aile yemeği").exists())

    def test_only_owner_can_manage(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        services.join_family(self.can, family.invite_code)
        can_membership = services.get_membership(self.can, family.pk)
        owner = services.get_membership(self.ayse, family.pk)
        for action in (
            lambda: services.regenerate_code(can_membership),
            lambda: services.remove_member(can_membership, owner.pk),
            lambda: services.delete_family(can_membership),
        ):
            with self.assertRaisesMessage(services.FamilyError, "sadece aile kurucusu"):
                action()

    def test_owner_removes_member(self):
        family = services.create_family(self.ayse, "Yılmazlar")
        services.join_family(self.can, family.invite_code)
        owner = services.get_membership(self.ayse, family.pk)
        services.remove_member(owner, services.get_membership(self.can, family.pk).pk)
        self.assertIsNone(services.get_membership(self.can, family.pk))
        with self.assertRaises(services.FamilyError):
            services.remove_member(owner, owner.pk)


class FamilyViewTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.family = services.create_family(self.ayse, "Yılmazlar")

    def test_non_member_gets_404(self):
        self.client.force_login(self.can)
        self.assertEqual(self.client.get(reverse("family_detail", args=[self.family.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("family_leave", args=[self.family.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("family_delete", args=[self.family.pk])).status_code, 404)

    def test_create_and_join_via_pages(self):
        self.client.force_login(self.can)
        response = self.client.post(reverse("family_list"), {"action": "join", "join-code": self.family.invite_code})
        self.assertRedirects(response, reverse("family_detail", args=[self.family.pk]))
        self.assertEqual(self.client.session[SESSION_KEY], self.family.pk)
        response = self.client.post(reverse("family_list"), {"action": "create", "create-name": "Canlar"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FamilyMember.objects.filter(user=self.can).count(), 2)

    def test_family_name_limit(self):
        self.client.force_login(self.can)
        response = self.client.post(reverse("family_list"), {
            "action": "create", "create-name": "A" * (limits.FAMILY_NAME_MAX + 1),
        })
        self.assertContains(response, f"en fazla {limits.FAMILY_NAME_MAX} karakter")

    def test_wrong_code_shows_message(self):
        self.client.force_login(self.can)
        response = self.client.post(reverse("family_list"), {"action": "join", "join-code": "YANLIS99"})
        self.assertContains(response, "Bu kodla bir aile bulamadık")

    def test_member_cannot_rename_or_delete(self):
        services.join_family(self.can, self.family.invite_code)
        self.client.force_login(self.can)
        self.client.post(reverse("family_detail", args=[self.family.pk]), {"action": "rename", "rename-name": "Ele geçti"})
        self.client.post(reverse("family_delete", args=[self.family.pk]))
        self.family.refresh_from_db()
        self.assertEqual(self.family.name, "Yılmazlar")

    def test_owner_renames(self):
        self.client.force_login(self.ayse)
        self.client.post(reverse("family_detail", args=[self.family.pk]), {"action": "rename", "rename-name": "Yeni ad"})
        self.family.refresh_from_db()
        self.assertEqual(self.family.name, "Yeni ad")

    def test_detail_shows_code_to_members(self):
        self.client.force_login(self.ayse)
        self.assertContains(self.client.get(reverse("family_detail", args=[self.family.pk])), self.family.invite_code)

    def test_account_delete_transfers_ownership(self):
        services.join_family(self.can, self.family.invite_code)
        self.client.force_login(self.ayse)
        self.client.post(reverse("delete_account"), {"del-password": PASSWORD})
        self.assertTrue(services.get_membership(self.can, self.family.pk).is_owner)


class ContextAndSharedCalendarTests(TestCase):
    def setUp(self):
        self.ayse = make_user("Ayse")
        self.can = make_user("Can")
        self.zeynep = make_user("Zeynep")  # aileye üye değil
        self.family = services.create_family(self.ayse, "Yılmazlar")
        services.join_family(self.can, self.family.invite_code)
        self.day = date(2026, 10, 13)
        self.day_url = reverse("calendar_day", args=[2026, 10, 13])

    def switch(self, family_id):
        return self.client.post(reverse("switch_context"), {"family": family_id or "", "next": self.day_url})

    def add_item(self, title):
        return self.client.post(reverse("item_create"), {
            "kind": "event", "title": title, "date": self.day.isoformat(), "all_day": "on", "repeat": "none",
        })

    def test_item_created_in_family_context_is_shared(self):
        self.client.force_login(self.ayse)
        self.switch(self.family.pk)
        self.add_item("Pazar kahvaltısı")
        item = CalendarItem.objects.get(title="Pazar kahvaltısı")
        self.assertEqual(item.family, self.family)

        self.client.force_login(self.can)
        self.switch(self.family.pk)
        response = self.client.get(self.day_url)
        self.assertContains(response, "Pazar kahvaltısı")
        self.assertContains(response, "Ayse ekledi")

    def test_personal_items_not_in_family_view(self):
        CalendarItem.objects.create(owner=self.ayse, title="Gizli kişisel", date=self.day)
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        self.assertNotContains(self.client.get(self.day_url), "Gizli kişisel")
        self.client.force_login(self.ayse)
        self.switch(None)
        self.assertContains(self.client.get(self.day_url), "Gizli kişisel")

    def test_family_items_not_in_personal_view(self):
        CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile yemeği", date=self.day)
        self.client.force_login(self.ayse)
        self.switch(None)
        self.assertNotContains(self.client.get(self.day_url), "Aile yemeği")

    def test_non_member_cannot_switch_or_access(self):
        item = CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile yemeği", date=self.day)
        self.client.force_login(self.zeynep)
        self.switch(self.family.pk)
        self.assertIsNone(self.client.session.get(SESSION_KEY))
        self.assertNotContains(self.client.get(self.day_url), "Aile yemeği")
        self.assertEqual(self.client.get(reverse("item_edit", args=[item.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("item_delete", args=[item.pk])).status_code, 404)

    def edit_post(self, item, title):
        return self.client.post(reverse("item_edit", args=[item.pk]), {
            "kind": "event", "title": title, "date": self.day.isoformat(), "all_day": "on", "repeat": "none",
        })

    def test_member_cannot_edit_or_delete_others_family_item(self):
        # Kural (bölüm 6): üye kendi eklediğini düzenler/siler, kurucu her şeyi yönetir
        item = CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile yemeği", date=self.day)
        self.client.force_login(self.can)
        self.assertEqual(self.edit_post(item, "Ele geçirildi").status_code, 403)
        self.assertEqual(self.client.post(reverse("item_delete", args=[item.pk])).status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.title, "Aile yemeği")
        # Ama görebilir ve tamamlandı işaretleyebilir (görev ise)
        self.switch(self.family.pk)
        self.assertContains(self.client.get(self.day_url), "Aile yemeği")

    def test_member_edits_own_family_item(self):
        item = CalendarItem.objects.create(owner=self.can, family=self.family, title="Can'in planı", date=self.day)
        self.client.force_login(self.can)
        self.assertEqual(self.edit_post(item, "Can'in yeni planı").status_code, 302)
        item.refresh_from_db()
        self.assertEqual((item.title, item.owner), ("Can'in yeni planı", self.can))

    def test_family_owner_manages_everything_owner_field_unchanged(self):
        item = CalendarItem.objects.create(owner=self.can, family=self.family, title="Can'in planı", date=self.day)
        self.client.force_login(self.ayse)  # Ayşe kurucu
        self.assertEqual(self.edit_post(item, "Kurucu düzeltti").status_code, 302)
        item.refresh_from_db()
        self.assertEqual((item.title, item.owner), ("Kurucu düzeltti", self.can))
        self.client.post(reverse("item_delete", args=[item.pk]))
        self.assertFalse(CalendarItem.objects.filter(pk=item.pk).exists())

    def test_edit_buttons_hidden_for_non_manager(self):
        CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile yemeği", date=self.day)
        mine = CalendarItem.objects.create(owner=self.can, family=self.family, title="Benimki", date=self.day)
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        response = self.client.get(self.day_url)
        self.assertContains(response, reverse("item_edit", args=[mine.pk]))
        self.assertContains(response, "Düzenle: Benimki")
        self.assertNotContains(response, "Düzenle: Aile yemeği")

    def test_leaving_removes_access_and_context(self):
        item = CalendarItem.objects.create(owner=self.ayse, family=self.family, title="Aile yemeği", date=self.day)
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        self.client.post(reverse("family_leave", args=[self.family.pk]))
        self.assertEqual(self.client.get(reverse("item_edit", args=[item.pk])).status_code, 404)
        self.assertNotContains(self.client.get(self.day_url), "Aile yemeği")

    def test_removed_member_context_falls_back_to_personal(self):
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        owner = services.get_membership(self.ayse, self.family.pk)
        services.remove_member(owner, services.get_membership(self.can, self.family.pk).pk)
        response = self.client.get(self.day_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_daily_limit_counts_personal_and_own_family_items(self):
        for i in range(limits.MAX_ITEMS_PER_DAY // 2):
            CalendarItem.objects.create(owner=self.ayse, title=f"K{i}", date=self.day)
            CalendarItem.objects.create(owner=self.ayse, family=self.family, title=f"A{i}", date=self.day)
        self.client.force_login(self.ayse)
        self.switch(self.family.pk)
        response = self.add_item("Fazladan")
        self.assertContains(response, f"Bu güne en fazla {limits.MAX_ITEMS_PER_DAY} kayıt ekleyebilirsin.")
        # Can'in kotası Ayşe'nin kayıtlarından etkilenmez
        self.client.force_login(self.can)
        self.switch(self.family.pk)
        self.assertEqual(self.add_item("Can'in kaydı").status_code, 302)

    def test_switch_rejects_external_next(self):
        self.client.force_login(self.ayse)
        response = self.client.post(reverse("switch_context"), {"family": "", "next": "https://evil.example.com/"})
        self.assertEqual(response["Location"], "/")
