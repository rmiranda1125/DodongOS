from django.contrib.admin.views.decorators import (
    staff_member_required,
)
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.automation import services as automation_services


@staff_member_required
@require_GET
def automation_run_history(request):
    """
    Staff-only, read-only history of background CRM check runs.

    Shows deterministic run outcome plus the optional AI summary
    outcome (status / source / text / error). Data is read through
    the automation service layer, not the ORM directly.
    """

    runs = automation_services.get_recent_check_runs(
        limit=50,
    )

    return render(
        request,
        "automation/run_history.html",
        {
            "runs": runs,
        },
    )
