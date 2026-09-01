# Dodong OS Implementation Roadmap

This document tracks the actual implementation progress of Dodong OS.

For the broader long-term product, learning, AI, engineering, and business vision, see `MASTER_ROADMAP.md`.

---

# Current Position

**Current Phase:** Phase 6 — Background Automation (design proposed; not yet implemented). Phase 9 — Controlled AI CRM Agent is complete.

**Automated test baseline:** 322 passing tests

Canonical test command (from `backend/`): `python manage.py test`

```text
Phase 1     Foundation                    ✅
Phase 2     AI Prototype                  ✅
Phase 3     AI Provider Layer             ✅
Phase 4     Lead Scanner                  🟡 Iterative
Phase 5     CRM Foundation                ✅
Phase 5.5   Agent-Ready CRM Tool Layer    ✅
Phase 5.6   Documentation Sync            ✅
Phase 6     Background Automation         📐 DESIGN PROPOSED
Phase 7     RAG / AI Memory               ⏳
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

# Phase 6 — Background Automation (design proposed, not yet implemented)

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

# Not started

- **Phase 7 — RAG / AI Memory:** no vector store or retrieval layer yet.
- **Phase 10 — Production Hardening**
- **Phase 11 — Dodong OS v1.0**
