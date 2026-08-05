from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """
    Base interface for every AI provider.

    All providers (GPT, Ollama, Claude, etc.)
    must implement this interface.
    """

    @abstractmethod
    def analyze(self, prompt: str) -> str:
        """
        Send a prompt to the AI model and
        return the raw text response.
        """
        pass