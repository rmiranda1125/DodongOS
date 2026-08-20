import re


def normalize_message(message):
    """
    Normalize user input for deterministic CRM read routing.
    """

    return " ".join(
        message.strip().lower().split()
    )


def extract_lead_id(message):
    """
    Extract a lead ID from phrases such as:

    lead 12
    lead #12
    """

    match = re.search(
        r"\blead\s*#?\s*(\d+)\b",
        message,
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    return int(match.group(1))


def route_crm_read_intent(message):
    """
    Convert a supported CRM read question into a registered
    read-only tool name and structured tool arguments.

    This router does not execute tools and does not access ORM.

    Write requests are explicitly blocked because this router
    is used by the read-only CRM agent.
    """

    normalized = normalize_message(
        message,
    )

    # -----------------------------------------------------
    # Explicitly block write-language
    # -----------------------------------------------------

    blocked_write_terms = (
        "delete",
        "remove",
        "create",
        "complete",
        "mark as complete",
        "update",
        "change status",
        "move lead",
        "edit",
    )

    if any(
        term in normalized
        for term in blocked_write_terms
    ):
        return {
            "success": False,
            "error": {
                "code": "WRITE_INTENT_NOT_ALLOWED",
                "message": (
                    "CRM write requests are not available "
                    "in the read-only agent."
                ),
            },
        }

    lead_id = extract_lead_id(
        normalized,
    )

    # -----------------------------------------------------
    # Lead-specific intents must be checked first.
    # -----------------------------------------------------

    if lead_id is not None:

        if "task" in normalized:
            return {
                "success": True,
                "intent": "lead_tasks",
                "tool_name": "get_lead_tasks",
                "arguments": {
                    "lead_id": lead_id,
                },
            }

        activity_terms = (
            "activity",
            "activities",
            "history",
            "happened",
            "what happened",
            "last contact",
            "contacted",
        )

        if any(
            term in normalized
            for term in activity_terms
        ):
            return {
                "success": True,
                "intent": "lead_activities",
                "tool_name": "get_lead_activities",
                "arguments": {
                    "lead_id": lead_id,
                },
            }

        return {
            "success": True,
            "intent": "get_lead",
            "tool_name": "get_lead",
            "arguments": {
                "lead_id": lead_id,
            },
        }

    # -----------------------------------------------------
    # General task intents
    # -----------------------------------------------------

    if (
        "overdue" in normalized
        and "task" in normalized
    ):
        return {
            "success": True,
            "intent": "overdue_tasks",
            "tool_name": "get_overdue_tasks",
            "arguments": {},
        }

    if (
        "pending" in normalized
        and "task" in normalized
    ):
        return {
            "success": True,
            "intent": "pending_tasks",
            "tool_name": "get_pending_tasks",
            "arguments": {},
        }

    # -----------------------------------------------------
    # Pipeline
    # -----------------------------------------------------

    pipeline_terms = (
        "pipeline",
        "pipeline summary",
        "summarize my pipeline",
        "summarise my pipeline",
    )

    if any(
        term in normalized
        for term in pipeline_terms
    ):
        return {
            "success": True,
            "intent": "pipeline_summary",
            "tool_name": "get_pipeline_summary",
            "arguments": {},
        }

    # -----------------------------------------------------
    # Priority / attention
    # -----------------------------------------------------

    priority_terms = (
        "need my attention",
        "priority tasks",
        "highest priority",
        "important tasks",
        "tasks should i work on",
        "tasks should i do",
    )

    if (
        "task" in normalized
        and any(
            term in normalized
            for term in priority_terms
        )
    ):
        return {
            "success": True,
            "intent": "priority_tasks",
            "tool_name": "get_priority_tasks",
            "arguments": {},
        }

    # -----------------------------------------------------
    # Unsupported read intent
    # -----------------------------------------------------

    return {
        "success": False,
        "error": {
            "code": "UNSUPPORTED_READ_INTENT",
            "message": (
                "This CRM Read Agent does not yet understand "
                "that read request."
            ),
        },
    }