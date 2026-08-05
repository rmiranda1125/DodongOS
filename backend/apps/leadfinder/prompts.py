import json


def build_website_prompt(text: str) -> str:

    schema = {
        "company_name": "",
        "industry": "",
        "summary": "",
        "lead_score": 0,
        "recommended_services": [],
        "next_action": ""
    }

    return f"""
You are an expert business consultant.

Analyze the following company website.

{text}

Return ONLY valid JSON.

Use this exact schema:

{json.dumps(schema, indent=4)}

Rules:

- No markdown
- No explanations
- No code fences
- Output ONLY JSON
"""