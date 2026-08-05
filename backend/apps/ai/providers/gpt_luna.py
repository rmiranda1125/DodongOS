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
    """

    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

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