# PostgreSQL

Production database. Configured via `DATABASE_URL` (see `backend/.env.example`).
Production (`DJANGO_ENV=production`) refuses the SQLite fallback. Development may
keep using SQLite. See **`PRODUCTION.md`** sections 4, 9, 10, 15.
