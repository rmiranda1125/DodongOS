from django.core.management.base import BaseCommand

from apps.automation import checks as automation_checks
from apps.automation import digest as automation_digest
from apps.automation import services as automation_services
from apps.automation import summary as automation_summary


class Command(BaseCommand):
    """
    Run scheduled background CRM checks.

    Phase 6D: runs the deterministic, read-only CRM checks
    (due-soon tasks, stale leads), persists and deduplicates the
    findings into CRMDigest, resolves previously active findings
    absent from this successful run, then requests an OPTIONAL AI
    summary of the digest.

    The AI summary is additive only. A provider failure produces a
    deterministic fallback summary and never changes the run
    outcome: ScheduledCheckRun success/failure reflects the
    deterministic checks and digest persistence, not provider
    availability. Phase 6E1: the summary outcome (status, source,
    text, error) is persisted on the ScheduledCheckRun for staff
    observability.

    ``findings_count`` on the run record is the number of findings
    the current check run produced, not the number of CRMDigest
    rows in the database.

    This module must not access the Django ORM directly. Run-record
    and digest persistence go through apps/automation/services.py;
    CRM state is read only through apps/automation/checks.py;
    dedup shaping goes through apps/automation/digest.py; AI
    summarization goes through apps/automation/summary.py.
    """

    help = (
        "Run scheduled background CRM checks and record the run."
    )

    def handle(self, *args, **options):

        try:
            run = automation_services.start_check_run()
        except automation_services.OverlappingRunError as exc:
            #
            # An earlier run is still in progress (and is not stale).
            # This is normal cron overlap, not a failure: do nothing,
            # touch no CRM data, create no run/digest records.
            #
            self.stdout.write(
                self.style.WARNING(
                    f"run_crm_checks skipped: {exc}"
                )
            )
            return

        try:
            #
            # -----------------------------------------------------
            # DETERMINISTIC CRM CHECKS
            # -----------------------------------------------------
            #
            # Read-only. Only a fully successful run below reaches
            # digest persistence / resolution.
            #

            outcome = automation_checks.run_all_checks()

            checks_run = outcome["checks_run"]
            findings = outcome["findings"]
            findings_count = len(findings)

            digest_result = automation_digest.persist_findings(
                findings=findings,
            )

            #
            # Optional AI summary. Never fails the run: any error
            # here is swallowed and reported as AI_SUMMARY_FAILED
            # with a deterministic fallback summary.
            #
            try:
                summary_result = (
                    automation_summary.summarize_digest(
                        digest_findings=(
                            digest_result["digest_findings"]
                        ),
                    )
                )
            except Exception as summary_exc:  # pragma: no cover
                summary_result = {
                    "status": "AI_SUMMARY_FAILED",
                    "source": "deterministic_fallback",
                    "summary": "",
                    "error": str(summary_exc),
                }

            automation_services.record_run_summary(
                run=run,
                summary_result=summary_result,
            )

            automation_services.finish_check_run_succeeded(
                run=run,
                checks_run=checks_run,
                findings_count=findings_count,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"CRM check run {run.id} succeeded "
                    f"(checks_run={checks_run}, "
                    f"findings_count={findings_count}, "
                    f"digest_active={digest_result['active']}, "
                    f"digest_resolved={digest_result['resolved']})."
                )
            )

            self.stdout.write(
                f"AI summary: {summary_result['status']} "
                f"({summary_result['source']})"
            )

            self.stdout.write(
                summary_result["summary"]
            )

        except Exception as exc:

            automation_services.finish_check_run_failed(
                run=run,
                error_message=str(exc),
            )

            raise
