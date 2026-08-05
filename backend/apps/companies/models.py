from django.db import models


class Company(models.Model):

    name = models.CharField(max_length=255)

    website = models.URLField(blank=True)

    industry = models.CharField(max_length=150, blank=True)

    country = models.CharField(max_length=100, blank=True)

    email = models.EmailField(blank=True)

    phone = models.CharField(max_length=50, blank=True)

    notes = models.TextField(blank=True)

    # -------------------
    # AI Analysis Fields
    # -------------------

    ai_score = models.IntegerField(
        default=0
    )

    ai_summary = models.TextField(
        blank=True
    )

    ai_next_action = models.TextField(
        blank=True
    )

    ai_last_analyzed = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name