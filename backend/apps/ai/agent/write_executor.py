import uuid

from django.db import (
    IntegrityError,
    transaction,
)

from apps.ai import audit_services
from apps.ai.models import AIActionAudit
from apps.ai.tools.registry import (
    execute_confirmed_write_tool,
)


SUPPORTED_WRITE_ACTIONS = {
    "create_lead_task",
    "complete_lead_task",
    "change_lead_status",
    "add_lead_note",
}


def execute_confirmed_proposal(
    *,
    proposal,
    confirmed=False,
):
    """
    Execute one confirmed write proposal.

    Safety guarantees:
    - explicit confirmation is required
    - only approved write actions are supported
    - every proposal has a unique proposal_id
    - the proposal_id can execute only once
    - execution and audit recording are atomic
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

    if action not in SUPPORTED_WRITE_ACTIONS:
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

    raw_proposal_id = proposal.get(
        "proposal_id",
    )

    try:
        proposal_id = uuid.UUID(
            str(raw_proposal_id),
        )
    except (TypeError, ValueError, AttributeError):
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROPOSAL_ID",
                "message": (
                    "The CRM action proposal does not "
                    "contain a valid proposal ID."
                ),
            },
        }

    try:
        with transaction.atomic():

            audit = audit_services.create_action_audit(
                proposal_id=proposal_id,
                action=action,
                lead_id=arguments.get(
                    "lead_id",
                ),
                proposal_data=arguments,
            )

            result = execute_confirmed_write_tool(
                name=action,
                arguments=arguments,
                confirmed=True,
            )

            if not result.get("success"):

                error = result.get(
                    "error",
                    {},
                )

                audit_services.mark_action_audit_failed(
                    audit=audit,
                    error_code=error.get(
                        "code",
                        "WRITE_EXECUTION_FAILED",
                    ),
                )

                result["audit_id"] = audit.id
                result["proposal_id"] = str(
                    proposal_id,
                )

                return result

            task_data = result["data"]

            audit_services.mark_action_audit_executed(
                audit=audit,
                result_task_id=task_data.get(
                    "id",
                ),
            )

            return {
                "success": True,
                "action": action,
                "status": "executed",
                "proposal_id": str(
                    proposal_id,
                ),
                "audit_id": audit.id,
                "data": task_data,
            }

    except IntegrityError:

        return {
            "success": False,
            "error": {
                "code": "PROPOSAL_ALREADY_USED",
                "message": (
                    "This CRM action proposal has already "
                    "been submitted and cannot be "
                    "executed again."
                ),
            },
        }