from django.conf import settings

from apps.leads import reminders as lead_reminders


def _serialize_datetime(value):
    """
    Convert a Django datetime into a JSON-safe ISO string.
    """
    if value is None:
        return None

    return value.isoformat()


def _serialize_due_soon_task(task):
    """
    Convert a LeadTask into safe structured data.

    Django model objects must never be returned directly to the AI
    or to background automation.
    """
    return {
        "id": task.id,
        "lead_id": task.lead_id,
        "lead_company": task.lead.company_name,
        "title": task.title,
        "task_type": task.task_type,
        "priority": task.priority,
        "status": task.status,
        "due_date": _serialize_datetime(task.due_date),
    }


def _serialize_stale_lead(lead):
    """
    Convert a Lead into safe structured data.
    """
    return {
        "id": lead.id,
        "company_name": lead.company_name,
        "status": lead.status,
        "created_at": _serialize_datetime(lead.created_at),
        "last_meaningful_activity_at": _serialize_datetime(
            getattr(
                lead,
                "last_meaningful_activity_at",
                None,
            ),
        ),
    }


def get_due_soon_tasks_tool(*, within_hours=None):
    """
    Read-only CRM tool.

    Returns actionable CRM tasks due within the next
    ``within_hours`` hours (defaults to
    ``settings.CRM_DUE_SOON_HOURS``).

    This function must never query Django models directly.
    """

    if within_hours is None:
        within_hours = settings.CRM_DUE_SOON_HOURS

    if isinstance(within_hours, bool) or not isinstance(
        within_hours,
        (int, float),
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_WITHIN_HOURS",
                "message": "within_hours must be a positive number.",
            },
        }

    if within_hours <= 0:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WITHIN_HOURS",
                "message": "within_hours must be a positive number.",
            },
        }

    try:
        tasks = lead_reminders.get_due_soon_tasks(
            within_hours=within_hours,
        )

        return {
            "success": True,
            "data": [
                _serialize_due_soon_task(task)
                for task in tasks
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve due-soon tasks.",
            },
        }


def get_stale_leads_tool(*, stale_after_days=None):
    """
    Read-only CRM tool.

    Returns active CRM leads with no meaningful activity within the
    last ``stale_after_days`` days (defaults to
    ``settings.CRM_STALE_LEAD_DAYS``).

    This function must never query Django models directly.
    """

    if stale_after_days is None:
        stale_after_days = settings.CRM_STALE_LEAD_DAYS

    if isinstance(stale_after_days, bool) or not isinstance(
        stale_after_days,
        (int, float),
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_STALE_AFTER_DAYS",
                "message": (
                    "stale_after_days must be a positive number."
                ),
            },
        }

    if stale_after_days <= 0:
        return {
            "success": False,
            "error": {
                "code": "INVALID_STALE_AFTER_DAYS",
                "message": (
                    "stale_after_days must be a positive number."
                ),
            },
        }

    try:
        leads = lead_reminders.get_stale_leads(
            stale_after_days=stale_after_days,
        )

        return {
            "success": True,
            "data": [
                _serialize_stale_lead(lead)
                for lead in leads
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve stale leads.",
            },
        }
