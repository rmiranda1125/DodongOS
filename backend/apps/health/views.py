"""
Production liveness / readiness endpoints.

These are deliberately cheap and side-effect-free:

- They never call OpenAI, Ollama, the RAG provider, or any external
  API.
- They never mutate data.
- They return minimal JSON and expose no secrets, stack traces, or
  configuration.
"""

from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(request):
    """
    Liveness: the process is up and can serve a request. No
    dependencies are checked. Reports the canonical release
    version (not environment or config).
    """

    return JsonResponse(
        {"status": "ok", "version": settings.DODONG_VERSION}
    )


@require_GET
def readiness(request):
    """
    Readiness: the app can reach its required dependencies.

    Currently just the default database (a trivial ``SELECT 1``).
    On failure, return 503 with a generic reason - never the
    exception text.
    """

    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse(
            {"status": "unavailable", "checks": {"database": "fail"}},
            status=503,
        )

    return JsonResponse(
        {"status": "ok", "checks": {"database": "ok"}}
    )
