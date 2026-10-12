"""
Takvim iş kuralları: günlük limit ve tekrar eden öğelerin hesaplanması.
Limit kontrolü burada, sunucu tarafında yapılır (bkz. docs/callender.md bölüm 5).
"""
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db import transaction

from core import limits

from .models import CalendarItem, Occurrence


class DailyLimitError(Exception):
    """Bir güne eklenebilecek öğe sınırı aşıldı."""

    def __init__(self):
        super().__init__(f"Bu güne en fazla {limits.MAX_ITEMS_PER_DAY} kayıt ekleyebilirsin.")


def items_on_date_count(user, day, exclude_pk=None):
    """Kullanıcının o tarihe kaydettiği öğe sayısı (yıllık tekrarlar ilk tarihlerinde sayılır)."""
    qs = CalendarItem.objects.filter(owner=user, date=day)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def save_item(user, item):
    """
    Öğeyi günlük limiti kontrol ederek kaydeder. Aynı anda gelen iki istek limiti
    aşmasın diye kullanıcı satırı işlem boyunca kilitlenir.
    """
    with transaction.atomic():
        get_user_model().objects.select_for_update().only("pk").get(pk=user.pk)
        if items_on_date_count(user, item.date, exclude_pk=item.pk) >= limits.MAX_ITEMS_PER_DAY:
            raise DailyLimitError()
        item.owner = user
        item.save()
    return item


def occurrences_between(user, start, end):
    """
    [start, end] aralığındaki tüm görünümler, tarihe göre sözlük olarak.
    Tek seferlik öğeler doğrudan, yıllık öğeler her yıl için hesaplanarak eklenir.
    """
    by_date = defaultdict(list)

    one_off = CalendarItem.objects.filter(
        owner=user, repeat=CalendarItem.Repeat.NONE, date__range=(start, end)
    )
    for item in one_off:
        by_date[item.date].append(Occurrence(item, item.date))

    yearly = CalendarItem.objects.filter(owner=user, repeat=CalendarItem.Repeat.YEARLY, date__lte=end)
    for item in yearly:
        for year in range(start.year, end.year + 1):
            day = item.occurs_in_year(year)
            if day and start <= day <= end:
                by_date[day].append(Occurrence(item, day))

    for occurrences in by_date.values():
        occurrences.sort(key=_sort_key)
    return by_date


def occurrences_on(user, day):
    return occurrences_between(user, day, day).get(day, [])


def _sort_key(occurrence):
    item = occurrence.item
    # Tüm gün öğeleri önce, sonra saate göre
    return (not item.all_day, item.start_time or item.created_at.time(), item.created_at)
