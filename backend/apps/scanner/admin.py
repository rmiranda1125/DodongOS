from django.contrib import admin

from apps.scanner.models import LeadCandidate, LeadScanRun


@admin.register(LeadCandidate)
class LeadCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "opportunity_title",
        "source",
        "score",
        "qualification",
        "status",
        "discovered_at",
    )
    list_filter = ("status", "qualification", "source")
    search_fields = (
        "company_name",
        "opportunity_title",
        "source_url",
        "dedup_key",
    )
    ordering = ("-score", "-discovered_at")
    readonly_fields = (
        "source",
        "source_identifier",
        "source_url",
        "dedup_key",
        "raw_data",
        "normalized_data",
        "score",
        "score_components",
        "score_reasons",
        "qualification",
        "ai_note",
        "times_seen",
        "discovered_at",
        "last_seen_at",
        "imported_lead_id",
        "imported_at",
        "imported_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(LeadScanRun)
class LeadScanRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "source",
        "status",
        "candidates_seen",
        "candidates_created",
        "candidates_updated",
        "rows_rejected",
    )
    list_filter = ("status", "source")
    ordering = ("-started_at",)
    readonly_fields = [
        f.name for f in LeadScanRun._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
