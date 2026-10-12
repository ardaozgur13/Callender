import calendar
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.db import models

from core import limits


class CalendarItem(models.Model):
    """
    Takvim öğesi. Tekrar eden öğeler (doğum günü vb.) veritabanında tek satırdır;
    takvimde gösterilirken ilgili gün için hesaplanır (bkz. occurs_in_year).
    """

    class Kind(models.TextChoices):
        EVENT = "event", "Etkinlik"
        TASK = "task", "Görev"
        GOAL = "goal", "Amaç"
        BIRTHDAY = "birthday", "Doğum günü"
        ANNIVERSARY = "anniversary", "Yıldönümü"
        REMINDER = "reminder", "Hatırlatma"

    class Repeat(models.TextChoices):
        NONE = "none", "Tekrar yok"
        YEARLY = "yearly", "Her yıl"

    # Varsayılan olarak her yıl tekrar eden türler
    YEARLY_KINDS = (Kind.BIRTHDAY, Kind.ANNIVERSARY)
    # "Tamamlandı" işareti alabilen türler
    CHECKABLE_KINDS = (Kind.TASK, Kind.GOAL)

    KIND_ICONS = {
        Kind.EVENT: "📌",
        Kind.TASK: "✅",
        Kind.GOAL: "🎯",
        Kind.BIRTHDAY: "🎂",
        Kind.ANNIVERSARY: "💐",
        Kind.REMINDER: "🔔",
    }

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar_items", verbose_name="oluşturan"
    )
    # Boş = kişisel öğe; dolu = ailenin tüm üyelerinin gördüğü aile öğesi
    family = models.ForeignKey(
        "families.Family", on_delete=models.CASCADE, null=True, blank=True, related_name="calendar_items",
        verbose_name="aile",
    )
    kind = models.CharField("tür", max_length=20, choices=Kind.choices, default=Kind.EVENT)
    title = models.CharField("başlık", max_length=limits.TITLE_MAX)
    description = models.TextField("açıklama", max_length=limits.DESCRIPTION_MAX, blank=True)
    date = models.DateField("tarih", db_index=True)
    all_day = models.BooleanField("tüm gün", default=True)
    start_time = models.TimeField("başlangıç", null=True, blank=True)
    end_time = models.TimeField("bitiş", null=True, blank=True)
    repeat = models.CharField("tekrar", max_length=10, choices=Repeat.choices, default=Repeat.NONE)
    is_done = models.BooleanField("tamamlandı", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "takvim öğesi"
        verbose_name_plural = "takvim öğeleri"
        ordering = ["date", "-all_day", "start_time", "created_at"]
        indexes = [models.Index(fields=["owner", "date"])]

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def icon(self):
        return self.KIND_ICONS.get(self.kind, "📌")

    @property
    def is_checkable(self):
        return self.kind in self.CHECKABLE_KINDS

    def occurs_in_year(self, year):
        """
        Yıllık tekrar eden öğenin verilen yıldaki tarihi. Öğenin ilk tarihinden önceki
        yıllarda None döner. 29 Şubat, artık olmayan yıllarda 28 Şubat'a düşer.
        """
        if year < self.date.year:
            return None
        day = self.date.day
        if self.date.month == 2 and day == 29 and not calendar.isleap(year):
            day = 28
        return date(year, self.date.month, day)


@dataclass
class Occurrence:
    """Bir öğenin takvimde belirli bir güne düşen görünümü."""

    item: CalendarItem
    date: date

    @property
    def years(self):
        """Yıllık tekrarda kaçıncı yıl olduğu (doğum günü yaşı, yıldönümü yılı). İlk yıl için None."""
        if self.item.repeat != CalendarItem.Repeat.YEARLY:
            return None
        return (self.date.year - self.item.date.year) or None
