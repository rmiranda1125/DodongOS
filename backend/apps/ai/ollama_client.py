from ollama import Client


class OllamaClient:
    """
    Client for communicating with the local Ollama server.

    ``timeout`` (seconds) is optional. When provided it is passed to
    the underlying httpx client so callers such as background
    automation can bound the network wait. When omitted the client
    is unbounded, matching the previous behaviour.
    """

    MODEL = "qwen2.5:7b"

    def __init__(self, timeout=None):
        self._client = Client(timeout=timeout)

    def analyze(self, prompt: str) -> str:
        response = self._client.chat(
            model=self.MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]
