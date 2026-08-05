import json


class LeadParser:

    def parse(self, text: str):

        # Remove markdown code fences if they exist
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1)

        if text.startswith("```"):
            text = text.replace("```", "", 1)

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)

        except json.JSONDecodeError:

            return {
                "company_name": "",
                "industry": "",
                "lead_score": 0,
                "summary": text,
                "recommended_services": [],
                "next_action": "",
            }