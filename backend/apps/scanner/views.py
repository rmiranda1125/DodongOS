"""
Staff-only lead scanner UI.

Read-only review queue + explicit import/reject actions. These
views contain no ORM and no CRM logic - everything goes through
apps/scanner/services.py, which delegates CRM creation to
apps/leads/services.py.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from apps.scanner import services as scanner_services


@staff_member_required
@require_GET
def review_queue(request):
    status = request.GET.get("status") or None
    source = request.GET.get("source") or None
    min_score = request.GET.get("min_score") or None

    candidates = scanner_services.list_candidates(
        status=status,
        source=source,
        min_score=min_score,
    )

    return render(
        request,
        "scanner/review_queue.html",
        {
            "candidates": candidates,
            "sources": scanner_services.candidate_sources(),
            "selected_status": status,
            "selected_source": source,
            "selected_min_score": min_score,
            "status_choices": [
                "new",
                "reviewed",
                "approved",
                "rejected",
                "imported",
            ],
        },
    )


@staff_member_required
@require_GET
def candidate_detail(request, candidate_id):
    candidate = scanner_services.get_candidate(candidate_id=candidate_id)
    if candidate is None:
        return render(
            request,
            "scanner/candidate_detail.html",
            {"candidate": None},
            status=404,
        )

    preview = scanner_services.preview_import(candidate_id=candidate_id)

    return render(
        request,
        "scanner/candidate_detail.html",
        {"candidate": candidate, "preview": preview},
    )


@staff_member_required
@require_POST
def import_candidate(request, candidate_id):
    result = scanner_services.import_candidate(
        candidate_id=candidate_id,
        user=request.user,
    )
    if result.get("success"):
        messages.success(
            request,
            f"Imported as CRM lead #{result['lead_id']}.",
        )
    else:
        code = result.get("error", {}).get("code", "IMPORT_FAILED")
        messages.warning(request, f"Not imported: {code}.")
    return redirect("scanner:candidate_detail", candidate_id=candidate_id)


@staff_member_required
@require_POST
def reject_candidate(request, candidate_id):
    scanner_services.reject_candidate(
        candidate_id=candidate_id,
        reason=request.POST.get("reason", ""),
    )
    messages.success(request, "Candidate rejected.")
    return redirect("scanner:candidate_detail", candidate_id=candidate_id)


@staff_member_required
@require_POST
def mark_reviewed(request, candidate_id):
    scanner_services.set_candidate_status(
        candidate_id=candidate_id,
        status="reviewed",
    )
    return redirect("scanner:candidate_detail", candidate_id=candidate_id)


@staff_member_required
@require_http_methods(["GET", "POST"])
def upload_csv(request):
    """
    Staff-only: upload a lead CSV (e.g. produced by a Claude
    routine) and run it through the csv source adapter.

    Discovery only - this never creates a CRM lead. Candidates land
    in the review queue for explicit import.
    """

    context = {"max_kb": settings.SCANNER_CSV_MAX_BYTES // 1000}

    if request.method == "GET":
        return render(request, "scanner/upload.html", context)

    upload = request.FILES.get("csv_file")

    if upload is None:
        context["error"] = "Choose a .csv file to upload."
        return render(request, "scanner/upload.html", context)

    if upload.size > settings.SCANNER_CSV_MAX_BYTES:
        context["error"] = (
            f"File is too large (max {context['max_kb']} KB)."
        )
        return render(request, "scanner/upload.html", context)

    try:
        content = upload.read().decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError):
        context["error"] = (
            "That file is not valid UTF-8 text. Export it as a "
            "plain CSV and try again."
        )
        return render(request, "scanner/upload.html", context)

    run = scanner_services.run_scan(
        source="csv",
        config={"content": content},
    )

    context["result"] = run
    if run.status == "failed":
        messages.warning(
            request, f"Upload scan failed: {run.error_message}"
        )
    else:
        messages.success(
            request,
            f"Scanned {run.candidates_seen} row(s): "
            f"{run.candidates_created} new, "
            f"{run.candidates_updated} updated, "
            f"{run.rows_rejected} rejected.",
        )
    return render(request, "scanner/upload.html", context)


@staff_member_required
@require_GET
def scan_runs(request):
    return render(
        request,
        "scanner/scan_runs.html",
        {"runs": scanner_services.list_scan_runs()},
    )


@staff_member_required
@require_GET
def export_csv(request):
    content = scanner_services.export_candidates_csv(
        status=request.GET.get("status") or None,
        source=request.GET.get("source") or None,
    )
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="lead_candidates.csv"'
    )
    return response
