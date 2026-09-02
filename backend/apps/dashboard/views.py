from django.conf import settings
from django.shortcuts import render
from django.utils import timezone

from apps.leads import services as lead_services


def _greeting(now):
    hour = now.hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def home(request):
    """
    v1 operations landing page.

    Only reads through existing, cheap CRM/automation/scanner
    services. Staff see summary + "needs attention" tiles; other
    users see navigation cards.
    """

    context = {"greeting": _greeting(timezone.now())}

    if request.user.is_staff:
        try:
            summary = lead_services.get_pipeline_summary()
        except Exception:
            summary = {}

        overdue = list(lead_services.get_overdue_tasks())
        pending = list(lead_services.get_pending_tasks())

        high_priority_candidates = []
        latest_run = None
        try:
            from apps.scanner import services as scanner_services

            high_priority_candidates = scanner_services.list_candidates(
                status="new",
                min_score=settings.SCANNER_SCORE_HIGH,
                limit=50,
            )
        except Exception:
            high_priority_candidates = []
        try:
            from apps.automation import services as automation_services

            recent = automation_services.get_recent_check_runs(limit=1)
            latest_run = recent[0] if recent else None
        except Exception:
            latest_run = None

        context.update(
            {
                "total_leads": summary.get("total_leads", 0),
                "pending_task_count": len(pending),
                "overdue_task_count": len(overdue),
                "overdue_tasks": overdue[:5],
                "high_priority_candidate_count": len(
                    high_priority_candidates
                ),
                "high_priority_candidates": high_priority_candidates[:5],
                "latest_run": latest_run,
            }
        )

    return render(request, "dashboard/home.html", context)


def hello_htmx(request):
    return render(request, "dashboard/partials/hello.html")


def server_time(request):
    return render(
        request,
        "dashboard/partials/server_time.html",
        {"current_time": timezone.now()},
    )
