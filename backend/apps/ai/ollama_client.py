from ollama import chat


class OllamaClient:
    """
    Client for communicating with the local Ollama server.
    """

    MODEL = "qwen2.5:7b"

    def analyze(self, prompt: str) -> str:
        response = chat(
            model=self.MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]