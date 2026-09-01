# Dodong OS Implementation Roadmap

This document tracks the actual implementation progress of Dodong OS.

For the broader long-term product, learning, AI, engineering, and business vision, see `MASTER_ROADMAP.md`.

---

# Current Position

**Current Phase:** Phase 10 — Production Hardening (not started). Phases 6, 7 and 9 are complete.

**Automated test baseline:** 483 passing tests

Canonical test command (from `backend/`): `python manage.py test`

```text
Phase 1     Foundation                    ✅
Phase 2     AI Prototype                  ✅
Phase 3     AI Provider Layer             ✅
Phase 4     Lead Scanner                  🟡 Iterative
Phase 5     CRM Foundation                ✅
Phase 5.5   Agent-Ready CRM Tool Layer    ✅
Phase 5.6   Documentation Sync            ✅
Phase 6     Background Automation         ✅
Phase 7     RAG / AI Memory               ✅
Phase 8     CRM Read Agent                ✅
Phase 9     Controlled AI CRM Agent       ✅
Phase 10    Production Hardening          ⏳
Phase 11    Dodong OS v1.0               ⏳
```

---

# Phase 9 — Controlled AI CRM Agent — ✅ COMPLETE

Confirmed-write architecture:
`AI Agent → Agent Tools → CRM Services → Django ORM`, with every mutation gated by
`proposal → signed token → explicit Confirm button → confirmed write executor → CRM service → verification → AIActionAudit`.

**Shared write infrastructure — ✅ complete**
Proposal boundary, signed proposal tokens, replay protection, confirmed-write
executor, and audit visibility (`AIActionAudit`).

**Approved controlled write actions** (all with proposal → signed token →
confirm → executor → verification → audit, and full acceptance coverage):

1. `create_lead_task`
2. `complete_lead_task`
3. `change_lead_status`
4. `add_lead_note`

| Action              | Proposal | Confirmed executor | Natural language + UI | Acceptance coverage |
|---------------------|----------|--------------------|-----------------------|---------------------|
| create_lead_task    | ✅       | ✅                 | ✅                    | ✅                  |
| complete_lead_task  | ✅       | ✅                 | ✅                    | ✅                  |
| change_lead_status  | ✅       | ✅                 | ✅                    | ✅                  |
| add_lead_note       | ✅       | ✅                 | ✅                    | ✅                  |

**Phase 9E — Controlled Lead Notes — ✅ COMPLETE**

- 9E1 Proposal boundary ✅
- 9E2 Confirmed execution ✅
- 9E3 Natural-language + UI ✅
- 9E4 Acceptance + safety ✅

**Open design decision (not yet resolved):** `LeadActivity.description` has no
length limit anywhere in the stack (model `TextField()`, proposal builder,
write tool, router capture group, and UI template are all unbounded). No
limit has been added — needs an explicit decision before it's treated as
settled.

Phase 9 is closed. No Phase 9F is defined.

---

# Phase 6 — Background Automation — ✅ COMPLETE

Scheduled, deterministic detection of CRM conditions (due-soon tasks, stale
leads) persisted as a deduplicated digest, with an optional, non-authoritative
AI summary layered on top. No autonomous CRM writes; no email/Slack.

**Subphase status**

| Sub | Scope | Status |
|---|---|---|
| 6A | Scheduling foundation — `apps.automation`, `run_crm_checks`, `ScheduledCheckRun` | ✅ |
| 6B | Deterministic checks — `get_due_soon_tasks` / `get_stale_leads` services + read tools | ✅ |
| 6C | `CRMDigest` persistence + dedup (`<finding_type>:<id>` key) + resolve/reopen | ✅ |
| 6D | Optional AI summary via `apps.ai.providers.factory`; deterministic fallback | ✅ |
| 6E1 | Summary outcome persisted on `ScheduledCheckRun`; staff run-history page `/automation/runs/`; read-only admin | ✅ |
| 6E2 | Overlap protection, stale-run recovery, bounded AI timeout, full acceptance suite | ✅ |

**Final architecture**

```
external scheduler (cron / Azure WebJob / Task Scheduler)
  → manage.py run_crm_checks
      → services.start_check_run()        # overlap guard + stale recovery (ORM)
      → checks.run_all_checks()           # no ORM; reads via apps/ai/tools/crm/* read tools
          → leads/reminders.py            # deterministic, read-only (ORM)
      → digest.persist_findings()         # no ORM; shapes findings
          → services.sync_digest_findings()  # CRMDigest upsert + resolve, atomic (ORM)
      → summary.summarize_digest()        # no ORM; bounded-timeout provider, always falls back
      → services.record_run_summary()     # persists summary_status/source/text/error (ORM)
      → services.finish_check_run_succeeded()  # or finish_check_run_failed() on deterministic failure
  staff view /automation/runs/            # no ORM; reads via services.get_recent_check_runs()
```

ORM boundary (architecture-tested): `checks.py`, `digest.py`, `summary.py`,
`views.py`, and `management/commands/` contain **no** `.objects` access; all
persistence goes through `apps/automation/services.py` /
`apps/automation/models.py` and `apps/leads/services.py` /
`apps/leads/reminders.py`.

**Guarantees**

- Deterministic checks + digest persistence define run success. An AI
  timeout/error is *degradation*: run stays `succeeded`,
  `summary_status=AI_SUMMARY_FAILED`, `summary_source=deterministic_fallback`,
  fallback text + error persisted, `CRMDigest` untouched.
- A deterministic check/digest failure marks the run `failed`, resolves
  nothing, and persists no AI outcome.
- Digest rows are deduplicated by identity; repeated runs increment
  `occurrence_count`; an absent finding is resolved **only** by a fully
  successful run; a resolved finding reopens the same row.
- No `Lead` / `LeadTask` / `LeadActivity` / `AIActionAudit` mutation anywhere
  in the pipeline; the confirmed-write executor is never invoked.

**Settings** (env-tunable; defaults are conservative product decisions):

| Setting | Default | Purpose |
|---|---|---|
| `CRM_DUE_SOON_HOURS` | 48 | due-soon task horizon |
| `CRM_STALE_LEAD_DAYS` | 14 | stale-lead inactivity threshold |
| `CRM_AUTOMATION_STALE_RUN_MINUTES` | 30 | a `running` row older than this is recovered as `failed` (`STALE_RUN_RECOVERED`) |
| `CRM_AUTOMATION_AI_TIMEOUT_SECONDS` | 15 | bounded provider network timeout for the automation summary only (interactive AI unaffected); automation also uses `max_retries=0` |

**Concurrency:** `start_check_run()` serializes on `ScheduledCheckRun`
(`select_for_update` + `status="running"` check); a non-stale running row
raises `OverlappingRunError` and the command exits cleanly without touching
CRM data. This is a durable single-host coordination record, not a
distributed lock.

**Known remaining hardening (deferred, not blocking Phase 6):**

- `get_stale_leads` evaluates the last-activity rule in Python over all
  active leads; move to a DB annotation if lead volume grows.
- `/automation/runs/` and `get_recent_check_runs` are capped at 50 with no
  pagination.
- No partial index on `CRMDigest(resolved_at IS NULL)`.
- `select_for_update` is a no-op on SQLite (dev/test); real row locking
  requires the PostgreSQL deployment.

---

## Original Phase 6 design notes (retained for reference)

Goal: scheduled, deterministic detection of CRM conditions (overdue tasks,
due follow-ups, stale leads, operational reminders), with an optional AI
summary layered on top. No autonomous CRM writes.

**ORM boundary within `apps/automation`** (correction to the original
"no ORM anywhere in automation" framing — automation needs legitimate
persistence for its own run/digest records):

| Layer | ORM allowed? |
|---|---|
| `apps/automation/checks.py` | ❌ no — orchestration only, reads via `apps/ai/tools/crm/*` |
| `apps/automation/digest.py` | ❌ no — orchestration only |
| `apps/automation/summary.py` | ❌ no — orchestration only |
| `apps/automation/management/commands/` | ❌ no — orchestration only |
| `apps/automation/models.py` | ✅ yes — defines `ScheduledCheckRun` / `CRMDigest` |
| `apps/automation/services.py` | ✅ yes — owns `ScheduledCheckRun`/`CRMDigest` persistence |
| `apps/leads/services.py`, `apps/leads/reminders.py` | ✅ yes — existing CRM domain owner |

Orchestration code (`checks.py`, `digest.py`, `summary.py`, the management
command) must reach `ScheduledCheckRun`/`CRMDigest` only through
`apps/automation/services.py` — never through `.objects.*` directly. This
mirrors the existing rule that `apps/ai/agent/*` never touches the ORM
directly and instead goes through CRM services/tools; the automation app
gets its own equivalent services module rather than being lumped under the
same "zero ORM" blanket rule as the read/write agent directories, since it
owns its own persistence.

**Subphases**

- **6A — Scheduling foundation.** New `apps.automation` app. A single
  `python manage.py run_crm_checks` management command as the entrypoint
  (no checks yet). New `ScheduledCheckRun` model (mirrors `AIActionAudit`'s
  durable-record pattern), with all ORM operations on it behind
  `apps/automation/services.py`, for observability and run-concurrency
  guarding.
- **6B — Deterministic CRM checks.** Read-only "Finding" detectors: reuse
  `get_overdue_tasks_tool`/`get_pending_tasks_tool` as-is; add
  `get_due_soon_tasks` and `get_stale_leads` CRM services (`apps/leads/`)
  exposed as new read tools (`apps/ai/tools/crm/`), orchestrated from
  `apps/automation/checks.py` through the existing read-tool layer only.
- **6C — Notification/digest layer.** New `CRMDigest` model persists each
  run's findings with dedup (same `finding_type` + lead within a lookback
  window is not re-surfaced). Delivery stays in-repo (admin/dashboard) —
  no email/Slack integration yet.
- **6D — AI summary layer.** Optional prose summary over the digest via the
  existing `apps.ai.providers.factory` abstraction (same pattern as the
  read agent). Additive and non-authoritative: the deterministic digest is
  always produced/shown even if the AI summary call fails.
- **6E — Acceptance/observability.** End-to-end acceptance suite proving
  the pipeline is fully read-only (zero `Lead`/`LeadTask`/`LeadActivity`/
  `AIActionAudit` mutations), idempotent across repeated runs, degrades
  gracefully without an AI provider, and does not regress Phase 8/9. A
  staff-only run-history view mirrors the existing `crm_action_audit` page.

**Recommended first implementation milestone:** 6A only — the app skeleton,
`ScheduledCheckRun` model/migration, and a `run_crm_checks` command that
runs zero checks yet, proven idempotent and read-only by its own tests.

**Scheduler approach:** plain Django management command invoked by an
external OS-level trigger (cron / Azure App Service scheduled WebJob /
Windows Task Scheduler for local dev) — not Celery/APScheduler. The current
stack has no broker or task-queue dependency (`requirements.txt` is Django +
django-environ + django-htmx + psycopg only); a command-plus-external-cron
approach needs no new infrastructure and keeps each run a single idempotent
process. Revisit only if concurrency/latency needs grow.

**New models/services:** `ScheduledCheckRun` (6A), `CRMDigest` (6C); new
read-only service functions in `apps/leads/` (`get_due_soon_tasks`,
`get_stale_leads`) and corresponding `apps/ai/tools/crm/` read tools; no
changes to any existing write path or model.

**Failure/retry/idempotency:** checks are pure reads recomputed fresh each
run, so re-running is inherently safe; idempotency is enforced at 6A (a
run-concurrency guard so overlapping trigger firings don't double-run) and
at 6C (digest dedup so a repeat run doesn't resurface the same finding).
No automatic retry of failed runs in this design — a failed
`ScheduledCheckRun` is left visible for a human to notice via 6E, not
auto-retried.

**Explicitly out of scope for Phase 6:** any autonomous CRM write, any new
confirmed-write action, email/SMS/Slack delivery channels, an in-process
scheduler daemon, and resolving the Phase 9E note-length-limit question.

**Test strategy:** matches the existing house style — one `TestCase` per
new service/tool (deterministic, no provider mocking needed for 6A–6C), an
architecture test extending the existing ORM-boundary scan
(`CRMReadAgentArchitectureSafetyTests`-style) to the orchestration-only
modules (`checks.py`, `digest.py`, `summary.py`, `management/commands/`) —
not `models.py`/`services.py`, which legitimately use the ORM — a
mocked-provider test for 6D following the pattern already used for
`run_crm_read_agent_with_provider`, and a 9E4-style acceptance class for 6E.

**Migration/deployment impact:** one new Django app + two new models means
two small migrations; no changes to existing tables. Nothing in Phase 6
requires new infrastructure (no Redis, no broker, no new service) — only,
eventually, whatever OS-level scheduler the deployment target already
offers, which is a Phase 10 deployment concern, not app code.

---

# Phase 7 — RAG / AI Memory — ✅ COMPLETE

A safe, read-first knowledge/RAG capability. Deterministic knowledge
retrieval is the source of truth; the AI provider only rephrases retrieved
evidence and never has ORM access or write ability.

**Subphase status**

| Sub | Scope | Status |
|---|---|---|
| 7A | `apps.knowledge` app, `KnowledgeDocument` / `KnowledgeChunk` models, deterministic chunker | ✅ |
| 7B | Deterministic lexical retrieval + `search_knowledge` read tool | ✅ |
| 7C | `apps/ai/agent/rag_agent.py` grounded answer + deterministic fallback | ✅ |
| 7D | Controlled ingestion service + staff admin/reindex + knowledge assistant UI | ✅ |
| 7E | Full Phase 7 acceptance / safety / regression suite | ✅ |

**Architecture**

```
question
  → apps/ai/agent/rag_agent.run_rag_agent()          # no ORM
      → execute_registered_tool("search_knowledge")   # read-only registry path
          → apps/ai/tools/knowledge.search_knowledge_tool   # no ORM
              → apps/knowledge/services.retrieve_knowledge  # ORM (active chunks only)
                  → apps/knowledge/retrieval.rank_chunks    # pure lexical ranking
      → deterministic evidence  →  provider prompt (evidence only)
      → grounded answer   OR   deterministic evidence-only fallback

ingestion:
  approved source (manual / internal_note)
    → apps/knowledge/services.ingest_document()   # validate + secret guard
    → normalize → create/update KnowledgeDocument by (source_type, source_reference)
    → rebuild all KnowledgeChunk rows deterministically
staff admin: KnowledgeDocument add/change (save rebuilds chunks) + "Reindex selected"
staff UI:   GET/POST /assistant/knowledge/
```

**ORM boundary (architecture-tested):** `chunking.py`, `retrieval.py`,
`views.py`, `admin.py`, and `apps/ai/agent/rag_agent.py` contain **no**
`.objects` access. Only `apps/knowledge/models.py` and
`apps/knowledge/services.py` touch the knowledge ORM. `rag_agent.py` is
covered by the existing `apps/ai/agent/*` ORM-boundary test.

**Knowledge model**

- `KnowledgeDocument(title, source_type[manual|internal_note],
  source_reference, normalized_text, active, created_at, updated_at)` —
  unique `(source_type, source_reference)`; re-ingesting the same identity
  updates in place.
- `KnowledgeChunk(document FK, chunk_index, content, metadata JSON,
  created_at)` — unique `(document, chunk_index)`; always rebuilt as a set,
  never edited individually.

**Chunking:** deterministic; whitespace-normalized to single spaces; packs
words up to `RAG_CHUNK_SIZE` chars/chunk; consecutive chunks share up to
`RAG_CHUNK_OVERLAP` trailing chars; never empty; empty/whitespace input
rejected; no AI involved.

**Embedding / index strategy:** none — deterministic lexical index. The
deployment is SQLite with no pgvector, numpy, or embedding libraries.
`retrieval.rank_chunks` is a pure function returning the real stored
chunks, so a pgvector/embedding ranker can replace it later without
changing callers. **Deferred:** embeddings + pgvector, contingent on the
PostgreSQL deployment (Phase 10).

**Retrieval / ranking:** token-overlap score = (distinct query terms
present in chunk) + (total query-term occurrences / chunk token count);
ties break by `(document_id, chunk_index)`. Active documents only. Returns
JSON-safe evidence: `document_id/title`, `source_type/reference`,
`chunk_id/index`, `content`, `score`.

**RAG answer / fallback:** `run_rag_agent` → grounded answer via provider
when it returns non-blank text (`source="ai_provider"`); on provider
error, timeout, or blank output → deterministic answer listing the
retrieved evidence (`source="deterministic_fallback"`,
`warning.code="AI_ANSWER_FAILED"`); no evidence →
`warning.code="NO_KNOWLEDGE_MATCH"`. Never raises, never mutates, never
calls a write tool.

**Prompt-injection protections:** the prompt states retrieved excerpts are
DATA and any embedded command / system-prompt / policy override must be
ignored; only the application rules govern behaviour. It also forbids
fabrication, forbids claiming live CRM state or that any action was taken,
and forbids describing CRM writes. Ingestion additionally refuses obvious
secret material (`OPENAI_API_KEY`, private-key headers, `PASSWORD=`, …) and
only accepts `manual` / `internal_note` source types — no automatic
filesystem, `.env`, or bulk-CRM ingestion.

**Knowledge management route/admin:** staff-only knowledge assistant at
`/assistant/knowledge/` (query UI + document list). Document CRUD is Django
admin (`KnowledgeDocumentAdmin`); saving a document rebuilds its chunks via
the service, and a "Reindex selected documents" bulk action is provided.
`KnowledgeChunkAdmin` is read-only.

**Settings (env-tunable):** `RAG_CHUNK_SIZE`=800, `RAG_CHUNK_OVERLAP`=120,
`RAG_RETRIEVAL_LIMIT`=5, `RAG_AI_TIMEOUT_SECONDS`=15 (its own setting, not
shared with automation; RAG also uses `max_retries=0`).

**RAG + CRM read coexistence:** RAG does not replace the CRM read tools.
Operational/factual CRM questions still route to the deterministic CRM read
agent; knowledge/policy questions use `run_rag_agent`. **Deferred:**
automatic combined routing ("which overdue leads violate our follow-up
policy?") — for now a caller issues a CRM read and a RAG query separately.

**Observability:** the RAG result already carries `source`, evidence
count, and any `warning`. **Deferred:** persisting a retrieval/query log —
would expand scope and risk storing sensitive prompts.

**Deferred Phase 7 hardening (non-blocking):**
- embeddings + pgvector semantic retrieval (needs PostgreSQL)
- combined CRM+knowledge question routing
- retrieval/query observability persistence
- `retrieve_knowledge` loads all active chunks into memory then ranks in
  Python — fine at current scale, revisit with a DB-side prefilter or
  vector index as the corpus grows
- knowledge assistant page has no pagination on the document list

---

# Not started

- **Phase 10 — Production Hardening**
- **Phase 11 — Dodong OS v1.0**
