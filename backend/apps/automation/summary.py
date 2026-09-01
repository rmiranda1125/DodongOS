"""
Optional AI summary over the deterministic CRM digest.

Orchestration only. This module MUST NOT access the Django ORM and
MUST NOT change CRM state, choose tools, or invoke any write path.

It receives already-shaped, deterministic digest findings, asks the
existing AI provider abstraction for a concise operational summary,
and — whenever that fails in any way — returns a deterministic
fallback built purely from the finding counts and summaries.

An AI failure here is never fatal: the caller keeps the automation
run successful as long as the deterministic checks and digest
persistence succeeded.
"""

import json

from django.conf import settings

from apps.ai.providers.factory import AIProviderFactory


AI_SUMMARY_OK = "AI_SUMMARY_OK"
AI_SUMMARY_FAILED = "AI_SUMMARY_FAILED"

# Background automation must never wait on the AI provider the way
# an interactive caller can. A bounded timeout + no retries means a
# slow/hanging provider degrades quickly to the deterministic
# fallback instead of stalling the whole cron run.
_AUTOMATION_AI_MAX_RETRIES = 0

DUE_SOON_TASK = "due_soon_task"
STALE_LEAD = "stale_lead"


def build_digest_payload(*, digest_findings):
    """
    Compact, JSON-safe view of the deterministic digest, split by
    finding type. This is the only data the AI provider ever sees.
    """

    due_soon = [
        finding
        for finding in digest_findings
        if finding["finding_type"] == DUE_SOON_TASK
    ]

    stale = [
        finding
        for finding in digest_findings
        if finding["finding_type"] == STALE_LEAD
    ]

    return {
        "due_soon_tasks": [
            {
                "task_id": finding.get("task_id"),
                "lead_id": finding.get("lead_id"),
                "summary": finding["summary"],
            }
            for finding in due_soon
        ],
        "stale_leads": [
            {
                "lead_id": finding.get("lead_id"),
                "summary": finding["summary"],
            }
            for finding in stale
        ],
        "counts": {
            "due_soon_tasks": len(due_soon),
            "stale_leads": len(stale),
        },
    }


def build_summary_prompt(*, payload):
    """
    Build the AI prompt from the deterministic digest payload only.
    """

    crm_findings = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
You are Dodong OS CRM Automation Summarizer.

The JSON below is a deterministic digest of CRM findings that were
already produced by automated read-only checks.

You MUST follow these rules:

1. Summarize ONLY the findings supplied below.
2. Clearly distinguish due-soon tasks from stale leads.
3. Do not invent leads, tasks, dates, statuses, or numbers.
4. Do not claim that any action was taken or any record changed.
5. Do not recommend or describe executing CRM writes.
6. Keep the summary concise and operational (a few short lines).
7. If there are no findings, say that plainly.

CRM findings:
{crm_findings}

Write the concise operational summary now.
""".strip()


def build_deterministic_fallback(*, payload):
    """
    Deterministic, provider-free summary text.

    Example first line: "2 due-soon tasks; 1 stale lead."
    """

    counts = payload["counts"]
    due_soon_count = counts["due_soon_tasks"]
    stale_count = counts["stale_leads"]

    def _plural(count, noun):
        return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

    lines = [
        f"{_plural(due_soon_count, 'due-soon task')}; "
        f"{_plural(stale_count, 'stale lead')}."
    ]

    for task in payload["due_soon_tasks"]:
        lines.append(
            f"- due-soon task #{task['task_id']}: {task['summary']}"
        )

    for lead in payload["stale_leads"]:
        lines.append(
            f"- stale lead #{lead['lead_id']}: {lead['summary']}"
        )

    return "\n".join(lines)


def summarize_digest(*, digest_findings, provider=None):
    """
    Return an AI summary of the deterministic digest, or a
    deterministic fallback if the AI provider cannot be used.

    Never raises. Never touches CRM state.

    Returns:
        {
            "status": AI_SUMMARY_OK | AI_SUMMARY_FAILED,
            "source": "ai_provider" | "deterministic_fallback",
            "summary": <str>,
            "payload": <deterministic payload dict>,
            "error": <str or None>,
        }
    """

    payload = build_digest_payload(
        digest_findings=digest_findings,
    )

    fallback = build_deterministic_fallback(
        payload=payload,
    )

    try:
        if provider is not None:
            active_provider = provider
        else:
            active_provider = AIProviderFactory.create(
                timeout=settings.CRM_AUTOMATION_AI_TIMEOUT_SECONDS,
                max_retries=_AUTOMATION_AI_MAX_RETRIES,
            )

        prompt = build_summary_prompt(
            payload=payload,
        )

        raw = active_provider.analyze(prompt)

        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(
                "AI provider returned a blank or non-string summary."
            )

        return {
            "status": AI_SUMMARY_OK,
            "source": "ai_provider",
            "summary": raw.strip(),
            "payload": payload,
            "error": None,
        }

    except Exception as exc:
        return {
            "status": AI_SUMMARY_FAILED,
            "source": "deterministic_fallback",
            "summary": fallback,
            "payload": payload,
            "error": str(exc),
        }
