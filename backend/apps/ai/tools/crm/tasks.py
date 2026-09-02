from django.utils.dateparse import parse_datetime

from apps.leads import services as lead_services


def _serialize_datetime(value):
    """
    Convert a Django datetime into a JSON-safe ISO string.
    """
    if value is None:
        return None

    return value.isoformat()


def _serialize_task(task):
    """
    Convert a LeadTask model instance into safe structured data.

    Django model objects must never be returned directly to the AI.
    """
    return {
        "id": task.id,
        "lead_id": task.lead_id,
        "lead_company": task.lead.company_name,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "priority": task.priority,
        "status": task.status,
        "due_date": _serialize_datetime(task.due_date),
        "completed_at": _serialize_datetime(task.completed_at),
    }


def get_priority_tasks_tool(*, limit=10):
    """
    Read-only CRM tool.

    Returns the highest-priority actionable CRM tasks using the
    existing CRM service layer.

    This function must never query Django models directly.
    """

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 100:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 100.",
            },
        }

    try:
        tasks = lead_services.get_priority_tasks(
            limit=limit,
        )

        return {
            "success": True,
            "data": [
                _serialize_task(task)
                for task in tasks
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve priority tasks.",
            },
        }

def get_overdue_tasks_tool(*, limit=50):
    """
    Read-only CRM tool.

    Returns overdue CRM tasks using the existing CRM service layer.

    This function must never query Django models directly.
    """

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 100:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 100.",
            },
        }

    try:
        tasks = lead_services.get_overdue_tasks()

        return {
            "success": True,
            "data": [
                _serialize_task(task)
                for task in tasks[:limit]
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve overdue tasks.",
            },
        } 

def get_pending_tasks_tool(*, limit=50, priority=None):
    """
    Read-only CRM tool.

    Returns pending and in-progress CRM tasks using the
    existing CRM service layer.

    This function must never query Django models directly.
    """

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 100:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 100.",
            },
        }

    allowed_priorities = {
        "low",
        "medium",
        "high",
        "urgent",
    }

    if priority is not None and priority not in allowed_priorities:
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

    try:
        tasks = lead_services.get_pending_tasks(
            priority=priority,
        )

        return {
            "success": True,
            "data": [
                _serialize_task(task)
                for task in tasks[:limit]
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve pending tasks.",
            },
        }

def get_lead_tasks_tool(
    *,
    lead_id,
    limit=50,
    status=None,
    priority=None,
):
    """
    Read-only CRM tool.

    Return tasks belonging to one lead.

    The AI layer must never query Django models directly.
    Lead resolution is performed by the CRM service layer.
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

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 100:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 100.",
            },
        }

    allowed_statuses = {
        "pending",
        "in_progress",
        "completed",
        "cancelled",
    }

    if status is not None and status not in allowed_statuses:
        return {
            "success": False,
            "error": {
                "code": "INVALID_STATUS",
                "message": (
                    "status must be one of: "
                    "pending, in_progress, completed, cancelled."
                ),
            },
        }

    allowed_priorities = {
        "low",
        "medium",
        "high",
        "urgent",
    }

    if priority is not None and priority not in allowed_priorities:
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

    try:
        tasks = lead_services.get_lead_tasks_by_id(
            lead_id=lead_id,
            status=status,
            priority=priority,
        )

        if tasks is None:
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
            "data": [
                _serialize_task(task)
                for task in tasks[:limit]
            ],
        }

    except Exception:
        return {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": "Unable to retrieve lead tasks.",
            },
        }

def create_lead_task_tool(
    *,
    lead_id,
    title,
    description="",
    task_type="follow_up",
    priority="medium",
    due_date=None,
):
    """
    Create one CRM task through the CRM service layer.

    This is a WRITE tool.

    It must only be called through the confirmed-write
    execution path.
    """

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

    parsed_due_date = None

    if due_date:
        parsed_due_date = parse_datetime(
            due_date,
        )

        if parsed_due_date is None:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_DUE_DATE",
                    "message": (
                        "due_date must be an ISO "
                        "datetime string."
                    ),
                },
            }

    task = lead_services.create_lead_task(
        lead=lead,
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        status="pending",
        due_date=parsed_due_date,
    )

    #
    # Verification step:
    # Re-read through the CRM service layer.
    #

    verified_tasks = (
        lead_services.get_lead_tasks_by_id(
            lead_id=lead_id,
        )
    )

    verified_task = next(
        (
            candidate
            for candidate in verified_tasks
            if candidate.id == task.id
        ),
        None,
    )

    if verified_task is None:
        return {
            "success": False,
            "error": {
                "code": "TASK_VERIFICATION_FAILED",
                "message": (
                    "The task was created but could "
                    "not be verified."
                ),
            },
        }

    return {
        "success": True,
        "data": _serialize_task(
            verified_task,
        ),
    }

def complete_lead_task_tool(
    *,
    task_id,
):
    """
    Complete one CRM task through the CRM service layer.

    WRITE TOOL:
    Must only run through confirmed write execution.
    """

    task = lead_services.get_lead_task_by_id(
        task_id=task_id,
    )

    if task is None:
        return {
            "success": False,
            "error": {
                "code": "TASK_NOT_FOUND",
                "message": f"Task {task_id} was not found.",
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

    completed_task = (
        lead_services.complete_lead_task(
            task=task,
        )
    )

    verified_task = (
        lead_services.get_lead_task_by_id(
            task_id=completed_task.id,
        )
    )

    if (
        verified_task is None
        or verified_task.status != "completed"
        or verified_task.completed_at is None
    ):
        return {
            "success": False,
            "error": {
                "code": "TASK_COMPLETION_VERIFICATION_FAILED",
                "message": (
                    "The task completion could not "
                    "be verified."
                ),
            },
        }

    return {
        "success": True,
        "data": _serialize_task(
            verified_task,
        ),
    }