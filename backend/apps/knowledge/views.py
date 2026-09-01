from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.ai.agent.rag_agent import run_rag_agent
from apps.knowledge import services as knowledge_services


@staff_member_required
@require_GET
def knowledge_assistant(request):
    """
    Staff-only knowledge assistant page (RAG query UI).
    """

    documents = knowledge_services.get_documents(limit=100)

    return render(
        request,
        "knowledge/assistant.html",
        {
            "documents": documents,
        },
    )


@staff_member_required
@require_POST
def knowledge_assistant_ask(request):
    """
    Run one grounded RAG query and render the result partial.

    Read-only: no CRM mutation, no write tools, no confirmed-write
    execution.
    """

    question = request.POST.get("question", "").strip()

    if not question:
        return render(
            request,
            "knowledge/partials/answer.html",
            {
                "result": {
                    "success": False,
                    "error": {
                        "code": "INVALID_QUESTION",
                        "message": "Please enter a question.",
                    },
                },
                "question": question,
            },
        )

    result = run_rag_agent(question=question)

    return render(
        request,
        "knowledge/partials/answer.html",
        {
            "result": result,
            "question": question,
        },
    )
