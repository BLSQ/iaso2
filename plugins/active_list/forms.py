from django import forms
from .models import Validation


class ValidationForm(forms.ModelForm):
    class Meta:
        model = Validation
        fields = ["comment", "validation_status", "level", "source_import"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4}), "source_import": forms.HiddenInput()}
