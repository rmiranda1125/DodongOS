from pathlib import Path

from django.test import TestCase, override_settings

from apps.knowledge import chunking
from apps.knowledge import retrieval
from apps.knowledge import services as knowledge_services
from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


# =========================================================
# 7A - DETERMINISTIC CHUNKING
# =========================================================


class ChunkingTests(TestCase):

    def test_short_document_is_one_chunk(self):
        chunks = chunking.chunk_text(
            "Follow up with qualified leads within two days.",
            chunk_size=200,
            overlap=20,
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0],
            "Follow up with qualified leads within two days.",
        )

    def test_multi_chunk_document_preserves_order(self):
        words = " ".join(f"word{i}" for i in range(1, 61))
        chunks = chunking.chunk_text(
            words, chunk_size=60, overlap=10
        )
        self.assertGreater(len(chunks), 1)
        rejoined = " ".join(chunks)
        # every original word appears, in order
        self.assertIn("word1", chunks[0])
        self.assertIn("word60", chunks[-1])
        self.assertLess(
            rejoined.index("word1"),
            rejoined.index("word60"),
        )

    def test_output_is_deterministic(self):
        text = " ".join(f"token{i}" for i in range(1, 40))
        a = chunking.chunk_text(text, chunk_size=50, overlap=12)
        b = chunking.chunk_text(text, chunk_size=50, overlap=12)
        self.assertEqual(a, b)

    def test_whitespace_is_normalized(self):
        chunks = chunking.chunk_text(
            "  alpha \n\n beta \t  gamma  ",
            chunk_size=100,
            overlap=0,
        )
        self.assertEqual(chunks, ["alpha beta gamma"])

    def test_empty_content_is_rejected(self):
        for bad in ("", "   ", "\n\t  \n"):
            with self.assertRaises(ValueError):
                chunking.chunk_text(
                    bad, chunk_size=100, overlap=0
                )

    def test_invalid_sizing_is_rejected(self):
        with self.assertRaises(ValueError):
            chunking.chunk_text("x", chunk_size=0, overlap=0)
        with self.assertRaises(ValueError):
            chunking.chunk_text("x", chunk_size=10, overlap=10)

    def test_no_empty_chunks_even_with_long_word(self):
        long_word = "x" * 50
        chunks = chunking.chunk_text(
            f"a {long_word} b", chunk_size=10, overlap=3
        )
        self.assertTrue(all(c.strip() for c in chunks))
        self.assertIn(long_word, " ".join(chunks))

    def test_consecutive_chunks_share_overlap(self):
        text = " ".join(f"w{i}" for i in range(1, 40))
        chunks = chunking.chunk_text(
            text, chunk_size=30, overlap=12
        )
        # last word(s) of chunk n reappear at start of chunk n+1
        first_tail = chunks[0].split(" ")[-1]
        self.assertIn(first_tail, chunks[1].split(" "))

    def test_secret_detector_flags_credentials(self):
        self.assertTrue(
            chunking.looks_like_secret(
                "OPENAI_API_KEY=sk-test-value"
            )
        )
        self.assertFalse(
            chunking.looks_like_secret(
                "Our follow-up policy for qualified leads."
            )
        )


# =========================================================
# 7B - DETERMINISTIC RANKING
# =========================================================


class RetrievalRankingTests(TestCase):

    def _chunk(self, doc_id, idx, content):
        return {
            "document_id": doc_id,
            "chunk_index": idx,
            "content": content,
            "chunk_id": doc_id * 100 + idx,
        }

    def test_ranks_by_term_coverage_then_density(self):
        chunks = [
            self._chunk(1, 0, "policy for qualified leads follow up"),
            self._chunk(2, 0, "qualified qualified qualified"),
            self._chunk(3, 0, "unrelated content about invoices"),
        ]
        ranked = retrieval.rank_chunks(
            query="qualified leads policy",
            chunks=chunks,
            limit=5,
        )
        self.assertEqual(ranked[0]["document_id"], 1)
        self.assertEqual(
            [r["document_id"] for r in ranked], [1, 2]
        )

    def test_non_matching_chunks_are_dropped(self):
        chunks = [self._chunk(1, 0, "totally different subject")]
        ranked = retrieval.rank_chunks(
            query="qualified leads", chunks=chunks, limit=5
        )
        self.assertEqual(ranked, [])

    def test_limit_is_enforced(self):
        chunks = [
            self._chunk(i, 0, "qualified leads policy")
            for i in range(1, 11)
        ]
        ranked = retrieval.rank_chunks(
            query="qualified", chunks=chunks, limit=3
        )
        self.assertEqual(len(ranked), 3)

    def test_ties_break_by_document_then_chunk_index(self):
        chunks = [
            self._chunk(2, 1, "qualified"),
            self._chunk(2, 0, "qualified"),
            self._chunk(1, 0, "qualified"),
        ]
        ranked = retrieval.rank_chunks(
            query="qualified", chunks=chunks, limit=5
        )
        self.assertEqual(
            [(r["document_id"], r["chunk_index"]) for r in ranked],
            [(1, 0), (2, 0), (2, 1)],
        )

    def test_ranking_is_deterministic(self):
        chunks = [
            self._chunk(1, 0, "qualified leads policy follow up"),
            self._chunk(2, 0, "qualified leads"),
        ]
        a = retrieval.rank_chunks(
            query="qualified leads", chunks=chunks, limit=5
        )
        b = retrieval.rank_chunks(
            query="qualified leads", chunks=chunks, limit=5
        )
        self.assertEqual(a, b)


# =========================================================
# 7A/7D - CONTROLLED INGESTION
# =========================================================


@override_settings(RAG_CHUNK_SIZE=120, RAG_CHUNK_OVERLAP=20)
class KnowledgeIngestionServiceTests(TestCase):

    def test_ingest_creates_document_and_chunks(self):
        doc = knowledge_services.ingest_document(
            title="Follow-up policy",
            source_reference="policy/followup",
            text=(
                "Qualified leads must be contacted within two "
                "business days. A follow-up task is required "
                "after every proposal is sent to the lead."
            ),
        )
        self.assertEqual(KnowledgeDocument.objects.count(), 1)
        self.assertGreaterEqual(doc.chunks.count(), 1)
        self.assertEqual(doc.source_type, "manual")
        self.assertTrue(doc.active)

    def test_normalized_text_collapses_whitespace(self):
        doc = knowledge_services.ingest_document(
            title="Notes",
            source_reference="notes/1",
            text="line one\n\n   line   two\t\tline three",
        )
        self.assertEqual(
            doc.normalized_text,
            "line one line two line three",
        )

    def test_repeated_ingestion_updates_in_place(self):
        knowledge_services.ingest_document(
            title="Policy v1",
            source_reference="policy/followup",
            text="Contact qualified leads within three days.",
        )
        doc = knowledge_services.ingest_document(
            title="Policy v2",
            source_reference="policy/followup",
            text="Contact qualified leads within two days.",
        )
        self.assertEqual(KnowledgeDocument.objects.count(), 1)
        self.assertEqual(doc.title, "Policy v2")
        self.assertIn("two days", doc.normalized_text)
        # chunks rebuilt, indices contiguous from 0
        indices = list(
            doc.chunks.values_list("chunk_index", flat=True)
        )
        self.assertEqual(indices, list(range(len(indices))))

    def test_reindex_rebuilds_chunks(self):
        doc = knowledge_services.ingest_document(
            title="Doc",
            source_reference="doc/1",
            text="alpha beta gamma delta epsilon zeta",
        )
        KnowledgeChunk.objects.filter(document=doc).delete()
        count = knowledge_services.reindex_document(
            document_id=doc.id
        )
        self.assertEqual(count, doc.chunks.count())
        self.assertGreaterEqual(count, 1)

    def test_empty_text_is_rejected(self):
        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="Empty",
                source_reference="empty/1",
                text="   \n\t ",
            )

    def test_unapproved_source_type_is_rejected(self):
        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="Bad",
                source_reference="bad/1",
                text="content",
                source_type="web_scrape",
            )

    def test_missing_source_reference_is_rejected(self):
        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="NoRef",
                source_reference="  ",
                text="content",
            )

    def test_secret_like_content_is_rejected(self):
        with self.assertRaises(
            knowledge_services.KnowledgeIngestionError
        ):
            knowledge_services.ingest_document(
                title="Env dump",
                source_reference="env/1",
                text="OPENAI_API_KEY=sk-proj-do-not-store-this",
            )


# =========================================================
# 7B - RETRIEVAL SERVICE
# =========================================================


@override_settings(
    RAG_CHUNK_SIZE=200,
    RAG_CHUNK_OVERLAP=20,
    RAG_RETRIEVAL_LIMIT=5,
)
class RetrieveKnowledgeServiceTests(TestCase):

    def setUp(self):
        knowledge_services.ingest_document(
            title="Follow-up policy",
            source_reference="policy/followup",
            text=(
                "Qualified leads must be contacted within two "
                "business days and always receive a follow-up task."
            ),
        )
        knowledge_services.ingest_document(
            title="Refund policy",
            source_reference="policy/refund",
            text=(
                "Refund requests are processed within seven days "
                "by the finance team."
            ),
        )

    def test_finds_relevant_document(self):
        result = knowledge_services.retrieve_knowledge(
            query="how soon must qualified leads be contacted",
        )
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["result_count"], 1)
        top = result["evidence"][0]
        self.assertEqual(top["document_title"], "Follow-up policy")
        for key in (
            "document_id",
            "document_title",
            "source_type",
            "source_reference",
            "chunk_id",
            "chunk_index",
            "content",
            "score",
        ):
            self.assertIn(key, top)

    def test_empty_query_is_rejected(self):
        result = knowledge_services.retrieve_knowledge(query="   ")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "INVALID_QUERY")

    def test_limit_is_enforced(self):
        result = knowledge_services.retrieve_knowledge(
            query="policy", limit=1
        )
        self.assertTrue(result["success"])
        self.assertLessEqual(len(result["evidence"]), 1)

    def test_inactive_documents_are_excluded(self):
        doc = KnowledgeDocument.objects.get(
            source_reference="policy/followup"
        )
        knowledge_services.set_document_active(
            document_id=doc.id, active=False
        )
        result = knowledge_services.retrieve_knowledge(
            query="qualified leads contacted business days",
        )
        titles = [
            e["document_title"] for e in result["evidence"]
        ]
        self.assertNotIn("Follow-up policy", titles)

    def test_retrieval_result_is_json_safe(self):
        import json

        result = knowledge_services.retrieve_knowledge(
            query="refund finance team seven days",
        )
        json.dumps(result["evidence"])


# =========================================================
# ARCHITECTURE BOUNDARY
# =========================================================


class KnowledgeArchitectureSafetyTests(TestCase):

    ORM_OWNING_MODULES = {
        "models.py",
        "services.py",
        "tests.py",
    }

    FORBIDDEN = (".objects.", ".objects(")

    def test_orchestration_modules_have_no_direct_orm(self):
        base = Path(__file__).resolve().parent
        violations = []
        for path in base.rglob("*.py"):
            if path.name in self.ORM_OWNING_MODULES:
                continue
            if "migrations" in path.parts:
                continue
            if "__pycache__" in path.parts:
                continue
            src = path.read_text(encoding="utf-8")
            for pattern in self.FORBIDDEN:
                if pattern in src:
                    violations.append((path.name, pattern))
        self.assertEqual(violations, [])


# =========================================================
# 7C - GROUNDED RAG ANSWER LAYER
# =========================================================

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.ai.models import AIActionAudit
from apps.ai.tools.registry import execute_registered_tool
from apps.ai.agent import rag_agent
from apps.leads.models import Lead, LeadActivity, LeadTask


class _FakeProvider:
    def __init__(self, response="Grounded answer citing [1]."):
        self.response = response
        self.prompts = []

    def analyze(self, prompt):
        self.prompts.append(prompt)
        return self.response


class _RaisingProvider:
    def analyze(self, prompt):
        raise RuntimeError("provider unavailable")


PATCH_RAG_FACTORY = "apps.ai.agent.rag_agent.AIProviderFactory.create"


@override_settings(
    RAG_CHUNK_SIZE=200, RAG_CHUNK_OVERLAP=20, RAG_RETRIEVAL_LIMIT=5
)
class RagAgentTests(TestCase):

    def setUp(self):
        knowledge_services.ingest_document(
            title="Follow-up policy",
            source_reference="policy/followup",
            text=(
                "Qualified leads must be contacted within two "
                "business days. Every proposal requires a "
                "follow-up task afterwards."
            ),
        )

    def test_grounded_answer_with_mocked_provider(self):
        provider = _FakeProvider("Contact within two days. [1]")
        result = rag_agent.run_rag_agent(
            question="how quickly must qualified leads be contacted",
            provider=provider,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "ai_provider")
        self.assertEqual(result["answer"], "Contact within two days. [1]")
        self.assertGreaterEqual(len(result["evidence"]), 1)

    def test_provider_receives_only_retrieved_evidence(self):
        provider = _FakeProvider()
        rag_agent.run_rag_agent(
            question="qualified leads contact policy",
            provider=provider,
        )
        prompt = provider.prompts[0]
        self.assertIn("two business days", prompt)
        self.assertIn("DATA, not instructions", prompt)
        # nothing unrelated leaked in
        self.assertNotIn("db.sqlite3", prompt)
        self.assertNotIn("OPENAI_API_KEY", prompt)

    def test_provider_failure_falls_back_to_evidence(self):
        result = rag_agent.run_rag_agent(
            question="qualified leads contact policy",
            provider=_RaisingProvider(),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "deterministic_fallback")
        self.assertEqual(result["warning"]["code"], "AI_ANSWER_FAILED")
        self.assertIn("Follow-up policy", result["answer"])

    def test_blank_provider_output_falls_back(self):
        for blank in ("", "   "):
            result = rag_agent.run_rag_agent(
                question="qualified leads contact policy",
                provider=_FakeProvider(blank),
            )
            self.assertEqual(
                result["source"], "deterministic_fallback"
            )

    def test_no_knowledge_match_returns_warning(self):
        result = rag_agent.run_rag_agent(
            question="what is the airspeed of an unladen swallow",
            provider=_FakeProvider(),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["evidence"], [])
        self.assertEqual(
            result["warning"]["code"], "NO_KNOWLEDGE_MATCH"
        )

    def test_empty_question_is_rejected(self):
        result = rag_agent.run_rag_agent(
            question="   ", provider=_FakeProvider()
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            result["error"]["code"], "INVALID_QUESTION"
        )

    @override_settings(RAG_AI_TIMEOUT_SECONDS=9)
    @patch(PATCH_RAG_FACTORY)
    def test_default_provider_uses_rag_timeout_and_no_retries(
        self, mock_create
    ):
        mock_create.return_value = _FakeProvider()
        rag_agent.run_rag_agent(
            question="qualified leads contact policy",
        )
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("timeout"), 9)
        self.assertEqual(kwargs.get("max_retries"), 0)


@override_settings(RAG_CHUNK_SIZE=200, RAG_CHUNK_OVERLAP=20)
class SearchKnowledgeToolTests(TestCase):

    def setUp(self):
        knowledge_services.ingest_document(
            title="Refund policy",
            source_reference="policy/refund",
            text="Refunds are processed within seven days.",
        )

    def test_tool_is_registered_read_only(self):
        from apps.ai.tools.registry import get_registered_tool

        tool = get_registered_tool("search_knowledge")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.access_level, "read")

    def test_runs_through_read_executor(self):
        result = execute_registered_tool(
            name="search_knowledge",
            arguments={"query": "refund processed seven days"},
        )
        self.assertTrue(result["success"])
        self.assertGreaterEqual(len(result["data"]), 1)
        json.dumps(result["data"])

    def test_invalid_query_and_limit_rejected(self):
        r1 = execute_registered_tool(
            name="search_knowledge", arguments={"query": "  "}
        )
        self.assertFalse(r1["success"])
        r2 = execute_registered_tool(
            name="search_knowledge",
            arguments={"query": "refund", "limit": 99},
        )
        self.assertFalse(r2["success"])

    def test_tool_does_not_mutate_crm(self):
        before = (
            Lead.objects.count(),
            LeadTask.objects.count(),
            LeadActivity.objects.count(),
            AIActionAudit.objects.count(),
        )
        execute_registered_tool(
            name="search_knowledge",
            arguments={"query": "refund"},
        )
        self.assertEqual(
            before,
            (
                Lead.objects.count(),
                LeadTask.objects.count(),
                LeadActivity.objects.count(),
                AIActionAudit.objects.count(),
            ),
        )


@override_settings(RAG_CHUNK_SIZE=200, RAG_CHUNK_OVERLAP=20)
class KnowledgeAssistantViewTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create(
            username="k-staff", is_staff=True
        )
        self.plain = User.objects.create(
            username="k-plain", is_staff=False
        )
        knowledge_services.ingest_document(
            title="Follow-up policy",
            source_reference="policy/followup",
            text=(
                "Qualified leads must be contacted within two "
                "business days."
            ),
        )

    def test_anonymous_and_non_staff_rejected(self):
        self.assertNotEqual(
            self.client.get(
                reverse("knowledge:assistant")
            ).status_code,
            200,
        )
        self.client.force_login(self.plain)
        self.assertNotEqual(
            self.client.get(
                reverse("knowledge:assistant")
            ).status_code,
            200,
        )

    def test_staff_can_open_assistant(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("knowledge:assistant"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dodong Knowledge Assistant")
        self.assertContains(response, "Follow-up policy")

    def test_ask_renders_grounded_answer(self):
        self.client.force_login(self.staff)
        with patch(
            PATCH_RAG_FACTORY,
            return_value=_FakeProvider("Two business days. [1]"),
        ):
            response = self.client.post(
                reverse("knowledge:assistant_ask"),
                {"question": "how fast to contact qualified leads"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two business days.")
        self.assertContains(response, "ai_provider")

    def test_ask_renders_fallback_on_provider_failure(self):
        self.client.force_login(self.staff)
        with patch(
            PATCH_RAG_FACTORY,
            side_effect=RuntimeError("down"),
        ):
            response = self.client.post(
                reverse("knowledge:assistant_ask"),
                {"question": "how fast to contact qualified leads"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "deterministic_fallback")
        self.assertContains(response, "AI_ANSWER_FAILED")


# =========================================================
# 7E - PHASE 7 END-TO-END ACCEPTANCE
# =========================================================


@override_settings(
    RAG_CHUNK_SIZE=160, RAG_CHUNK_OVERLAP=20, RAG_RETRIEVAL_LIMIT=5
)
class Phase7RagAcceptanceTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create(
            username="p7-staff", is_staff=True
        )

    def _crm_snapshot(self):
        return (
            Lead.objects.count(),
            LeadTask.objects.count(),
            LeadActivity.objects.count(),
            AIActionAudit.objects.count(),
        )

    def test_end_to_end_ingest_retrieve_answer(self):
        baseline = self._crm_snapshot()

        knowledge_services.ingest_document(
            title="Qualified lead follow-up policy",
            source_reference="policy/qualified-followup",
            text=(
                "When a lead becomes qualified, contact them "
                "within two business days and create a follow-up "
                "task. Escalate if no response after five days."
            ),
        )

        doc = KnowledgeDocument.objects.get(
            source_reference="policy/qualified-followup"
        )
        self.assertGreaterEqual(doc.chunks.count(), 1)

        provider = _FakeProvider(
            "Contact qualified leads within two business days. [1]"
        )
        result = rag_agent.run_rag_agent(
            question="how should we follow up with qualified leads",
            provider=provider,
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "ai_provider")
        self.assertGreaterEqual(len(result["evidence"]), 1)
        self.assertEqual(
            result["evidence"][0]["document_title"],
            "Qualified lead follow-up policy",
        )

        # nothing in CRM changed
        self.assertEqual(self._crm_snapshot(), baseline)

    def test_repeated_ingestion_is_controlled(self):
        for text in (
            "Contact qualified leads within three days.",
            "Contact qualified leads within two days.",
            "Contact qualified leads within two days. Always log it.",
        ):
            knowledge_services.ingest_document(
                title="Policy",
                source_reference="policy/qualified-followup",
                text=text,
            )
        self.assertEqual(KnowledgeDocument.objects.count(), 1)
        doc = KnowledgeDocument.objects.get()
        self.assertIn("Always log it", doc.normalized_text)
        indices = list(
            doc.chunks.values_list("chunk_index", flat=True)
        )
        self.assertEqual(indices, list(range(len(indices))))

    def test_inactive_knowledge_is_excluded_end_to_end(self):
        knowledge_services.ingest_document(
            title="Secret internal policy",
            source_reference="policy/secret",
            text="Qualified leads get a personal call from the CEO.",
            active=False,
        )
        result = rag_agent.run_rag_agent(
            question="what do qualified leads get",
            provider=_FakeProvider(),
        )
        self.assertEqual(result["evidence"], [])
        self.assertEqual(result["warning"]["code"], "NO_KNOWLEDGE_MATCH")

    def test_provider_gets_only_approved_evidence(self):
        knowledge_services.ingest_document(
            title="Policy A",
            source_reference="policy/a",
            text="Qualified leads are contacted within two days.",
        )
        knowledge_services.ingest_document(
            title="Unrelated invoices doc",
            source_reference="doc/invoices",
            text="Invoices are due net thirty from receipt.",
        )
        provider = _FakeProvider()
        rag_agent.run_rag_agent(
            question="qualified leads contact timing",
            provider=provider,
        )
        prompt = provider.prompts[0]
        self.assertIn("within two days", prompt)
        self.assertNotIn("net thirty", prompt)

    def test_provider_failure_still_succeeds_with_evidence(self):
        knowledge_services.ingest_document(
            title="Policy",
            source_reference="policy/x",
            text="Qualified leads are contacted within two days.",
        )
        result = rag_agent.run_rag_agent(
            question="qualified leads contact timing",
            provider=_RaisingProvider(),
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "deterministic_fallback")
        self.assertIn("Policy", result["answer"])

    def test_no_secret_material_can_be_ingested(self):
        for bad in (
            "OPENAI_API_KEY=sk-proj-should-never-store",
            "-----BEGIN RSA PRIVATE KEY-----",
            "db password=supersecret",
        ):
            with self.assertRaises(
                knowledge_services.KnowledgeIngestionError
            ):
                knowledge_services.ingest_document(
                    title="bad",
                    source_reference=f"bad/{len(bad)}",
                    text=bad,
                )
        self.assertEqual(KnowledgeDocument.objects.count(), 0)

    def test_rag_never_invokes_confirmed_write_path(self):
        knowledge_services.ingest_document(
            title="Policy",
            source_reference="policy/x",
            text="Qualified leads are contacted within two days.",
        )
        with patch(
            "apps.ai.tools.registry.execute_confirmed_write_tool"
        ) as mock_write, patch(
            "apps.ai.agent.write_executor.execute_confirmed_proposal"
        ) as mock_exec:
            rag_agent.run_rag_agent(
                question="qualified leads contact timing",
                provider=_FakeProvider(),
            )
            rag_agent.run_rag_agent(
                question="qualified leads contact timing",
                provider=_RaisingProvider(),
            )
        mock_write.assert_not_called()
        mock_exec.assert_not_called()

    def test_read_executor_still_refuses_write_tools(self):
        for name in (
            "create_lead_task",
            "complete_lead_task",
            "change_lead_status",
            "add_lead_note",
        ):
            result = execute_registered_tool(
                name=name, arguments={}
            )
            self.assertFalse(result["success"])
            self.assertEqual(
                result["error"]["code"], "TOOL_ACCESS_DENIED"
            )

    def test_rag_and_knowledge_modules_have_no_direct_orm(self):
        targets = [
            Path(rag_agent.__file__),
            Path(knowledge_services.__file__).parent / "chunking.py",
            Path(knowledge_services.__file__).parent / "retrieval.py",
            Path(knowledge_services.__file__).parent / "views.py",
            Path(knowledge_services.__file__).parent / "admin.py",
        ]
        for path in targets:
            src = path.read_text(encoding="utf-8")
            self.assertNotIn(".objects", src, msg=path.name)

    def test_no_crm_or_audit_mutation_across_full_flow(self):
        baseline = self._crm_snapshot()
        knowledge_services.ingest_document(
            title="Policy",
            source_reference="policy/x",
            text="Qualified leads are contacted within two days.",
        )
        knowledge_services.reindex_document(
            document_id=KnowledgeDocument.objects.get().id
        )
        rag_agent.run_rag_agent(
            question="qualified leads contact timing",
            provider=_FakeProvider(),
        )
        rag_agent.run_rag_agent(
            question="qualified leads contact timing",
            provider=_RaisingProvider(),
        )
        execute_registered_tool(
            name="search_knowledge",
            arguments={"query": "qualified leads"},
        )
        self.assertEqual(self._crm_snapshot(), baseline)
