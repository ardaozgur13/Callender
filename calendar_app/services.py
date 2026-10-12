"""
Takvim iş kuralları: kapsam (kişisel / aile), günlük limit ve tekrar eden öğelerin hesaplanması.
Limit ve yetki kontrolleri burada, sunucu tarafında yapılır (bkz. docs/callender.md bölüm 5).
"""
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from core import limits
from families.models import FamilyMember

from .models import CalendarItem, Occurrence


class DailyLimitError(Exception):
    """Bir güne eklenebilecek öğe sınırı aşıldı."""

    def __init__(self):
        super().__init__(f"Bu güne en fazla {limits.MAX_ITEMS_PER_DAY} kayıt ekleyebilirsin.")


def accessible_items(user):
    """Kullanıcının erişebildiği tüm öğeler: kendi kişisel öğeleri + üyesi olduğu ailelerin öğeleri."""
    family_ids = FamilyMember.objects.filter(user=user).values("family_id")
    return CalendarItem.objects.filter(Q(owner=user, family__isnull=True) | Q(family_id__in=family_ids))


def scope_items(user, family=None):
    """Bağlama göre görünen öğeler: Bireysel = kişisel öğeler, Aile = o ailenin öğeleri."""
    if family is None:
        return CalendarItem.objects.filter(owner=user, family__isnull=True)
    if not FamilyMember.objects.filter(user=user, family=family).exists():
        return CalendarItem.objects.none()
    return CalendarItem.objects.filter(family=family)


def items_on_date_count(user, day, exclude_pk=None):
    """
    Kullanıcının o tarihe kendi oluşturduğu öğe sayısı: kişisel + kendi eklediği aile öğeleri.
    Yıllık tekrarlar ilk tarihlerinde sayılır.
    """
    qs = CalendarItem.objects.filter(owner=user, date=day)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def save_item(user, item):
    """
    Öğeyi günlük limiti kontrol ederek kaydeder. Limit öğeyi oluşturanın hesabına sayılır.
    Aynı anda gelen iki istek limiti aşmasın diye o kullanıcının satırı işlem boyunca kilitlenir.
    """
    if item.pk is None:
        item.owner = user
    with transaction.atomic():
        get_user_model().objects.select_for_update().only("pk").get(pk=item.owner_id)
        if items_on_date_count(item.owner, item.date, exclude_pk=item.pk) >= limits.MAX_ITEMS_PER_DAY:
            raise DailyLimitError()
        item.save()
    return item


def occurrences_between(user, start, end, family=None):
    """
    [start, end] aralığındaki tüm görünümler, tarihe göre sözlük olarak.
    Tek seferlik öğeler doğrudan, yıllık öğeler her yıl için hesaplanarak eklenir.
    """
    base = scope_items(user, family).select_related("owner")
    by_date = defaultdict(list)

    for item in base.filter(repeat=CalendarItem.Repeat.NONE, date__range=(start, end)):
        by_date[item.date].append(Occurrence(item, item.date))

    for item in base.filter(repeat=CalendarItem.Repeat.YEARLY, date__lte=end):
        for year in range(start.year, end.year + 1):
            day = item.occurs_in_year(year)
            if day and start <= day <= end:
                by_date[day].append(Occurrence(item, day))

    for occurrences in by_date.values():
        occurrences.sort(key=_sort_key)
    return by_date


def occurrences_on(user, day, family=None):
    return occurrences_between(user, day, day, family).get(day, [])


def _sort_key(occurrence):
    item = occurrence.item
    # Tüm gün öğeleri önce, sonra saate göre
    return (not item.all_day, item.start_time or item.created_at.time(), item.created_at)
