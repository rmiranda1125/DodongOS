"""
Fast pre-flight for a production deploy.

Verifies configuration and database reachability WITHOUT printing
secrets, calling any external AI provider, or mutating data. Exits
non-zero if any hard check fails so it can gate a release.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = (
        "Verify production configuration and DB connectivity. "
        "Prints no secrets, calls no external services, mutates "
        "nothing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-production",
            action="store_true",
            help="Fail unless DJANGO_ENV=production.",
        )

    def handle(self, *args, **options):
        failures = []
        warnings = []

        is_prod = getattr(settings, "IS_PRODUCTION", False)

        if options["require_production"] and not is_prod:
            failures.append(
                "DJANGO_ENV is not 'production'."
            )

        if is_prod:
            if settings.DEBUG:
                failures.append("DEBUG is True.")
            if not settings.ALLOWED_HOSTS:
                failures.append("ALLOWED_HOSTS is empty.")
            if settings.SECRET_KEY == (
                "dev-insecure-secret-key-do-not-use-in-production"
            ):
                failures.append(
                    "SECRET_KEY is the insecure development default."
                )
            engine = settings.DATABASES["default"]["ENGINE"]
            if "postgresql" not in engine:
                failures.append(
                    f"Production DB engine is '{engine}', "
                    "expected PostgreSQL."
                )
            if not settings.SECURE_SSL_REDIRECT:
                warnings.append("SECURE_SSL_REDIRECT is False.")
            if not settings.SESSION_COOKIE_SECURE:
                warnings.append("SESSION_COOKIE_SECURE is False.")
            if not settings.CSRF_COOKIE_SECURE:
                warnings.append("CSRF_COOKIE_SECURE is False.")
            if not settings.CSRF_TRUSTED_ORIGINS:
                warnings.append("CSRF_TRUSTED_ORIGINS is empty.")

        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            self.stdout.write("database: reachable")
        except Exception as exc:  # pragma: no cover - infra path
            failures.append(
                f"database unreachable: {type(exc).__name__}"
            )

        for warning in warnings:
            self.stdout.write(
                self.style.WARNING(f"WARN: {warning}")
            )

        if failures:
            for failure in failures:
                self.stderr.write(
                    self.style.ERROR(f"FAIL: {failure}")
                )
            self.stderr.write(
                self.style.ERROR(
                    f"production_check failed ({len(failures)} "
                    "issue(s))."
                )
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS("production_check passed.")
        )
