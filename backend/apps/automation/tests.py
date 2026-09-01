import json
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.ai.models import AIActionAudit
from apps.automation import digest as automation_digest
from apps.automation import services as automation_services
from apps.automation.models import CRMDigest, ScheduledCheckRun
from apps.leads.models import Lead, LeadActivity, LeadTask


class _StubSummaryProvider:
    """Offline AI provider stub for command tests that are not
    exercising the Phase 6D summary path."""

    def analyze(self, prompt):
        return "stub operational summary"


_PATCH_SUMMARY_PROVIDER = "apps.automation.summary.AIProviderFactory.create"


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

        with patch(
            _PATCH_SUMMARY_PROVIDER,
            return_value=_StubSummaryProvider(),
        ):
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



# =========================================================
# PHASE 6C - CRM DIGEST PERSISTENCE + DEDUP
# =========================================================


def _raw_due_soon(*, task_id=1, lead_id=10, summary="Task due soon."):
    return {
        "check": "due_soon_tasks",
        "finding_type": "due_soon_task",
        "lead_id": lead_id,
        "object_id": task_id,
        "summary": summary,
        "data": {
            "id": task_id,
            "lead_id": lead_id,
            "lead_company": "Acme Analytics",
            "title": "Call back",
            "task_type": "follow_up",
            "priority": "high",
            "status": "pending",
            "due_date": "2026-01-01T00:00:00+00:00",
        },
    }


def _raw_stale(*, lead_id=10, summary="Lead is stale."):
    return {
        "check": "stale_leads",
        "finding_type": "stale_lead",
        "lead_id": lead_id,
        "object_id": lead_id,
        "summary": summary,
        "data": {
            "id": lead_id,
            "company_name": "Acme Analytics",
            "status": "contacted",
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_meaningful_activity_at": "2026-01-01T00:00:00+00:00",
        },
    }


class CRMDigestDedupKeyTests(TestCase):

    def test_dedup_key_format(self):
        self.assertEqual(
            automation_digest.build_dedup_key(
                finding_type="due_soon_task",
                object_id=7,
            ),
            "due_soon_task:7",
        )

        self.assertEqual(
            automation_digest.build_dedup_key(
                finding_type="stale_lead",
                object_id=3,
            ),
            "stale_lead:3",
        )

    def test_dedup_key_rejects_unsupported_type(self):
        with self.assertRaises(ValueError):
            automation_digest.build_dedup_key(
                finding_type="ai_summary",
                object_id=1,
            )

    def test_digest_module_has_no_orm_access(self):
        source = (
            Path(automation_digest.__file__)
            .read_text(encoding="utf-8")
        )

        self.assertNotIn(".objects", source)


class CRMDigestPersistenceTests(TestCase):

    def test_first_finding_creates_one_row(self):
        result = automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1, lead_id=10)],
        )

        self.assertEqual(
            CRMDigest.objects.count(),
            1,
        )

        row = CRMDigest.objects.get()

        self.assertEqual(row.dedup_key, "due_soon_task:1")
        self.assertEqual(row.finding_type, "due_soon_task")
        self.assertEqual(row.task_id, 1)
        self.assertEqual(row.lead_id, 10)
        self.assertEqual(row.occurrence_count, 1)
        self.assertIsNone(row.resolved_at)

        self.assertEqual(result["active"], 1)
        self.assertEqual(result["resolved"], 0)

    def test_same_finding_second_run_does_not_duplicate(self):
        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
        )
        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
        )

        self.assertEqual(
            CRMDigest.objects.count(),
            1,
        )

    def test_occurrence_count_increments(self):
        for _ in range(3):
            automation_digest.persist_findings(
                findings=[_raw_due_soon(task_id=1)],
            )

        row = CRMDigest.objects.get()

        self.assertEqual(row.occurrence_count, 3)

    def test_first_seen_stable_last_seen_advances(self):
        t1 = timezone.now() - timedelta(hours=2)
        t2 = timezone.now()

        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
            seen_at=t1,
        )
        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
            seen_at=t2,
        )

        row = CRMDigest.objects.get()

        self.assertEqual(row.first_seen_at, t1)
        self.assertEqual(row.last_seen_at, t2)

    def test_absent_finding_after_successful_run_is_resolved(self):
        t1 = timezone.now() - timedelta(hours=1)
        t2 = timezone.now()

        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
            seen_at=t1,
        )

        result = automation_digest.persist_findings(
            findings=[],
            seen_at=t2,
        )

        row = CRMDigest.objects.get()

        self.assertEqual(row.resolved_at, t2)
        self.assertEqual(row.occurrence_count, 1)
        self.assertEqual(result["resolved"], 1)

    def test_resolved_finding_reappearing_reopens_same_row(self):
        t1 = timezone.now() - timedelta(hours=2)
        t2 = timezone.now() - timedelta(hours=1)
        t3 = timezone.now()

        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
            seen_at=t1,
        )
        original_id = CRMDigest.objects.get().id

        automation_digest.persist_findings(
            findings=[],
            seen_at=t2,
        )

        automation_digest.persist_findings(
            findings=[_raw_due_soon(task_id=1)],
            seen_at=t3,
        )

        self.assertEqual(CRMDigest.objects.count(), 1)

        row = CRMDigest.objects.get()

        self.assertEqual(row.id, original_id)
        self.assertIsNone(row.resolved_at)
        self.assertEqual(row.first_seen_at, t1)
        self.assertEqual(row.last_seen_at, t3)
        self.assertEqual(row.occurrence_count, 2)

    def test_due_soon_dedup_is_task_specific(self):
        automation_digest.persist_findings(
            findings=[
                _raw_due_soon(task_id=1, lead_id=10),
                _raw_due_soon(task_id=2, lead_id=10),
            ],
        )

        self.assertEqual(
            sorted(
                CRMDigest.objects.values_list(
                    "dedup_key",
                    flat=True,
                )
            ),
            ["due_soon_task:1", "due_soon_task:2"],
        )

    def test_stale_dedup_is_lead_specific(self):
        automation_digest.persist_findings(
            findings=[
                _raw_stale(lead_id=10),
                _raw_stale(lead_id=11),
            ],
        )

        self.assertEqual(
            sorted(
                CRMDigest.objects.values_list(
                    "dedup_key",
                    flat=True,
                )
            ),
            ["stale_lead:10", "stale_lead:11"],
        )

    def test_one_lead_can_hold_both_finding_types(self):
        automation_digest.persist_findings(
            findings=[
                _raw_due_soon(task_id=5, lead_id=10),
                _raw_stale(lead_id=10),
            ],
        )

        self.assertEqual(CRMDigest.objects.count(), 2)

        self.assertEqual(
            sorted(
                CRMDigest.objects.values_list(
                    "dedup_key",
                    flat=True,
                )
            ),
            ["due_soon_task:5", "stale_lead:10"],
        )

    def test_finding_data_is_json_safe(self):
        raw = _raw_due_soon(task_id=1)

        automation_digest.persist_findings(
            findings=[raw],
        )

        row = CRMDigest.objects.get()

        json.dumps(row.finding_data)

        self.assertEqual(
            row.finding_data,
            raw["data"],
        )


class CRMDigestCommandIntegrationTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

    def _run(self):
        with patch(
            _PATCH_SUMMARY_PROVIDER,
            return_value=_StubSummaryProvider(),
        ):
            call_command(
                "run_crm_checks",
                stdout=StringIO(),
            )

    def _due_soon_task(self, *, title="Call back"):
        return LeadTask.objects.create(
            lead=self.lead,
            title=title,
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(hours=6),
        )

    def test_repeated_identical_run_is_user_facing_deduplicated(self):
        self._due_soon_task()

        self._run()
        self._run()
        self._run()

        self.assertEqual(CRMDigest.objects.count(), 1)

        row = CRMDigest.objects.get()

        self.assertEqual(row.occurrence_count, 3)
        self.assertIsNone(row.resolved_at)

        self.assertEqual(ScheduledCheckRun.objects.count(), 3)

    def test_findings_count_is_run_scoped_not_digest_total(self):
        task_a = self._due_soon_task(title="Task A")

        self._run()

        run_one = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run_one.findings_count, 1)

        # Task A no longer due soon; Task B now due soon.
        task_a.status = "completed"
        task_a.save(update_fields=["status", "updated_at"])
        self._due_soon_task(title="Task B")

        self._run()

        run_two = ScheduledCheckRun.objects.latest("id")

        # Only one finding this run, even though the digest now
        # holds two rows (Task A resolved + Task B active).
        self.assertEqual(run_two.findings_count, 1)
        self.assertEqual(CRMDigest.objects.count(), 2)

        self.assertEqual(
            CRMDigest.objects.filter(
                resolved_at__isnull=False,
            ).count(),
            1,
        )

    def test_failed_run_does_not_resolve_active_findings(self):
        self._due_soon_task()
        self._run()

        row = CRMDigest.objects.get()
        self.assertIsNone(row.resolved_at)

        with patch(
            "apps.automation.management.commands."
            "run_crm_checks.automation_checks.run_all_checks",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                self._run()

        row.refresh_from_db()

        self.assertIsNone(row.resolved_at)
        self.assertEqual(row.occurrence_count, 1)

        failed_run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(failed_run.status, "failed")
        self.assertIn("boom", failed_run.error_message)

    def test_digest_persistence_does_not_mutate_crm(self):
        self._due_soon_task()

        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="note",
            description="Initial contact.",
        )

        lead_count = Lead.objects.count()
        task_count = LeadTask.objects.count()
        activity_count = LeadActivity.objects.count()
        audit_count = AIActionAudit.objects.count()

        self._run()
        self._run()

        self.assertEqual(Lead.objects.count(), lead_count)
        self.assertEqual(LeadTask.objects.count(), task_count)
        self.assertEqual(
            LeadActivity.objects.count(),
            activity_count,
        )
        self.assertEqual(
            AIActionAudit.objects.count(),
            audit_count,
        )


# =========================================================
# PHASE 6D - OPTIONAL AI DIGEST SUMMARY
# =========================================================

from apps.automation import summary as automation_summary


class _FakeProvider:
    def __init__(self, response="AI generated operational summary."):
        self.response = response
        self.prompts = []

    def analyze(self, prompt):
        self.prompts.append(prompt)
        return self.response


class _RaisingProvider:
    def analyze(self, prompt):
        raise RuntimeError("provider down")


def _shaped(*raw_findings):
    return [
        automation_digest.shape_finding(raw)
        for raw in raw_findings
    ]


class CRMDigestAISummaryTests(TestCase):

    def test_summary_module_has_no_orm_access(self):
        source = (
            Path(automation_summary.__file__)
            .read_text(encoding="utf-8")
        )

        self.assertNotIn(".objects", source)

    def test_successful_provider_response_is_returned(self):
        provider = _FakeProvider("Two tasks need attention today.")

        result = automation_summary.summarize_digest(
            digest_findings=_shaped(_raw_due_soon(task_id=1)),
            provider=provider,
        )

        self.assertEqual(result["status"], "AI_SUMMARY_OK")
        self.assertEqual(result["source"], "ai_provider")
        self.assertEqual(
            result["summary"],
            "Two tasks need attention today.",
        )
        self.assertIsNone(result["error"])

    def test_provider_receives_only_deterministic_finding_data(self):
        provider = _FakeProvider()

        shaped = _shaped(
            _raw_due_soon(task_id=1, lead_id=10),
            _raw_stale(lead_id=10),
        )

        automation_summary.summarize_digest(
            digest_findings=shaped,
            provider=provider,
        )

        self.assertEqual(len(provider.prompts), 1)

        prompt = provider.prompts[0]

        expected_prompt = automation_summary.build_summary_prompt(
            payload=automation_summary.build_digest_payload(
                digest_findings=shaped,
            ),
        )

        self.assertEqual(prompt, expected_prompt)

        # Compact deterministic fields only - not the raw finding_data blob.
        self.assertIn('"task_id": 1', prompt)
        self.assertIn('"stale_leads"', prompt)
        self.assertNotIn("lead_company", prompt)

    def test_provider_call_failure_returns_deterministic_fallback(self):
        shaped = _shaped(_raw_due_soon(task_id=1))

        result = automation_summary.summarize_digest(
            digest_findings=shaped,
            provider=_RaisingProvider(),
        )

        self.assertEqual(result["status"], "AI_SUMMARY_FAILED")
        self.assertEqual(
            result["source"],
            "deterministic_fallback",
        )
        self.assertIn("provider down", result["error"])
        self.assertEqual(
            result["summary"],
            automation_summary.build_deterministic_fallback(
                payload=automation_summary.build_digest_payload(
                    digest_findings=shaped,
                ),
            ),
        )

    def test_provider_factory_failure_returns_deterministic_fallback(self):
        shaped = _shaped(_raw_due_soon(task_id=1))

        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            side_effect=RuntimeError("no factory"),
        ):
            result = automation_summary.summarize_digest(
                digest_findings=shaped,
            )

        self.assertEqual(result["status"], "AI_SUMMARY_FAILED")
        self.assertEqual(
            result["source"],
            "deterministic_fallback",
        )
        self.assertIn("no factory", result["error"])

    def test_blank_provider_response_returns_deterministic_fallback(self):
        shaped = _shaped(_raw_due_soon(task_id=1))

        for blank in ("", "   ", None):
            result = automation_summary.summarize_digest(
                digest_findings=shaped,
                provider=_FakeProvider(blank),
            )

            self.assertEqual(
                result["status"],
                "AI_SUMMARY_FAILED",
            )
            self.assertEqual(
                result["source"],
                "deterministic_fallback",
            )

    def test_deterministic_fallback_format_plural(self):
        shaped = _shaped(
            _raw_due_soon(task_id=1, summary="Call Acme."),
            _raw_due_soon(task_id=2, summary="Email Beta."),
            _raw_stale(lead_id=10, summary="Acme has gone quiet."),
        )

        result = automation_summary.summarize_digest(
            digest_findings=shaped,
            provider=_RaisingProvider(),
        )

        lines = result["summary"].splitlines()

        self.assertEqual(
            lines[0],
            "2 due-soon tasks; 1 stale lead.",
        )
        self.assertIn("- due-soon task #1: Call Acme.", lines)
        self.assertIn("- due-soon task #2: Email Beta.", lines)
        self.assertIn(
            "- stale lead #10: Acme has gone quiet.",
            lines,
        )

    def test_deterministic_fallback_format_singular(self):
        shaped = _shaped(_raw_due_soon(task_id=1))

        result = automation_summary.summarize_digest(
            digest_findings=shaped,
            provider=_RaisingProvider(),
        )

        self.assertEqual(
            result["summary"].splitlines()[0],
            "1 due-soon task; 0 stale leads.",
        )


class CRMDigestAISummaryCommandTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Call back",
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(hours=6),
        )

    def _run(self):
        out = StringIO()
        call_command("run_crm_checks", stdout=out)
        return out.getvalue()

    def test_run_succeeds_when_ai_summary_fails(self):
        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            side_effect=RuntimeError("boom"),
        ):
            output = self._run()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "succeeded")
        self.assertEqual(CRMDigest.objects.count(), 1)
        self.assertIn("AI_SUMMARY_FAILED", output)

    def test_run_reports_ai_summary_when_provider_succeeds(self):
        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            return_value=_FakeProvider("OPS SUMMARY TEXT"),
        ):
            output = self._run()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "succeeded")
        self.assertIn("AI_SUMMARY_OK", output)
        self.assertIn("OPS SUMMARY TEXT", output)

    def test_summary_does_not_mutate_crm_or_audit(self):
        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="note",
            description="Initial contact.",
        )

        counts = (
            Lead.objects.count(),
            LeadTask.objects.count(),
            LeadActivity.objects.count(),
            AIActionAudit.objects.count(),
        )

        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            return_value=_FakeProvider("ok"),
        ):
            self._run()

        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            side_effect=RuntimeError("boom"),
        ):
            self._run()

        self.assertEqual(
            counts,
            (
                Lead.objects.count(),
                LeadTask.objects.count(),
                LeadActivity.objects.count(),
                AIActionAudit.objects.count(),
            ),
        )

    def test_summary_does_not_invoke_confirmed_write_path(self):
        with patch(
            "apps.ai.tools.registry.execute_confirmed_write_tool",
        ) as mock_write:
            with patch(
                "apps.automation.summary.AIProviderFactory.create",
                return_value=_FakeProvider("ok"),
            ):
                self._run()

        mock_write.assert_not_called()

    def test_crmdigest_rows_unchanged_by_summarization(self):
        with patch(
            "apps.automation.summary.AIProviderFactory.create",
            return_value=_FakeProvider("ok"),
        ):
            self._run()

        row = CRMDigest.objects.get()
        before = (
            row.occurrence_count,
            row.last_seen_at,
            row.updated_at,
            row.resolved_at,
            row.finding_data,
        )

        task_id = row.task_id

        automation_summary.summarize_digest(
            digest_findings=_shaped(
                _raw_due_soon(task_id=task_id, lead_id=self.lead.id),
            ),
            provider=_FakeProvider("ok"),
        )

        row.refresh_from_db()
        after = (
            row.occurrence_count,
            row.last_seen_at,
            row.updated_at,
            row.resolved_at,
            row.finding_data,
        )

        self.assertEqual(before, after)
        self.assertEqual(CRMDigest.objects.count(), 1)



# =========================================================
# PHASE 6E1 - AUTOMATION OBSERVABILITY + SUMMARY HISTORY
# =========================================================


class _RunHistoryTestBase(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Call back",
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(hours=6),
        )

    def _run_with_provider_ok(self, text="OPS SUMMARY TEXT"):
        with patch(
            _PATCH_SUMMARY_PROVIDER,
            return_value=_FakeProvider(text),
        ):
            call_command("run_crm_checks", stdout=StringIO())

    def _run_with_provider_failure(self):
        with patch(
            _PATCH_SUMMARY_PROVIDER,
            side_effect=RuntimeError("provider offline"),
        ):
            call_command("run_crm_checks", stdout=StringIO())

    def _run_with_check_failure(self):
        with patch(
            "apps.automation.management.commands."
            "run_crm_checks.automation_checks.run_all_checks",
            side_effect=RuntimeError("check boom"),
        ):
            with self.assertRaises(RuntimeError):
                call_command("run_crm_checks", stdout=StringIO())


class ScheduledCheckRunSummaryPersistenceTests(_RunHistoryTestBase):

    def test_successful_ai_summary_is_persisted(self):
        self._run_with_provider_ok("Two items need attention.")

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.summary_status, "AI_SUMMARY_OK")
        self.assertEqual(run.summary_source, "ai_provider")
        self.assertEqual(
            run.summary_text,
            "Two items need attention.",
        )
        self.assertEqual(run.summary_error, "")

    def test_deterministic_fallback_summary_is_persisted(self):
        self._run_with_provider_failure()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "succeeded")
        self.assertEqual(
            run.summary_status,
            "AI_SUMMARY_FAILED",
        )
        self.assertEqual(
            run.summary_source,
            "deterministic_fallback",
        )
        self.assertIn("due-soon task", run.summary_text)
        self.assertIn("provider offline", run.summary_error)

    def test_provider_failure_leaves_run_succeeded(self):
        self._run_with_provider_failure()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "succeeded")

    def test_check_failure_leaves_run_failed(self):
        self._run_with_check_failure()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.status, "failed")
        self.assertIn("check boom", run.error_message)

    def test_failed_run_does_not_persist_ai_outcome(self):
        self._run_with_check_failure()

        run = ScheduledCheckRun.objects.latest("id")

        self.assertEqual(run.summary_status, "")
        self.assertEqual(run.summary_source, "")
        self.assertEqual(run.summary_text, "")
        self.assertEqual(run.summary_error, "")

    def test_crmdigest_has_no_ai_summary_prose(self):
        marker = "ZZZ_AI_PROSE_MARKER_ZZZ"

        self._run_with_provider_ok(marker)

        for row in CRMDigest.objects.all():
            self.assertNotIn(marker, row.summary)
            self.assertNotIn(marker, json.dumps(row.finding_data))

    def test_summary_persistence_does_not_mutate_crm_or_audit(self):
        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="note",
            description="Initial contact.",
        )

        counts = (
            Lead.objects.count(),
            LeadTask.objects.count(),
            LeadActivity.objects.count(),
            AIActionAudit.objects.count(),
        )

        self._run_with_provider_ok()
        self._run_with_provider_failure()

        self.assertEqual(
            counts,
            (
                Lead.objects.count(),
                LeadTask.objects.count(),
                LeadActivity.objects.count(),
                AIActionAudit.objects.count(),
            ),
        )


class AutomationRunHistoryServiceTests(_RunHistoryTestBase):

    def test_recent_runs_are_newest_first(self):
        self._run_with_provider_ok("first")
        self._run_with_provider_ok("second")
        self._run_with_provider_failure()

        runs = automation_services.get_recent_check_runs(limit=10)

        ids = [row["id"] for row in runs]

        self.assertEqual(
            ids,
            sorted(ids, reverse=True),
        )

        self.assertEqual(
            runs[0]["summary_status"],
            "AI_SUMMARY_FAILED",
        )

    def test_recent_runs_expose_summary_observability_fields(self):
        self._run_with_provider_ok("visible summary text")

        row = automation_services.get_recent_check_runs(
            limit=1,
        )[0]

        for key in (
            "started_at",
            "finished_at",
            "status",
            "checks_run",
            "findings_count",
            "summary_status",
            "summary_source",
            "summary_text",
            "summary_error",
        ):
            self.assertIn(key, row)

        self.assertEqual(
            row["summary_text"],
            "visible summary text",
        )


class AutomationRunHistoryViewTests(_RunHistoryTestBase):

    def setUp(self):
        super().setUp()

        User = get_user_model()

        self.staff_user = User.objects.create_user(
            username="automationstaff",
            password="test-password",
            is_staff=True,
        )

        self.plain_user = User.objects.create_user(
            username="automationplain",
            password="test-password",
            is_staff=False,
        )

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(
            reverse("automation:run_history"),
        )

        self.assertNotEqual(response.status_code, 200)

    def test_non_staff_user_is_rejected(self):
        self.client.force_login(self.plain_user)

        response = self.client.get(
            reverse("automation:run_history"),
        )

        self.assertNotEqual(response.status_code, 200)

    def test_staff_user_can_view_history(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse("automation:run_history"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automation Run History")

    def test_history_renders_ai_and_fallback_summaries(self):
        self._run_with_provider_ok("AI GENERATED LINE")
        self._run_with_provider_failure()

        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse("automation:run_history"),
        )

        self.assertContains(response, "AI summary OK")
        self.assertContains(response, "AI summary failed")
        self.assertContains(response, "AI GENERATED LINE")
        self.assertContains(response, "provider offline")

    def test_history_page_lists_runs_newest_first(self):
        self._run_with_provider_ok("older run")
        self._run_with_provider_ok("newer run")

        self.client.force_login(self.staff_user)

        response = self.client.get(
            reverse("automation:run_history"),
        )

        content = response.content.decode()

        self.assertLess(
            content.index("newer run"),
            content.index("older run"),
        )
