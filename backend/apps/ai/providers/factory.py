import os

from dotenv import load_dotenv

from .gpt_luna import GPTLunaProvider
from .ollama import OllamaProvider


load_dotenv()


class AIProviderFactory:
    """
    Returns the configured AI provider.

    Provider is selected from the .env file.
    """

    @staticmethod
    def create():

        provider = os.getenv(
            "AI_PROVIDER",
            "openai",
        ).lower()

        if provider == "openai":
            return GPTLunaProvider()

        if provider == "ollama":
            return OllamaProvider()

        raise ValueError(
            f"Unknown AI provider: {provider}"
        )