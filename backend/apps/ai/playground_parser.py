from apps.ai.models import CompanyAnalysis

analysis = CompanyAnalysis(
    lead_score=95,
    summary="Excellent prospect.",
    recommended_services=[
        "Power BI",
        "Python Automation",
    ],
    pain_points=[
        "Manual reporting",
    ],
    next_action="Schedule a discovery call.",
)

print(analysis)
print(analysis.lead_score)
print(analysis.summary)