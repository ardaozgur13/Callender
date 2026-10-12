from django import forms

from core import limits

from .models import CalendarItem


class CalendarItemForm(forms.ModelForm):
    class Meta:
        model = CalendarItem
        fields = ("kind", "title", "date", "all_day", "start_time", "end_time", "repeat", "description")
        widgets = {
            "title": forms.TextInput(attrs={"maxlength": limits.TITLE_MAX, "autofocus": True}),
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3, "maxlength": limits.DESCRIPTION_MAX}),
        }
        labels = {"all_day": "Tüm gün"}
        error_messages = {
            "title": {"max_length": f"Başlık en fazla {limits.TITLE_MAX} karakter olabilir."},
            "description": {"max_length": f"Açıklama en fazla {limits.DESCRIPTION_MAX} karakter olabilir."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["placeholder"] = "Örn. Annemin doğum günü"
        self.fields["description"].required = False

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Başlık boş olamaz.")
        return title

    def clean(self):
        cleaned = super().clean()
        all_day = cleaned.get("all_day")
        start, end = cleaned.get("start_time"), cleaned.get("end_time")

        if all_day:
            cleaned["start_time"] = cleaned["end_time"] = None
        else:
            if not start:
                self.add_error("start_time", "Saat seç ya da \"Tüm gün\"ü işaretle.")
            elif end and end <= start:
                self.add_error("end_time", "Bitiş saati başlangıçtan sonra olmalı.")

        # Tamamlandı işareti sadece görev/amaç için anlamlı
        if cleaned.get("kind") not in CalendarItem.CHECKABLE_KINDS:
            self.instance.is_done = False
        return cleaned
