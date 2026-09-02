"""
Scanner service layer.

This module (with models.py) is the ONLY place allowed to touch
the scanner ORM. Adapters / normalization / dedup / scoring /
analysis / views / the management command all go through here.

CRM mutation is delegated to apps/leads/services.py - this module
never calls ``Lead.objects.*``.
"""

import csv as _csv
import io

from django.db import transaction
from django.utils import timezone

from apps.leads import services as lead_services
from apps.scanner import (
    adapters,
    analysis,
    dedup,
    job_url_scanner,
    normalization,
    scoring,
)
from apps.scanner.models import LeadCandidate, LeadScanRun


class ScannerImportError(Exception):
    """Raised when a candidate cannot be imported into the CRM."""


# =========================================================
# SCAN RUN
# =========================================================

def _record_run_started(*, source):
    return LeadScanRun.objects.create(source=source, status="running")


def _finish_run(*, run, status, **fields):
    run.status = status
    run.finished_at = timezone.now()
    for key, value in fields.items():
        setattr(run, key, value)
    run.save()
    return run


def upsert_candidate(
    *, raw, run=None, with_ai=False, now=None, default_status="new"
):
    """
    Normalize, dedup, score and persist one raw candidate.

    Returns ("created" | "updated", LeadCandidate). Rediscovering an
    existing candidate updates its data and re-scores it but never
    changes its review/import ``status``. ``default_status`` only
    applies to a freshly created candidate.
    """

    now = now or timezone.now()
    normalized = normalization.normalize_candidate(raw)
    key = dedup.build_dedup_key(normalized)

    score_input = dict(normalized)
    score_input["discovered_at"] = now
    score_result = scoring.score_candidate(score_input, now=now)
    qualification = scoring.qualification_for(score_result["score"])

    ai_note = ""
    if with_ai:
        ai_note = analysis.explain_candidate(
            normalized=normalized, score_result=score_result
        )

    with transaction.atomic():
        existing = (
            LeadCandidate.objects.select_for_update()
            .filter(dedup_key=key)
            .first()
        )
        if existing is None:
            candidate = LeadCandidate.objects.create(
                source=normalized["source"],
                source_identifier=normalized["source_identifier"],
                source_url=normalized["source_url"],
                company_name=normalized["company_name"] or "Unknown",
                contact_name=normalized["contact_name"],
                opportunity_title=normalized["opportunity_title"],
                description=normalized["description"],
                location=normalized["location"],
                work_arrangement=normalized["work_arrangement"],
                compensation_text=normalized["compensation_text"],
                raw_data=raw,
                normalized_data=normalized,
                dedup_key=key,
                score=score_result["score"],
                score_components=score_result["components"],
                score_reasons=score_result["reasons"],
                skills_analysis=score_result.get("skills", {}),
                qualification=qualification,
                ai_note=ai_note,
                status=default_status,
            )
            return "created", candidate

        # Rediscovered: refresh safe fields, keep review state.
        existing.source_url = (
            normalized["source_url"] or existing.source_url
        )
        existing.contact_name = (
            normalized["contact_name"] or existing.contact_name
        )
        existing.opportunity_title = (
            normalized["opportunity_title"]
            or existing.opportunity_title
        )
        existing.description = (
            normalized["description"] or existing.description
        )
        existing.location = normalized["location"] or existing.location
        existing.work_arrangement = (
            normalized["work_arrangement"] or existing.work_arrangement
        )
        existing.compensation_text = (
            normalized["compensation_text"]
            or existing.compensation_text
        )
        existing.raw_data = raw
        existing.normalized_data = normalized
        existing.score = score_result["score"]
        existing.score_components = score_result["components"]
        existing.score_reasons = score_result["reasons"]
        existing.skills_analysis = score_result.get("skills", {})
        existing.qualification = qualification
        if ai_note:
            existing.ai_note = ai_note
        existing.times_seen = existing.times_seen + 1
        existing.last_seen_at = now
        existing.save()
        return "updated", existing


def run_scan(*, source, config=None, with_ai=False, now=None):
    """
    Execute one scan for ``source``. Records a LeadScanRun, upserts
    candidates, and NEVER imports anything into the CRM. A source
    failure is captured on the run (status="failed"); rows that
    cannot be read are reported individually without aborting the
    run.
    """

    config = dict(config or {})
    config.setdefault("source", source)
    run = _record_run_started(source=source)

    try:
        adapter = adapters.get_adapter(source)
        raw_items = adapter.scan(config)
    except adapters.SourceAdapterError as exc:
        _finish_run(run=run, status="failed", error_message=str(exc))
        return run
    except Exception as exc:  # pragma: no cover - defensive
        _finish_run(
            run=run,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )
        return run

    created = updated = rejected = 0
    row_errors = []

    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict) or not (
            raw.get("company_name") or raw.get("company")
        ):
            rejected += 1
            row_errors.append(
                {"row": index, "error": "missing company_name"}
            )
            continue
        try:
            outcome, _candidate = upsert_candidate(
                raw=raw, run=run, with_ai=with_ai, now=now
            )
        except Exception as exc:  # pragma: no cover - defensive
            rejected += 1
            row_errors.append(
                {"row": index, "error": f"{type(exc).__name__}: {exc}"}
            )
            continue
        if outcome == "created":
            created += 1
        else:
            updated += 1

    _finish_run(
        run=run,
        status="succeeded",
        candidates_seen=len(raw_items),
        candidates_created=created,
        candidates_updated=updated,
        rows_rejected=rejected,
        row_errors=row_errors,
    )
    return run


# =========================================================
# JOB URL SCAN (paste-a-link, single opportunity)
# =========================================================

def scan_job_url(*, url, with_ai=False, now=None, fetch=None, provider=None):
    """
    Scan one public job-posting URL and upsert it as a candidate.

    Records a LeadScanRun (source="job_url"). NEVER creates a CRM
    lead - a new candidate starts in the ``discovered`` state and
    still requires an explicit staff import.

    Returns on success:
        {"success": True, "created": bool, "candidate_id": int,
         "company_name": str, "opportunity_title": str, "score": int,
         "qualification": str, "run_id": int}
    Returns on failure (no exception is raised to the caller):
        {"success": False, "error": {"code": str, "message": str},
         "run_id": int}
    """

    now = now or timezone.now()
    run = _record_run_started(source="job_url")

    try:
        raw = job_url_scanner.scan_job_url(
            url, fetch=fetch, provider=provider
        )
    except job_url_scanner.JobUrlError as exc:
        _finish_run(
            run=run,
            status="failed",
            error_message=f"{exc.code}: {exc.user_message}",
        )
        return {
            "success": False,
            "error": {"code": exc.code, "message": exc.user_message},
            "run_id": run.id,
        }
    except Exception as exc:  # pragma: no cover - defensive
        _finish_run(
            run=run,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )
        return {
            "success": False,
            "error": {
                "code": "SCAN_ERROR",
                "message": (
                    "Unable to scan this job posting right now."
                ),
            },
            "run_id": run.id,
        }

    outcome, candidate = upsert_candidate(
        raw=raw,
        run=run,
        with_ai=with_ai,
        now=now,
        default_status="discovered",
    )

    _finish_run(
        run=run,
        status="succeeded",
        candidates_seen=1,
        candidates_created=1 if outcome == "created" else 0,
        candidates_updated=1 if outcome == "updated" else 0,
    )

    return {
        "success": True,
        "created": outcome == "created",
        "candidate_id": candidate.id,
        "company_name": candidate.company_name,
        "opportunity_title": candidate.opportunity_title,
        "score": candidate.score,
        "qualification": candidate.qualification,
        "run_id": run.id,
    }


# =========================================================
# REVIEW QUEUE READ HELPERS
# =========================================================

def list_candidates(*, status=None, source=None, min_score=None, limit=200):
    qs = LeadCandidate.objects.all()
    if status:
        qs = qs.filter(status=status)
    if source:
        qs = qs.filter(source=source)
    if min_score is not None:
        qs = qs.filter(score__gte=int(min_score))
    return list(qs[: max(1, int(limit))])


def get_candidate(*, candidate_id):
    return LeadCandidate.objects.filter(id=candidate_id).first()


def list_scan_runs(*, limit=50):
    return list(LeadScanRun.objects.all()[: max(1, int(limit))])


def candidate_sources():
    return sorted(
        LeadCandidate.objects.values_list(
            "source", flat=True
        ).distinct()
    )


# =========================================================
# CRM IMPORT MAPPING + ACTIONS
# =========================================================

def build_import_mapping(candidate):
    """Deterministic candidate -> CRM Lead field mapping (preview)."""

    return {
        "company_name": candidate.company_name,
        "job_title": candidate.opportunity_title,
        "source_platform": candidate.source,
        "source_url": candidate.source_url,
        "location": candidate.location,
        "work_setup": candidate.work_arrangement,
        "salary": candidate.compensation_text,
        "lead_score": candidate.score,
        "status": "new",
    }


def _context_note(candidate):
    lines = [
        "Imported from the Dodong lead scanner.",
        f"Source: {candidate.source}",
    ]
    if candidate.source_url:
        lines.append(f"Source link: {candidate.source_url}")
    if candidate.contact_name:
        lines.append(f"Contact: {candidate.contact_name}")
    lines.append(
        f"Scanner score: {candidate.score}/100 ({candidate.qualification})"
    )
    if candidate.score_reasons:
        lines.append("Why it matched: " + "; ".join(candidate.score_reasons))
    if candidate.ai_note:
        lines.append(f"AI note: {candidate.ai_note}")
    if candidate.description:
        lines.append("")
        lines.append("Original opportunity:")
        lines.append(candidate.description)
    return "\n".join(lines)


def preview_import(*, candidate_id):
    candidate = get_candidate(candidate_id=candidate_id)
    if candidate is None:
        return {"success": False, "error": {"code": "CANDIDATE_NOT_FOUND"}}
    if candidate.status == "imported":
        return {
            "success": False,
            "error": {"code": "ALREADY_IMPORTED"},
            "imported_lead_id": candidate.imported_lead_id,
        }
    duplicate = lead_services.find_duplicate_lead(
        company_name=candidate.company_name,
        source_url=candidate.source_url,
    )
    return {
        "success": True,
        "mapping": build_import_mapping(candidate),
        "duplicate_lead_id": duplicate.id if duplicate else None,
    }


def import_candidate(*, candidate_id, user=None):
    """
    Explicit staff import of one candidate into the CRM. Idempotent
    per candidate: a second call after success returns
    ALREADY_IMPORTED without creating another Lead.
    """

    with transaction.atomic():
        candidate = (
            LeadCandidate.objects.select_for_update()
            .filter(id=candidate_id)
            .first()
        )
        if candidate is None:
            raise ScannerImportError("CANDIDATE_NOT_FOUND")
        if candidate.status == "imported":
            return {
                "success": False,
                "error": {"code": "ALREADY_IMPORTED"},
                "imported_lead_id": candidate.imported_lead_id,
            }
        if not candidate.company_name.strip():
            raise ScannerImportError("MISSING_COMPANY_NAME")

        duplicate = lead_services.find_duplicate_lead(
            company_name=candidate.company_name,
            source_url=candidate.source_url,
        )
        if duplicate is not None:
            return {
                "success": False,
                "error": {"code": "CRM_DUPLICATE"},
                "duplicate_lead_id": duplicate.id,
            }

        lead = lead_services.import_scanner_candidate(
            mapping=build_import_mapping(candidate),
            context_note=_context_note(candidate),
        )

        candidate.status = "imported"
        candidate.imported_lead_id = lead.id
        candidate.imported_at = timezone.now()
        candidate.imported_by = (
            getattr(user, "get_username", lambda: "")() or ""
        )
        candidate.save(
            update_fields=[
                "status",
                "imported_lead_id",
                "imported_at",
                "imported_by",
                "updated_at",
            ]
        )

    return {"success": True, "lead_id": lead.id}


def reject_candidate(*, candidate_id, reason=""):
    candidate = get_candidate(candidate_id=candidate_id)
    if candidate is None:
        raise ScannerImportError("CANDIDATE_NOT_FOUND")
    if candidate.status == "imported":
        return {"success": False, "error": {"code": "ALREADY_IMPORTED"}}
    candidate.status = "rejected"
    candidate.rejection_reason = (reason or "").strip()[:255]
    candidate.save(
        update_fields=["status", "rejection_reason", "updated_at"]
    )
    return {"success": True}


def set_candidate_status(*, candidate_id, status):
    if status not in {"new", "reviewed"}:
        raise ScannerImportError("INVALID_STATUS")
    candidate = get_candidate(candidate_id=candidate_id)
    if candidate is None:
        raise ScannerImportError("CANDIDATE_NOT_FOUND")
    if candidate.status == "imported":
        return {"success": False, "error": {"code": "ALREADY_IMPORTED"}}
    candidate.status = status
    candidate.save(update_fields=["status", "updated_at"])
    return {"success": True}


# =========================================================
# CSV EXPORT (read-only)
# =========================================================

EXPORT_COLUMNS = [
    "id",
    "company_name",
    "contact_name",
    "opportunity_title",
    "source",
    "source_url",
    "location",
    "work_arrangement",
    "compensation_text",
    "score",
    "qualification",
    "status",
    "why_it_matched",
    "discovered_at",
]


def export_candidates_csv(*, status=None, source=None):
    """Return a CSV string of scored candidates. Mutates nothing."""

    buffer = io.StringIO()
    writer = _csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for candidate in list_candidates(
        status=status, source=source, limit=5000
    ):
        writer.writerow(
            [
                candidate.id,
                candidate.company_name,
                candidate.contact_name,
                candidate.opportunity_title,
                candidate.source,
                candidate.source_url,
                candidate.location,
                candidate.work_arrangement,
                candidate.compensation_text,
                candidate.score,
                candidate.qualification,
                candidate.status,
                "; ".join(candidate.score_reasons or []),
                candidate.discovered_at.isoformat(),
            ]
        )
    return buffer.getvalue()
