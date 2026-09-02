from django.shortcuts import render
from django.views.decorators.http import (
    require_GET,
    require_POST,
)
from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.contrib.auth.decorators import login_required

from apps.ai.agent.read_agent import (
    run_crm_read_agent_with_provider,
)
from apps.ai.agent.proposal_tokens import (
    load_action_proposal,
    sign_action_proposal,
)
from apps.ai.agent.write_proposals import (
    build_create_lead_task_proposal,
    build_write_proposal_from_message,
)
from apps.ai.agent.write_executor import (
    execute_confirmed_proposal,
)
from apps.ai.agent.outreach_agent import (
    draft_lead_outreach,
)
from apps.ai import audit_services


@login_required
@require_GET
def crm_assistant(request):
    """
    Render the CRM Read Assistant page.

    No CRM business logic belongs in this view.
    """

    return render(
        request,
        "ai/crm_assistant.html",
    )


@login_required
@require_POST
def crm_assistant_ask(request):
    """
    Handle one CRM Assistant request.

    Supported controlled write requests may prepare a
    proposal, but this endpoint never executes a CRM write.
    """

    message = request.POST.get(
        "message",
        "",
    ).strip()

    if not message:
        result = {
            "success": False,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": "Please enter a CRM question.",
            },
        }

        return render(
            request,
            "ai/partials/crm_assistant_response.html",
            {
                "result": result,
            },
        )

    #
    # -----------------------------------------------------
    # CONTROLLED WRITE PROPOSAL
    # -----------------------------------------------------
    #
    # Try the deterministic write-proposal parser first.
    #
    # A successful result creates only a proposal.
    # No CRM write is executed here.
    #

    proposal_result = (
        build_write_proposal_from_message(
            message
        )
    )

    if proposal_result.get("success"):

        proposal = proposal_result[
            "proposal"
        ]

        proposal_token = (
            sign_action_proposal(
                proposal
            )
        )

        return render(
            request,
            "ai/partials/create_task_proposal.html",
            {
                "result": {
                    "success": True,
                    "proposal": proposal,
                },
                "proposal_token": proposal_token,
                "user_message": message,
            },
        )

    proposal_error_code = (
        proposal_result
        .get("error", {})
        .get("code")
    )

    #
    # If the sentence WAS recognized as a supported
    # write proposal but proposal validation failed
    # (for example, lead not found), show that error.
    #
    # Only UNSUPPORTED_WRITE_PROPOSAL_INTENT falls
    # through to the existing read agent.
    #

    if (
        proposal_error_code
        != "UNSUPPORTED_WRITE_PROPOSAL_INTENT"
    ):
        return render(
            request,
            "ai/partials/create_task_proposal.html",
            {
                "result": proposal_result,
                "user_message": message,
            },
        )

    #
    # -----------------------------------------------------
    # EXISTING READ AGENT
    # -----------------------------------------------------
    #

    result = run_crm_read_agent_with_provider(
        message=message,
    )

    return render(
        request,
        "ai/partials/crm_assistant_response.html",
        {
            "result": result,
            "user_message": message,
        },
    )


@login_required
@require_POST
def crm_assistant_task_proposal(request):
    """
    Prepare one follow-up task proposal.

    IMPORTANT:
    This endpoint performs no CRM write.
    """

    raw_lead_id = request.POST.get(
        "lead_id",
        "",
    ).strip()

    title = request.POST.get(
        "title",
        "",
    ).strip()

    description = request.POST.get(
        "description",
        "",
    )

    priority = request.POST.get(
        "priority",
        "medium",
    ).strip()

    due_date = request.POST.get(
        "due_date",
        "",
    ).strip()

    try:
        lead_id = int(
            raw_lead_id,
        )
    except (TypeError, ValueError):
        lead_id = None

    result = build_create_lead_task_proposal(
        lead_id=lead_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date or None,
    )

    context = {
        "result": result,
    }

    if result.get("success"):
        context["proposal_token"] = (
            sign_action_proposal(
                result["proposal"],
            )
        )

    return render(
        request,
        "ai/partials/create_task_proposal.html",
        context,
    )


@login_required
@require_POST
def crm_assistant_task_confirm(request):
    """
    Confirm and execute one signed CRM action proposal.

    The request is not trusted to provide task fields.
    Only the verified signed proposal token may determine
    what CRM mutation is performed.
    """

    proposal_token = request.POST.get(
        "proposal_token",
        "",
    ).strip()

    if not proposal_token:
        result = {
            "success": False,
            "error": {
                "code": "MISSING_PROPOSAL_TOKEN",
                "message": (
                    "A signed CRM action proposal "
                    "is required."
                ),
            },
        }

        return render(
            request,
            "ai/partials/create_task_result.html",
            {
                "result": result,
            },
        )

    loaded = load_action_proposal(
        proposal_token,
    )

    if not loaded.get("success"):
        return render(
            request,
            "ai/partials/create_task_result.html",
            {
                "result": loaded,
            },
        )

    result = execute_confirmed_proposal(
        proposal=loaded["proposal"],
        confirmed=True,
    )

    return render(
        request,
        "ai/partials/create_task_result.html",
        {
            "result": result,
        },
    )


@login_required
@require_POST
def lead_outreach_draft(request, lead_id):
    """
    Draft a first-contact message for one CRM lead.

    Read + generate only. This endpoint never writes to the CRM
    and never contacts the lead - it returns editable draft text.
    """

    tone = request.POST.get(
        "tone",
        "",
    ).strip() or None

    result = draft_lead_outreach(
        lead_id=lead_id,
        tone=tone,
    )

    return render(
        request,
        "ai/partials/lead_outreach_draft.html",
        {
            "result": result,
        },
    )


@staff_member_required
@require_GET
def crm_action_audit(request):
    """
    Staff-only visibility into confirmed
    AI-assisted CRM actions.
    """

    audits = (
        audit_services.get_recent_action_audits(
            limit=50,
        )
    )

    return render(
        request,
        "ai/crm_action_audit.html",
        {
            "audits": audits,
        },
    )