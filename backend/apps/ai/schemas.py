from dataclasses import dataclass


@dataclass
class CompanyAnalysisRequest:

    company_name: str

    website: str = ""

    industry: str = ""

    country: str = ""

    notes: str = ""


@dataclass
class CompanyAnalysisResult:

    score: int

    summary: str

    strengths: list[str]

    risks: list[str]