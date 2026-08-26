import re


CREATE_FOLLOW_UP_TASK_PATTERN = re.compile(
    r"""
    ^\s*
    (?:please\s+)?
    create
    \s+
    (?:a\s+)?
    (?:
        (?P<priority>low|medium|high|urgent)
        \s+
        (?:priority\s+)?
    )?
    follow(?:[-\s]?up)
    \s+
    task
    \s+
    for
    \s+
    lead
    \s*\#?\s*
    (?P<lead_id>\d+)
    (?:
        \s+
        to
        \s+
        (?P<title>.+?)
    )?
    [.!?]?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def route_crm_write_proposal_intent(message):
    """
    Deterministically recognize supported CRM write
    proposal requests.

    IMPORTANT:
    This function performs no database access and no write.
    """

    if not isinstance(message, str) or not message.strip():
        return {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": (
                    "A non-empty CRM action request is required."
                ),
            },
        }

    match = CREATE_FOLLOW_UP_TASK_PATTERN.fullmatch(
        message,
    )

    if match is None:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_WRITE_PROPOSAL_INTENT",
                "message": (
                    "This CRM write request cannot currently "
                    "be prepared as a controlled proposal."
                ),
            },
        }

    lead_id = int(
        match.group("lead_id")
    )

    priority = (
        match.group("priority")
        or "medium"
    ).lower()

    requested_title = match.group(
        "title"
    )

    if requested_title:
        title = requested_title.strip().rstrip(
            ".!?"
        )
        title_is_default = False

    else:
        title = (
            f"Follow up with lead {lead_id}"
        )
        title_is_default = True

    return {
        "success": True,
        "intent": "create_lead_task_proposal",
        "action": "create_lead_task",
        "arguments": {
            "lead_id": lead_id,
            "title": title,
            "description": "",
            "priority": priority,
            "title_is_default": title_is_default,
        },
    }