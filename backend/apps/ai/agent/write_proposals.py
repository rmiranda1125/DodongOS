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


ALLOWED_LEAD_STATUSES = {
    "new",
    "contacted",
    "qualified",
    "proposal",
    "won",
    "lost",
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
                    "message": (
                        "due_date must be an ISO datetime string."
                    ),
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
                    "message": (
                        "due_date must be an ISO datetime string."
                    ),
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
            "proposal_id": str(
                uuid.uuid4()
            ),
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

    action = route.get(
        "action",
    )

    #
    # -----------------------------------------------------
    # CREATE LEAD TASK
    # -----------------------------------------------------
    #

    if action == "create_lead_task":

        arguments = dict(
            route["arguments"]
        )

        title_is_default = (
            arguments.pop(
                "title_is_default",
                False,
            )
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

        if title_is_default is True:

            company_name = proposal[
                "lead"
            ]["company_name"]

            proposal[
                "arguments"
            ]["title"] = (
                f"Follow up with {company_name}"
            )

        return {
            "success": True,
            "intent": route["intent"],
            "proposal": proposal,
        }

    #
    # -----------------------------------------------------
    # COMPLETE LEAD TASK
    # -----------------------------------------------------
    #

    if action == "complete_lead_task":

        proposal_result = (
            build_complete_lead_task_proposal(
                **route["arguments"]
            )
        )

        if not proposal_result.get(
            "success"
        ):
            return proposal_result

        return {
            "success": True,
            "intent": route["intent"],
            "proposal": proposal_result[
                "proposal"
            ],
        }

    #
    # -----------------------------------------------------
    # CHANGE LEAD STATUS
    # -----------------------------------------------------
    #

    if action == "change_lead_status":

        proposal_result = (
            build_change_lead_status_proposal(
                **route["arguments"]
            )
        )

        if not proposal_result.get(
            "success"
        ):
            return proposal_result

        return {
            "success": True,
            "intent": route["intent"],
            "proposal": proposal_result[
                "proposal"
            ],
        }

    return {
        "success": False,
        "error": {
            "code": "UNSUPPORTED_WRITE_ACTION",
            "message": (
                "This CRM write action is not enabled."
            ),
        },
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


def build_change_lead_status_proposal(
    *,
    lead_id,
    status,
):
    """
    Build a validated proposal for changing one lead's status.

    This function MUST NOT mutate CRM data.
    """

    if (
        isinstance(lead_id, bool)
        or not isinstance(lead_id, int)
        or lead_id <= 0
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": (
                    "A valid positive lead ID is required."
                ),
            },
        }

    if (
        not isinstance(status, str)
        or not status.strip()
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_STATUS",
                "message": (
                    "A valid lead status is required."
                ),
            },
        }

    target_status = (
        status
        .strip()
        .lower()
    )

    if target_status not in ALLOWED_LEAD_STATUSES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_STATUS",
                "message": (
                    f"Lead status '{target_status}' "
                    "is not supported."
                ),
            },
        }

    lead = lead_services.get_lead_by_id(
        lead_id=lead_id,
    )

    if lead is None:
        return {
            "success": False,
            "error": {
                "code": "LEAD_NOT_FOUND",
                "message": (
                    f"Lead {lead_id} was not found."
                ),
            },
        }

    if lead.status == target_status:
        return {
            "success": False,
            "error": {
                "code": "LEAD_ALREADY_IN_STATUS",
                "message": (
                    f"Lead {lead_id} is already "
                    f"in status '{target_status}'."
                ),
            },
        }

    return {
        "success": True,
        "proposal": {
            "proposal_id": str(
                uuid.uuid4()
            ),
            "action": "change_lead_status",
            "access_level": "write",
            "status": "awaiting_confirmation",
            "requires_confirmation": True,
            "lead": {
                "id": lead.id,
                "company_name": lead.company_name,
                "status": lead.status,
            },
            "arguments": {
                "lead_id": lead.id,
                "status": target_status,
                "expected_status": lead.status,
            },
        },
    }

def build_add_lead_note_proposal(
    *,
    lead_id,
    note,
):
    """
    Build a validated proposal for adding a note
    to one CRM lead.

    This function MUST NOT mutate CRM data.
    """

    if (
        isinstance(lead_id, bool)
        or not isinstance(lead_id, int)
        or lead_id <= 0
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LEAD_ID",
                "message": (
                    "A valid positive lead ID is required."
                ),
            },
        }

    if (
        not isinstance(note, str)
        or not note.strip()
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_NOTE",
                "message": (
                    "A non-empty lead note is required."
                ),
            },
        }

    cleaned_note = note.strip()

    lead = lead_services.get_lead_by_id(
        lead_id=lead_id,
    )

    if lead is None:
        return {
            "success": False,
            "error": {
                "code": "LEAD_NOT_FOUND",
                "message": (
                    f"Lead {lead_id} was not found."
                ),
            },
        }

    return {
        "success": True,
        "proposal": {
            "proposal_id": str(
                uuid.uuid4()
            ),
            "action": "add_lead_note",
            "access_level": "write",
            "status": "awaiting_confirmation",
            "requires_confirmation": True,
            "lead": {
                "id": lead.id,
                "company_name": lead.company_name,
                "status": lead.status,
            },
            "activity": {
                "activity_type": "note",
                "description": cleaned_note,
            },
            "arguments": {
                "lead_id": lead.id,
                "activity_type": "note",
                "description": cleaned_note,
            },
        },
    }