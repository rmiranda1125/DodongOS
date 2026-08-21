from django.utils.dateparse import parse_datetime

from apps.leads import services as lead_services


ALLOWED_TASK_PRIORITIES = {
    "low",
    "medium",
    "high",
    "urgent",
}


def build_create_lead_task_proposal(
    *,
    lead_id,
    title,
    description="",
    priority="medium",
    due_date=None,
):
    """
    Build a proposed follow-up task without writing to the database.

    Phase 9A1 is proposal-only:
    - validate inputs
    - verify the lead exists
    - return a structured action proposal
    - require explicit confirmation
    - perform NO database mutation
    """

    if (
        not isinstance(lead_id, int)
        or isinstance(lead_id, bool)
        or lead_id < 1
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": "lead_id must be a positive integer.",
            },
        }

    if not isinstance(title, str) or not title.strip():
        return {
            "success": False,
            "error": {
                "code": "INVALID_TASK_TITLE",
                "message": "Task title must be a non-empty string.",
            },
        }

    title = title.strip()

    if not isinstance(description, str):
        return {
            "success": False,
            "error": {
                "code": "INVALID_TASK_DESCRIPTION",
                "message": "Task description must be a string.",
            },
        }

    if priority not in ALLOWED_TASK_PRIORITIES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRIORITY",
                "message": (
                    "priority must be one of: "
                    "low, medium, high, urgent."
                ),
            },
        }

    normalized_due_date = None

    if due_date not in (None, ""):
        if not isinstance(due_date, str):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DUE_DATE",
                    "message": "due_date must be an ISO datetime string.",
                },
            }

        parsed_due_date = parse_datetime(
            due_date,
        )

        if parsed_due_date is None:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DUE_DATE",
                    "message": "due_date must be an ISO datetime string.",
                },
            }

        normalized_due_date = parsed_due_date.isoformat()

    lead = lead_services.get_lead_by_id(
        lead_id=lead_id,
    )

    if lead is None:
        return {
            "success": False,
            "error": {
                "code": "LEAD_NOT_FOUND",
                "message": f"Lead {lead_id} was not found.",
            },
        }

    return {
        "success": True,
        "proposal": {
            "action": "create_lead_task",
            "access_level": "write",
            "status": "awaiting_confirmation",
            "requires_confirmation": True,
            "lead": {
                "id": lead.id,
                "company_name": lead.company_name,
            },
            "arguments": {
                "lead_id": lead.id,
                "title": title,
                "description": description.strip(),
                "task_type": "follow_up",
                "priority": priority,
                "due_date": normalized_due_date,
            },
        },
    }