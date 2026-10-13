from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core import limits


class Storage(models.TextChoices):
    FRIDGE = "fridge", "Buzdolabı"
    ROOM = "room", "Oda sıcaklığı"
    FREEZER = "freezer", "Dondurucu"


class ShelfLifeRule(models.Model):
    """Açıldıktan sonra önerilen süre (seed ile doldurulur, bkz. seed_shelf_life.py)."""

    class Source(models.TextChoices):
        USDA = "usda", "USDA kaynağında doğrulandı"
        ESTIMATE = "estimate", "Muhafazakâr tahmin"

    key = models.SlugField("anahtar", unique=True)
    name_tr = models.CharField("ad", max_length=limits.FOOD_NAME_MAX)
    category = models.CharField("kategori", max_length=40)
    storage = models.CharField("saklama", max_length=10, choices=Storage.choices, default=Storage.FRIDGE)
    opened_days = models.PositiveSmallIntegerField("açıldıktan sonra (gün)")
    source = models.CharField("kaynak", max_length=10, choices=Source.choices)
    note = models.CharField("not", max_length=200, blank=True)

    class Meta:
        verbose_name = "raf ömrü kuralı"
        verbose_name_plural = "raf ömrü kuralları"
        ordering = ["category", "name_tr"]

    def __str__(self):
        return self.name_tr


class FoodItemQuerySet(models.QuerySet):
    def for_user(self, user):
        """Kullanıcının erişebildiği ürünler: kişisel buzdolabı + üyesi olduğu ailelerin buzdolapları."""
        from families.models import FamilyMember

        family_ids = FamilyMember.objects.filter(user=user).values("family_id")
        return self.filter(Q(owner=user, family__isnull=True) | Q(family_id__in=family_ids))


class FoodItem(models.Model):
    class Status(models.TextChoices):
        FRESH = "fresh", "Taze"
        SOON = "soon", "Yaklaşıyor"
        LATE = "late", "Süresi geçti"
        UNKNOWN = "unknown", "Tarih yok"

    # Boş = kişisel buzdolabı (owner'ın); dolu = ailenin ortak buzdolabı
    family = models.ForeignKey(
        "families.Family", on_delete=models.CASCADE, null=True, blank=True, related_name="food_items",
        verbose_name="aile",
    )
    # Hesap silinince aile buzdolabındaki ürünler kalır; kişisel ürünler hesap silmede ayrıca silinir
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="food_items",
        verbose_name="ekleyen",
    )
    name = models.CharField("ürün adı", max_length=limits.FOOD_NAME_MAX)
    rule = models.ForeignKey(
        ShelfLifeRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="öneri"
    )
    storage = models.CharField("saklama yeri", max_length=10, choices=Storage.choices, default=Storage.FRIDGE)
    opened_on = models.DateField("açılma tarihi", null=True, blank=True)
    package_expiry = models.DateField("ambalajdaki SKT", null=True, blank=True)
    suggested_days = models.PositiveSmallIntegerField("açıldıktan sonra (gün)", null=True, blank=True)
    use_by = models.DateField("son tüketim", null=True, blank=True, db_index=True, editable=False)
    note = models.CharField("not", max_length=limits.FOOD_NOTE_MAX, blank=True)
    is_consumed = models.BooleanField("tüketildi", default=False)
    consumed_at = models.DateTimeField("tüketilme zamanı", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FoodItemQuerySet.as_manager()

    class Meta:
        verbose_name = "gıda"
        verbose_name_plural = "gıdalar"
        ordering = [models.F("use_by").asc(nulls_last=True), "name"]
        indexes = [models.Index(fields=["family", "is_consumed", "use_by"])]
        constraints = [
            # Sahipsiz ürün olamaz: ya bir aileye ya da bir kullanıcıya ait olmalı
            models.CheckConstraint(
                condition=Q(family__isnull=False) | Q(owner__isnull=False), name="food_has_family_or_owner"
            ),
        ]

    def __str__(self):
        return self.name

    def compute_use_by(self):
        """
        Geçerli son tüketim tarihi (tek kaynak burası):
        açılmışsa açılma + önerilen gün; ambalaj SKT'si de varsa ikisinin erken olanı.
        Sadece SKT varsa o, hiçbiri yoksa None.
        """
        candidates = []
        if self.opened_on and self.suggested_days is not None:
            candidates.append(self.opened_on + timedelta(days=self.suggested_days))
        if self.package_expiry:
            candidates.append(self.package_expiry)
        return min(candidates) if candidates else None

    def save(self, *args, **kwargs):
        self.use_by = self.compute_use_by()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"use_by"}
        super().save(*args, **kwargs)

    @property
    def days_left(self):
        """SKT'ye kalan gün (bugün = 0, geçmişse negatif); tarih yoksa None."""
        if self.use_by is None:
            return None
        return (self.use_by - timezone.localdate()).days

    @property
    def status(self):
        days = self.days_left
        if days is None:
            return self.Status.UNKNOWN
        if days < 0:
            return self.Status.LATE
        if days <= limits.EXPIRY_WARNING_DAYS:
            return self.Status.SOON
        return self.Status.FRESH

    @property
    def days_left_label(self):
        days = self.days_left
        if days is None:
            return "Tarih girilmedi"
        if days < 0:
            return f"{-days} gün geçti"
        if days == 0:
            return "Bugün son gün"
        if days == 1:
            return "Yarın son gün"
        return f"{days} gün kaldı"
