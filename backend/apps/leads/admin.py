from django.contrib import admin

from .models import Lead, LeadActivity


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):

    list_display = (
        "company_name",
        "industry",
        "country",
        "lead_score",
        "status",
    )

    search_fields = (
        "company_name",
        "industry",
    )

    list_filter = (
        "status",
        "country",
    )


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):

    list_display = (
        "lead",
        "activity_type",
        "created_at",
    )

    list_filter = (
        "activity_type",
        "created_at",
    )

    search_fields = (
        "lead__company_name",
        "description",
    )

    ordering = (
        "-created_at",
    )