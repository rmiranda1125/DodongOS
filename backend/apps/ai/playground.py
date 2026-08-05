from apps.ai.schemas import CompanyAnalysisRequest
from apps.ai.services import AIService


request = CompanyAnalysisRequest(

    company_name="ABC Construction",

    website="https://abc.com",

    technologies="Power BI, Azure",

    employee_count=800,

)

service = AIService()

result = service.analyze_company(request)

print(result)