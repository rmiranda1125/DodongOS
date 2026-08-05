from apps.companies.models import Company
from apps.ai.company_analysis import CompanyAnalysisService


company = Company.objects.first()

if company is None:
    print("No companies found in the database.")
else:

    print(f"Analyzing: {company.name}")

    service = CompanyAnalysisService()

    response = service.analyze(company)

    print("\n" + "=" * 80)
    print("FINAL RESPONSE")
    print("=" * 80)
    print(response)
    print("=" * 80)