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