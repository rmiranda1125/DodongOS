from apps.ai.ollama_client import OllamaClient
from apps.ai.prompts import build_company_prompt
from apps.ai.memory import CompanyMemory


class CompanyAnalysisService:

    def __init__(self):

        self.client = OllamaClient()
        self.memory = CompanyMemory()

    def analyze(self, company):

        # Get previous company context
        context = self.memory.get_context()

        # Build the prompt
        prompt = build_company_prompt(
            company,
            context,
        )

        print("\n" + "=" * 80)
        print("PROMPT SENT TO OLLAMA")
        print("=" * 80)
        print(prompt)
        print("=" * 80)

        # Call Ollama
        response = self.client.analyze(prompt)

        print("\n" + "=" * 80)
        print("TYPE:", type(response))
        print("=" * 80)

        print("\nRAW RESPONSE:")
        print(repr(response))
        print("=" * 80)

        # Return the raw response (do NOT parse yet)
        return response