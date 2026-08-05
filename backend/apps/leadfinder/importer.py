from urllib.parse import urlparse

from apps.companies.models import Company


class CompanyImporter:

    def import_company(
        self,
        website: str,
    ):

        domain = urlparse(website).netloc

        company_name = (
            domain.replace("www.", "")
            .split(".")[0]
            .title()
        )

        company, created = Company.objects.get_or_create(
            website=website,
            defaults={
                "name": company_name,
            },
        )

        return company