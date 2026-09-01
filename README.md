# 🚀 Dodong OS

> **An AI-powered Business Intelligence, CRM, and Lead Intelligence Platform.**

Dodong OS is being built as an AI operating system for consultants, agencies, and small businesses.

The long-term goal is to evolve Dodong OS from a traditional CRM into an **AI CRM Agent** capable of observing CRM data, reasoning about business situations, recommending actions, and safely executing authorized CRM operations.

---

# Vision

Dodong OS aims to bring the consulting and client-acquisition workflow into one system.

The platform is being designed to:

* 🔍 Discover potential clients
* 🤖 Analyze companies using AI
* 📊 Score business opportunities
* 👥 Manage CRM relationships
* ✅ Track tasks and follow-ups
* 📝 Maintain activity history
* 📧 Assist with outreach
* 📈 Summarize pipeline health
* 🧠 Build long-term AI memory using RAG
* ⚡ Automate controlled business workflows
* 🤖 Eventually operate as an AI CRM employee

Instead of switching between many disconnected tools, Dodong OS aims to provide one controlled platform where AI can safely interact with business data and CRM operations.

---

# Current Status

**Updated:** September 2, 2026

## Current Development Stage

**Dodong OS v1.0.0 — release checkpoint.** The full implementation roadmap
(Phases 1–11) is complete; Phase 4 (Lead Scanner) continues iteratively.
Live Azure deployment is prepared but not yet executed
(`V1_RELEASE_READY_BUT_NOT_LIVE_DEPLOYED`).

Dodong OS provides: the CRM foundation (leads, pipeline, tasks, notes,
activities); a deterministic CRM Read Assistant; four controlled
confirmed-write actions (create task, complete task, change lead status, add
lead note), each gated by proposal → signed token → explicit Confirm →
verified executor → post-write verification → audit; deterministic
background automation with an optional AI digest summary and deterministic
fallback; a read-first RAG / knowledge assistant (lexical retrieval, no
embeddings) that treats retrieved text as data; and a hardened production
configuration (env-driven settings, PostgreSQL readiness, health/readiness
endpoints, WhiteNoise, gunicorn, Docker, GitHub Actions CI).

**Safe AI write model:** the AI layer never touches the ORM directly and can
never perform an autonomous CRM write. Every write needs an explicit human
Confirm with a valid, single-use, time-limited, tamper-evident signed
proposal token over a CSRF-protected POST. Conversational phrases never
confirm.

**Version:** 1.0.0 &nbsp;·&nbsp; **Tests:** 532 passing (`python manage.py test`,
zero real external AI calls) &nbsp;·&nbsp;
Roadmap: `docs/ROADMAP.md` &nbsp;·&nbsp;
Release notes: `docs/RELEASES/v1.0.0.md` &nbsp;·&nbsp;
Deployment: `docs/04_DEPLOYMENT/PRODUCTION.md`

### Completed

* ✅ Django application foundation
* ✅ HTMX integration
* ✅ Company management
* ✅ AI service layer
* ✅ AI provider abstraction
* ✅ GPT provider implementation
* ✅ Ollama fallback
* ✅ Company analysis framework
* ✅ Lead model
* ✅ CRM lead status pipeline
* ✅ Lead notes
* ✅ Lead activities
* ✅ Lead tasks
* ✅ Task priorities and statuses
* ✅ CRM service layer
* ✅ Pending-task detection
* ✅ Overdue-task detection
* ✅ Priority-task ranking
* ✅ Task completion
* ✅ Activity creation from task completion
* ✅ Lead lookup
* ✅ Lead search
* ✅ Lead-specific task retrieval
* ✅ Lead activity retrieval
* ✅ Pipeline summary
* ✅ Agent-ready CRM read tools
* ✅ Controlled read-only AI tool registry
* ✅ Structured tool inputs and outputs
* ✅ Structured AI-tool errors
* ✅ **532 automated tests passing** (CRM, AI, automation, RAG, production hardening, v1.0 acceptance)

---

# Current Architecture

Dodong OS now enforces a clear boundary between AI and the database.

```text
                 DODONG OS

                     User
                      |
                      v
              Future AI Agent
                      |
                      v
             Read-Only Tool Registry
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
        Leads        Tasks    Activities
          |           |           |
          +-----------+-----------+
                      |
                      v
                CRM Services
                      |
                      v
                 Django ORM
                      |
                      v
                   Database
```

The AI layer does **not** directly query or modify Django models.

The architectural rule is:

```text
AI
 ↓
Agent Tool
 ↓
CRM Service
 ↓
Validation / Permissions
 ↓
Django ORM
 ↓
Database
```

The AI must never bypass the service layer.

---

# Agent-Ready CRM Tool Layer

Phase 5.5 established the first controlled AI-facing CRM interface.

Eight read-only CRM tools are currently registered.

## Task Tools

### `get_priority_tasks`

Returns the highest-priority actionable CRM tasks.

### `get_overdue_tasks`

Returns overdue CRM tasks.

### `get_pending_tasks`

Returns pending and in-progress tasks.

Supports priority filtering.

### `get_lead_tasks`

Returns tasks belonging to a specific lead.

Supports:

* Lead ID
* Status
* Priority
* Result limit

---

## Lead Tools

### `get_lead`

Returns structured information for one CRM lead.

### `search_leads`

Searches CRM leads using fields such as:

* Company name
* Job title
* Industry
* Country
* Location
* AI summary
* CRM status

---

## Activity Tools

### `get_lead_activities`

Returns the activity history for a lead.

Supported activity types include:

* `note`
* `call`
* `email`
* `meeting`
* `follow_up`
* `status_changed`

---

## Pipeline Tools

### `get_pipeline_summary`

Returns structured CRM pipeline information including:

* Total leads
* Lead count by status
* Average score for scored leads

---

# Tool Registry

AI-accessible tools are registered through a controlled registry.

The registry provides:

* Tool name
* Description
* Access level
* Input schema
* Callable implementation

Current access level:

```text
READ ONLY
```

Only explicitly registered tools may execute.

Unknown tools are rejected.

Example flow:

```text
Requested Tool
      |
      v
Is Tool Registered?
      |
      v
Is Access Level READ?
      |
      v
Validate Arguments
      |
      v
Execute CRM Tool
      |
      v
CRM Service
      |
      v
Database
```

Write tools are intentionally not exposed yet.

---

# Structured Tool Responses

Tools return structured, JSON-safe results.

Example success response:

```json
{
  "success": true,
  "data": {
    "id": 12,
    "company_name": "Example Company",
    "status": "qualified"
  }
}
```

Example error:

```json
{
  "success": false,
  "error": {
    "code": "LEAD_NOT_FOUND",
    "message": "Lead 12 was not found."
  }
}
```

Django model instances are never returned directly to the AI.

---

# CRM Foundation

The current CRM supports the following core objects.

## Lead

Lead information includes:

* Company information
* Job information
* Source information
* Work setup
* Employment type
* Location
* Salary
* AI results
* Lead score
* AI summary
* Recommended services
* Pain points
* CRM status
* Timestamps

### Lead Statuses

```text
new
contacted
qualified
proposal
won
lost
```

---

## Lead Notes

Notes can be attached to CRM leads for internal context and relationship tracking.

---

## Lead Activities

CRM activity types include:

```text
note
call
email
meeting
follow_up
status_changed
```

Activities form a historical timeline for each lead.

---

## Lead Tasks

Lead tasks support:

* Lead
* Title
* Description
* Task type
* Priority
* Status
* Due date
* Completion timestamp
* Created timestamp
* Updated timestamp

### Task Types

```text
follow_up
call
email
meeting
research
other
```

### Task Priorities

```text
low
medium
high
urgent
```

### Task Statuses

```text
pending
in_progress
completed
cancelled
```

---

# CRM Service Layer

Business operations are implemented through CRM services.

Current service capabilities include:

```text
create_lead_task()
get_lead_tasks()
get_lead_tasks_by_id()

get_pending_tasks()
get_overdue_tasks()
get_priority_tasks()

complete_lead_task()

get_lead_by_id()
search_leads()

get_lead_activities()
get_lead_activities_by_id()

get_pipeline_summary()
```

These services form the business-operation boundary between Django models and future AI agents.

---

# AI Provider Architecture

Dodong OS uses a provider-based AI architecture.

Current direction:

```text
AI Service
    |
    v
Provider Abstraction
    |
    +---- GPT Provider
    |
    +---- Ollama Provider
```

CRM services must remain independent of the AI provider.

Provider-specific code must not leak into CRM business logic.

---

# Technology Stack

## Backend

* Python 3
* Django
* HTMX

## Database

### Development

* SQLite

### Production Direction

* PostgreSQL

## AI

Current:

* GPT provider abstraction
* Ollama fallback
* Structured AI service layer

Planned:

* Embeddings
* pgvector
* RAG
* AI agents
* Controlled tool calling

---

# Project Structure

Current high-level repository structure:

```text
DodongOS/
│
├── backend/
│   │
│   ├── apps/
│   │   ├── ai/
│   │   ├── companies/
│   │   ├── dashboard/
│   │   ├── leadfinder/
│   │   ├── leads/
│   │   └── scanner/
│   │
│   ├── config/
│   ├── services/
│   ├── static/
│   ├── templates/
│   │
│   ├── manage.py
│   └── requirements.txt
│
├── docs/
│
├── .gitignore
└── README.md
```

The AI CRM tool layer is located under:

```text
backend/apps/ai/tools/
```

Current CRM tool organization:

```text
apps/
└── ai/
    └── tools/
        ├── registry.py
        │
        └── crm/
            ├── activities.py
            ├── leads.py
            ├── pipeline.py
            └── tasks.py
```

---

# Roadmap

| Phase     | Goal                              | Status                     |
| --------- | --------------------------------- | -------------------------- |
| Phase 1   | Foundation                        | ✅ Complete                 |
| Phase 2   | AI Prototype                      | ✅ Complete                 |
| Phase 3   | AI Provider Layer                 | ✅ Core foundation complete |
| Phase 4   | Lead Scanner                      | 🟡 Iterative development   |
| Phase 5   | CRM Foundation                    | ✅ Complete                 |
| Phase 5.5 | Agent-Ready CRM Tool Layer        | ✅ Complete                 |
| Phase 5.6 | Documentation Sync                | ✅ Complete                 |
| Phase 6   | Background Jobs / Automation      | ✅ Complete                 |
| Phase 7   | RAG / AI Memory                   | ✅ Complete                 |
| Phase 8   | AI Assistant / CRM Read Agent     | ✅ Complete                 |
| Phase 9   | Controlled AI CRM Agent           | ✅ Complete                 |
| Phase 10  | Production Deployment / Hardening | ✅ Complete (ready, not yet deployed) |
| Phase 11  | Dodong OS v1.0                    | ✅ Complete (release checkpoint) |

---

# Current Position

```text
Phase 1     Foundation                     ✅
Phase 2     AI Prototype                   ✅
Phase 3     AI Provider Layer              ✅
Phase 4     Lead Scanner                   🟡
Phase 5     CRM Foundation                 ✅
Phase 5.5   Agent-Ready CRM Tools          ✅
Phase 5.6   Documentation Sync             ✅
Phase 6     Background Automation          ✅
Phase 7     RAG / Memory                   ✅
Phase 8     CRM Read Agent                 ✅
Phase 9     Controlled AI CRM Agent        ✅
Phase 10    Production Hardening           ✅  (ready, not yet deployed)
Phase 11    Dodong OS v1.0                 ✅  (release checkpoint)
```

---

# Next Major Milestone

## 🎯 CRM Read Agent v0.1

The next major development objective is to connect the existing AI provider layer to the controlled CRM read-tool registry.

The first target question is:

> **"What tasks need my attention?"**

Expected flow:

```text
User
 |
 v
AI Provider
 |
 v
CRM Read Agent
 |
 v
Tool Registry
 |
 v
get_priority_tasks
 |
 v
CRM Service
 |
 v
Database
 |
 v
Structured Tool Result
 |
 v
AI Response
```

The first CRM Read Agent will remain **strictly read-only**.

---

# CRM Read Agent Safety Rules

The first agent version must follow these rules:

1. Only registered read tools may execute.
2. AI code must not query Django ORM directly.
3. AI code must not modify CRM data.
4. Tool inputs must be validated.
5. Tool outputs must remain structured.
6. Tool errors must remain structured.
7. Unknown tools must be rejected.
8. The AI must not claim an action occurred unless the tool result confirms it.
9. Write tools must remain unavailable during the read-agent phase.

---

# Future Read-Agent Questions

After the first CRM Read Agent works, it should gradually support questions such as:

> "What tasks are overdue?"

> "What are my highest-priority tasks?"

> "Show me pending tasks."

> "Find Acme Analytics."

> "Tell me about lead 12."

> "What tasks belong to this lead?"

> "What happened recently with this lead?"

> "When did we last contact this company?"

> "How many qualified leads do we have?"

> "Summarize my pipeline."

> "Which leads need attention today?"

---

# Controlled Write Agent

Write tools will only be introduced after the CRM Read Agent is stable.

Potential future tools include:

```text
create_lead_task
complete_lead_task
update_lead_status
create_activity
```

Write actions will require additional controls such as:

* Authentication
* Permissions
* Input validation
* User confirmation where appropriate
* Audit logging
* Result verification

The AI must never write directly to the database.

Future architecture:

```text
User
 |
 v
AI Agent
 |
 v
Agent Tool
 |
 v
Permission / Confirmation
 |
 v
CRM Service
 |
 v
Validation
 |
 v
Django ORM
 |
 v
Database
 |
 v
Verify Result
 |
 v
Report Result
```

---

# Development Principles

Dodong OS follows these engineering rules.

## Thin Django Views

Views should primarily handle:

* HTTP
* Authentication
* Permissions
* Forms
* Request validation
* Service calls
* Responses

Business logic belongs in services.

---

## Business Logic in Services

Important CRM operations should live in reusable service functions.

```text
View
   \
    \
     → CRM Service → Django ORM
    /
AI Tool
```

This allows browser workflows and future AI agents to use the same business logic.

---

## AI Must Use Tools and Services

AI code must never directly perform operations such as:

```python
Lead.objects.filter(...)
LeadTask.objects.create(...)
LeadActivity.objects.create(...)
```

Instead:

```text
AI
 ↓
Tool
 ↓
Service
 ↓
ORM
```

---

## Structured AI Interfaces

AI-facing tools should use:

* Structured inputs
* Structured outputs
* Explicit error codes
* JSON-safe data
* Validation

Avoid arbitrary text contracts between the agent and business logic.

---

## Incremental Development

Development follows:

```text
Inspect
 ↓
Plan
 ↓
Implement One Small Change
 ↓
Run Django Check
 ↓
Run Tests
 ↓
Verify Behavior
 ↓
Commit
 ↓
Continue
```

Large autonomous changes should be avoided.

---

# Testing

Automated testing is required for important CRM services and AI tools.

Current relevant test baseline:

```text
532 tests passing
```

Run:

```bash
python manage.py check
python manage.py test apps.leads.tests apps.ai.tests
```

Expected result:

```text
System check identified no issues.

Ran 532 tests

OK
```

The exact test count will increase as development continues.

A feature is not considered complete merely because it works in the browser.

---

# Development Workflow

Feature work should use focused Git branches.

Example:

```text
main
 |
 +-- feature/phase-5-5a-priority-task-tool
 |
 +-- feature/phase-5-5b-overdue-task-tool
 |
 +-- feature/phase-5-5c-pending-task-tool
 |
 +-- feature/phase-5-5d-lead-task-tool
 |
 +-- feature/phase-5-5e-lead-read-tools
 |
 +-- feature/phase-5-5f-lead-activities-tool
 |
 +-- feature/phase-5-5g-pipeline-summary
 |
 +-- feature/phase-5-5h-tool-registry
 |
 +-- feature/phase-5-6-doc-sync
```

Before committing:

```bash
git status
git diff

python manage.py check
python manage.py test apps.leads.tests apps.ai.tests
```

Keep commits focused and avoid mixing unrelated cleanup with feature work.

---

# Local Development

Clone the repository:

```bash
git clone https://github.com/rmiranda1125/DodongOS.git
```

Enter the project:

```bash
cd DodongOS
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment.

## Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

## Windows Command Prompt

```cmd
.venv\Scripts\activate
```

## macOS / Linux

```bash
source .venv/bin/activate
```

Move into the Django backend:

```bash
cd backend
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Run Django checks:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test apps.leads.tests apps.ai.tests
```

Start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000
```

---

# Documentation

Project documentation is located under:

```text
docs/
```

Important documents include:

```text
docs/MASTER_ROADMAP.md
docs/ROADMAP.md
```

Use:

* `README.md` for the public project overview and current milestone.
* `docs/ROADMAP.md` for actual implementation progress.
* `docs/MASTER_ROADMAP.md` for the broader long-term product, learning, engineering, AI, and business vision.

Architecture-specific documentation should continue to be added as the agent layer becomes more sophisticated.

---

# Long-Term AI CRM Agent

The long-term target is not simply an AI chatbot attached to a CRM.

Dodong OS should behave like a controlled **AI CRM employee**.

The target architecture is:

```text
                    DODONG OS
                        |
                        v
                  AI CRM AGENT
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
       OBSERVE        REASON          ACT
          |             |             |
          v             v             v
       CRM Data       Planning     CRM Tools
          |             |             |
          +-------------+-------------+
                        |
                        v
                  Verified Result
```

Example future request:

> "Take care of my leads today."

Possible future process:

```text
Observe CRM
     |
     v
Find overdue and priority work
     |
     v
Analyze lead context
     |
     v
Create recommended plan
     |
     v
Request approval when required
     |
     v
Execute authorized CRM tools
     |
     v
Verify database result
     |
     v
Report completed work
```

Autonomous behavior will only be introduced after reliable services, permissions, confirmation controls, auditability, and verification are in place.

---

# Definition of Success

Dodong OS reaches its intended product direction when it can safely:

1. Observe CRM and business data.
2. Identify situations that require attention.
3. Retrieve relevant context.
4. Reason about next actions.
5. Recommend a plan.
6. Execute only authorized CRM operations.
7. Verify the result.
8. Clearly report what happened.

The goal is:

> **An AI-powered Business Intelligence, CRM, and Lead Intelligence Platform that evolves into a safe AI employee for CRM operations.**

---

# Current Milestone

## Phase 5.6 — Documentation Sync

Recently completed:

```text
CRM Foundation
      ✅

Agent-Ready CRM Services
      ✅

8 Read-Only CRM Tools
      ✅

Read-Only Tool Registry
      ✅

532 Relevant Tests
      ✅
```

Next:

```text
CRM Read Agent v0.1
```

First target:

> **"What tasks need my attention?"**

No AI write actions will be enabled during the first read-agent milestone.

---

# License

Dodong OS is currently under active development.

A formal license will be added before the first stable `v1.0` release.
