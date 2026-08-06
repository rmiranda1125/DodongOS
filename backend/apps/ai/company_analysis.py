from apps.ai.providers.factory import AIProviderFactory
from apps.ai.prompts import build_company_prompt
from apps.ai.memory import CompanyMemory


class CompanyAnalysisService:
    """
    Service responsible for analyzing a company using
    the configured AI provider.
    """

    def __init__(self):

        self.provider = AIProviderFactory.create()
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
        print("PROMPT SENT TO AI")
        print("=" * 80)
        print(prompt)
        print("=" * 80)

        # Call the configured AI provider
        response = self.provider.analyze(prompt)

        print("\n" + "=" * 80)
        print("AI PROVIDER:", self.provider.__class__.__name__)
        print("=" * 80)

        print("\nTYPE:", type(response))

        print("\nRAW RESPONSE:")
        print(repr(response))
        print("=" * 80)

        return response