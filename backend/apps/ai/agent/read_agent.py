from apps.ai.tools.registry import execute_registered_tool


SUPPORTED_PRIORITY_TASK_INTENTS = {
    "what tasks need my attention",
    "what tasks need my attention?",
    "show me my priority tasks",
    "show my priority tasks",
    "what are my priority tasks",
    "what are my priority tasks?",
    "show me the highest priority tasks",
    "show my highest priority tasks",
}


def _normalize_message(message):
    """
    Normalize a user message for the first deterministic
    CRM Read Agent intent.
    """

    return " ".join(
        message.strip().lower().split()
    )


def _format_priority_tasks(tasks):
    """
    Produce a simple human-readable answer from structured
    priority-task tool results.

    This formatter contains no database logic.
    """

    if not tasks:
        return (
            "You have no priority CRM tasks "
            "requiring attention."
        )

    lines = [
        "Here are the CRM tasks that need your attention:"
    ]

    for index, task in enumerate(tasks, start=1):
        company = (
            task.get("lead_company")
            or "Unknown company"
        )

        title = (
            task.get("title")
            or "Untitled task"
        )

        priority = (
            task.get("priority")
            or "unknown"
        )

        status = (
            task.get("status")
            or "unknown"
        )

        due_date = task.get("due_date")

        line = (
            f"{index}. {title} — {company} "
            f"[{priority}, {status}]"
        )

        if due_date:
            line += f" — due {due_date}"

        lines.append(line)

    return "\n".join(lines)


def run_crm_read_agent(
    *,
    message,
    limit=10,
):
    """
    CRM Read Agent v0.1 core.

    For this milestone the agent supports exactly one
    deterministic read intent:

        "What tasks need my attention?"

    The runtime may execute only tools exposed through
    the read-only tool registry.

    It must never query Django models directly.
    """

    if not isinstance(message, str):
        return {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "message must be a string.",
            },
        }

    normalized_message = _normalize_message(
        message,
    )

    if not normalized_message:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "message cannot be empty.",
            },
        }

    if (
        normalized_message
        not in SUPPORTED_PRIORITY_TASK_INTENTS
    ):
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_READ_INTENT",
                "message": (
                    "This CRM Read Agent version currently "
                    "supports only priority-task questions."
                ),
            },
        }

    tool_result = execute_registered_tool(
        name="get_priority_tasks",
        arguments={
            "limit": limit,
        },
    )

    if not tool_result.get("success"):
        return {
            "success": False,
            "tool_used": "get_priority_tasks",
            "error": tool_result.get(
                "error",
                {
                    "code": "CRM_READ_AGENT_ERROR",
                    "message": (
                        "Unable to retrieve priority tasks."
                    ),
                },
            ),
        }

    tasks = tool_result.get(
        "data",
        [],
    )

    return {
        "success": True,
        "tool_used": "get_priority_tasks",
        "answer": _format_priority_tasks(
            tasks,
        ),
        "data": tasks,
    }