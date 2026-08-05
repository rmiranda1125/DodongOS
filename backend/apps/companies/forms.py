from django import forms
from .models import Company


class CompanyForm(forms.ModelForm):

    class Meta:
        model = Company

        fields = [
            "name",
            "website",
            "industry",
            "country",
            "email",
            "phone",
            "notes",
        ]

        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }