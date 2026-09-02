import json

from apps.ai.providers.factory import AIProviderFactory


def build_crm_read_response_prompt(
    *,
    user_message,
    tool_used,
    data,
):
    """
    Build a prompt using CRM data that has already been
    retrieved through the controlled read-only tool registry.

    The provider must summarize the supplied data only.
    """

    crm_data = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return f"""
You are Dodong OS CRM Read Assistant.

The CRM data below has already been retrieved through an
authorized read-only CRM tool.

You MUST follow these rules:

1. Answer using only the supplied CRM data.
2. Do not invent leads, tasks, dates, statuses, or actions.
3. Do not claim that you changed any CRM data.
4. Do not claim that you contacted anyone.
5. Do not claim that you completed a task.
6. If the CRM data is empty, clearly say that no matching
   CRM records were found.
7. Keep the answer concise and practical.
8. Do not expose internal tool implementation details unless
   they are needed to explain an error.

User question:
{user_message}

Verified CRM tool:
{tool_used}

Verified CRM data:
{crm_data}

Answer the user's question using only the verified CRM data.
""".strip()


def generate_crm_read_response(
    *,
    user_message,
    tool_used,
    data,
    provider=None,
):
    """
    Generate a natural-language response from verified CRM data.

    No ORM access and no tool execution happens here.
    """

    if provider is None:
        provider = AIProviderFactory.create()

    prompt = build_crm_read_response_prompt(
        user_message=user_message,
        tool_used=tool_used,
        data=data,
    )

    response = provider.analyze(
        prompt,
    )

    if not isinstance(response, str):
        raise ValueError(
            "AI provider response must be a string."
        )

    response = response.strip()

    if not response:
        raise ValueError(
            "AI provider returned an empty response."
        )

    return response