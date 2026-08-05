import json


def build_company_prompt(company, context):

    schema = {
        "lead_score": 0,
        "summary": "",
        "recommended_services": [],
        "pain_points": [],
        "next_action": "",
    }

    return f"""
You are an expert business consultant.

You MUST return ONLY valid JSON.

DO NOT explain.

DO NOT use markdown.

DO NOT wrap the JSON in ```.

DO NOT write anything before the JSON.

DO NOT write anything after the JSON.

Previous companies:

{json.dumps(context, indent=4)}

Analyze this company.

Company Name:
{company.name}

Website:
{company.website}

Industry:
{company.industry}

Country:
{company.country}

Notes:
{company.notes}

Return ONLY this schema:

{json.dumps(schema, indent=4)}
"""