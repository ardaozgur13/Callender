"""
Ev işleri ve ev durumu iş kuralları. Yetki ve limitler burada, sunucu tarafında zorlanır.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from core import limits
from families.models import Family

from .models import Chore, ChoreLog, HomeStatus


class HomeError(Exception):
    """Kullanıcıya gösterilecek nazik mesaj taşıyan hata."""


def accessible_chores(user):
    """Kullanıcının üyesi olduğu ailelerin işleri (bkz. ChoreQuerySet.for_user)."""
    return Chore.objects.for_user(user)


def family_chores(family):
    return Chore.objects.filter(family=family, is_active=True).select_related("assigned_to")


def save_chore(chore, family):
    """Yeni işi aktif iş limitini kontrol ederek kaydeder (aile satırı kilitlenir)."""
    with transaction.atomic():
        Family.objects.select_for_update().only("pk").get(pk=family.pk)
        becomes_active = chore.is_active and (
            chore.pk is None or not Chore.objects.filter(pk=chore.pk, is_active=True).exists()
        )
        if becomes_active and Chore.objects.filter(family=family, is_active=True).count() >= limits.MAX_CHORES_PER_FAMILY:
            raise HomeError(f"Bir ailede en fazla {limits.MAX_CHORES_PER_FAMILY} aktif ev işi olabilir.")
        chore.family = family
        chore.save()
    return chore


def week_days(any_day):
    """O günün içinde olduğu haftanın Pazartesi–Pazar günleri."""
    monday = any_day - timedelta(days=any_day.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def week_schedule(family, days):
    """Her gün için [(iş, kayıt ya da None)] listesi."""
    chores = list(family_chores(family))
    logs = {
        (log.chore_id, log.date): log
        for log in ChoreLog.objects.filter(chore__family=family, date__range=(days[0], days[-1])).select_related("done_by")
    }
    return [
        {"date": day, "entries": [(c, logs.get((c.pk, day))) for c in chores if c.occurs_on(day)]}
        for day in days
    ]


def toggle_done(chore, day, user):
    """'Yaptım' aç/kapat. Gelecek günler işaretlenemez. Yeni durumda True döner."""
    if not chore.is_active:
        raise HomeError("Bu iş pasif; önce aktif hale getir.")
    if day > timezone.localdate():
        raise HomeError("Gelecekteki bir gün için “yaptım” denemez.")
    if not chore.occurs_on(day):
        raise HomeError("Bu iş o gün yapılacaklar listesinde değil.")
    deleted, _ = ChoreLog.objects.filter(chore=chore, date=day).delete()
    if deleted:
        return False
    try:
        with transaction.atomic():
            ChoreLog.objects.create(chore=chore, date=day, done_by=user)
    except IntegrityError:
        pass  # Aynı anda başka biri işaretledi; sonuç zaten "yapıldı"
    return True


def unassign_member(family_id, user):
    """Aileden ayrılan/çıkarılan kişinin işleri 'herkes'e döner."""
    Chore.objects.filter(family_id=family_id, assigned_to=user).update(assigned_to=None)


def get_statuses(family):
    """Ailenin bulaşık ve çamaşır kartları; yoksa ilk durumla oluşturulur."""
    statuses = []
    for kind in HomeStatus.Kind:
        status, _ = HomeStatus.objects.get_or_create(
            family=family, kind=kind, defaults={"status": HomeStatus.INITIAL[kind]}
        )
        statuses.append(status)
    return statuses


def change_status(family, kind, user, expected, new_status=None):
    """
    Durumu değiştirir. new_status yoksa bir sonraki adıma geçer. `expected`, kullanıcının
    sayfada gördüğü durumdur; bu arada başkası değiştirdiyse işlem yapılmaz (çift tıklama /
    iki kişinin aynı anda basması adımı iki kez ilerletmesin).
    """
    if kind not in HomeStatus.Kind.values:
        raise HomeError("Bilinmeyen durum kartı.")
    get_statuses(family)
    with transaction.atomic():
        card = HomeStatus.objects.select_for_update().get(family=family, kind=kind)
        if expected and expected != card.status:
            who = card.updated_by.display_name if card.updated_by else "Biri"
            raise HomeError(f"{who} bu arada durumu “{card.status_label}” yaptı. Güncel hali aşağıda.")
        target = new_status or card.next_status
        if target not in card.step_keys:
            raise HomeError("Geçersiz durum.")
        card.status = target
        card.updated_by = user
        card.save()
    return card
