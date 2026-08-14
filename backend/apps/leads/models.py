from django.db import models


class Lead(models.Model):

    # =====================================================
    # COMPANY INFORMATION
    # =====================================================

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


    # =====================================================
    # JOB INFORMATION
    # =====================================================

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


    # =====================================================
    # AI RESULTS
    # =====================================================

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


    # =====================================================
    # LEAD STATUS
    # =====================================================

    STATUS_CHOICES = [

        ("new", "New"),

        ("contacted", "Contacted"),

        ("qualified", "Qualified"),

        ("proposal", "Proposal"),

        ("won", "Won"),

        ("lost", "Lost"),

    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
    )


    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    def __str__(self):

        return f"{self.company_name} - {self.job_title}"


# =========================================================
# LEAD NOTE
# =========================================================

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

        ordering = [
            "-created_at",
        ]


    def __str__(self):

        return f"Note for {self.lead.company_name}"


# =========================================================
# LEAD ACTIVITY
# =========================================================

# =========================================================
# LEAD ACTIVITY
# =========================================================

class LeadActivity(models.Model):

    ACTIVITY_TYPES = [
        ("note", "Note"),
        ("call", "Call"),
        ("email", "Email"),
        ("meeting", "Meeting"),
        ("follow_up", "Follow Up"),
        ("status_changed", "Status Changed"),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        default="note",
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.lead.company_name} - {self.activity_type}"