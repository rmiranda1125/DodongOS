# Dodong OS — Production Deployment Runbook (Phase 10)

Authoritative deployment guide. The one-line stubs in this folder
(`AZURE.md`, `DOCKER.md`, `POSTGRES.md`) point here.

---

## 1. Architecture

```
            HTTPS
Internet ──────────► Azure App Service for Containers (Linux)
                         │  gunicorn → config.wsgi  (non-root, port 8000)
                         │  WhiteNoise serves /static/ from the image
                         ▼
                     Azure Database for PostgreSQL — Flexible Server
                         ▲
                         │  python manage.py run_crm_checks  (scheduled)
                     Azure Container Apps Job (cron)  — same image
```

- **Compute:** Azure App Service for Containers (Linux), single web
  app running the image built from the repo `Dockerfile`.
- **Database:** Azure Database for PostgreSQL – Flexible Server.
- **Static files:** collected into the image at build time, served
  by WhiteNoise. No CDN / blob storage required.
- **Media / uploads:** none today. If added later, point
  `MEDIA_ROOT` at durable storage (Azure Blob) — the container
  filesystem is ephemeral.
- **Scheduler:** an Azure Container Apps **Job** (or App Service
  WebJob) that runs `python manage.py run_crm_checks` on a cron
  schedule using the same image and env.
- **TLS:** terminated by Azure; the original scheme arrives in
  `X-Forwarded-Proto` (handled by `SECURE_PROXY_SSL_HEADER`).

TLS terminates at Azure. Azure PostgreSQL backups are
platform-managed (see §9).

---

## 2. Prerequisites

- An Azure subscription with permission to create App Service,
  PostgreSQL Flexible Server, and Container Apps.
- A container registry (Azure Container Registry or GHCR).
- Python 3.13 + Docker locally to build/test the image.
- The values in `backend/.env.example` decided for production.

---

## 3. Environment variables

Set these on the **App Service** and on the **scheduler job**
(identical DB + AI config). See `backend/.env.example` for the full
annotated list. Required in production:

| Variable | Notes |
|---|---|
| `DJANGO_ENV` | `production` |
| `DJANGO_SKIP_DOTENV` | `1` |
| `SECRET_KEY` | 50+ random chars; never reuse dev value |
| `DEBUG` | `False` (enforced) |
| `ALLOWED_HOSTS` | e.g. `dodong.azurewebsites.net,dodong.example.com` |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://dodong.example.com` |
| `DATABASE_URL` | `postgres://USER:PASSWORD@HOST:5432/DB` |
| `AI_PROVIDER` | `openai` |
| `OPENAI_API_KEY` | provider key (store as an App Service *secret* setting) |
| `OPENAI_MODEL` | model id |

Optional / tuned: `DB_CONN_MAX_AGE`, `LOG_LEVEL`, `WEB_CONCURRENCY`,
the `CRM_AUTOMATION_*` and `RAG_*` values, and the security toggles
(all default to secure values when `DJANGO_ENV=production`).

Secrets are supplied only as platform environment variables /
secret settings. `.env` is never deployed and never baked into the
image (`.dockerignore`).

---

## 4. Database setup

1. Create an Azure PostgreSQL Flexible Server (v16+), a database
   `dodong`, and a least-privilege application role.
2. Allow the App Service outbound IPs / VNet integration.
3. Put the DSN in `DATABASE_URL`.
4. `select_for_update()` (automation overlap guard, knowledge
   ingestion) has real row-locking semantics only on PostgreSQL —
   this is why production must not run SQLite.

---

## 5. Release procedure

Every deploy:

1. **Build & push image**
   `docker build -t <registry>/dodong-os:<sha> .`
   `docker push <registry>/dodong-os:<sha>`
2. **Run migrations** as a one-off (App Service SSH, a Container
   Apps job, or `az webapp ... exec`), **before** routing traffic
   to the new image:
   `python manage.py migrate --noinput`
3. **Static** — already collected in the image; nothing to do.
4. **Deploy** the new image tag to the App Service; **restart**.
5. **Verify health** — `GET /health/` → `{"status":"ok"}`,
   `GET /ready/` → `200` with `database: ok`.
6. **Verify DB** — `python manage.py showmigrations` shows all
   applied; `python manage.py production_check --require-production`.
7. Point the scheduler job at the new image tag.

Migrations to date are **additive / backward-compatible** (new
apps, new nullable columns, new indexes, `Meta.ordering` changes).
A brief window where old and new code both run is safe. Do **not**
squash migration history.

---

## 6. Production start command

```
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 60 \
    --access-logfile - --error-logfile -
```

(The image `CMD` already does this.) Never use `manage.py
runserver` in production.

### Worker count

`gunicorn` reads `WEB_CONCURRENCY` for `--workers`. **Default 3.**
Keep it conservative: each worker holds its own DB connection and
may make a bounded outbound AI call. Start at `2 × vCPU + 1`,
verify against the PostgreSQL `max_connections` budget
(`workers × instances + scheduler + migrations headroom`), and
raise only with evidence.

---

## 7. Background automation scheduling

- **Command:** `python manage.py run_crm_checks`
- **Runner:** an Azure Container Apps Job (cron trigger) or App
  Service WebJob, using the **same image and env** as the web app.
- **Cadence:** no product SLA is defined. **Default: every 30
  minutes** (`*/30 * * * *`), env/schedule-configurable. Do not run
  it more aggressively without a business reason.
- **Environment:** needs `DATABASE_URL` + AI vars; does not need
  `ALLOWED_HOSTS` / web settings.
- **Overlap:** the app's own `ScheduledCheckRun` guard
  (`CRM_AUTOMATION_STALE_RUN_MINUTES`, default 30) is the safety
  net — a slow run makes the next invocation exit cleanly without
  double-running. Still, do not schedule a cadence shorter than a
  healthy run.
- **Failure visibility:** staff page `/automation/runs/` shows
  every run's status, `checks_run`, `findings_count`, and AI
  summary status (`AI_SUMMARY_OK` / `AI_SUMMARY_FAILED` →
  degraded, not failed). Operators should check it after incidents
  and can also inspect the job's own run history / exit codes in
  Azure. External alerting (e.g. "no successful run in N hours") is
  **deferred** to Phase 11.

---

## 8. Health, readiness & observability

| Endpoint | Purpose | Calls AI? | Touches DB? |
|---|---|---|---|
| `GET /health/` | liveness — process is up | no | no |
| `GET /ready/` | readiness — `SELECT 1` on default DB | no | yes (trivial) |

Both return minimal JSON and never expose secrets, config, or
tracebacks. Point the App Service health probe at `/health/`.

Operational surfaces:

- **Logs:** stdout/stderr → App Service log stream / Container Apps
  logs. `LOG_LEVEL` (default `INFO`) is env-tunable. Formatters do
  not render request bodies, headers, env, or credentials; RAG
  document contents and user prompts are not logged by default.
- **Automation history:** `/automation/runs/` (staff only).
- **AI action audit:** `/assistant/audit/` (staff only) — every
  confirmed CRM write.
- **Admin:** `/admin/` (staff only).
- **Knowledge assistant:** `/assistant/knowledge/` (staff only).

---

## 9. Backup

**Status: platform-managed backups are the plan; on-demand logical
backup is documented. Neither is verified here — both require the
production Azure account.**

1. **Primary — Azure PostgreSQL automated backups.** Flexible
   Server takes automatic backups; set **retention 14–35 days** and
   enable **geo-redundant** backup for production. This is the
   default recovery mechanism (point-in-time restore).
2. **On-demand logical backup** (portability / pre-risky-change):
   ```
   pg_dump --format=custom --no-owner --no-privileges \
       "$DATABASE_URL" > dodong_$(date +%Y%m%d_%H%M%S).dump
   ```
   Store off-platform (encrypted bucket). Recommend a weekly
   logical dump in addition to platform backups.
3. **Retention:** platform PITR 14–35 days; logical dumps 90 days.
4. **Ownership:** the deploying engineer / account owner is
   responsible for enabling retention and periodically running the
   restore drill (§10).

---

## 10. Restore drill (non-destructive)

Never restore over live production automatically. Drill:

1. Provision a **disposable** PostgreSQL server/database.
2. Restore into it — Azure PITR to a new server, or
   `pg_restore --no-owner --no-privileges -d "$DISPOSABLE_URL" dump.dump`.
3. `DATABASE_URL=$DISPOSABLE_URL python manage.py migrate --plan`
   then `migrate` — expect **no pending migrations** for a
   same-version restore.
4. Run the smoke checklist (§13) against the disposable instance.
5. Verify critical counts (`Lead`, `LeadTask`, `AIActionAudit`,
   `KnowledgeDocument`) look sane vs. the source.
6. **Delete the disposable server.**

Record the date of the last successful drill.

---

## 11. Rollback

1. **Code:** redeploy the previous good image tag (keep the last
   3–5 tags in the registry). Azure App Service "Deployment
   Center" / slot swap also rolls back.
2. **Identify the previous good release:** the image tag = commit
   SHA; cross-check `git log` and the `/automation/runs/` +
   `AIActionAudit` timestamps.
3. **Migrations:** prefer a **forward fix**. Reverting code is safe
   when the newer migrations are additive (all Phase ≤10
   migrations are). Do **not** blindly `migrate <app> <prev>` — a
   reverse migration that drops a column loses data. If a bad
   migration dropped/renamed something, roll forward with a new
   corrective migration instead.
4. If code is rolled back but its migrations are already applied
   and additive, that is fine — the old code ignores the new
   columns.

Not every migration is guaranteed reversible; destructive schema
changes must be fixed forward.

---

## 12. Release checklist

- [ ] `python manage.py test` green locally / in CI
- [ ] `python manage.py makemigrations --check` clean
- [ ] `python manage.py check --deploy` clean under production env
      (the single `security.W021` HSTS-preload warning is
      intentional — see §14)
- [ ] Image builds; `collectstatic` succeeds in the build
- [ ] `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`,
      `CSRF_TRUSTED_ORIGINS`, `OPENAI_API_KEY` set on App Service
      **and** scheduler job
- [ ] Migrations run as a release step (not by web workers)
- [ ] `/health/` and `/ready/` green post-deploy
- [ ] `production_check --require-production` passes
- [ ] Scheduler job repointed to the new image; next run visible
      in `/automation/runs/`
- [ ] Previous image tag retained for rollback

---

## 13. Production smoke test (non-destructive)

Run after every deploy. **Never executes a confirmed CRM write.**

1. `curl -fsS https://<host>/health/` → `{"status":"ok"}`
2. `curl -fsS https://<host>/ready/` → `200`, `database: ok`
3. `python manage.py migrate --check` (or `showmigrations`) → all
   applied
4. `python manage.py production_check --require-production` → passes
5. `GET /admin/login/` → `200` (admin reachable, not logged in)
6. Static asset loads, e.g. `GET /static/<a real file>` → `200`
7. CRM read tool: in `manage.py shell`,
   `from apps.ai.tools.registry import execute_registered_tool;
   execute_registered_tool(name="get_pipeline_summary", arguments={})`
   → `success: True`
8. RAG retrieval:
   `execute_registered_tool(name="search_knowledge",
   arguments={"query": "policy"})` → `success: True`
9. Automation (controlled, read-only): trigger the scheduler job
   once and confirm a `succeeded` row appears in `/automation/runs/`.

---

## 14. Troubleshooting

| Symptom | Check |
|---|---|
| App won't boot, `ImproperlyConfigured` | a required prod var is missing (`SECRET_KEY` / `ALLOWED_HOSTS` / `DATABASE_URL`) or `DEBUG=True` with `DJANGO_ENV=production` |
| `DisallowedHost` | add the hostname to `ALLOWED_HOSTS` |
| CSRF failures on admin/HTMX POST | add the origin (scheme + host) to `CSRF_TRUSTED_ORIGINS` |
| Infinite HTTPS redirect | ensure `USE_X_FORWARDED_PROTO=True` (default in prod) so `X-Forwarded-Proto` is trusted |
| `/ready/` returns 503 | DB unreachable — firewall / DSN / server down |
| Static 404s | the image build's `collectstatic` failed, or `STATIC_ROOT` not shipped |
| `check --deploy` warns `security.W021` | intentional; set `SECURE_HSTS_PRELOAD=True` only when you commit to HSTS preload (hard to undo) |
| Automation "didn't run" | scheduler job history in Azure; `/automation/runs/` shows last run time |
| AI summary shows `AI_SUMMARY_FAILED` | provider outage/timeout — run still `succeeded`; deterministic fallback used |

---

## 15. PostgreSQL runtime verification status

The CI workflow includes an **optional `postgres-smoke` job** that
runs `migrate` + the full suite against a PostgreSQL 16 service
container. Local development in this repo uses SQLite; a real
PostgreSQL runtime has **not** been exercised from this machine.
Run the `postgres-smoke` CI job (or the drill in §10) before the
first production cutover to confirm engine-specific behaviour
(`select_for_update`, `jsonb`, ordering, unique constraints).
