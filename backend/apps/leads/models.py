from django.db import models


class Lead(models.Model):

    # Company Information
    company_name = models.CharField(
        max_length=255,
    )

    website = models.URLField(
        blank=True,
    )

    industry = models.CharField(
        max_length=200,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    employee_count = models.IntegerField(
        null=True,
        blank=True,
    )

    technologies = models.TextField(
        blank=True,
    )

    # Job Information
    job_title = models.CharField(
        max_length=255,
        blank=True,
    )

    source_url = models.URLField(
        blank=True,
        null=True,
        unique=True,
    )

    source_platform = models.CharField(
        max_length=100,
        blank=True,
    )

    work_setup = models.CharField(
        max_length=50,
        blank=True,
    )

    employment_type = models.CharField(
        max_length=50,
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    salary = models.CharField(
        max_length=255,
        blank=True,
    )

    # AI Results
    lead_score = models.IntegerField(
        default=0,
    )

    ai_summary = models.TextField(
        blank=True,
    )

    recommended_services = models.JSONField(
        default=list,
    )

    pain_points = models.JSONField(
        default=list,
    )

    # Lead Status
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
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.company_name} - {self.job_title}"


class LeadNote(models.Model):

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="notes",
    )

    note = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.lead.company_name}"


class LeadActivity(models.Model):

    ACTIVITY_TYPES = [

        ("created", "Lead Created"),

        ("status_changed", "Status Changed"),

        ("note_added", "Note Added"),

        ("ai_analysis", "AI Analysis"),

        ("proposal_sent", "Proposal Sent"),

        ("won", "Lead Won"),

        ("lost", "Lead Lost"),

    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead.company_name} - {self.activity_type}"