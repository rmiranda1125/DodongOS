# syntax=docker/dockerfile:1

# =============================================================
# Dodong OS production image
#
# Build context: repository root.
#   docker build -t dodong-os:latest .
#
# Runs Django under gunicorn as a non-root user. Static files are
# collected at build time. Database migrations are NOT run here -
# run them as an explicit release step (see docs/04_DEPLOYMENT/
# PRODUCTION.md) so they never race across web workers.
# =============================================================

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_ENV=production \
    DJANGO_SKIP_DOTENV=1

WORKDIR /app

# System deps: libpq for psycopg, then drop apt lists.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/ ./

# Collect static with a throwaway key so the build never needs
# real secrets. Runtime overrides all of these.
RUN SECRET_KEY=build-only-not-used \
    ALLOWED_HOSTS=build.invalid \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput

# Non-root runtime user.
RUN useradd --system --uid 10001 --home /app appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# WEB_CONCURRENCY (gunicorn --workers) defaults to 3; tune per plan.
ENV WEB_CONCURRENCY=3

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
