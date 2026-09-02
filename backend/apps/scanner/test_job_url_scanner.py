"""
Tests for the paste-a-link Job URL scanner.

Kept in a dedicated module because it is a self-contained feature on
top of the existing scanner pipeline. The shared ``PROFILE`` fixture
mirrors the one in tests.py.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.leads.models import Lead, LeadActivity
from apps.scanner import job_url_scanner
from apps.scanner import services as scanner_services
from apps.scanner.models import LeadCandidate, LeadScanRun


PROFILE = {
    "required_skills": ["power bi", "sql"],
    "preferred_skills": ["dax"],
    "role_keywords": ["developer", "analyst"],
    "excluded_terms": ["unpaid", "volunteer"],
    "remote_required": False,
    "min_compensation": 0,
    "recency_days": 30,
}


class _FailProvider:
    def analyze(self, prompt):
        raise RuntimeError("provider down")


class _JsonProvider:
    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def analyze(self, prompt):
        self.prompts.append(prompt)
        return self.payload


def _job_html(
    *,
    title="Senior Data Analyst - ABC Company",
    body=(
        "We need strong Power BI, SQL and Python skills to build "
        "finance dashboards. Fully remote role."
    ),
):
    filler = " ".join(["dashboard"] * 60)
    return (
        "<html><head>"
        f"<title>{title}</title>"
        '<meta property="og:site_name" content="ABC Company">'
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"Senior Data Analyst",'
        '"identifier":{"value":"REQ-123"},'
        '"hiringOrganization":{"name":"ABC Company"},'
        '"jobLocationType":"TELECOMMUTE",'
        '"jobLocation":{"address":{"addressCountry":"Philippines"}},'
        '"baseSalary":{"currency":"USD","value":{"minValue":70000,'
        '"maxValue":90000,"unitText":"YEAR"}}}'
        "</script>"
        "</head><body>"
        "<script>window.__x = 'alert-token';</script>"
        f"<h1>Senior Data Analyst</h1><p>{body}</p><p>{filler}</p>"
        "</body></html>"
    )


class JobUrlScannerModuleTests(TestCase):

    def test_validate_url_adds_scheme_and_rejects_non_http(self):
        self.assertEqual(
            job_url_scanner.validate_url("example.com/jobs/1"),
            "https://example.com/jobs/1",
        )
        for bad in ("", "   ", "ftp://example.com/x", "not a url"):
            with self.assertRaises(job_url_scanner.JobUrlError):
                job_url_scanner.validate_url(bad)

    def test_guard_blocks_private_loopback_and_metadata(self):
        for blocked in (
            "http://127.0.0.1/x",
            "https://10.0.0.5/x",
            "http://192.168.1.10/x",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/x",
            "http://localhost/x",
            "http://db.internal/x",
        ):
            with self.assertRaises(job_url_scanner.JobUrlError) as ctx:
                job_url_scanner._guard_hop(blocked, allow_private=False)
            self.assertEqual(ctx.exception.code, "BLOCKED_ADDRESS")

    def test_guard_allows_public_ip_literal(self):
        job_url_scanner._guard_hop("https://8.8.8.8/x", allow_private=False)

    def test_guard_can_be_disabled_for_local_dev(self):
        job_url_scanner._guard_hop("http://127.0.0.1/x", allow_private=True)

    def test_extract_readable_strips_scripts(self):
        meta, text = job_url_scanner.extract_readable(_job_html())
        self.assertNotIn("alert-token", text)
        self.assertNotIn("<script", text)
        self.assertIn("Power BI", text)
        self.assertEqual(meta["json_ld"]["identifier"]["value"], "REQ-123")

    def test_parse_job_is_deterministic_when_ai_unavailable(self):
        meta, text = job_url_scanner.extract_readable(_job_html())
        raw = job_url_scanner.parse_job(
            url="https://jobs.abc.com/req-123",
            meta=meta,
            text=text,
            profile=PROFILE,
            provider=_FailProvider(),
        )
        self.assertEqual(raw["company_name"], "ABC Company")
        self.assertEqual(raw["opportunity_title"], "Senior Data Analyst")
        self.assertEqual(raw["work_arrangement"], "remote")
        self.assertEqual(raw["location"], "Philippines")
        self.assertIn("70000", raw["compensation_text"])
        self.assertEqual(raw["source_identifier"], "REQ-123")
        self.assertEqual(raw["source"], "abc")
        self.assertEqual(raw["source_url"], "https://jobs.abc.com/req-123")

    def test_parse_job_prefers_ai_extracted_values(self):
        meta, text = job_url_scanner.extract_readable(_job_html())
        provider = _JsonProvider(
            '{"job_title": "Lead BI Engineer", "company": "ACME Corp",'
            ' "work_type": "Hybrid", "location": "Remote PH",'
            ' "compensation": "$120k", "required_skills": ["power bi"],'
            ' "matching_skills": ["power bi"], "missing_skills": []}'
        )
        raw = job_url_scanner.parse_job(
            url="https://jobs.abc.com/1",
            meta=meta,
            text=text,
            profile=PROFILE,
            provider=provider,
        )
        self.assertEqual(raw["opportunity_title"], "Lead BI Engineer")
        self.assertEqual(raw["company_name"], "ACME Corp")
        self.assertEqual(raw["work_arrangement"], "hybrid")
        self.assertEqual(raw["compensation_text"], "$120k")

    def test_scan_job_url_rejects_thin_pages(self):
        with self.assertRaises(job_url_scanner.JobUrlError) as ctx:
            job_url_scanner.scan_job_url(
                "https://jobs.abc.com/1",
                fetch=lambda url: (
                    url,
                    "<html><body>login required</body></html>",
                ),
                provider=_FailProvider(),
            )
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_CONTENT")

    def test_scan_job_url_preserves_original_url(self):
        raw = job_url_scanner.scan_job_url(
            "https://jobs.abc.com/req-123?utm_source=x",
            fetch=lambda url: (url, _job_html()),
            provider=_FailProvider(),
        )
        self.assertEqual(
            raw["source_url"],
            "https://jobs.abc.com/req-123?utm_source=x",
        )


@override_settings(SCANNER_PROFILE=PROFILE)
class JobUrlScanServiceTests(TestCase):

    URL = "https://jobs.abc.com/req-123"

    def _fetch(self, html=None):
        payload = html if html is not None else _job_html()
        return lambda url: (url, payload)

    def test_scan_creates_discovered_candidate_and_no_crm_lead(self):
        before = (Lead.objects.count(), LeadActivity.objects.count())
        result = scanner_services.scan_job_url(
            url=self.URL, fetch=self._fetch(), provider=_FailProvider()
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["created"])

        candidate = LeadCandidate.objects.get()
        self.assertEqual(candidate.status, "discovered")
        self.assertEqual(candidate.source, "abc")
        self.assertEqual(candidate.source_url, self.URL)
        self.assertIn(
            "power bi", candidate.skills_analysis["matching_required"]
        )
        self.assertIn("sql", candidate.skills_analysis["matching_required"])

        run = LeadScanRun.objects.get()
        self.assertEqual(run.source, "job_url")
        self.assertEqual(run.status, "succeeded")
        self.assertEqual(run.candidates_seen, 1)
        self.assertEqual(run.candidates_created, 1)

        self.assertEqual(
            (Lead.objects.count(), LeadActivity.objects.count()), before
        )

    def test_rescan_same_url_updates_not_duplicates(self):
        scanner_services.scan_job_url(
            url=self.URL, fetch=self._fetch(), provider=_FailProvider()
        )
        second = scanner_services.scan_job_url(
            url=self.URL, fetch=self._fetch(), provider=_FailProvider()
        )
        self.assertTrue(second["success"])
        self.assertFalse(second["created"])
        self.assertEqual(LeadCandidate.objects.count(), 1)
        self.assertEqual(LeadScanRun.objects.count(), 2)
        self.assertEqual(
            LeadScanRun.objects.first().candidates_updated, 1
        )

    def test_missing_required_skill_is_reported(self):
        html = _job_html(
            body="We use Power BI and Excel for reporting. Remote."
        )
        scanner_services.scan_job_url(
            url=self.URL, fetch=self._fetch(html), provider=_FailProvider()
        )
        candidate = LeadCandidate.objects.get()
        self.assertIn(
            "sql", candidate.skills_analysis["missing_required"]
        )
        self.assertNotIn(
            "sql", candidate.skills_analysis["matching_required"]
        )

    def test_fetch_failure_records_failed_run_and_no_candidate(self):
        def boom(url):
            raise job_url_scanner.JobUrlError(
                "LOGIN_REQUIRED", "Requires login or blocks bots."
            )

        result = scanner_services.scan_job_url(url=self.URL, fetch=boom)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "LOGIN_REQUIRED")
        self.assertEqual(LeadCandidate.objects.count(), 0)
        run = LeadScanRun.objects.get()
        self.assertEqual(run.status, "failed")
        self.assertIn("LOGIN_REQUIRED", run.error_message)

    def test_unexpected_error_is_contained(self):
        def boom(url):
            raise RuntimeError("kaboom")

        result = scanner_services.scan_job_url(url=self.URL, fetch=boom)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], "SCAN_ERROR")
        self.assertEqual(LeadScanRun.objects.get().status, "failed")
        self.assertEqual(LeadCandidate.objects.count(), 0)

    def test_scanned_job_imports_to_crm_with_url_preserved(self):
        scanner_services.scan_job_url(
            url=self.URL, fetch=self._fetch(), provider=_FailProvider()
        )
        candidate = LeadCandidate.objects.get()
        result = scanner_services.import_candidate(
            candidate_id=candidate.id
        )
        self.assertTrue(result["success"])
        lead = Lead.objects.get(id=result["lead_id"])
        self.assertEqual(lead.source_url, self.URL)


@override_settings(SCANNER_PROFILE=PROFILE)
class JobUrlScanViewTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create(
            username="url-staff", is_staff=True
        )
        self.member = User.objects.create(username="url-member")

    def test_page_is_staff_only(self):
        self.assertNotEqual(
            self.client.get(reverse("scanner:scan_url")).status_code, 200
        )
        self.client.force_login(self.member)
        self.assertNotEqual(
            self.client.get(reverse("scanner:scan_url")).status_code, 200
        )

    def test_review_queue_shows_scan_job_form(self):
        self.client.force_login(self.staff)
        page = self.client.get(reverse("scanner:review_queue"))
        self.assertContains(page, reverse("scanner:scan_url"))
        self.assertContains(page, 'name="job_url"')

    def test_empty_url_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("scanner:scan_url"), {"job_url": ""}
        )
        self.assertContains(response, "Paste a job posting URL first.")
        self.assertEqual(LeadScanRun.objects.count(), 0)

    @patch("apps.scanner.services.scan_job_url")
    def test_success_links_to_candidate(self, mock_scan):
        mock_scan.return_value = {
            "success": True,
            "created": True,
            "candidate_id": 7,
            "company_name": "ABC Company",
            "opportunity_title": "Senior Data Analyst",
            "score": 95,
            "qualification": "high",
            "run_id": 3,
        }
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("scanner:scan_url"),
            {"job_url": "https://jobs.abc.com/1"},
        )
        self.assertContains(response, "Review this opportunity")
        self.assertContains(
            response, reverse("scanner:candidate_detail", args=[7])
        )

    @patch("apps.scanner.services.scan_job_url")
    def test_duplicate_offers_existing_result(self, mock_scan):
        mock_scan.return_value = {
            "success": True,
            "created": False,
            "candidate_id": 9,
            "company_name": "ABC Company",
            "opportunity_title": "Senior Data Analyst",
            "score": 95,
            "qualification": "high",
            "run_id": 4,
        }
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("scanner:scan_url"),
            {"job_url": "https://jobs.abc.com/1"},
        )
        self.assertContains(response, "already been scanned")
        self.assertContains(response, "View existing result")

    @patch("apps.scanner.services.scan_job_url")
    def test_failure_shows_message_without_crashing(self, mock_scan):
        mock_scan.return_value = {
            "success": False,
            "error": {
                "code": "LOGIN_REQUIRED",
                "message": (
                    "Unable to scan this job posting. The website "
                    "may require login or block automated access."
                ),
            },
            "run_id": 5,
        }
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("scanner:scan_url"),
            {"job_url": "https://jobs.abc.com/1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "require login or block automated access"
        )
        self.assertContains(response, "LOGIN_REQUIRED")
