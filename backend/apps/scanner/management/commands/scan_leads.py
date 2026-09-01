"""
Run one lead-scanner scan.

    python manage.py scan_leads --source csv --path leads.csv
    python manage.py scan_leads --source manual --json '[{"company_name": "..."}]'

Discovery only: this command never imports a CRM Lead and never
calls the confirmed-write executor. It records a LeadScanRun,
handles source failure cleanly (no permanently "running" row), and
reports per-row errors without aborting the whole scan.

Compatible with an external scheduler (cron / Azure Container Apps
Job), exactly like `run_crm_checks`. Do not schedule live external
scraping here - v1 ships offline adapters only.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.scanner import adapters
from apps.scanner import services as scanner_services


class Command(BaseCommand):
    help = "Scan one source for lead candidates (no CRM import)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            required=True,
            choices=list(adapters.SUPPORTED_SOURCES),
        )
        parser.add_argument("--path", default=None)
        parser.add_argument("--json", dest="json_items", default=None)
        parser.add_argument(
            "--with-ai",
            action="store_true",
            help="Also request the optional AI explanation note.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        config = {"source": source}

        if source == "csv":
            if not options["path"]:
                raise CommandError("--source csv requires --path")
            config["path"] = options["path"]
        elif source == "manual":
            if not options["json_items"]:
                raise CommandError("--source manual requires --json")
            try:
                config["items"] = json.loads(options["json_items"])
            except json.JSONDecodeError as exc:
                raise CommandError(f"--json is not valid JSON: {exc}")

        run = scanner_services.run_scan(
            source=source,
            config=config,
            with_ai=options["with_ai"],
        )

        if run.status == "failed":
            self.stderr.write(
                self.style.ERROR(
                    f"scan_leads run {run.id} failed: {run.error_message}"
                )
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"scan_leads run {run.id} succeeded "
                f"(seen={run.candidates_seen}, "
                f"created={run.candidates_created}, "
                f"updated={run.candidates_updated}, "
                f"rejected={run.rows_rejected})."
            )
        )
