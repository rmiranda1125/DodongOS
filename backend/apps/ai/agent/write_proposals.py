from django.utils.dateparse import parse_datetime
import uuid
from apps.leads import services as lead_services
from apps.ai.agent.write_router import (
    route_crm_write_proposal_intent,
)

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
            "proposal_id": str(uuid.uuid4()),
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

def build_write_proposal_from_message(
    message,
):
    """
    Convert one supported natural-language CRM write
    request into a validated proposal.

    No CRM mutation occurs here.
    """

    route = route_crm_write_proposal_intent(
        message,
    )

    if not route.get("success"):
        return route

    if (
        route.get("action")
        != "create_lead_task"
    ):
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_WRITE_ACTION",
                "message": (
                    "This CRM write action is not enabled."
                ),
            },
        }

    #
    # Copy the parser arguments so we do not mutate
    # the router result.
    #

    arguments = dict(
        route["arguments"]
    )

    #
    # This is parser metadata only.
    # It must NOT be passed to the CRM proposal builder.
    #

    title_is_default = arguments.pop(
        "title_is_default",
        False,
    )

    proposal_result = (
        build_create_lead_task_proposal(
            **arguments
        )
    )

    if not proposal_result.get(
        "success"
    ):
        return proposal_result

    proposal = proposal_result[
        "proposal"
    ]

    #
    # Only replace the generated fallback title.
    #
    # Explicit user titles such as:
    #
    # "to Send pricing proposal"
    #
    # must remain untouched.
    #

    if title_is_default is True:

        company_name = proposal[
            "lead"
        ]["company_name"]

        proposal["arguments"]["title"] = (
            f"Follow up with {company_name}"
        )

    return {
        "success": True,
        "intent": route["intent"],
        "proposal": proposal,
    }

def build_complete_lead_task_proposal(
    *,
    task_id,
):
    """
    Build a proposal to complete one CRM task.

    This performs no CRM mutation.
    """

    if (
        not isinstance(task_id, int)
        or isinstance(task_id, bool)
        or task_id < 1
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_TASK_ID",
                "message": (
                    "task_id must be a positive integer."
                ),
            },
        }

    task = lead_services.get_lead_task_by_id(
        task_id=task_id,
    )

    if task is None:
        return {
            "success": False,
            "error": {
                "code": "TASK_NOT_FOUND",
                "message": (
                    f"Task {task_id} was not found."
                ),
            },
        }

    if task.status == "completed":
        return {
            "success": False,
            "error": {
                "code": "TASK_ALREADY_COMPLETED",
                "message": (
                    f"Task {task_id} is already completed."
                ),
            },
        }

    return {
        "success": True,
        "proposal": {
            "proposal_id": str(
                uuid.uuid4()
            ),
            "action": "complete_lead_task",
            "access_level": "write",
            "status": "awaiting_confirmation",
            "requires_confirmation": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "task_type": task.task_type,
            },
            "lead": {
                "id": task.lead_id,
                "company_name": (
                    task.lead.company_name
                ),
            },
            "arguments": {
                "task_id": task.id,
            },
        },
    }