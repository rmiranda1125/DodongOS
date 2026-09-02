"""
Deterministic background CRM checks.

Orchestration only. This module MUST NOT access the Django ORM.
It reads CRM state exclusively through the registered read-only
tool executor, and returns structured findings. It does not
persist anything.
"""

from django.conf import settings

from apps.ai.tools.registry import execute_registered_tool


DUE_SOON_TASKS_CHECK = "due_soon_tasks"
STALE_LEADS_CHECK = "stale_leads"


class CrmCheckError(RuntimeError):
    """
    Raised when a read tool a check depends on fails unexpectedly.

    The management command turns this into a failed
    ScheduledCheckRun rather than a crash with no record.
    """


def _run_read_tool(*, name, arguments):
    result = execute_registered_tool(
        name=name,
        arguments=arguments,
    )

    if not result.get("success"):
        error = result.get("error", {})
        raise CrmCheckError(
            f"read tool '{name}' failed: "
            f"{error.get('code', 'UNKNOWN')}"
        )

    return result.get("data", [])


def check_due_soon_tasks(*, within_hours=None):
    """
    Findings for actionable tasks that are due soon.
    """

    if within_hours is None:
        within_hours = settings.CRM_DUE_SOON_HOURS

    rows = _run_read_tool(
        name="get_due_soon_tasks",
        arguments={
            "within_hours": within_hours,
        },
    )

    return [
        {
            "check": DUE_SOON_TASKS_CHECK,
            "finding_type": "due_soon_task",
            "lead_id": row["lead_id"],
            "object_id": row["id"],
            "summary": (
                f"Task '{row['title']}' for "
                f"{row['lead_company']} is due at "
                f"{row['due_date']}."
            ),
            "data": row,
        }
        for row in rows
    ]


def check_stale_leads(*, stale_after_days=None):
    """
    Findings for active leads with no recent meaningful activity.
    """

    if stale_after_days is None:
        stale_after_days = settings.CRM_STALE_LEAD_DAYS

    rows = _run_read_tool(
        name="get_stale_leads",
        arguments={
            "stale_after_days": stale_after_days,
        },
    )

    return [
        {
            "check": STALE_LEADS_CHECK,
            "finding_type": "stale_lead",
            "lead_id": row["id"],
            "object_id": row["id"],
            "summary": (
                f"Lead {row['company_name']} "
                f"({row['status']}) has had no meaningful "
                f"activity since "
                f"{row['last_meaningful_activity_at']}."
            ),
            "data": row,
        }
        for row in rows
    ]


def run_all_checks(
    *,
    within_hours=None,
    stale_after_days=None,
):
    """
    Run every deterministic CRM check and return a summary.

    Returns:
        {
            "checks_run": <int>,
            "findings": [<finding dict>, ...],
        }
    """

    findings = []

    findings.extend(
        check_due_soon_tasks(
            within_hours=within_hours,
        ),
    )

    findings.extend(
        check_stale_leads(
            stale_after_days=stale_after_days,
        ),
    )

    return {
        "checks_run": 2,
        "findings": findings,
    }
