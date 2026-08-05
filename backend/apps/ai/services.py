from .schemas import (
    CompanyAnalysisRequest,
    CompanyAnalysisResult,
)

from .ollama_client import OllamaClient
from .prompts import build_company_prompt


class AIService:

    def __init__(self):
        self.client = OllamaClient()

    def analyze_company(
        self,
        request: CompanyAnalysisRequest,
    ):

        # Rule-based score
        score = self.calculate_score(request)

        # Build prompt for the LLM
        prompt = build_company_prompt(request)

        # Ask Ollama (Qwen)
        summary = self.client.analyze(prompt)

        # Return the result
        return CompanyAnalysisResult(
            score=score,
            summary=summary,
            strengths=[
                "Placeholder Strength"
            ],
            risks=[
                "Placeholder Risk"
            ],
        )

    def calculate_score(
        self,
        request: CompanyAnalysisRequest,
    ):

        score = 50

        technologies = request.technologies.lower()

        if "power bi" in technologies:
            score += 20

        if "azure" in technologies:
            score += 20

        if request.employee_count:

            if request.employee_count > 500:
                score += 10

        return min(score, 100)