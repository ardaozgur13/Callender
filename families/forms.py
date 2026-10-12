from django import forms

from core import limits

from .models import Family


class FamilyNameForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ("name",)
        labels = {"name": "Aile adı"}
        widgets = {"name": forms.TextInput(attrs={"maxlength": limits.FAMILY_NAME_MAX, "placeholder": "Örn. Yılmazlar"})}
        error_messages = {"name": {"max_length": f"Aile adı en fazla {limits.FAMILY_NAME_MAX} karakter olabilir."}}

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Aile adı boş olamaz.")
        return name


class JoinFamilyForm(forms.Form):
    code = forms.CharField(
        label="Davet kodu",
        max_length=20,
        widget=forms.TextInput(attrs={
            "autocomplete": "off", "autocapitalize": "characters", "spellcheck": "false",
            "placeholder": "Örn. K7MP2RTV",
        }),
    )
