from django.contrib import admin

from .models import Lead


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