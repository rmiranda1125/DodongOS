# Dodong OS Implementation Roadmap

This document tracks the actual implementation progress of Dodong OS.

For the broader long-term product, learning, AI, engineering, and business vision, see `MASTER_ROADMAP.md`.

---

# Current Position

**Current Phase:** Phase 9 — Controlled AI CRM Agent (lead-note vertical; 9E3 complete)

**Automated test baseline:** 305 passing tests

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

**Confirmed write actions**

| Action              | Proposal | Confirmed executor | Natural language + UI | Acceptance coverage |
|---------------------|----------|--------------------|-----------------------|---------------------|
| create_lead_task    | ✅       | ✅                 | ✅                    | ✅                  |
| complete_lead_task  | ✅       | ✅                 | ✅                    | ✅                  |
| change_lead_status  | ✅       | ✅                 | ✅                    | ✅                  |
| add_lead_note (9E)  | ✅ (9E1) | ✅ (9E2)           | ✅ (9E3)              | — (9E4, undefined)  |

**Not yet scoped:** 9E4 acceptance coverage for the lead-note flow, and any
further write actions (edit/delete note, etc.).

---

# Not started

- **Phase 6 — Background Automation:** no task queue / scheduler infrastructure yet.
- **Phase 7 — RAG / AI Memory:** no vector store or retrieval layer yet.
- **Phase 10 — Production Hardening**
- **Phase 11 — Dodong OS v1.0**
