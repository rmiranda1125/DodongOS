from django.shortcuts import render
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from apps.ai.agent.read_agent import (
    run_crm_read_agent_with_provider,
)


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