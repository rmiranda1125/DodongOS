from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.automation.models import CRMDigest, ScheduledCheckRun


STALE_RUN_RECOVERED = "STALE_RUN_RECOVERED"


class OverlappingRunError(Exception):
    """
    Raised when a non-stale ``running`` ScheduledCheckRun already
    exists, so a new run must not start.
    """

    def __init__(self, *, active_run_id):
        self.active_run_id = active_run_id
        super().__init__(
            f"another check run (#{active_run_id}) is already "
            "running"
        )


def _stale_cutoff(*, now, stale_after_minutes):
    if stale_after_minutes is None:
        stale_after_minutes = (
            settings.CRM_AUTOMATION_STALE_RUN_MINUTES
        )

    return now - timedelta(minutes=stale_after_minutes)


def start_check_run(*, now=None, stale_after_minutes=None):
    """
    Create and return one new, in-progress check run record.

    Overlapping-run protection (Phase 6E2):

    - A ``running`` record older than the stale threshold is assumed
      to be a crashed process: it is finalized as ``failed`` with
      error ``STALE_RUN_RECOVERED`` (history is never deleted), and
      the new run is then allowed to start.
    - A ``running`` record younger than the stale threshold blocks
      the new run: ``OverlappingRunError`` is raised and no new
      record, CRM read, or digest write happens.

    This is the only place allowed to create a ScheduledCheckRun.
    """

    if now is None:
        now = timezone.now()

    cutoff = _stale_cutoff(
        now=now,
        stale_after_minutes=stale_after_minutes,
    )

    with transaction.atomic():

        running = list(
            ScheduledCheckRun.objects
            .select_for_update()
            .filter(status="running")
        )

        for record in running:

            if record.started_at <= cutoff:
                record.status = "failed"
                record.finished_at = now
                record.error_message = STALE_RUN_RECOVERED
                record.save(
                    update_fields=[
                        "status",
                        "finished_at",
                        "error_message",
                    ],
                )

        active = [
            record
            for record in running
            if record.started_at > cutoff
        ]

        if active:
            raise OverlappingRunError(
                active_run_id=active[0].id,
            )

        return ScheduledCheckRun.objects.create(
            status="running",
        )


def finish_check_run_succeeded(
    *,
    run,
    checks_run,
    findings_count,
):
    """
    Finalize one check run as succeeded.
    """

    run.status = "succeeded"
    run.checks_run = checks_run
    run.findings_count = findings_count
    run.finished_at = timezone.now()

    run.save(
        update_fields=[
            "status",
            "checks_run",
            "findings_count",
            "finished_at",
        ],
    )

    return run


def finish_check_run_failed(
    *,
    run,
    error_message,
):
    """
    Finalize one check run as failed.
    """

    run.status = "failed"
    run.error_message = error_message or ""
    run.finished_at = timezone.now()

    run.save(
        update_fields=[
            "status",
            "error_message",
            "finished_at",
        ],
    )

    return run


def record_run_summary(
    *,
    run,
    summary_result,
):
    """
    Persist the optional AI summary outcome on a check run.

    ``summary_result`` is the dict returned by
    apps/automation/summary.summarize_digest(). Only the
    observational fields are stored (status, source, text,
    error) - never the prompt payload or provider internals.

    This must only be called for a run whose deterministic
    checks and digest persistence succeeded.
    """

    run.summary_status = summary_result.get("status", "") or ""
    run.summary_source = summary_result.get("source", "") or ""
    run.summary_text = summary_result.get("summary", "") or ""
    run.summary_error = summary_result.get("error") or ""

    run.save(
        update_fields=[
            "summary_status",
            "summary_source",
            "summary_text",
            "summary_error",
        ],
    )

    return run


def get_recent_check_runs(
    *,
    limit=50,
):
    """
    Return recent check runs as JSON-safe dicts, newest first.
    """

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        limit = 50

    runs = ScheduledCheckRun.objects.all()[:limit]

    return [
        {
            "id": run.id,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "status": run.status,
            "checks_run": run.checks_run,
            "findings_count": run.findings_count,
            "error_message": run.error_message,
            "summary_status": run.summary_status,
            "summary_source": run.summary_source,
            "summary_text": run.summary_text,
            "summary_error": run.summary_error,
        }
        for run in runs
    ]


# =========================================================
# CRM DIGEST PERSISTENCE
# =========================================================


def _upsert_digest_finding(*, digest_finding, seen_at):
    """
    Create or update one CRMDigest row for a shaped digest finding.

    A shaped digest finding is a dict with keys:
    dedup_key, finding_type, lead_id, task_id, summary, finding_data.
    """

    existing = CRMDigest.objects.filter(
        dedup_key=digest_finding["dedup_key"],
    ).first()

    if existing is None:
        return CRMDigest.objects.create(
            dedup_key=digest_finding["dedup_key"],
            finding_type=digest_finding["finding_type"],
            lead_id=digest_finding.get("lead_id"),
            task_id=digest_finding.get("task_id"),
            summary=digest_finding["summary"],
            finding_data=digest_finding["finding_data"],
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            resolved_at=None,
            occurrence_count=1,
        )

    # Existing identity seen again: refresh the mutable fields,
    # keep first_seen_at, reopen if it had been resolved.
    existing.summary = digest_finding["summary"]
    existing.finding_data = digest_finding["finding_data"]
    existing.lead_id = digest_finding.get("lead_id")
    existing.task_id = digest_finding.get("task_id")
    existing.last_seen_at = seen_at
    existing.resolved_at = None
    existing.occurrence_count = existing.occurrence_count + 1

    existing.save(
        update_fields=[
            "summary",
            "finding_data",
            "lead_id",
            "task_id",
            "last_seen_at",
            "resolved_at",
            "occurrence_count",
            "updated_at",
        ],
    )

    return existing


def sync_digest_findings(
    *,
    digest_findings,
    seen_at=None,
):
    """
    Persist every shaped digest finding and resolve any previously
    active CRMDigest row that is absent from this set.

    Callers MUST only invoke this after a fully successful check
    run. A failed or partial run must never reach here, so that
    absent findings are never mistaken for resolved conditions.

    Returns:
        {"active": <int>, "resolved": <int>}
    """

    if seen_at is None:
        seen_at = timezone.now()

    active_keys = [
        finding["dedup_key"]
        for finding in digest_findings
    ]

    with transaction.atomic():

        for finding in digest_findings:
            _upsert_digest_finding(
                digest_finding=finding,
                seen_at=seen_at,
            )

        resolved = (
            CRMDigest.objects.filter(
                resolved_at__isnull=True,
            )
            .exclude(
                dedup_key__in=active_keys,
            )
            .update(
                resolved_at=seen_at,
                updated_at=seen_at,
            )
        )

    return {
        "active": len(active_keys),
        "resolved": resolved,
    }
