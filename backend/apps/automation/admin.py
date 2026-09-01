from django.contrib import admin

from apps.automation.models import CRMDigest, ScheduledCheckRun


class _ReadOnlyAdmin(admin.ModelAdmin):
    """Read-oriented admin: no add, no delete."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ScheduledCheckRun)
class ScheduledCheckRunAdmin(_ReadOnlyAdmin):

    list_display = (
        "started_at",
        "finished_at",
        "status",
        "checks_run",
        "findings_count",
        "summary_status",
        "summary_source",
    )

    list_filter = (
        "status",
        "summary_status",
        "summary_source",
        "started_at",
    )

    ordering = (
        "-started_at",
    )

    readonly_fields = (
        "started_at",
        "finished_at",
        "status",
        "checks_run",
        "findings_count",
        "error_message",
        "summary_status",
        "summary_source",
        "summary_text",
        "summary_error",
    )


@admin.register(CRMDigest)
class CRMDigestAdmin(_ReadOnlyAdmin):

    list_display = (
        "dedup_key",
        "finding_type",
        "lead_id",
        "task_id",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
        "resolved_at",
    )

    list_filter = (
        "finding_type",
        "resolved_at",
        "last_seen_at",
    )

    search_fields = (
        "dedup_key",
        "summary",
    )

    ordering = (
        "-last_seen_at",
    )

    readonly_fields = (
        "finding_type",
        "lead_id",
        "task_id",
        "summary",
        "finding_data",
        "dedup_key",
        "first_seen_at",
        "last_seen_at",
        "resolved_at",
        "occurrence_count",
        "created_at",
        "updated_at",
    )
