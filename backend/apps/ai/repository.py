from django.utils import timezone


class AIRepository:

    def save_analysis(
        self,
        company,
        result,
    ):

        company.ai_score = result["lead_score"]

        company.ai_summary = result["summary"]

        company.ai_next_action = result["next_action"]

        company.ai_last_analyzed = timezone.now()

        company.save()

        return company