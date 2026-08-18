from django import forms

from .models import Lead, LeadNote, LeadActivity, LeadTask


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


class LeadForm(forms.ModelForm):

    class Meta:
        model = Lead

        fields = [
            "company_name",
            "website",
            "industry",
            "country",
            "employee_count",
            "technologies",
            "job_title",
            "source_url",
            "source_platform",
            "work_setup",
            "employment_type",
            "location",
            "salary",
            "lead_score",
            "ai_summary",
            "recommended_services",
            "pain_points",
            "status",
        ]

        widgets = {

            "company_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "website": forms.URLInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "industry": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "country": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "employee_count": forms.NumberInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "technologies": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "job_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "source_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "source_platform": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "work_setup": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "employment_type": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "salary": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "lead_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 100,
                }
            ),

            "ai_summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                }
            ),

            "recommended_services": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "pain_points": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }


class LeadActivityForm(forms.ModelForm):

    class Meta:
        model = LeadActivity

        fields = [
            "activity_type",
            "description",
        ]

        widgets = {

            "activity_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe what happened...",
                }
            ),
        }

      

class LeadTaskForm(forms.ModelForm):

    class Meta:

        model = LeadTask

        fields = [
            "title",
            "description",
            "task_type",
            "priority",
            "status",
            "due_date",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter task title...",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the task...",
                }
            ),

            "task_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "due_date": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }