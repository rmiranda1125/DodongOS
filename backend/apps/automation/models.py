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


class CRMDigest(models.Model):
    """
    One durable row per deterministic CRM finding identity.

    A finding identity is stable (see apps/automation/digest.py
    ``build_dedup_key``) and is derived only from persisted CRM ids,
    never from generated text or timestamps. Repeated runs update
    the same row rather than inserting duplicates.

    No AI-generated prose is stored here (that is Phase 6D).

    ORM access to this model MUST go through
    apps/automation/services.py.
    """

    FINDING_TYPE_CHOICES = [
        ("due_soon_task", "Due-soon task"),
        ("stale_lead", "Stale lead"),
    ]

    finding_type = models.CharField(
        max_length=32,
        choices=FINDING_TYPE_CHOICES,
    )

    lead_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    task_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    summary = models.TextField()

    finding_data = models.JSONField(
        default=dict,
    )

    dedup_key = models.CharField(
        max_length=128,
        unique=True,
    )

    first_seen_at = models.DateTimeField()

    last_seen_at = models.DateTimeField()

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    occurrence_count = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-last_seen_at",
            "id",
        ]

    def __str__(self):
        return (
            f"CRMDigest {self.dedup_key} "
            f"(x{self.occurrence_count})"
        )

