from django import forms

from .models import LeadNote


class LeadNoteForm(forms.ModelForm):

    class Meta:
        model = LeadNote

        fields = [
            "note",
        ]

        widgets = {
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Add a note about this lead...",
                }
            ),
        }