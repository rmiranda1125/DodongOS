from apps.companies.models import Company


class CompanyMemory:

    def get_context(self):

        companies = Company.objects.order_by("-id")[:10]

        context = []

        for company in companies:

            context.append(
                {
                    "name": company.name,
                    "industry": company.industry,
                    "website": company.website,
                    "score": company.ai_score,
                }
            )

        return context