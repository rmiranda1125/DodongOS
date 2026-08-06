import json


class AIResponseValidator:
    """
    Validates AI responses before
    saving anything to the database.
    """

    REQUIRED_FIELDS = [
        "company_name",
        "industry",
        "summary",
        "services",
        "pain_points",
        "confidence",
    ]

    def validate(self, response: str) -> dict:

        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "AI did not return valid JSON."
            ) from exc

        for field in self.REQUIRED_FIELDS:

            if field not in data:

                raise ValueError(
                    f"Missing field: {field}"
                )

        return data