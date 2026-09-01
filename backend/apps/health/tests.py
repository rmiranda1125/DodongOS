import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_settings_import(extra_env):
    """
    Import Django settings in a clean subprocess with the given env
    overrides. Returns (returncode, stderr_text).
    """

    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "DJANGO_ENV",
            "SECRET_KEY",
            "DEBUG",
            "DATABASE_URL",
            "ALLOWED_HOSTS",
            "CSRF_TRUSTED_ORIGINS",
        }
    }
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    # Never touch the developer's .env from these guard tests.
    env["DJANGO_SKIP_DOTENV"] = "1"
    env.setdefault("DEBUG", "False")
    env.update(extra_env)

    proc = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr


# =========================================================
# HEALTH / READINESS
# =========================================================


class HealthEndpointTests(TestCase):

    def test_liveness_returns_ok_json(self):
        response = self.client.get(reverse("health_liveness"))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["version"], "1.0.0")

    def test_liveness_does_not_call_ai_provider(self):
        with patch(
            "apps.ai.providers.factory.AIProviderFactory.create"
        ) as mock_create:
            self.client.get(reverse("health_liveness"))
        mock_create.assert_not_called()

    def test_readiness_reports_database_ok(self):
        response = self.client.get(reverse("health_readiness"))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["checks"]["database"], "ok")

    def test_readiness_does_not_call_ai_provider(self):
        with patch(
            "apps.ai.providers.factory.AIProviderFactory.create"
        ) as mock_create:
            self.client.get(reverse("health_readiness"))
        mock_create.assert_not_called()

    def test_readiness_failure_hides_details_and_returns_503(self):
        with patch(
            "apps.health.views.connections"
        ) as mock_connections:
            mock_connections.__getitem__.side_effect = RuntimeError(
                "password=SUPERSECRET host=db.internal"
            )
            response = self.client.get(
                reverse("health_readiness")
            )
        self.assertEqual(response.status_code, 503)
        text = response.content.decode()
        self.assertNotIn("SUPERSECRET", text)
        self.assertNotIn("db.internal", text)
        self.assertNotIn("Traceback", text)

    def test_health_endpoints_expose_no_secrets(self):
        from django.conf import settings

        for name in ("health_liveness", "health_readiness"):
            text = self.client.get(
                reverse(name)
            ).content.decode()
            self.assertNotIn(settings.SECRET_KEY, text)
            self.assertNotIn("OPENAI_API_KEY", text)


# =========================================================
# production_check COMMAND
# =========================================================


class ProductionCheckCommandTests(TestCase):

    def test_passes_in_development_with_reachable_db(self):
        out = StringIO()
        call_command("production_check", stdout=out, stderr=StringIO())
        self.assertIn("passed", out.getvalue())

    def test_require_production_flag_fails_in_dev(self):
        with self.assertRaises(SystemExit):
            call_command(
                "production_check",
                "--require-production",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_command_prints_no_secret_key(self):
        from django.conf import settings

        out, err = StringIO(), StringIO()
        call_command("production_check", stdout=out, stderr=err)
        self.assertNotIn(
            settings.SECRET_KEY, out.getvalue() + err.getvalue()
        )


# =========================================================
# PRODUCTION SETTINGS GUARDS (subprocess: real settings import)
# =========================================================


class ProductionSettingsGuardTests(TestCase):

    def test_production_requires_secret_key(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            }
        )
        self.assertNotEqual(code, 0)
        self.assertIn("SECRET_KEY", err)

    def test_production_rejects_debug_true(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "DEBUG": "True",
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            }
        )
        self.assertNotEqual(code, 0)
        self.assertIn("DEBUG", err)

    def test_production_requires_allowed_hosts(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            }
        )
        self.assertNotEqual(code, 0)
        self.assertIn("ALLOWED_HOSTS", err)

    def test_production_refuses_sqlite_fallback(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "ALLOWED_HOSTS": "example.com",
            }
        )
        self.assertNotEqual(code, 0)
        self.assertIn("DATABASE_URL", err)

    def test_production_config_loads_with_postgres_url(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "ALLOWED_HOSTS": "example.com",
                "CSRF_TRUSTED_ORIGINS": "https://example.com",
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            }
        )
        self.assertEqual(code, 0, err)

    def test_development_still_uses_sqlite(self):
        code, err = _run_settings_import(
            {"SECRET_KEY": "x" * 50}
        )
        self.assertEqual(code, 0, err)


# =========================================================
# PRODUCTION SECURITY BEHAVIOUR
# =========================================================


@override_settings(
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=31536000,
)
class ProductionSecuritySettingsTests(TestCase):

    def test_https_settings_can_be_enabled(self):
        response = self.client.get(
            reverse("health_liveness")
        )
        # SSL redirect kicks in for the plain-HTTP test request.
        self.assertIn(response.status_code, (301, 302))
        self.assertTrue(
            response["Location"].startswith("https://")
        )

    def test_deploy_check_is_clean_under_production_security(self):
        out = StringIO()
        call_command("check", "--deploy", stdout=out, stderr=out)


class DebugOffBehaviourTests(TestCase):

    @override_settings(DEBUG=False)
    def test_unknown_path_returns_404_without_traceback(self):
        response = self.client.get("/definitely-not-a-real-path/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Traceback", response.content.decode())
        self.assertNotIn(
            "DJANGO_SETTINGS_MODULE", response.content.decode()
        )


# =========================================================
# WRITE / CSRF / AUTH BOUNDARIES STILL INTACT
# =========================================================


class WriteEndpointProtectionTests(TestCase):

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create(
            username="write-endpoint-user"
        )

    def test_confirm_endpoint_requires_authentication(self):
        # Anonymous -> redirect to login, never the view.
        response = self.client.post(
            reverse("ai:crm_assistant_task_confirm"),
            {"proposal_token": "anything"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_confirm_endpoint_rejects_get_when_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ai:crm_assistant_task_confirm")
        )
        self.assertEqual(response.status_code, 405)

    def test_confirm_endpoint_requires_csrf_when_authenticated(self):
        from django.contrib.auth import get_user_model

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(
            get_user_model().objects.create(username="csrf-user")
        )
        response = csrf_client.post(
            reverse("ai:crm_assistant_task_confirm"),
            {"proposal_token": "anything"},
        )
        self.assertEqual(response.status_code, 403)

    def test_assistant_and_staff_routes_reject_anonymous(self):
        for name in (
            "ai:crm_assistant",
            "ai:crm_action_audit",
            "automation:run_history",
            "knowledge:assistant",
        ):
            self.assertNotEqual(
                self.client.get(reverse(name)).status_code,
                200,
                msg=name,
            )

    def test_non_staff_user_still_blocked_from_staff_surfaces(self):
        self.client.force_login(self.user)
        for name in (
            "ai:crm_action_audit",
            "automation:run_history",
            "knowledge:assistant",
        ):
            self.assertNotEqual(
                self.client.get(reverse(name)).status_code,
                200,
                msg=name,
            )
        # ...but the CRM Assistant is available to any authed user.
        self.assertEqual(
            self.client.get(
                reverse("ai:crm_assistant")
            ).status_code,
            200,
        )


# =========================================================
# READ-ONLY AI / RAG / AUTOMATION SAFETY (regression anchors)
# =========================================================


class ProductionReadOnlySafetyTests(TestCase):

    def test_rag_and_automation_never_touch_confirmed_write(self):
        from apps.ai.agent import rag_agent
        from apps.knowledge import services as knowledge_services

        knowledge_services.ingest_document(
            title="Policy",
            source_reference="policy/x",
            text="Qualified leads are contacted within two days.",
        )

        class _P:
            def analyze(self, prompt):
                return "grounded answer"

        with patch(
            "apps.ai.tools.registry.execute_confirmed_write_tool"
        ) as mock_write, patch(
            "apps.ai.agent.write_executor.execute_confirmed_proposal"
        ) as mock_exec, patch(
            "apps.automation.summary.AIProviderFactory.create",
            return_value=_P(),
        ):
            rag_agent.run_rag_agent(
                question="qualified leads contact timing",
                provider=_P(),
            )
            call_command(
                "run_crm_checks",
                stdout=StringIO(),
                stderr=StringIO(),
            )

        mock_write.assert_not_called()
        mock_exec.assert_not_called()

    def test_env_file_cannot_be_ingested_as_knowledge(self):
        from apps.knowledge import services as knowledge_services

        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="env",
                source_reference="env/prod",
                text="SECRET_KEY=abc\nOPENAI_API_KEY=sk-proj-xyz",
            )


# =========================================================
# INPUT LIMIT HARDENING (Phase 10 §29/§30)
# =========================================================


@override_settings(
    CRM_NOTE_MAX_LENGTH=100,
    RAG_QUERY_MAX_CHARS=50,
    KNOWLEDGE_DOC_MAX_CHARS=200,
)
class InputLimitHardeningTests(TestCase):

    def test_over_long_note_rejected_at_proposal_boundary(self):
        from apps.ai.agent.write_proposals import (
            build_add_lead_note_proposal,
        )
        from apps.leads.models import Lead

        lead = Lead.objects.create(
            company_name="Acme", job_title="Analyst"
        )
        result = build_add_lead_note_proposal(
            lead_id=lead.id, note="x" * 101
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "NOTE_TOO_LONG")

    def test_over_long_note_rejected_at_write_tool_boundary(self):
        from apps.ai.tools.crm.activities import add_lead_note_tool
        from apps.leads.models import Lead, LeadActivity

        lead = Lead.objects.create(
            company_name="Acme", job_title="Analyst"
        )
        result = add_lead_note_tool(
            lead_id=lead.id,
            activity_type="note",
            description="y" * 101,
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "NOTE_TOO_LONG")
        self.assertEqual(LeadActivity.objects.count(), 0)

    def test_note_at_limit_is_accepted(self):
        from apps.ai.agent.write_proposals import (
            build_add_lead_note_proposal,
        )
        from apps.leads.models import Lead

        lead = Lead.objects.create(
            company_name="Acme", job_title="Analyst"
        )
        result = build_add_lead_note_proposal(
            lead_id=lead.id, note="z" * 100
        )
        self.assertTrue(result["success"])

    def test_over_long_rag_query_rejected(self):
        from apps.knowledge import services as knowledge_services

        result = knowledge_services.retrieve_knowledge(
            query="q" * 51
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["error"]["code"], "QUERY_TOO_LONG"
        )

    def test_over_long_knowledge_document_rejected(self):
        from apps.knowledge import services as knowledge_services

        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="Big",
                source_reference="big/1",
                text="word " * 100,
            )


class ProductionStaticConfigTests(TestCase):

    def test_production_uses_manifest_static_storage(self):
        code, err = _run_settings_import(
            {
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            }
        )
        self.assertEqual(code, 0, err)
        check = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import django;django.setup();"
                    "from django.conf import settings;"
                    "print(settings.STORAGES['staticfiles']"
                    "['BACKEND'])"
                ),
            ],
            cwd=str(BACKEND_DIR),
            env={
                **{
                    k: v
                    for k, v in os.environ.items()
                    if k
                    not in {
                        "DJANGO_ENV",
                        "SECRET_KEY",
                        "DATABASE_URL",
                        "ALLOWED_HOSTS",
                    }
                },
                "DJANGO_SETTINGS_MODULE": "config.settings",
                "DJANGO_SKIP_DOTENV": "1",
                "DEBUG": "False",
                "DJANGO_ENV": "production",
                "SECRET_KEY": "x" * 50,
                "ALLOWED_HOSTS": "example.com",
                "DATABASE_URL": "postgres://u:p@h:5432/n",
            },
            capture_output=True,
            text=True,
        )
        self.assertIn("whitenoise", check.stdout)
