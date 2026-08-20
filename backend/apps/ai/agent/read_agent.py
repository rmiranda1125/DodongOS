from apps.ai.agent.response import (
    generate_crm_read_response,
)
from apps.ai.agent.router import (
    route_crm_read_intent,
)
from apps.ai.tools.registry import (
    execute_registered_tool,
)


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


def _format_search_leads(leads):
    """
    Produce a deterministic human-readable answer from
    structured search_leads tool results.

    This formatter contains no database logic.
    """

    if not leads:
        return "No matching CRM leads were found."

    lines = [
        (
            f"Found {len(leads)} matching CRM "
            f"lead{'s' if len(leads) != 1 else ''}:"
        )
    ]

    for index, lead in enumerate(
        leads,
        start=1,
    ):
        company = (
            lead.get("company_name")
            or "Unknown company"
        )

        job_title = (
            lead.get("job_title")
            or "Unknown role"
        )

        status = (
            lead.get("status")
            or "unknown"
        )

        lines.append(
            (
                f"{index}. {company} — "
                f"{job_title} "
                f"[{status}]"
            )
        )

    return "\n".join(lines)


def run_crm_read_agent(
    *,
    message,
    limit=10,
):
    """
    CRM Read Agent core.

    Routes supported CRM read questions to registered
    read-only tools.

    No ORM access is allowed here.
    """

    if not isinstance(message, str):
        return {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "message must be a string.",
            },
        }

    if not message.strip():
        return {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "message cannot be empty.",
            },
        }

    route = route_crm_read_intent(
        message,
    )

    if not route.get("success"):
        return route

    tool_name = route["tool_name"]

    arguments = dict(
        route.get(
            "arguments",
            {},
        )
    )

    # Apply the read-agent result limit only to tools that
    # support a limit argument.
    tools_with_limit = {
        "get_priority_tasks",
        "get_overdue_tasks",
        "get_pending_tasks",
        "get_lead_tasks",
        "get_lead_activities",
        "search_leads",
    }

    if tool_name in tools_with_limit:
        arguments["limit"] = limit

    tool_result = execute_registered_tool(
        name=tool_name,
        arguments=arguments,
    )

    if not tool_result.get("success"):
        return {
            "success": False,
            "intent": route["intent"],
            "tool_used": tool_name,
            "error": tool_result.get(
                "error",
                {
                    "code": "CRM_READ_AGENT_ERROR",
                    "message": (
                        "Unable to retrieve CRM data."
                    ),
                },
            ),
        }

    data = tool_result.get(
        "data",
        [],
    )

    return {
        "success": True,
        "intent": route["intent"],
        "tool_used": tool_name,
        "answer": _format_read_result(
            tool_name=tool_name,
            data=data,
        ),
        "data": data,
    }


def run_crm_read_agent_with_provider(
    *,
    message,
    limit=10,
    provider=None,
):
    """
    CRM Read Agent v0.1 with AI-generated final response.

    CRM retrieval remains controlled by run_crm_read_agent().
    The AI provider only receives already-verified read data.

    If the provider fails, return the deterministic answer
    produced by the core read agent.
    """

    core_result = run_crm_read_agent(
        message=message,
        limit=limit,
    )

    if not core_result.get("success"):
        return core_result

    try:
        ai_answer = generate_crm_read_response(
            user_message=message,
            tool_used=core_result["tool_used"],
            data=core_result["data"],
            provider=provider,
        )

        return {
            **core_result,
            "answer": ai_answer,
            "response_source": "ai_provider",
        }

    except Exception:
        return {
            **core_result,
            "response_source": "deterministic_fallback",
            "warning": {
                "code": "AI_RESPONSE_FAILED",
                "message": (
                    "CRM data was retrieved successfully, "
                    "but the AI response could not be generated."
                ),
            },
        }


def _format_read_result(
    *,
    tool_name,
    data,
):
    """
    Provide a deterministic fallback response for every
    currently supported CRM read tool.
    """

    if tool_name == "get_priority_tasks":
        return _format_priority_tasks(
            data,
        )

    if tool_name == "get_overdue_tasks":
        if not data:
            return "You have no overdue CRM tasks."

        return (
            f"You have {len(data)} overdue CRM "
            f"task{'s' if len(data) != 1 else ''}."
        )

    if tool_name == "get_pending_tasks":
        if not data:
            return "You have no pending CRM tasks."

        return (
            f"You have {len(data)} pending or "
            f"in-progress CRM "
            f"task{'s' if len(data) != 1 else ''}."
        )

    if tool_name == "get_pipeline_summary":
        if not data:
            return "No CRM pipeline data is available."

        total = data.get(
            "total_leads",
            0,
        )

        return (
            f"Your CRM pipeline currently contains "
            f"{total} lead{'s' if total != 1 else ''}."
        )

    if tool_name == "get_lead":
        if not data:
            return "The requested CRM lead was not found."

        company = (
            data.get("company_name")
            or "Unknown company"
        )

        status = (
            data.get("status")
            or "unknown"
        )

        return (
            f"{company} is currently in CRM status "
            f"'{status}'."
        )

    if tool_name == "get_lead_tasks":
        if not data:
            return (
                "This lead currently has no CRM tasks."
            )

        return (
            f"This lead has {len(data)} CRM "
            f"task{'s' if len(data) != 1 else ''}."
        )

    if tool_name == "get_lead_activities":
        if not data:
            return (
                "This lead currently has no CRM "
                "activity history."
            )

        return (
            f"This lead has {len(data)} recorded CRM "
            f"activit{'ies' if len(data) != 1 else 'y'}."
        )

    if tool_name == "search_leads":
        return _format_search_leads(
            data,
        )

    return "CRM data was retrieved successfully."