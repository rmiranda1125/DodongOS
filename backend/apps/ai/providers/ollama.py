from apps.ai.ollama_client import OllamaClient

from .base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """
    Wrapper around the existing Ollama client.

    This allows Ollama to work with the same
    interface as GPT-5.6 Luna.
    """

    def __init__(self):

        self.client = OllamaClient()

    def analyze(self, prompt: str) -> str:

        return self.client.analyze(prompt)