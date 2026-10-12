"""
Buzdolabı iş kuralları: kapsam (kişisel / aile), aktif ürün limiti, yaklaşan SKT'ler.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core import limits
from families.models import Family, FamilyMember

from .models import FoodItem


class FridgeLimitError(Exception):
    def __init__(self):
        super().__init__(f"Buzdolabında en fazla {limits.MAX_FRIDGE_ITEMS_PER_FAMILY} aktif ürün olabilir. "
                         "Tüketilenleri işaretlemeyi dene.")


def accessible_items(user):
    """Kullanıcının erişebildiği ürünler: kişisel buzdolabı + üyesi olduğu ailelerin buzdolapları."""
    family_ids = FamilyMember.objects.filter(user=user).values("family_id")
    return FoodItem.objects.filter(Q(owner=user, family__isnull=True) | Q(family_id__in=family_ids))


def scope_items(user, family=None):
    """Bağlama göre buzdolabı: Bireysel = kişisel, Aile = ailenin ortak buzdolabı."""
    if family is None:
        return FoodItem.objects.filter(owner=user, family__isnull=True)
    if not FamilyMember.objects.filter(user=user, family=family).exists():
        return FoodItem.objects.none()
    return FoodItem.objects.filter(family=family)


def active_items(user, family=None):
    return scope_items(user, family).filter(is_consumed=False).select_related("owner", "rule")


def expiring_items(user, family=None, days=limits.EXPIRY_WARNING_DAYS):
    """SKT'si `days` gün içinde dolan ya da geçmiş, tüketilmemiş ürünler."""
    limit_date = timezone.localdate() + timedelta(days=days)
    return active_items(user, family).filter(use_by__lte=limit_date)


def add_item(user, item, family=None):
    """
    Yeni ürünü aktif ürün limitini kontrol ederek ekler. Eşzamanlı eklemelere karşı
    aile (ya da kişisel buzdolabında kullanıcı) satırı kilitlenir.
    """
    item.owner = user
    item.family = family
    with transaction.atomic():
        if family is not None:
            Family.objects.select_for_update().only("pk").get(pk=family.pk)
        else:
            get_user_model().objects.select_for_update().only("pk").get(pk=user.pk)
        if scope_items(user, family).filter(is_consumed=False).count() >= limits.MAX_FRIDGE_ITEMS_PER_FAMILY:
            raise FridgeLimitError()
        item.save()
    return item


def mark_consumed(item, consumed=True):
    item.is_consumed = consumed
    item.consumed_at = timezone.now() if consumed else None
    item.save(update_fields=["is_consumed", "consumed_at"])


def mark_opened_today(item):
    """'Bugün açtım': açılma tarihini bugün yapar; öneri günü yoksa kuraldan alır."""
    item.opened_on = timezone.localdate()
    if item.suggested_days is None and item.rule_id:
        item.suggested_days = item.rule.opened_days
    item.save(update_fields=["opened_on", "suggested_days"])
