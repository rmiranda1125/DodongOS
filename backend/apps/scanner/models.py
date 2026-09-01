from django.db import models


class LeadCandidate(models.Model):
    """
    A discovered opportunity that is NOT yet a CRM Lead.

    The scanner only produces candidates. A candidate becomes a CRM
    Lead only through an explicit staff import
    (apps/scanner/services.import_candidate ->
    apps/leads/services.import_scanner_candidate). Nothing in the
    scanner ever calls ``Lead.objects.create()``.

    Identity for controlled re-scanning is the deduplication key
    (see apps/scanner/dedup.py): rediscovering the same opportunity
    updates this row and never creates a duplicate.

    ORM access to this model MUST go through
    apps/scanner/services.py.
    """

    STATUS_CHOICES = [
        ("new", "New"),
        ("reviewed", "Reviewed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("imported", "Imported"),
    ]

    QUALIFICATION_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    source = models.CharField(max_length=64)
    source_identifier = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    source_url = models.URLField(blank=True, default="")

    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    opportunity_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    description = models.TextField(blank=True, default="")
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    work_arrangement = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )
    compensation_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    raw_data = models.JSONField(default=dict)
    normalized_data = models.JSONField(default=dict)

    dedup_key = models.CharField(max_length=200, unique=True)

    score = models.PositiveIntegerField(default=0)
    score_components = models.JSONField(default=dict)
    score_reasons = models.JSONField(default=list)
    qualification = models.CharField(
        max_length=8,
        choices=QUALIFICATION_CHOICES,
        default="low",
    )

    ai_note = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="new",
    )
    rejection_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    times_seen = models.PositiveIntegerField(default=1)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)

    imported_lead_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        unique=True,
    )
    imported_at = models.DateTimeField(null=True, blank=True)
    imported_by = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "-discovered_at", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["source"]),
            models.Index(fields=["qualification"]),
            models.Index(fields=["-score"]),
            models.Index(fields=["source", "source_identifier"]),
        ]

    def __str__(self):
        return (
            f"LeadCandidate {self.id} - {self.company_name} "
            f"({self.status})"
        )


class LeadScanRun(models.Model):
    """
    Durable record of one scanner run. Source-run metadata only -
    never candidate content, never secrets/tokens.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
    ]

    source = models.CharField(max_length=64)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="running",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    candidates_seen = models.PositiveIntegerField(default=0)
    candidates_created = models.PositiveIntegerField(default=0)
    candidates_updated = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True, default="")
    row_errors = models.JSONField(default=list)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"LeadScanRun {self.id} - {self.source} "
            f"({self.status})"
        )
