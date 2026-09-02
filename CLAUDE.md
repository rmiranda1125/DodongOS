# Dodong OS Claude Instructions

## Stack
Django + HTMX + PostgreSQL.

## Architecture
AI must never access Django ORM directly.

Read:
Agent → Tool Registry → CRM Tool → CRM Service → ORM

Write:
Proposal → signed token → explicit confirmation → confirmed write executor → CRM Tool → CRM Service → ORM → verification → audit

## Safety
- No direct ORM inside apps/ai/agent/.
- execute_registered_tool() is read-only.
- Writes use execute_confirmed_write_tool().
- Conversational Yes/Confirm/Go ahead/Do it never confirms writes.
- Preserve signed-token and replay protection.
- Do not enable delete, bulk, autonomous, or arbitrary writes.
- Do not weaken tests to make them pass.

## Working style
- Inspect code before editing.
- Make minimal scoped changes.
- Do not rewrite working code unnecessarily.
- Run focused tests first, then:
  python manage.py check
  python manage.py test apps.leads.tests apps.ai.tests
- Do not commit/push unless explicitly requested.
- Keep responses concise and avoid repeating context.