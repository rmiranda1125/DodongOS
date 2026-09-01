"""
CRM digest orchestration.

Turns the structured findings produced by
``apps/automation/checks.py`` into deduplicated, persisted
``CRMDigest`` rows.

Orchestration only. This module MUST NOT access the Django ORM.
All persistence goes through ``apps/automation/services.py``. No
AI-generated prose is produced or stored here (Phase 6D).
"""

from apps.automation import services as automation_services


DUE_SOON_TASK = "due_soon_task"
STALE_LEAD = "stale_lead"

SUPPORTED_FINDING_TYPES = (
    DUE_SOON_TASK,
    STALE_LEAD,
)


def build_dedup_key(*, finding_type, object_id):
    """
    Build the stable deduplication key for a deterministic finding.

    The key is derived only from the finding type and a persisted
    CRM id. It never contains timestamps or generated text, so the
    same condition always maps to the same key across runs.

        due-soon task -> "due_soon_task:<task_id>"
        stale lead    -> "stale_lead:<lead_id>"
    """

    if finding_type not in SUPPORTED_FINDING_TYPES:
        raise ValueError(
            f"Unsupported finding_type: {finding_type!r}",
        )

    return f"{finding_type}:{object_id}"


def shape_finding(raw_finding):
    """
    Convert one raw check finding into a shaped digest finding.

    Raw findings come from apps/automation/checks.py and carry:
    finding_type, lead_id, object_id, summary, data.
    """

    finding_type = raw_finding["finding_type"]
    object_id = raw_finding["object_id"]

    dedup_key = build_dedup_key(
        finding_type=finding_type,
        object_id=object_id,
    )

    task_id = (
        object_id
        if finding_type == DUE_SOON_TASK
        else None
    )

    return {
        "dedup_key": dedup_key,
        "finding_type": finding_type,
        "lead_id": raw_finding.get("lead_id"),
        "task_id": task_id,
        "summary": raw_finding["summary"],
        "finding_data": raw_finding["data"],
    }


def persist_findings(*, findings, seen_at=None):
    """
    Deduplicate and persist a full set of raw check findings from a
    successful run, and resolve any previously active finding that
    is absent from this set.

    MUST only be called for a fully successful check run.

    Returns:
        {
            "active": <int>,
            "resolved": <int>,
            "digest_findings": [<shaped finding>, ...],
        }

    ``digest_findings`` is the deterministic, JSON-safe shaped data
    the optional AI summary layer (Phase 6D) works from.
    """

    digest_findings = [
        shape_finding(raw_finding)
        for raw_finding in findings
    ]

    sync_result = automation_services.sync_digest_findings(
        digest_findings=digest_findings,
        seen_at=seen_at,
    )

    return {
        **sync_result,
        "digest_findings": digest_findings,
    }
