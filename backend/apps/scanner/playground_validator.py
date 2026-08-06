from apps.scanner.services.validator import AIResponseValidator

response = """
{
    "company_name":"ABC Manufacturing",
    "industry":"Construction",
    "summary":"Growing company.",
    "services":["Power BI"],
    "pain_points":["Manual reporting"],
    "confidence":92
}
"""

validator = AIResponseValidator()

lead = validator.validate(response)

print(type(lead))

print()

print(lead)