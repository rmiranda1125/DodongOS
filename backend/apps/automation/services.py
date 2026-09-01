from django.utils import timezone

from apps.automation.models import ScheduledCheckRun


def start_check_run():
    """
    Create and return one new, in-progress check run record.

    This is the only place allowed to call
    ScheduledCheckRun.objects.create().
    """

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
