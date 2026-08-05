# 🚀 Dodong OS

> An AI-powered Business Intelligence, CRM, and Lead Intelligence Platform built with Django, HTMX, PostgreSQL, and GPT.

---

## Vision

Dodong OS is an AI Operating System for consultants, agencies, and small businesses.

Its goal is to automate the entire consulting workflow:

- 🔍 Find potential clients
- 🤖 Analyze companies using AI
- 📊 Score opportunities
- 👥 Manage CRM relationships
- 📧 Generate outreach emails
- 📈 Track business growth
- 🧠 Build long-term AI memory using RAG

Instead of switching between multiple tools, Dodong OS brings everything into one platform.

---

## Current Status

**Current Version**

```
v0.3
```

**Current Phase**

```
Phase 3 — AI Provider Layer
```

### Completed

- ✅ Django Project
- ✅ HTMX Integration
- ✅ Companies CRUD
- ✅ AI Service Layer
- ✅ Local Ollama Prototype
- ✅ Company Analysis Framework

### In Progress

- 🔄 GPT-5.6 Luna Integration
- 🔄 AI Provider Abstraction

---

# Technology Stack

## Backend

- Django
- Python 3
- HTMX

## Database

Development

- SQLite

Production

- PostgreSQL

## AI

Primary

- GPT-5.6 Luna

Fallback

- Ollama

Future

- pgvector
- Embeddings
- RAG
- AI Agents

---

# Project Structure

```
DodongOS/

apps/
    ai/
    companies/
    scanner/
    leads/
    crm/
    dashboard/

docs/

tests/

config/

README.md
```

---

# Roadmap

| Phase | Status |
|--------|--------|
| Phase 1 – Foundation | ✅ |
| Phase 2 – AI Prototype | ✅ |
| Phase 3 – AI Provider Layer | 🔄 |
| Phase 4 – Lead Scanner | ⏳ |
| Phase 5 – CRM | ⏳ |
| Phase 6 – Background Jobs | ⏳ |
| Phase 7 – RAG | ⏳ |
| Phase 8 – AI Assistant | ⏳ |
| Phase 9 – Production Deployment | ⏳ |
| Phase 10 – Version 1.0 | ⏳ |

---

# Development Principles

- Thin Django Views
- Business Logic in Services
- Strict JSON AI Responses
- Pydantic Validation
- Provider-Based AI Architecture
- AI Never Writes Directly to the Database

---

# Planned Features

## CRM

- Companies
- Contacts
- Activities
- Notes
- Tasks

## AI

- Company Analysis
- Lead Scoring
- Proposal Generator
- Email Writer
- Meeting Preparation

## Lead Scanner

- Manual URL Scan
- AI Extraction
- Validation
- Duplicate Detection
- CRM Integration
- CSV Export

## Future

- Background Jobs
- RAG
- AI Agents
- Docker Deployment
- Azure Deployment

---

# Development Workflow

```
main
│
└── develop
      │
      ├── feature/gpt-luna
      ├── feature/company-analysis
      ├── feature/lead-scanner
      ├── feature/crm
      ├── feature/rag
      └── feature/agents
```

---

# Local Development

Clone the repository:

```bash
git clone https://github.com/<your-username>/DodongOS.git
```

Go into the project:

```bash
cd DodongOS
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

Open:

```
http://127.0.0.1:8000
```

---

# Documentation

Project documentation is located in the `docs/` folder.

Topics include:

- Project Vision
- Roadmap
- Architecture
- AI
- Scanner
- Deployment
- Business Plan

---

# Current Milestone

🎯 Replace Ollama with GPT-5.6 Luna and build the AI-powered Lead Scanner using the canonical `lead_scanner_runtime_prompt.md`.

---

# License

This project is currently under active development.

License will be added before the first stable release (v1.0).