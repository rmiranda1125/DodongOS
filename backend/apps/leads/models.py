from django.db import models


class Lead(models.Model):

    company_name = models.CharField(max_length=255)

    website = models.URLField(blank=True)

    industry = models.CharField(
        max_length=200,
        blank=True
    )

    country = models.CharField(
        max_length=100,
        blank=True
    )

    employee_count = models.IntegerField(
        null=True,
        blank=True
    )

    technologies = models.TextField(
        blank=True
    )

    lead_score = models.IntegerField(
        default=0
    )

    ai_summary = models.TextField(
        blank=True
    )

    STATUS_CHOICES = [

        ("new", "New"),

        ("qualified", "Qualified"),

        ("contacted", "Contacted"),

        ("proposal", "Proposal Sent"),

        ("won", "Won"),

        ("lost", "Lost"),

    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.company_name