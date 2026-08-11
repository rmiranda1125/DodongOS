from apps.leads.models import Lead, LeadActivity


class LeadRepository:
    """
    Saves validated scanner output into the CRM.
    """

    def create(self, data: dict):

        lead = Lead.objects.create(

            # Company
            company_name=data.get("company_name", ""),
            website=data.get("website", ""),
            industry=data.get("industry", ""),
            country=data.get("country", ""),
            employee_count=data.get("employee_count"),
            technologies=data.get("technologies", ""),

            # Job
            job_title=data.get("job_title", ""),
            source_url=data.get("source_url") or None,
            source_platform=data.get("source_platform", ""),
            work_setup=data.get("work_setup", ""),
            employment_type=data.get("employment_type", ""),
            location=data.get("location", ""),
            salary=data.get("salary", ""),

            # AI
            lead_score=data.get("lead_score", 0),
            ai_summary=data.get("summary", ""),
            recommended_services=data.get(
                "recommended_services",
                [],
            ),
            pain_points=data.get(
                "pain_points",
                [],
            ),

            # CRM
            status="new",
        )

        LeadActivity.objects.create(
            lead=lead,
            activity_type="created",
            description="Lead was created from the scanner.",
        )

        return lead