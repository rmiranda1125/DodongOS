from django import forms


class ScanURLForm(forms.Form):

    url = forms.URLField(
        label="Job Posting URL",
        widget=forms.URLInput(
            attrs={
                "class": "input",
                "placeholder": "https://...",
            }
        ),
    )