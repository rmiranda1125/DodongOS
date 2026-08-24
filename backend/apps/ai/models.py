from pydantic import BaseModel, Field
from django.db import models as django_models

class CompanyAnalysis(BaseModel):

    lead_score: int = Field(default=0)

    summary: str = ""

    recommended_services: list[str] = []

    pain_points: list[str] = []

    next_action: str = ""

class AIActionAudit(django_models.Model):
    """
    Durable audit record for confirmed AI-assisted CRM writes.

    proposal_id is unique and also acts as the replay
    protection boundary.
    """

    STATUS_CHOICES = [
        ("executed", "Executed"),
        ("failed", "Failed"),
    ]

    proposal_id = django_models.UUIDField(
        unique=True,
    )

    action = django_models.CharField(
        max_length=100,
    )

    status = django_models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
    )

    lead_id = django_models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    result_task_id = django_models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    error_code = django_models.CharField(
        max_length=100,
        blank=True,
    )

    proposal_data = django_models.JSONField(
        default=dict,
    )

    confirmed_at = django_models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-confirmed_at",
        ]

    def __str__(self):
        return (
            f"{self.action} - "
            f"{self.proposal_id} - "
            f"{self.status}"
        )