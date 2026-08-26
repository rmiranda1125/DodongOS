from django.shortcuts import render
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from apps.ai.agent.read_agent import (
    run_crm_read_agent_with_provider,
)
from apps.ai.agent.proposal_tokens import (
    load_action_proposal,
    sign_action_proposal,
)
from apps.ai.agent.write_proposals import (
    build_create_lead_task_proposal,
)
from apps.ai.agent.write_executor import (
    execute_confirmed_proposal,
)
from django.contrib.admin.views.decorators import (
    staff_member_required,
)

from apps.ai import audit_services

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


@require_POST
def crm_assistant_ask(request):
    """
    Handle one CRM Read Agent question.

    The view delegates all routing, tool execution, and
    provider behavior to the CRM Read Agent.
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