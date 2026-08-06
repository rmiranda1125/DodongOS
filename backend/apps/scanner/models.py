from django.db import models


class Lead(models.Model):

    company_name = models.CharField(
        max_length=255,
    )

    website = models.URLField(
        blank=True,
    )

    source_url = models.URLField(
        unique=True,
    )

    industry = models.CharField(
        max_length=150,
        blank=True,
    )

    summary = models.TextField()

    recommended_services = models.JSONField(
        default=list,
    )

    pain_points = models.JSONField(
        default=list,
    )

    confidence = models.IntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return self.company_name