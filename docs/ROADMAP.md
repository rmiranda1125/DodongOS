# Dodong OS Implementation Roadmap

This document tracks the actual implementation progress of Dodong OS.

For the broader long-term product, learning, AI, engineering, and business vision, see `MASTER_ROADMAP.md`.

---

# Current Position

**Current Phase:** Phase 9 — Controlled AI CRM Agent (Phase 9E — Controlled Lead Notes — complete; Phase 9F not yet defined)

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
Phase 6     Background Automation         ⏳
Phase 7     RAG / AI Memory               ⏳
Phase 8     CRM Read Agent                ✅
Phase 9     Controlled AI CRM Agent       🔄 IN PROGRESS
Phase 10    Production Hardening          ⏳
Phase 11    Dodong OS v1.0               ⏳
```

---

# Phase 9 — Controlled AI CRM Agent

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

**Not yet scoped:** Phase 9F (next write action or capability) — not defined,
not started.

---

# Not started

- **Phase 6 — Background Automation:** no task queue / scheduler infrastructure yet.
- **Phase 7 — RAG / AI Memory:** no vector store or retrieval layer yet.
- **Phase 10 — Production Hardening**
- **Phase 11 — Dodong OS v1.0**
