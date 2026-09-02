import os

from dotenv import load_dotenv
from openai import OpenAI

from .base import BaseAIProvider


load_dotenv()


class GPTLunaProvider(BaseAIProvider):
    """
    GPT-5.6 Luna Provider

    Reads configuration from .env
    and communicates with OpenAI.

    ``timeout`` (seconds) and ``max_retries`` are optional. When
    provided they are applied to the OpenAI client so a caller such
    as background automation can bound the network wait. When
    omitted the OpenAI SDK defaults apply (unchanged interactive
    behaviour).
    """

    def __init__(self, timeout=None, max_retries=None):

        client_kwargs = {
            "api_key": os.getenv("OPENAI_API_KEY"),
        }

        if timeout is not None:
            client_kwargs["timeout"] = timeout

        if max_retries is not None:
            client_kwargs["max_retries"] = max_retries

        self.client = OpenAI(**client_kwargs)

        self.model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
        )

    def analyze(self, prompt: str) -> str:

        response = self.client.responses.create(

            model=self.model,

            input=prompt,

        )

        return response.output_text
