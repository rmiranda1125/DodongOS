from django.core.management.base import BaseCommand

from apps.automation import checks as automation_checks
from apps.automation import services as automation_services


class Command(BaseCommand):
    """
    Run scheduled background CRM checks.

    Phase 6B: runs the deterministic, read-only CRM checks
    (due-soon tasks, stale leads) and records how many checks ran
    and how many findings they produced. Findings are not persisted
    yet — that is Phase 6C.

    This module must not access the Django ORM directly. Run-record
    persistence goes through apps/automation/services.py; CRM state
    is read only through apps/automation/checks.py.
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
            # Read-only. No finding persistence in Phase 6B.
            #

            outcome = automation_checks.run_all_checks()

            checks_run = outcome["checks_run"]
            findings_count = len(outcome["findings"])

            automation_services.finish_check_run_succeeded(
                run=run,
                checks_run=checks_run,
                findings_count=findings_count,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"CRM check run {run.id} succeeded "
                    f"(checks_run={checks_run}, "
                    f"findings_count={findings_count})."
                )
            )

        except Exception as exc:

            automation_services.finish_check_run_failed(
                run=run,
                error_message=str(exc),
            )

            raise
