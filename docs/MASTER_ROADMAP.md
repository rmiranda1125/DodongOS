# Dodong OS
## AI-Powered CRM & Lead Generation Platform

> "Build one product that teaches me Software Engineering,
> AI Engineering, and Business at the same time."

---

# Vision

Dodong OS is an AI-powered CRM that helps me:

- Find clients automatically
- Analyze companies using AI
- Generate proposals
- Write personalized emails
- Manage relationships
- Track opportunities
- Grow my consulting business

Eventually it becomes my own AI employee.

---

# Current Implementation Status

> Updated: August 21, 2026

Dodong OS implementation has progressed beyond the original learning-phase timeline documented below.

The detailed implementation roadmap is maintained in:

`docs/ROADMAP.md`

## Current Software Milestone

**Dodong OS v1.0 — release checkpoint** (`V1_RELEASE_READY_BUT_NOT_LIVE_DEPLOYED`).

The full implementation roadmap (Phases 1–11) is complete, including a
bounded Phase 4 (Lead Scanner v1). See `docs/ROADMAP.md` and
`docs/RELEASES/v1.0.0.md`.

Delivered:

- ✅ CRM foundation (leads, statuses, tasks, notes, activity timeline)
- ✅ CRM Read Agent + read-only tool registry
- ✅ Four confirmed CRM write actions (proposal → signed token → Confirm →
  verified executor → audit); no autonomous writes
- ✅ Background automation (deterministic checks, digest, optional AI
  summary + deterministic fallback, overlap/stale-run guards)
- ✅ RAG / AI memory (controlled ingestion, deterministic chunking + lexical
  retrieval, grounded answers, prompt-injection boundary)
- ✅ Production hardening (env-driven config, PostgreSQL readiness, health/
  readiness, WhiteNoise, gunicorn, Docker, CI, deployment runbook)
- ✅ v1.0 UX polish, access-control review, integrated acceptance suite
- ✅ Lead Scanner v1 (offline source adapters, deterministic scoring,
  staff review, explicit CRM import; no autonomous CRM writes)
- ✅ 567 automated tests passing; zero real external AI calls

## Current Agent Architecture

```text
Future CRM Read Agent
        |
        v
Read-Only Tool Registry
        |
        v
CRM Tools
        |
        v
CRM Services
        |
        v
Django ORM
        |
        v
Database

# Development Tracks

We develop **three tracks in parallel**.

```
                    Dodong OS

        ┌────────────┼─────────────┐

        ▼            ▼             ▼

 Software      AI Engineering   Business

 Engineering
```

---

# Track 1
# Software Engineering

Goal:

Become an advanced backend/software engineer by building Dodong OS.

Topics

## Django

- Project Structure
- Apps
- URLs
- Views
- Templates
- Models
- Forms
- Authentication

---

## HTMX

- Requests
- Partial Templates
- Modals
- Live Search
- Pagination
- CRUD
- Infinite Scroll

---

## PostgreSQL

- Schema Design
- Relationships
- Indexes
- Performance
- Query Optimization

---

## Architecture

- Services
- Repositories
- DTOs
- Dependency Injection
- Clean Architecture

---

## APIs

- Django Ninja / DRF
- REST
- Webhooks
- Authentication

---

## Testing

- Pytest
- Unit Tests
- Integration Tests
- End-to-End Tests

---

## Deployment

- Docker
- Nginx
- Azure
- CI/CD
- GitHub Actions

---

# Track 2
# AI Engineering

Goal:

Learn how modern AI products are built.

Topics

## OpenAI

- GPT Models
- Responses API
- Function Calling
- Structured Output

---

## Prompt Engineering

- Prompt Design
- System Prompts
- Few-Shot Learning

---

## RAG

- Documents
- Chunking
- Embeddings
- Retrieval
- Context

---

## pgvector

- Vector Search
- Similarity Search
- Semantic Search

---

## Agents

- AI Workflows
- Planning
- Tool Calling
- Multi-Agent Systems

---

## Automation

- Playwright
- Tavily
- Email Automation
- Lead Scraping
- Browser Automation

---

# Track 3
# Business & Product

Goal:

Build a business instead of just software.

Topics

## CRM Design

Companies

Contacts

Leads

Opportunities

Tasks

Invoices

---

## Lead Generation

Google

LinkedIn

Directories

Facebook

Cold Email

---

## Sales

Discovery

Proposal

Negotiation

Closing

---

## Marketing

Website

SEO

Portfolio

Case Studies

LinkedIn

---

## Product

Pricing

Features

Roadmap

Feedback

User Experience

---

# Timeline

## Phase 1 (Weeks 1–4)
Foundation

Software

- Django
- HTMX
- PostgreSQL
- CRUD

AI

- OpenAI Basics
- Prompt Engineering

Business

- CRM Workflow
- Define Ideal Client

Deliverable

Basic CRM

---

## Phase 2 (Weeks 5–8)

Software

- Authentication
- Dashboard
- APIs

AI

- Company Analyzer
- Lead Summary

Business

- Lead Qualification
- Outreach Strategy

Deliverable

AI CRM

---

## Phase 3 (Weeks 9–12)

Software

- Search
- Filtering
- Deployment

AI

- RAG
- pgvector

Business

- Proposal Generator

Deliverable

Lead Finder MVP

---

## Phase 4 (Weeks 13–16)

Software

- Performance
- Testing

AI

- Multi-Agent Workflow

Business

- Client Portal

Deliverable

Production Version

---

# Daily Schedule

Monday–Saturday

## Session 1
Software Engineering
(2–3 hours)

Build one feature.

Example

- Company CRUD
- Contacts
- Dashboard
- Authentication

---

## Session 2
AI Engineering
(1–2 hours)

Learn one AI concept.

Example

- Embeddings
- Prompt Engineering
- Function Calling
- Agents

---

## Session 3
Business
(30–60 min)

Answer one question.

Examples

Who is my customer?

What problem am I solving?

How do I price this?

Can I sell this?

---

# Daily Workflow

Morning

Learn

↓

Build

↓

Commit

↓

Test

↓

Write Notes

↓

Sleep

Repeat

---

# Git Workflow

Every day

git add .

git commit -m "Day XX - Companies CRUD"

git push

---

# End Goal

At the end of this roadmap I will have:

Software Engineer

✓ Django

✓ PostgreSQL

✓ HTMX

✓ Docker

✓ Azure

✓ Testing

---

AI Engineer

✓ GPT

✓ RAG

✓ Agents

✓ Embeddings

✓ Automation

---

Business

✓ SaaS Product

✓ CRM

✓ Lead Finder

✓ AI Assistant

✓ Consulting Business

---

Final Product

Dodong OS

An AI-powered CRM and Lead Generation Platform built from scratch.

The product itself becomes:

- My portfolio
- My resume
- My business
- My learning platform
- My consulting toolkit