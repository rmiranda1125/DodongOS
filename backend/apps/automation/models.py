from django.db import models


class ScheduledCheckRun(models.Model):
    """
    Durable record of one background CRM check run.

    Phase 6A: no checks are registered yet. This model exists to
    prove the scheduling foundation is observable and idempotent
    before any deterministic CRM checks (Phase 6B) are added.

    ORM access to this model MUST go through
    apps/automation/services.py. Orchestration code (management
    commands, and later checks.py/digest.py/summary.py) must not
    query or mutate it directly.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
    ]

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="running",
    )

    checks_run = models.PositiveIntegerField(
        default=0,
    )

    findings_count = models.PositiveIntegerField(
        default=0,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "-started_at",
        ]

    def __str__(self):
        return (
            f"ScheduledCheckRun {self.id} - {self.status}"
        )
