from apps.ai.models import AIActionAudit


def create_action_audit(
    *,
    proposal_id,
    action,
    lead_id,
    proposal_data,
):
    """
    Reserve one proposal ID and create its audit record.

    The unique proposal_id provides replay protection.
    """

    return AIActionAudit.objects.create(
        proposal_id=proposal_id,
        action=action,
        status="failed",
        lead_id=lead_id,
        proposal_data=proposal_data,
    )


def mark_action_audit_failed(
    *,
    audit,
    error_code,
):
    audit.status = "failed"
    audit.error_code = error_code

    audit.save(
        update_fields=[
            "status",
            "error_code",
        ]
    )

    return audit


def mark_action_audit_executed(
    *,
    audit,
    result_task_id,
):
    audit.status = "executed"
    audit.result_task_id = result_task_id
    audit.error_code = ""

    audit.save(
        update_fields=[
            "status",
            "result_task_id",
            "error_code",
        ]
    )

    return audit

def get_recent_action_audits(
    *,
    limit=50,
):
    """
    Return recent AI CRM action audits as
    JSON-safe dictionaries.
    """

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        limit = 50

    audits = (
        AIActionAudit.objects
        .order_by("-confirmed_at")[:limit]
    )

    return [
        {
            "id": audit.id,
            "proposal_id": str(
                audit.proposal_id
            ),
            "action": audit.action,
            "status": audit.status,
            "lead_id": audit.lead_id,
            "result_task_id": (
                audit.result_task_id
            ),
            "error_code": audit.error_code,
            "proposal_data": (
                audit.proposal_data
            ),
            "confirmed_at": (
                audit.confirmed_at
            ),
        }
        for audit in audits
    ]