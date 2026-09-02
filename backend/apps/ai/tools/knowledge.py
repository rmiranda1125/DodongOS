from apps.knowledge import services as knowledge_services


def search_knowledge_tool(*, query, limit=5):
    """
    Read-only knowledge tool.

    Returns deterministic evidence chunks from the active knowledge
    store, ranked by lexical relevance. No AI provider is invoked
    and no data is mutated.

    This function must never query Django models directly - it goes
    through apps/knowledge/services.py.
    """

    if not isinstance(query, str) or not query.strip():
        return {
            "success": False,
            "error": {
                "code": "INVALID_QUERY",
                "message": "A non-empty query is required.",
            },
        }

    if not isinstance(limit, int) or isinstance(limit, bool):
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be an integer.",
            },
        }

    if limit < 1 or limit > 20:
        return {
            "success": False,
            "error": {
                "code": "INVALID_LIMIT",
                "message": "limit must be between 1 and 20.",
            },
        }

    result = knowledge_services.retrieve_knowledge(
        query=query,
        limit=limit,
    )

    if not result.get("success"):
        return result

    return {
        "success": True,
        "data": result["evidence"],
    }
