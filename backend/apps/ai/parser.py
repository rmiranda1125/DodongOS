import json
import re

from apps.ai.models import CompanyAnalysis


class AIParser:

    def parse(self, response: str):

        if not response:
            raise ValueError(
                "AI returned an empty response."
            )

        response = response.strip()

        print("\nRAW RESPONSE:")
        print(response)

        # Remove markdown fences
        response = re.sub(
            r"```json|```",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()

        # Find the first JSON object
        start = response.find("{")
        end = response.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "No JSON object found in AI response."
            )

        json_text = response[start:end + 1]

        print("\nEXTRACTED JSON:")
        print(json_text)

        try:

            data = json.loads(json_text)

        except json.JSONDecodeError as e:

            print("\nFAILED TO PARSE JSON:")
            print(json_text)

            raise e

        return CompanyAnalysis.model_validate(data)