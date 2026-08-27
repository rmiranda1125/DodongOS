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


COMPLETE_TASK_PATTERN = re.compile(
    r"""
    ^\s*
    (?:please\s+)?
    complete
    \s+
    (?:task\s*)
    \#?\s*
    (?P<task_id>\d+)
    [.!?]?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def route_crm_write_proposal_intent(message):
    """
    Deterministically recognize supported controlled
    CRM write proposal requests.

    No database access or mutation occurs here.
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

    #
    # -----------------------------------------------------
    # CREATE FOLLOW-UP TASK
    # -----------------------------------------------------
    #

    create_match = (
        CREATE_FOLLOW_UP_TASK_PATTERN.fullmatch(
            message,
        )
    )

    if create_match is not None:

        lead_id = int(
            create_match.group(
                "lead_id"
            )
        )

        priority = (
            create_match.group(
                "priority"
            )
            or "medium"
        ).lower()

        requested_title = (
            create_match.group(
                "title"
            )
        )

        if requested_title:
            title = (
                requested_title
                .strip()
                .rstrip(".!?")
            )

            title_is_default = False

        else:
            title = (
                f"Follow up with lead {lead_id}"
            )

            title_is_default = True

        return {
            "success": True,
            "intent": (
                "create_lead_task_proposal"
            ),
            "action": "create_lead_task",
            "arguments": {
                "lead_id": lead_id,
                "title": title,
                "description": "",
                "priority": priority,
                "title_is_default": (
                    title_is_default
                ),
            },
        }

    #
    # -----------------------------------------------------
    # COMPLETE TASK
    # -----------------------------------------------------
    #

    complete_match = (
        COMPLETE_TASK_PATTERN.fullmatch(
            message,
        )
    )

    if complete_match is not None:

        task_id = int(
            complete_match.group(
                "task_id"
            )
        )

        return {
            "success": True,
            "intent": (
                "complete_lead_task_proposal"
            ),
            "action": "complete_lead_task",
            "arguments": {
                "task_id": task_id,
            },
        }

    return {
        "success": False,
        "error": {
            "code": (
                "UNSUPPORTED_WRITE_PROPOSAL_INTENT"
            ),
            "message": (
                "This CRM write request cannot currently "
                "be prepared as a controlled proposal."
            ),
        },
    }