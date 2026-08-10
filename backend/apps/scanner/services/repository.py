from apps.leads.models import Lead


class LeadRepository:
    """
    Handles creating Lead records from validated AI output.
    """

    def create(self, data: dict):

        return Lead.objects.create(

            # =========================
            # Company Information
            # =========================

            company_name=data.get("company_name", "").strip(),

            website=data.get("website", "").strip(),

            industry=data.get("industry", "").strip(),

            country=data.get("country", "").strip(),

            employee_count=data.get("employee_count"),

            technologies=data.get("technologies", "").strip(),

            # =========================
            # Job Information
            # =========================

            job_title=data.get("job_title", "").strip(),

            source_url=data.get("source_url", "").strip(),

            source_platform=data.get(
                "source_platform",
                "",
            ).strip(),

            work_setup=data.get(
                "work_setup",
                "",
            ).strip(),

            employment_type=data.get(
                "employment_type",
                "",
            ).strip(),

            location=data.get("location", "").strip(),

            salary=data.get("salary", "").strip(),

            # =========================
            # AI Analysis
            # =========================

            lead_score=max(
                0,
                min(
                    int(data.get("lead_score", 0)),
                    100,
                ),
            ),

            ai_summary=data.get(
                "summary",
                "",
            ).strip(),

            recommended_services=data.get(
                "recommended_services",
                [],
            ),

            pain_points=data.get(
                "pain_points",
                [],
            ),

            # =========================
            # CRM
            # =========================

            status="new",
        )