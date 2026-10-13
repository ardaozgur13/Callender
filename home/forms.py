from django import forms
from django.contrib.auth import get_user_model

from core import limits

from .models import Chore


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ("title", "assigned_to", "weekday", "is_active")
        labels = {"title": "İş", "assigned_to": "Kim yapacak?", "weekday": "Hangi gün?", "is_active": "Aktif"}
        widgets = {"title": forms.TextInput(attrs={
            "maxlength": limits.TITLE_MAX, "autofocus": True, "placeholder": "Örn. Bulaşıkları boşalt",
        })}
        error_messages = {"title": {"max_length": f"İş adı en fazla {limits.TITLE_MAX} karakter olabilir."}}

    def __init__(self, *args, family, **kwargs):
        super().__init__(*args, **kwargs)
        # Sadece bu ailenin üyelerine atanabilir
        members = get_user_model().objects.filter(family_memberships__family=family).order_by("display_name")
        self.fields["assigned_to"].queryset = members
        self.fields["assigned_to"].empty_label = "Herkes"
        self.fields["assigned_to"].label_from_instance = lambda user: user.display_name
        self.fields["weekday"].choices = [("", "Her gün")] + list(self.fields["weekday"].choices)[1:]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("İş adı boş olamaz.")
        return title
