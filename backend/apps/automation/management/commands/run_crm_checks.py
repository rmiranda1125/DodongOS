from django.core.management.base import BaseCommand

from apps.automation import services as automation_services


class Command(BaseCommand):
    """
    Run scheduled background CRM checks.

    Phase 6A: no checks are registered yet. This command only
    proves the run-record lifecycle (start -> finish) works and is
    safe to invoke repeatedly. Phase 6B will add the first
    deterministic CRM checks.

    This module must not access the Django ORM directly. Run-record
    persistence goes through apps/automation/services.py.
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
            # Phase 6A intentionally runs zero checks. Phase 6B
            # will populate this section with deterministic CRM
            # check calls (overdue tasks, due-soon follow-ups,
            # stale leads, etc.).
            #

            checks_run = 0
            findings_count = 0

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
