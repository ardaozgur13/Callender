"""
Hesap silme ve veri dışa aktarma (KVKK, docs/callender.md bölüm 7 ve 13.2).
"""
from django.db import transaction
from django.utils import timezone

from calendar_app.models import CalendarItem
from families.models import FamilyMember
from families.services import leave_all_families
from fridge.models import FoodItem
from home.models import Chore, ChoreLog


def delete_account(user):
    """
    Hesabı ve kişisel veriyi siler:
    1. Ailelerden kurallara göre ayrıl (tek kurucuysa en eski üyeye devir; son üyeyse aile silinir).
    2. Kişisel takvim öğeleri ve kişisel gıdalar açıkça silinir.
    3. Kullanıcı silinir. Aile öğeleri/gıdaları kalır, `owner` SET_NULL ile "Silinmiş kullanıcı" olur;
       ev işi ataması, "yaptım" kayıtları ve ev durumu güncelleyeni de SET_NULL olur.
    """
    with transaction.atomic():
        leave_all_families(user)
        CalendarItem.objects.filter(owner=user, family__isnull=True).delete()
        FoodItem.objects.filter(owner=user, family__isnull=True).delete()
        user.delete()


def _dt(value):
    return value.isoformat() if value else None


def export_data(user):
    """
    Kullanıcının kendi verisi (JSON'a çevrilebilir sözlük). Diğer üyelerin e-postaları,
    davet kodları ve başkalarının eklediği kayıtlar dahil edilmez.
    """
    memberships = FamilyMember.objects.filter(user=user).select_related("family").order_by("joined_at")
    calendar_items = CalendarItem.objects.filter(owner=user).select_related("family").order_by("date", "pk")
    foods = FoodItem.objects.filter(owner=user).select_related("family").order_by("pk")
    chore_logs = ChoreLog.objects.filter(done_by=user).select_related("chore__family").order_by("date", "pk")
    assigned = Chore.objects.filter(assigned_to=user).select_related("family").order_by("pk")

    return {
        "aciklama": "Callender'da sana ait kayıtların dışa aktarımı.",
        "olusturulma_zamani": _dt(timezone.now()),
        "hesap": {
            "e_posta": user.email,
            "isim": user.display_name,
            "katilma_zamani": _dt(user.date_joined),
            "kosullari_onay_zamani": _dt(user.accepted_terms_at),
        },
        "aile_uyelikleri": [
            {"aile": m.family.name, "rol": m.get_role_display(), "katilma_zamani": _dt(m.joined_at)}
            for m in memberships
        ],
        "takvim": [
            {
                "baslik": i.title, "tur": i.get_kind_display(), "aciklama": i.description,
                "tarih": i.date.isoformat(), "tum_gun": i.all_day,
                "baslangic": i.start_time.strftime("%H:%M") if i.start_time else None,
                "bitis": i.end_time.strftime("%H:%M") if i.end_time else None,
                "tekrar": i.get_repeat_display(), "tamamlandi": i.is_done,
                "aile": i.family.name if i.family else None,
                "olusturulma_zamani": _dt(i.created_at),
            }
            for i in calendar_items
        ],
        "buzdolabi": [
            {
                "urun": f.name, "saklama": f.get_storage_display(),
                "acilma_tarihi": _dt(f.opened_on), "ambalaj_skt": _dt(f.package_expiry),
                "acildiktan_sonra_gun": f.suggested_days, "son_tuketim": _dt(f.use_by),
                "not": f.note, "tuketildi": f.is_consumed, "tuketilme_zamani": _dt(f.consumed_at),
                "aile": f.family.name if f.family else None, "eklenme_zamani": _dt(f.created_at),
            }
            for f in foods
        ],
        "bana_atanan_ev_isleri": [
            {"is": c.title, "gun": c.schedule_label, "aile": c.family.name, "aktif": c.is_active}
            for c in assigned
        ],
        "yaptigim_ev_isleri": [
            {"is": log.chore.title, "aile": log.chore.family.name, "tarih": log.date.isoformat(),
             "zaman": _dt(log.done_at)}
            for log in chore_logs
        ],
    }
