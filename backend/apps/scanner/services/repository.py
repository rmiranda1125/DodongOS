from apps.scanner.models import Lead


class LeadRepository:

    def create(self, data: dict):

        return Lead.objects.create(

            company_name=data.get("company_name", ""),

            website=data.get("website", ""),

            source_url=data.get("source_url", ""),

            industry=data.get("industry", ""),

            summary=data.get("summary", ""),

            recommended_services=data.get(
                "recommended_services",
                [],
            ),

            pain_points=data.get(
                "pain_points",
                [],
            ),

            confidence=data.get(
                "confidence",
                0,
            ),
        )