from django import forms
from django.utils import timezone

from core import limits

from .models import FoodItem, ShelfLifeRule


class FoodItemForm(forms.ModelForm):
    """
    Ürün formu. Ad yazılırken arayüz öneri listesi gösterir (datalist + JS); ad bir kuralla
    eşleşirse sunucu da kuralı bağlar ve gün boşsa kuraldan doldurur. Kullanıcının girdiği gün korunur.
    """

    class Meta:
        model = FoodItem
        fields = ("name", "storage", "opened_on", "suggested_days", "package_expiry", "note")
        labels = {
            "name": "Ürün adı",
            "storage": "Nerede duruyor?",
            "opened_on": "Ne zaman açıldı?",
            "suggested_days": "Açıldıktan sonra kaç gün?",
            "package_expiry": "Ambalajdaki son kullanma tarihi (SKT)",
            "note": "Not",
        }
        help_texts = {
            "opened_on": "Henüz açılmadıysa boş bırak; açınca “Bugün açtım” diyebilirsin.",
            "suggested_days": "Öneri otomatik gelir, istersen değiştir.",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "list": "shelf-life-rules", "autocomplete": "off", "autofocus": True,
                "maxlength": limits.FOOD_NAME_MAX, "placeholder": "Örn. Süt",
            }),
            "opened_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "package_expiry": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "suggested_days": forms.NumberInput(attrs={"min": 0, "max": limits.SUGGESTED_DAYS_MAX, "inputmode": "numeric"}),
            "note": forms.TextInput(attrs={"maxlength": limits.FOOD_NOTE_MAX}),
        }
        error_messages = {
            "name": {"max_length": f"Ürün adı en fazla {limits.FOOD_NAME_MAX} karakter olabilir."},
            "note": {"max_length": f"Not en fazla {limits.FOOD_NOTE_MAX} karakter olabilir."},
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Ürün adı boş olamaz.")
        return name

    def clean_opened_on(self):
        opened = self.cleaned_data.get("opened_on")
        if opened and opened > timezone.localdate():
            raise forms.ValidationError("Açılma tarihi ileri bir tarih olamaz.")
        return opened

    def clean_suggested_days(self):
        days = self.cleaned_data.get("suggested_days")
        if days is not None and days > limits.SUGGESTED_DAYS_MAX:
            raise forms.ValidationError(f"En fazla {limits.SUGGESTED_DAYS_MAX} gün girebilirsin.")
        return days

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        if name:
            rule = find_rule(name)
            self.instance.rule = rule
            if rule and cleaned.get("suggested_days") is None:
                cleaned["suggested_days"] = rule.opened_days
        return cleaned


def find_rule(name):
    """Ürün adı bir kuralın adıyla birebir (büyük/küçük harf duyarsız) eşleşirse o kural."""
    wanted = name.strip().casefold()
    for rule in ShelfLifeRule.objects.all():
        if rule.name_tr.casefold() == wanted:
            return rule
    return None
