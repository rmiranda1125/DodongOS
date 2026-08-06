from apps.scanner.models import Lead


class LeadDeduplicator:
    """
    Checks if a lead already exists.
    """

    def find_duplicate(self, data: dict):

        # 1. Check Source URL
        source_url = data.get("source_url")

        if source_url:

            lead = Lead.objects.filter(
                source_url=source_url
            ).first()

            if lead:
                return lead

        # 2. Check Website
        website = data.get("website")

        if website:

            lead = Lead.objects.filter(
                website__iexact=website
            ).first()

            if lead:
                return lead

        # 3. Check Company Name
        company = data.get("company_name")

        if company:

            lead = Lead.objects.filter(
                company_name__iexact=company
            ).first()

            if lead:
                return lead

        return None