from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.leads.models import Lead


class ApplicationShellTests(TestCase):
    """UI polish regressions: the shared shell, navigation
    visibility by role, and that major pages still render."""

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create(
            username="ui-staff", is_staff=True, is_superuser=True
        )
        self.member = User.objects.create(username="ui-member")

    # ---- shell / nav ----

    def test_shell_and_icons_present_for_authenticated_user(self):
        self.client.force_login(self.member)
        html = self.client.get("/").content.decode()
        self.assertIn("dodong-shell", html)
        self.assertIn("dodong-sidebar", html)
        self.assertIn("bootstrap-icons", html)
        self.assertIn("dodong.css", html)
        # mobile offcanvas trigger
        self.assertIn('data-bs-target="#dodongSidebar"', html)

    def test_staff_nav_links_visible_to_staff(self):
        self.client.force_login(self.staff)
        html = self.client.get("/").content.decode()
        for url_name in (
            "scanner:review_queue",
            "automation:run_history",
            "ai:crm_action_audit",
            "knowledge:assistant",
        ):
            self.assertIn(reverse(url_name), html, msg=url_name)
        self.assertIn("/admin/", html)

    def test_staff_nav_links_hidden_from_non_staff(self):
        self.client.force_login(self.member)
        html = self.client.get("/").content.decode()
        for url_name in (
            "scanner:review_queue",
            "automation:run_history",
            "ai:crm_action_audit",
            "knowledge:assistant",
        ):
            self.assertNotIn(reverse(url_name), html, msg=url_name)
        # ...but the shared AI + CRM links are present
        self.assertIn(reverse("ai:crm_assistant"), html)
        self.assertIn(reverse("leads:list"), html)

    def test_version_in_sidebar_footer(self):
        self.client.force_login(self.member)
        html = self.client.get("/").content.decode()
        self.assertIn("dodong-sidebar-footer", html)
        self.assertIn("v1.0.0", html)

    # ---- pages still render ----

    def test_major_pages_render_for_staff(self):
        Lead.objects.create(company_name="Acme", job_title="Analyst")
        self.client.force_login(self.staff)
        for name in (
            "dashboard",
            "leads:list",
            "leads:pipeline",
            "leads:dashboard",
            "ai:crm_assistant",
            "knowledge:assistant",
            "scanner:review_queue",
            "scanner:scan_runs",
            "automation:run_history",
            "ai:crm_action_audit",
        ):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, msg=name)

    def test_dashboard_shows_summary_tiles_for_staff(self):
        self.client.force_login(self.staff)
        html = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn("Pending tasks", html)
        self.assertIn("Last automation run", html)
        self.assertIn("Overdue tasks", html)

    def test_dashboard_member_sees_nav_cards_not_staff_tiles(self):
        self.client.force_login(self.member)
        html = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn("Dodong Assistant", html)
        self.assertNotIn("High-priority scanner candidates", html)

    # ---- safety unchanged ----

    def test_anonymous_still_redirected_from_assistant(self):
        self.assertNotEqual(
            self.client.get(reverse("ai:crm_assistant")).status_code,
            200,
        )
