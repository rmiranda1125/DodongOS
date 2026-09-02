import os

from dotenv import load_dotenv

from .gpt_luna import GPTLunaProvider
from .ollama import OllamaProvider


load_dotenv()


class AIProviderFactory:
    """
    Returns the configured AI provider.

    Provider is selected from the .env file.

    Optional ``timeout`` / ``max_retries`` let a caller (e.g.
    background automation) bound the network wait. When omitted the
    provider keeps its library-default behaviour, so interactive
    callers are unaffected.
    """

    @staticmethod
    def create(timeout=None, max_retries=None):

        provider = os.getenv(
            "AI_PROVIDER",
            "openai",
        ).lower()

        if provider == "openai":
            return GPTLunaProvider(
                timeout=timeout,
                max_retries=max_retries,
            )

        if provider == "ollama":
            return OllamaProvider(
                timeout=timeout,
            )

        raise ValueError(
            f"Unknown AI provider: {provider}"
        )
