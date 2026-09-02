"""
Deterministic, explainable candidate scoring.

Pure function of (normalized candidate, qualification profile). No
ORM, no AI, no randomness. The same candidate + same profile always
yields the same score, components and reasons.

An LLM must never influence the numeric score (see
apps/scanner/analysis.py for the optional, non-authoritative AI
note).

Component maxima (total 100):
  skills        40   required-skill coverage (+ preferred bonus)
  work          20   remote/hybrid vs profile.remote_required
  compensation  20   parsed annual vs profile.min_compensation
  title         15   role keywords present in the title
  recency        5   discovered within profile.recency_days

Any excluded term present -> score 0 with a reason.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


DEFAULT_PROFILE = {
    "required_skills": ["power bi", "sql"],
    "preferred_skills": ["dax", "power query", "tableau", "python"],
    "role_keywords": ["analyst", "bi", "data", "developer", "engineer"],
    "excluded_terms": ["unpaid", "volunteer"],
    "remote_required": False,
    "min_compensation": 0,
    "recency_days": 30,
}


def get_profile():
    """
    Merge the configured SCANNER_PROFILE over the conservative
    default. Missing keys fall back to the default.
    """

    configured = getattr(settings, "SCANNER_PROFILE", None) or {}
    profile = dict(DEFAULT_PROFILE)
    profile.update({k: v for k, v in configured.items() if v is not None})
    return profile


def _bands():
    return (
        int(getattr(settings, "SCANNER_SCORE_HIGH", 80)),
        int(getattr(settings, "SCANNER_SCORE_MEDIUM", 60)),
    )


def qualification_for(score):
    high, medium = _bands()
    if score >= high:
        return "high"
    if score >= medium:
        return "medium"
    return "low"


def score_candidate(normalized, *, profile=None, now=None):
    profile = profile or get_profile()
    now = now or timezone.now()

    text = (normalized.get("search_text") or "").lower()
    title = (normalized.get("opportunity_title") or "").lower()
    reasons = []

    excluded = [
        term
        for term in profile["excluded_terms"]
        if term and term.lower() in text
    ]
    if excluded:
        return {
            "score": 0,
            "components": {
                "skills": 0,
                "work": 0,
                "compensation": 0,
                "title": 0,
                "recency": 0,
            },
            "reasons": [f"Excluded term present: {', '.join(sorted(excluded))}"],
            "skills": {
                "matching_required": [],
                "missing_required": [
                    s.lower() for s in profile["required_skills"] if s
                ],
                "matching_preferred": [],
            },
        }

    # --- skills (max 40) ---
    required = [s.lower() for s in profile["required_skills"] if s]
    preferred = [s.lower() for s in profile["preferred_skills"] if s]
    req_hits = [s for s in required if s in text]
    req_missing = [s for s in required if s not in text]
    pref_hits = [s for s in preferred if s in text]
    skills_analysis = {
        "matching_required": req_hits,
        "missing_required": req_missing,
        "matching_preferred": pref_hits,
    }

    if required:
        skills = 30 * (len(req_hits) / len(required))
    else:
        skills = 30
    skills += min(10, 5 * len(pref_hits))
    skills = int(round(min(40, skills)))
    if req_hits:
        reasons.append(
            f"Matches required skills: {', '.join(sorted(req_hits))}"
        )
    if pref_hits:
        reasons.append(
            f"Matches preferred skills: {', '.join(sorted(pref_hits))}"
        )

    # --- work arrangement (max 20) ---
    arrangement = (normalized.get("work_arrangement") or "").lower()
    if profile["remote_required"]:
        if arrangement == "remote":
            work = 20
            reasons.append("Remote (required)")
        elif arrangement == "hybrid":
            work = 10
            reasons.append("Hybrid (remote preferred)")
        else:
            work = 0
            reasons.append("Not remote (remote is required)")
    else:
        work = {"remote": 20, "hybrid": 15}.get(arrangement, 10)
        reasons.append(f"Work arrangement: {arrangement or 'unknown'}")

    # --- compensation (max 20) ---
    annual = normalized.get("compensation_annual")
    minimum = int(profile["min_compensation"] or 0)
    if annual is None:
        compensation = 10
        reasons.append("Compensation not stated")
    elif minimum <= 0 or annual >= minimum:
        compensation = 20
        reasons.append(f"Compensation ~{annual} meets the minimum")
    else:
        compensation = 0
        reasons.append(
            f"Compensation ~{annual} below the minimum {minimum}"
        )

    # --- title relevance (max 15) ---
    keywords = [k.lower() for k in profile["role_keywords"] if k]
    kw_hits = [k for k in keywords if k in title]
    if keywords:
        title_score = int(round(15 * min(1.0, len(kw_hits) / 2)))
    else:
        title_score = 8
    if kw_hits:
        reasons.append(
            f"Title matches role keywords: {', '.join(sorted(kw_hits))}"
        )

    # --- recency (max 5) ---
    recency_days = int(profile["recency_days"] or 0)
    discovered = normalized.get("discovered_at") or now
    if recency_days <= 0 or discovered >= now - timedelta(days=recency_days):
        recency = 5
    else:
        recency = 0
        reasons.append("Older than the recency window")

    components = {
        "skills": skills,
        "work": work,
        "compensation": compensation,
        "title": title_score,
        "recency": recency,
    }
    total = int(min(100, sum(components.values())))

    return {
        "score": total,
        "components": components,
        "reasons": reasons,
        "skills": skills_analysis,
    }
