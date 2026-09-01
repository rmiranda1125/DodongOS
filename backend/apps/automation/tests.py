from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.ai.models import AIActionAudit
from apps.automation.models import ScheduledCheckRun
from apps.leads.models import Lead, LeadActivity, LeadTask


class ScheduledCheckRunFoundationTests(TestCase):
    """
    Scheduling foundation + Phase 6B deterministic checks.

    The run_crm_checks command must record one run per invocation
    through the service layer, run the deterministic checks,
    finalize a clean run as succeeded with the correct checks_run
    and findings_count, and never mutate CRM data.
    """

    def _run_command(self):
        out = StringIO()

        call_command(
            "run_crm_checks",
            stdout=out,
        )

        return out.getvalue()

    def test_command_runs_successfully(self):
        output = self._run_command()

        self.assertIn(
            "succeeded",
            output,
        )

    def test_command_creates_exactly_one_run_record(self):
        self._run_command()

        self.assertEqual(
            ScheduledCheckRun.objects.count(),
            1,
        )

    def test_successful_run_is_finalized_as_succeeded(self):
        self._run_command()

        run = ScheduledCheckRun.objects.get()

        self.assertEqual(
            run.status,
            "succeeded",
        )

        self.assertIsNotNone(
            run.finished_at,
        )

        self.assertEqual(
            run.error_message,
            "",
        )

    def test_successful_run_records_two_checks(self):
        self._run_command()

        run = ScheduledCheckRun.objects.get()

        self.assertEqual(
            run.checks_run,
            2,
        )

    def test_empty_crm_produces_zero_findings(self):
        self._run_command()

        run = ScheduledCheckRun.objects.get()

        self.assertEqual(
            run.findings_count,
            0,
        )

    def test_findings_count_matches_deterministic_findings(self):
        from apps.automation import checks as automation_checks

        lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

        LeadTask.objects.create(
            lead=lead,
            title="Call back",
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(hours=6),
        )

        expected = len(
            automation_checks.run_all_checks()["findings"]
        )

        self._run_command()

        run = ScheduledCheckRun.objects.get()

        self.assertEqual(
            run.findings_count,
            expected,
        )

        self.assertGreaterEqual(
            expected,
            1,
        )

    def test_two_invocations_create_two_independent_runs(self):
        self._run_command()
        self._run_command()

        runs = list(
            ScheduledCheckRun.objects.all()
        )

        self.assertEqual(
            len(runs),
            2,
        )

        self.assertNotEqual(
            runs[0].id,
            runs[1].id,
        )

        for run in runs:
            self.assertEqual(
                run.status,
                "succeeded",
            )

    def test_command_performs_no_crm_mutations(self):
        lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

        LeadTask.objects.create(
            lead=lead,
            title="Send pricing proposal",
            task_type="follow_up",
            priority="high",
            status="pending",
        )

        LeadActivity.objects.create(
            lead=lead,
            activity_type="note",
            description="Initial contact.",
        )

        lead_count = Lead.objects.count()
        task_count = LeadTask.objects.count()
        activity_count = LeadActivity.objects.count()
        audit_count = AIActionAudit.objects.count()

        self._run_command()
        self._run_command()

        self.assertEqual(
            Lead.objects.count(),
            lead_count,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            task_count,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            audit_count,
        )


class AutomationArchitectureSafetyTests(TestCase):
    """
    Automation orchestration code must not touch the Django ORM
    directly. Persistence goes through
    apps/automation/services.py; models.py and services.py are the
    only modules in the app allowed to use the ORM.
    """

    ORM_OWNING_MODULES = {
        "models.py",
        "services.py",
        "tests.py",
    }

    FORBIDDEN_PATTERNS = (
        ".objects.",
        ".objects(",
    )

    def test_orchestration_modules_have_no_direct_orm(self):
        automation_directory = (
            Path(__file__).resolve().parent
        )

        violations = []

        for file_path in automation_directory.rglob("*.py"):

            if file_path.name in self.ORM_OWNING_MODULES:
                continue

            if "migrations" in file_path.parts:
                continue

            if "__pycache__" in file_path.parts:
                continue

            source = file_path.read_text(
                encoding="utf-8",
            )

            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern in source:
                    violations.append(
                        (
                            file_path.name,
                            pattern,
                        )
                    )

        self.assertEqual(
            violations,
            [],
            msg=(
                "Automation orchestration modules must not "
                f"access the Django ORM directly: {violations}"
            ),
        )
