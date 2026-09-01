from django.core.management.base import BaseCommand

from apps.automation import checks as automation_checks
from apps.automation import digest as automation_digest
from apps.automation import services as automation_services


class Command(BaseCommand):
    """
    Run scheduled background CRM checks.

    Phase 6C: runs the deterministic, read-only CRM checks
    (due-soon tasks, stale leads), then persists and deduplicates
    the findings into CRMDigest and resolves previously active
    findings that are absent from this successful run. No AI
    prose, notifications, or CRM writes.

    ``findings_count`` on the run record is the number of findings
    the current check run produced, not the number of CRMDigest
    rows in the database.

    This module must not access the Django ORM directly. Run-record
    and digest persistence go through apps/automation/services.py;
    CRM state is read only through apps/automation/checks.py;
    dedup shaping goes through apps/automation/digest.py.
    """

    help = (
        "Run scheduled background CRM checks and record the run."
    )

    def handle(self, *args, **options):

        run = automation_services.start_check_run()

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

        except Exception as exc:

            automation_services.finish_check_run_failed(
                run=run,
                error_message=str(exc),
            )

            raise
