"""
Lead outreach draft generator.

Produces a short first-contact / cover letter draft for a CRM lead
so the user can start a conversation with that lead.

READ + GENERATE only:
- Lead data is retrieved through the controlled read-only tool
  registry (``get_lead``), never through the Django ORM.
- The AI provider only ever receives already-verified lead data.
- Nothing is written to the CRM. The draft is returned to the
  caller to review, edit and send manually.
"""

import json

from apps.ai.providers.factory import AIProviderFactory
from apps.ai.tools.registry import execute_registered_tool


ALLOWED_TONES = {
    "professional",
    "friendly",
    "concise",
}

DEFAULT_TONE = "professional"


def build_lead_outreach_prompt(*, lead, tone):
    """
    Build the provider prompt from verified lead data only.
    """

    lead_data = json.dumps(
        lead,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
You are Dodong OS Outreach Assistant.

Write a short first-contact message ("cover letter") that the
Dodong OS user can send to the lead below to open a conversation.

The lead data has already been retrieved through an authorized
read-only CRM tool.

Rules:
1. Use only the supplied lead data. Do not invent facts about the
   company, the role, budgets, names, or prior contact.
2. Do not claim that anyone has already been contacted.
3. Do not claim that any CRM record was created or changed.
4. If the sender's name, company or contact details are unknown,
   use clearly marked placeholders such as [Your name].
5. Keep it under 200 words. Lead with why the message is relevant
   to this specific company and role.
6. End with a low-pressure call to action.
7. Return only the message text - no preamble and no commentary.

Requested tone: {tone}

Verified lead data:
{lead_data}
""".strip()


def _fallback_draft(*, lead):
    """
    Deterministic draft used when the AI provider is unavailable.
    """

    company = lead.get("company_name") or "your team"
    role = lead.get("job_title")

    if role:
        reason = f"I came across the {role} role and wanted to reach out."
    else:
        reason = (
            "I wanted to reach out about how we might be able to "
            f"help {company}."
        )

    return "\n\n".join(
        [
            f"Hi {company} team,",
            reason,
            (
                "We help teams like yours deliver reporting and data "
                "work faster. If it is useful, I would be glad to "
                "share a couple of relevant examples."
            ),
            "Would you be open to a short call next week?",
            "Best regards,\n[Your name]",
        ]
    )


def draft_lead_outreach(*, lead_id, tone=None, provider=None):
    """
    Return a draft outreach message for one CRM lead.

    Result dict:
      success -> {"success": True, "lead_id", "company_name",
                  "tone", "draft", "draft_source"}
      failure -> {"success": False, "error": {"code", "message"}}

    No CRM write happens here.
    """

    if (
        isinstance(lead_id, bool)
        or not isinstance(lead_id, int)
        or lead_id < 1
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": "A valid positive lead ID is required.",
            },
        }

    if tone is None:
        tone = DEFAULT_TONE

    tone = str(tone).strip().lower()

    if tone not in ALLOWED_TONES:
        tone = DEFAULT_TONE

    tool_result = execute_registered_tool(
        name="get_lead",
        arguments={"lead_id": lead_id},
    )

    if not tool_result.get("success"):
        return {
            "success": False,
            "error": tool_result.get(
                "error",
                {
                    "code": "LEAD_LOOKUP_FAILED",
                    "message": "Unable to load the lead.",
                },
            ),
        }

    lead = tool_result.get("data") or {}

    prompt = build_lead_outreach_prompt(
        lead=lead,
        tone=tone,
    )

    if provider is None:
        try:
            provider = AIProviderFactory.create()
        except Exception:
            provider = None

    draft = None
    draft_source = "ai_provider"

    if provider is not None:
        try:
            response = provider.analyze(prompt)

            if isinstance(response, str) and response.strip():
                draft = response.strip()

        except Exception:
            draft = None

    if draft is None:
        draft = _fallback_draft(lead=lead)
        draft_source = "deterministic_fallback"

    return {
        "success": True,
        "lead_id": lead_id,
        "company_name": lead.get("company_name"),
        "tone": tone,
        "draft": draft,
        "draft_source": draft_source,
    }
