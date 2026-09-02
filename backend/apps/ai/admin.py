from django.contrib import admin

from apps.ai.models import AIActionAudit


@admin.register(AIActionAudit)
class AIActionAuditAdmin(admin.ModelAdmin):
    list_display = (
        "confirmed_at",
        "action",
        "status",
        "lead_id",
        "result_task_id",
        "proposal_id",
    )

    list_filter = (
        "status",
        "action",
        "confirmed_at",
    )

    search_fields = (
        "proposal_id",
        "lead_id",
        "result_task_id",
        "error_code",
    )

    ordering = (
        "-confirmed_at",
    )

    readonly_fields = (
        "proposal_id",
        "action",
        "status",
        "lead_id",
        "result_task_id",
        "error_code",
        "proposal_data",
        "confirmed_at",
    )

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False