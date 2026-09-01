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

        self.staff_user = User.objects.create(
            username="automationstaff",
            is_staff=True,
        )

        self.plain_user = User.objects.create(
            username="automationplain",
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


# =========================================================
# PHASE 6E2 - HARDENING + FINAL PHASE 6 ACCEPTANCE
# =========================================================

from django.test import override_settings

from apps.automation import checks as automation_checks


class _TimeoutProvider:
    def analyze(self, prompt):
        raise TimeoutError("provider request timed out")


class _Phase6Base(TestCase):

    def setUp(self):
        User = get_user_model()
        # No passwords: these tests use force_login, and password
        # hashing is the dominant cost in setUp otherwise.
        self.staff_user = User.objects.create(
            username="phase6staff",
            is_staff=True,
        )
        self.plain_user = User.objects.create(
            username="phase6plain",
            is_staff=False,
        )

    # --- fixtures ---

    def _lead(self, *, status="contacted", created_days_ago=0):
        lead = Lead.objects.create(
            company_name=f"Lead {status} {created_days_ago}",
            job_title="Analyst",
            status=status,
        )
        if created_days_ago:
            Lead.objects.filter(id=lead.id).update(
                created_at=timezone.now()
                - timedelta(days=created_days_ago),
            )
            lead.refresh_from_db()
        return lead

    def _due_soon_task(self, *, lead=None, hours=6, status="pending",
                       title="Call back"):
        return LeadTask.objects.create(
            lead=lead or self._lead(),
            title=title,
            task_type="follow_up",
            priority="high",
            status=status,
            due_date=timezone.now() + timedelta(hours=hours),
        )

    # --- command runners ---

    def _run(self, *, provider=None, factory_side_effect=None):
        kwargs = {}
        if factory_side_effect is not None:
            kwargs["side_effect"] = factory_side_effect
        else:
            kwargs["return_value"] = provider or _FakeProvider("ok")
        with patch(_PATCH_SUMMARY_PROVIDER, **kwargs):
            call_command("run_crm_checks", stdout=StringIO(),
                         stderr=StringIO())

    def _run_ok(self, text="OPS SUMMARY"):
        self._run(provider=_FakeProvider(text))

    def _run_fallback(self):
        self._run(factory_side_effect=RuntimeError("provider offline"))

    def _run_timeout(self):
        self._run(provider=_TimeoutProvider())

    def _run_check_failure(self):
        with patch(
            "apps.automation.management.commands."
            "run_crm_checks.automation_checks.run_all_checks",
            side_effect=RuntimeError("check boom"),
        ):
            with self.assertRaises(RuntimeError):
                call_command("run_crm_checks", stdout=StringIO(),
                             stderr=StringIO())

    def _seed_running(self, *, minutes_old=0):
        run = automation_services.start_check_run()
        if minutes_old:
            ScheduledCheckRun.objects.filter(id=run.id).update(
                started_at=timezone.now()
                - timedelta(minutes=minutes_old),
            )
            run.refresh_from_db()
        return run

    def _crm_snapshot(self):
        return (
            Lead.objects.count(),
            LeadTask.objects.count(),
            LeadActivity.objects.count(),
            AIActionAudit.objects.count(),
        )


class AutomationOverlapAndStaleRunTests(_Phase6Base):

    def test_active_running_record_blocks_new_run(self):
        run1 = self._seed_running()

        with self.assertRaises(
            automation_services.OverlappingRunError
        ) as ctx:
            automation_services.start_check_run()

        self.assertEqual(ctx.exception.active_run_id, run1.id)

    def test_blocked_run_via_command_performs_no_mutation(self):
        self._seed_running()
        self._due_soon_task()
        snapshot = self._crm_snapshot()

        self._run_ok()

        self.assertEqual(ScheduledCheckRun.objects.count(), 1)
        self.assertEqual(CRMDigest.objects.count(), 0)
        self.assertEqual(self._crm_snapshot(), snapshot)

    def test_stale_running_record_is_recovered(self):
        stale = self._seed_running(minutes_old=45)

        new_run = automation_services.start_check_run()

        stale.refresh_from_db()
        self.assertEqual(stale.status, "failed")
        self.assertEqual(
            stale.error_message,
            automation_services.STALE_RUN_RECOVERED,
        )
        self.assertIsNotNone(stale.finished_at)

        self.assertEqual(new_run.status, "running")
        self.assertEqual(ScheduledCheckRun.objects.count(), 2)

    def test_stale_recovery_then_command_runs_normally(self):
        stale = self._seed_running(minutes_old=45)
        self._due_soon_task()

        self._run_ok()

        stale.refresh_from_db()
        self.assertEqual(stale.status, "failed")
        self.assertEqual(
            stale.error_message,
            automation_services.STALE_RUN_RECOVERED,
        )

        latest = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(latest.status, "succeeded")
        self.assertEqual(CRMDigest.objects.count(), 1)

    @override_settings(CRM_AUTOMATION_STALE_RUN_MINUTES=1)
    def test_stale_threshold_is_configurable(self):
        stale = self._seed_running(minutes_old=2)

        automation_services.start_check_run()

        stale.refresh_from_db()
        self.assertEqual(stale.status, "failed")


class AutomationAITimeoutConfigTests(_Phase6Base):

    @patch("apps.ai.providers.gpt_luna.OpenAI")
    def test_factory_forwards_timeout_and_retries_to_openai(
        self, mock_openai
    ):
        from apps.ai.providers.factory import AIProviderFactory

        AIProviderFactory.create(timeout=15, max_retries=0)
        _, kwargs = mock_openai.call_args
        self.assertEqual(kwargs.get("timeout"), 15)
        self.assertEqual(kwargs.get("max_retries"), 0)

        mock_openai.reset_mock()
        AIProviderFactory.create()
        _, kwargs = mock_openai.call_args
        self.assertNotIn("timeout", kwargs)
        self.assertNotIn("max_retries", kwargs)

    @patch("apps.ai.ollama_client.Client")
    def test_ollama_client_forwards_timeout(self, mock_client):
        from apps.ai.ollama_client import OllamaClient

        OllamaClient(timeout=15)
        _, kwargs = mock_client.call_args
        self.assertEqual(kwargs.get("timeout"), 15)

        mock_client.reset_mock()
        OllamaClient()
        _, kwargs = mock_client.call_args
        self.assertIsNone(kwargs.get("timeout"))

    @override_settings(CRM_AUTOMATION_AI_TIMEOUT_SECONDS=7)
    @patch("apps.automation.summary.AIProviderFactory.create")
    def test_summary_uses_configured_automation_timeout(
        self, mock_create
    ):
        mock_create.return_value = _FakeProvider("ok")

        automation_summary.summarize_digest(
            digest_findings=_shaped(_raw_due_soon(task_id=1)),
        )

        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("timeout"), 7)
        self.assertEqual(kwargs.get("max_retries"), 0)

    def test_provider_timeout_degrades_without_failing_run(self):
        self._due_soon_task()

        self._run_timeout()

        run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.summary_status, "AI_SUMMARY_FAILED")
        self.assertEqual(
            run.summary_source, "deterministic_fallback"
        )
        self.assertIn("timed out", run.summary_error)
        self.assertEqual(CRMDigest.objects.count(), 1)


class Phase6BackgroundAutomationAcceptanceTests(_Phase6Base):

    # --- scheduling / run lifecycle ---

    def test_normal_run_creates_one_finalized_record(self):
        self._run_ok()

        self.assertEqual(ScheduledCheckRun.objects.count(), 1)
        run = ScheduledCheckRun.objects.get()
        self.assertEqual(run.status, "succeeded")
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(run.checks_run, 2)
        self.assertEqual(run.findings_count, 0)

    def test_failed_deterministic_run_finalizes_failed(self):
        self._due_soon_task()
        self._run_check_failure()

        run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run.status, "failed")
        self.assertIn("check boom", run.error_message)
        self.assertEqual(CRMDigest.objects.count(), 0)
        self.assertEqual(run.summary_status, "")

    def test_stale_run_recovered_in_acceptance(self):
        stale = self._seed_running(minutes_old=45)
        automation_services.start_check_run()
        stale.refresh_from_db()
        self.assertEqual(stale.status, "failed")
        self.assertEqual(
            stale.error_message,
            automation_services.STALE_RUN_RECOVERED,
        )

    def test_active_running_blocks_overlap_no_mutation(self):
        self._seed_running()
        self._due_soon_task()
        snapshot = self._crm_snapshot()

        self._run_ok()

        self.assertEqual(CRMDigest.objects.count(), 0)
        self.assertEqual(self._crm_snapshot(), snapshot)

    # --- deterministic checks ---

    def test_due_soon_and_stale_leads_detected(self):
        lead = self._lead(created_days_ago=40)
        self._due_soon_task(lead=lead)

        self._run_ok()

        keys = set(
            CRMDigest.objects.values_list("dedup_key", flat=True)
        )
        self.assertTrue(any(k.startswith("due_soon_task:")
                            for k in keys))
        self.assertTrue(any(k.startswith("stale_lead:")
                            for k in keys))

        run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run.findings_count, 2)

    def test_won_and_lost_leads_excluded(self):
        self._lead(status="won", created_days_ago=90)
        self._lead(status="lost", created_days_ago=90)

        self._run_ok()

        self.assertFalse(
            CRMDigest.objects.filter(
                finding_type="stale_lead"
            ).exists()
        )

    @override_settings(CRM_DUE_SOON_HOURS=1)
    def test_thresholds_still_configurable_narrow(self):
        self._due_soon_task(hours=6)
        result = automation_checks.run_all_checks()
        self.assertEqual(len(result["findings"]), 0)

    def test_thresholds_still_configurable_default(self):
        self._due_soon_task(hours=6)
        result = automation_checks.run_all_checks()
        self.assertEqual(len(result["findings"]), 1)

    # --- digest ---

    def test_findings_persisted_and_deduplicated(self):
        self._due_soon_task()

        self._run_ok()
        self._run_ok()

        self.assertEqual(CRMDigest.objects.count(), 1)
        self.assertEqual(
            CRMDigest.objects.get().occurrence_count, 2
        )

    def test_absent_finding_resolves_after_successful_run(self):
        task = self._due_soon_task()
        self._run_ok()

        task.status = "completed"
        task.save(update_fields=["status", "updated_at"])
        self._run_ok()

        row = CRMDigest.objects.get()
        self.assertIsNotNone(row.resolved_at)

    def test_failed_run_does_not_resolve_prior_findings(self):
        task = self._due_soon_task()
        self._run_ok()

        task.status = "completed"
        task.save(update_fields=["status", "updated_at"])
        self._run_check_failure()

        row = CRMDigest.objects.get()
        self.assertIsNone(row.resolved_at)

    def test_resolved_finding_can_reopen(self):
        task = self._due_soon_task()
        self._run_ok()
        original_id = CRMDigest.objects.get().id

        task.status = "completed"
        task.save(update_fields=["status", "updated_at"])
        self._run_ok()

        task.status = "pending"
        task.due_date = timezone.now() + timedelta(hours=6)
        task.save(update_fields=["status", "due_date", "updated_at"])
        self._run_ok()

        row = CRMDigest.objects.get()
        self.assertEqual(row.id, original_id)
        self.assertIsNone(row.resolved_at)
        self.assertGreaterEqual(row.occurrence_count, 2)

    # --- AI summary ---

    def test_successful_provider_summary_persisted(self):
        self._due_soon_task()
        self._run_ok("A concise operational summary.")

        run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run.summary_status, "AI_SUMMARY_OK")
        self.assertEqual(run.summary_source, "ai_provider")
        self.assertEqual(
            run.summary_text, "A concise operational summary."
        )

    def test_provider_error_uses_fallback_without_failing_run(self):
        self._due_soon_task()
        self._run_fallback()

        run = ScheduledCheckRun.objects.latest("id")
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.summary_status, "AI_SUMMARY_FAILED")
        self.assertEqual(
            run.summary_source, "deterministic_fallback"
        )
        self.assertIn("provider offline", run.summary_error)
        self.assertEqual(CRMDigest.objects.count(), 1)

    def test_no_ai_prose_in_crmdigest(self):
        marker = "ZZ_AI_PROSE_MARKER_ZZ"
        self._due_soon_task()
        self._run_ok(marker)

        for row in CRMDigest.objects.all():
            self.assertNotIn(marker, row.summary)
            self.assertNotIn(
                marker, json.dumps(row.finding_data)
            )

    # --- safety ---

    def test_no_crm_or_audit_mutation_across_paths(self):
        self._due_soon_task()
        self._lead(created_days_ago=40)
        baseline = self._crm_snapshot()

        self._run_ok()
        self._run_fallback()
        self._seed_running()
        self._run_ok()          # blocked
        ScheduledCheckRun.objects.filter(
            status="running"
        ).update(
            started_at=timezone.now() - timedelta(minutes=90)
        )
        self._run_check_failure()

        self.assertEqual(self._crm_snapshot(), baseline)

    def test_confirmed_write_executor_never_invoked(self):
        self._due_soon_task()

        with patch(
            "apps.ai.tools.registry.execute_confirmed_write_tool"
        ) as mock_write, patch(
            "apps.ai.agent.write_executor.execute_confirmed_proposal"
        ) as mock_exec:
            self._run_ok()
            self._run_fallback()

        mock_write.assert_not_called()
        mock_exec.assert_not_called()

    def test_automation_orchestration_modules_have_no_orm(self):
        base = Path(automation_summary.__file__).resolve().parent
        checked = []
        for name in (
            "checks.py", "digest.py", "summary.py", "views.py",
        ):
            src = (base / name).read_text(encoding="utf-8")
            checked.append(name)
            self.assertNotIn(".objects", src)
        cmd = (
            base / "management" / "commands" / "run_crm_checks.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(".objects", cmd)
        self.assertEqual(len(checked), 4)

    def test_existing_ai_agent_orm_boundary_still_holds(self):
        from apps.ai.agent import response as _agent_anchor

        agent_dir = Path(_agent_anchor.__file__).resolve().parent
        for path in agent_dir.glob("*.py"):
            src = path.read_text(encoding="utf-8")
            for pattern in (
                ".objects.filter(", ".objects.create(",
                ".objects.get(", ".objects.update(",
                ".objects.delete(",
            ):
                self.assertNotIn(pattern, src, msg=path.name)

    # --- observability ---

    def test_run_history_records_counts_and_summary_status(self):
        self._due_soon_task()
        self._run_ok("visible summary")

        row = automation_services.get_recent_check_runs(limit=1)[0]
        self.assertEqual(row["checks_run"], 2)
        self.assertEqual(row["findings_count"], 1)
        self.assertEqual(row["summary_status"], "AI_SUMMARY_OK")
        self.assertEqual(row["summary_text"], "visible summary")

    def test_staff_history_page_renders_all_run_kinds(self):
        self._due_soon_task()
        self._run_ok("AI LINE ALPHA")
        self._run_fallback()
        self._run_check_failure()

        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse("automation:run_history")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Succeeded")
        self.assertContains(response, "Failed")
        self.assertContains(response, "AI summary OK")
        self.assertContains(response, "AI summary failed")

        content = response.content.decode()
        self.assertLess(
            content.index("check boom"),
            content.index("AI LINE ALPHA"),
        )

    def test_history_page_rejects_non_staff(self):
        response = self.client.get(
            reverse("automation:run_history")
        )
        self.assertNotEqual(response.status_code, 200)

        self.client.force_login(self.plain_user)
        response = self.client.get(
            reverse("automation:run_history")
        )
        self.assertNotEqual(response.status_code, 200)
