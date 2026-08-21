from apps.ai.tools.registry import (
    execute_confirmed_write_tool,
)


def execute_confirmed_proposal(
    *,
    proposal,
    confirmed=False,
):
    """
    Execute a previously validated write proposal.

    Phase 9A supports only create_lead_task.
    """

    if not isinstance(proposal, dict):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL",
                "message": (
                    "A valid action proposal is required."
                ),
            },
        }

    if (
        proposal.get("status")
        != "awaiting_confirmation"
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL_STATE",
                "message": (
                    "The proposal is not awaiting "
                    "confirmation."
                ),
            },
        }

    if (
        proposal.get("requires_confirmation")
        is not True
    ):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL",
                "message": (
                    "The proposal does not contain the "
                    "required confirmation boundary."
                ),
            },
        }

    action = proposal.get(
        "action",
    )

    if action != "create_lead_task":
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_WRITE_ACTION",
                "message": (
                    "This write action is not enabled."
                ),
            },
        }

    arguments = proposal.get(
        "arguments",
    )

    if not isinstance(arguments, dict):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL",
                "message": (
                    "The proposal does not contain "
                    "valid action arguments."
                ),
            },
        }

    if confirmed is not True:
        return {
            "success": False,
            "error": {
                "code": "CONFIRMATION_REQUIRED",
                "message": (
                    "Explicit confirmation is required "
                    "before executing this CRM action."
                ),
            },
        }

    result = execute_confirmed_write_tool(
        name=action,
        arguments=arguments,
        confirmed=True,
    )

    if not result.get("success"):
        return result

    return {
        "success": True,
        "action": action,
        "status": "executed",
        "data": result["data"],
    }