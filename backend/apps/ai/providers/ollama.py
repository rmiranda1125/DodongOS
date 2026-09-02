from apps.ai.ollama_client import OllamaClient

from .base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """
    Wrapper around the existing Ollama client.

    This allows Ollama to work with the same
    interface as GPT-5.6 Luna.

    ``timeout`` (seconds) is optional and, when provided, is
    enforced on the underlying HTTP client. When omitted the client
    keeps its default (unbounded) behaviour.
    """

    def __init__(self, timeout=None):

        self.client = OllamaClient(timeout=timeout)

    def analyze(self, prompt: str) -> str:

        return self.client.analyze(prompt)
