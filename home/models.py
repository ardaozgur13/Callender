from django.conf import settings
from django.db import models

from core import limits

WEEKDAY_CHOICES = [
    (0, "Pazartesi"), (1, "Salı"), (2, "Çarşamba"), (3, "Perşembe"),
    (4, "Cuma"), (5, "Cumartesi"), (6, "Pazar"),
]


class Chore(models.Model):
    """Ailenin ev işi. Her hafta tekrar eder: belirli bir günde ya da (weekday boşsa) her gün."""

    family = models.ForeignKey(
        "families.Family", on_delete=models.CASCADE, related_name="chores", verbose_name="aile"
    )
    title = models.CharField("iş", max_length=limits.TITLE_MAX)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_chores", verbose_name="kim yapacak",
    )
    weekday = models.PositiveSmallIntegerField("hangi gün", choices=WEEKDAY_CHOICES, null=True, blank=True)
    is_active = models.BooleanField("aktif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ev işi"
        verbose_name_plural = "ev işleri"
        ordering = ["weekday", "title"]

    def __str__(self):
        return self.title

    def occurs_on(self, day):
        return self.weekday is None or self.weekday == day.weekday()

    @property
    def schedule_label(self):
        return "Her gün" if self.weekday is None else f"Her {self.get_weekday_display().lower()}"


class ChoreLog(models.Model):
    """Bir işin belirli bir günde yapıldığı kaydı."""

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="logs", verbose_name="iş")
    date = models.DateField("tarih")
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="yapan"
    )
    done_at = models.DateTimeField("yapılma zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "ev işi kaydı"
        verbose_name_plural = "ev işi kayıtları"
        constraints = [models.UniqueConstraint(fields=["chore", "date"], name="unique_chore_log_per_day")]


class HomeStatus(models.Model):
    """Ailenin bulaşık makinesi / çamaşır durumu kartı."""

    class Kind(models.TextChoices):
        DISHWASHER = "dishwasher", "Bulaşık makinesi"
        LAUNDRY = "laundry", "Çamaşır"

    # Her tür için durumların sırası (döngüsel), etiketleri ve ilk durum
    FLOWS = {
        Kind.DISHWASHER: [
            ("idle", "Boş"),
            ("loaded", "Dolu"),
            ("running", "Çalışıyor"),
            ("done", "Bitti"),
            ("needs_unloading", "Boşaltılmalı"),
        ],
        Kind.LAUNDRY: [
            ("washing", "Yıkanıyor"),
            ("washed", "Yıkandı, serilmeli"),
            ("hanging", "Serildi"),
            ("dry", "Kurudu, toplanmalı"),
            ("done", "Toplandı"),
        ],
    }
    INITIAL = {Kind.DISHWASHER: "idle", Kind.LAUNDRY: "done"}
    # Birinin bir şey yapması gereken durumlar (sarı vurgu)
    NEEDS_ACTION = {Kind.DISHWASHER: {"done", "needs_unloading"}, Kind.LAUNDRY: {"washed", "dry"}}
    # Sakin / tamam durumlar (yeşil)
    CALM = {Kind.DISHWASHER: {"idle"}, Kind.LAUNDRY: {"done"}}
    ICONS = {Kind.DISHWASHER: "🍽️", Kind.LAUNDRY: "🧺"}

    family = models.ForeignKey(
        "families.Family", on_delete=models.CASCADE, related_name="home_statuses", verbose_name="aile"
    )
    kind = models.CharField("tür", max_length=20, choices=Kind.choices)
    status = models.CharField("durum", max_length=20)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="güncelleyen",
    )
    updated_at = models.DateTimeField("güncellenme zamanı", auto_now=True)

    class Meta:
        verbose_name = "ev durumu"
        verbose_name_plural = "ev durumları"
        ordering = ["kind"]
        constraints = [models.UniqueConstraint(fields=["family", "kind"], name="unique_home_status_kind")]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.status_label}"

    @property
    def steps(self):
        return self.FLOWS[self.kind]

    @property
    def step_keys(self):
        return [key for key, _ in self.steps]

    @property
    def status_label(self):
        return dict(self.steps).get(self.status, self.status)

    @property
    def next_status(self):
        keys = self.step_keys
        index = keys.index(self.status) if self.status in keys else -1
        return keys[(index + 1) % len(keys)]

    @property
    def next_label(self):
        return dict(self.steps)[self.next_status]

    @property
    def tone(self):
        if self.status in self.NEEDS_ACTION[self.kind]:
            return "attention"
        if self.status in self.CALM[self.kind]:
            return "calm"
        return "busy"

    @property
    def icon(self):
        return self.ICONS[self.kind]
