from pydantic import BaseModel, Field


class CompanyAnalysis(BaseModel):

    lead_score: int = Field(default=0)

    summary: str = ""

    recommended_services: list[str] = []

    pain_points: list[str] = []

    next_action: str = ""