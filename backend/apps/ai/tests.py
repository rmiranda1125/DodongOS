from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.leads.models import Lead, LeadActivity, LeadTask

from apps.ai.tools.crm.tasks import (
    get_lead_tasks_tool,
    get_overdue_tasks_tool,
    get_pending_tasks_tool,
    get_priority_tasks_tool,
)

from apps.ai.tools.crm.leads import (
    get_lead_tool,
    search_leads_tool,
)

from apps.ai.tools.crm.activities import (
    get_lead_activities_tool,
)

from apps.ai.tools.crm.pipeline import (
    get_pipeline_summary_tool,
)

from apps.ai.tools.registry import (
    TOOL_REGISTRY,
    execute_registered_tool,
    get_registered_tool,
    list_registered_tools,
)

from apps.ai.agent.read_agent import (
    run_crm_read_agent,
    run_crm_read_agent_with_provider,
)

from apps.ai.agent.response import (
    build_crm_read_response_prompt,
    generate_crm_read_response,
)

from apps.ai.agent.router import (
    extract_lead_id,
    extract_lead_search_arguments,
    route_crm_read_intent,
)


# =========================================================
# PRIORITY TASKS TOOL TESTS
# =========================================================

class PriorityTasksToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Test Company",
            job_title="Data Analyst",
        )

    def test_tool_returns_success_and_structured_data(self):
        task = LeadTask.objects.create(
            lead=self.lead,
            title="Follow up with client",
            description="Contact client regarding proposal.",
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(days=1),
        )

        result = get_priority_tasks_tool()

        self.assertTrue(result["success"])

        self.assertEqual(
            len(result["data"]),
            1,
        )

        returned_task = result["data"][0]

        self.assertIsInstance(
            returned_task,
            dict,
        )

        self.assertEqual(
            returned_task["id"],
            task.id,
        )

        self.assertEqual(
            returned_task["lead_id"],
            self.lead.id,
        )

        self.assertEqual(
            returned_task["lead_company"],
            "Test Company",
        )

        self.assertEqual(
            returned_task["title"],
            "Follow up with client",
        )

        self.assertEqual(
            returned_task["priority"],
            "high",
        )

    def test_tool_preserves_priority_order(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Low Task",
            priority="low",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Urgent Task",
            priority="urgent",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="High Task",
            priority="high",
            status="pending",
        )

        result = get_priority_tasks_tool()

        titles = [
            task["title"]
            for task in result["data"]
        ]

        self.assertEqual(
            titles,
            [
                "Urgent Task",
                "High Task",
                "Low Task",
            ],
        )

    def test_tool_respects_limit(self):
        for number in range(5):
            LeadTask.objects.create(
                lead=self.lead,
                title=f"Task {number}",
                priority="high",
                status="pending",
            )

        result = get_priority_tasks_tool(
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    def test_tool_returns_empty_success(self):
        result = get_priority_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_rejects_invalid_limit(self):
        result = get_priority_tasks_tool(
            limit=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LIMIT",
        )

    @patch(
        "apps.ai.tools.crm.tasks."
        "lead_services.get_priority_tasks"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_priority_tasks,
    ):
        mock_get_priority_tasks.return_value = []

        result = get_priority_tasks_tool(
            limit=3,
        )

        self.assertTrue(
            result["success"],
        )

        mock_get_priority_tasks.assert_called_once_with(
            limit=3,
        )


# =========================================================
# OVERDUE TASKS TOOL TESTS
# =========================================================

class OverdueTasksToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Overdue Test Company",
            job_title="BI Developer",
        )

    def test_tool_returns_overdue_tasks(self):
        overdue_task = LeadTask.objects.create(
            lead=self.lead,
            title="Overdue Follow Up",
            description="This should already have been completed.",
            task_type="follow_up",
            priority="high",
            status="pending",
            due_date=timezone.now() - timedelta(days=2),
        )

        result = get_overdue_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        returned_task = result["data"][0]

        self.assertEqual(
            returned_task["id"],
            overdue_task.id,
        )

        self.assertEqual(
            returned_task["title"],
            "Overdue Follow Up",
        )

        self.assertEqual(
            returned_task["lead_company"],
            "Overdue Test Company",
        )

    def test_tool_does_not_return_future_tasks(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Future Task",
            priority="high",
            status="pending",
            due_date=timezone.now() + timedelta(days=2),
        )

        result = get_overdue_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_does_not_return_completed_overdue_tasks(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Completed Old Task",
            priority="high",
            status="completed",
            due_date=timezone.now() - timedelta(days=3),
            completed_at=timezone.now(),
        )

        result = get_overdue_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_returns_structured_data(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Structured Overdue Task",
            priority="urgent",
            status="pending",
            due_date=timezone.now() - timedelta(hours=1),
        )

        result = get_overdue_tasks_tool()

        task = result["data"][0]

        self.assertIsInstance(
            task,
            dict,
        )

        self.assertIn("id", task)
        self.assertIn("lead_id", task)
        self.assertIn("lead_company", task)
        self.assertIn("title", task)
        self.assertIn("priority", task)
        self.assertIn("status", task)
        self.assertIn("due_date", task)

    def test_tool_respects_limit(self):
        for number in range(5):
            LeadTask.objects.create(
                lead=self.lead,
                title=f"Overdue Task {number}",
                priority="high",
                status="pending",
                due_date=timezone.now() - timedelta(days=number + 1),
            )

        result = get_overdue_tasks_tool(
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    def test_tool_rejects_invalid_limit(self):
        result = get_overdue_tasks_tool(
            limit=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LIMIT",
        )

    @patch(
        "apps.ai.tools.crm.tasks."
        "lead_services.get_overdue_tasks"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_overdue_tasks,
    ):
        mock_get_overdue_tasks.return_value = []

        result = get_overdue_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        mock_get_overdue_tasks.assert_called_once_with()


# =========================================================
# PENDING TASKS TOOL TESTS
# =========================================================

class PendingTasksToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Pending Test Company",
            job_title="Data Engineer",
        )

    def test_tool_returns_pending_task(self):
        task = LeadTask.objects.create(
            lead=self.lead,
            title="Pending Follow Up",
            task_type="follow_up",
            priority="medium",
            status="pending",
            due_date=timezone.now() + timedelta(days=1),
        )

        result = get_pending_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        returned_task = result["data"][0]

        self.assertEqual(
            returned_task["id"],
            task.id,
        )

        self.assertEqual(
            returned_task["title"],
            "Pending Follow Up",
        )

    def test_tool_returns_in_progress_task(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Research Lead",
            task_type="research",
            priority="high",
            status="in_progress",
        )

        result = get_pending_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"][0]["status"],
            "in_progress",
        )

    def test_tool_excludes_completed_and_cancelled_tasks(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Completed Task",
            priority="high",
            status="completed",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Cancelled Task",
            priority="urgent",
            status="cancelled",
        )

        result = get_pending_tasks_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_filters_by_priority(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Urgent Task",
            priority="urgent",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Low Task",
            priority="low",
            status="pending",
        )

        result = get_pending_tasks_tool(
            priority="urgent",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["title"],
            "Urgent Task",
        )

    def test_tool_respects_limit(self):
        for number in range(5):
            LeadTask.objects.create(
                lead=self.lead,
                title=f"Pending Task {number}",
                priority="medium",
                status="pending",
                due_date=(
                    timezone.now()
                    + timedelta(days=number + 1)
                ),
            )

        result = get_pending_tasks_tool(
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    def test_tool_rejects_invalid_priority(self):
        result = get_pending_tasks_tool(
            priority="super_important",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_PRIORITY",
        )

    def test_tool_rejects_invalid_limit(self):
        result = get_pending_tasks_tool(
            limit=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LIMIT",
        )

    @patch(
        "apps.ai.tools.crm.tasks."
        "lead_services.get_pending_tasks"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_pending_tasks,
    ):
        mock_get_pending_tasks.return_value = []

        result = get_pending_tasks_tool(
            priority="high",
        )

        self.assertTrue(
            result["success"],
        )

        mock_get_pending_tasks.assert_called_once_with(
            priority="high",
        )


# =========================================================
# LEAD TASKS TOOL TESTS
# =========================================================

class LeadTasksToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Lead Tasks Company",
            job_title="BI Developer",
        )

        self.other_lead = Lead.objects.create(
            company_name="Other Company",
            job_title="Data Engineer",
        )

    def test_tool_returns_tasks_for_requested_lead(self):
        task = LeadTask.objects.create(
            lead=self.lead,
            title="Requested Lead Task",
            priority="high",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.other_lead,
            title="Other Lead Task",
            priority="urgent",
            status="pending",
        )

        result = get_lead_tasks_tool(
            lead_id=self.lead.id,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["id"],
            task.id,
        )

        self.assertEqual(
            result["data"][0]["lead_id"],
            self.lead.id,
        )

    def test_tool_filters_by_status(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Pending Task",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Completed Task",
            status="completed",
        )

        result = get_lead_tasks_tool(
            lead_id=self.lead.id,
            status="completed",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["title"],
            "Completed Task",
        )

    def test_tool_filters_by_priority(self):
        LeadTask.objects.create(
            lead=self.lead,
            title="Urgent Task",
            priority="urgent",
            status="pending",
        )

        LeadTask.objects.create(
            lead=self.lead,
            title="Low Task",
            priority="low",
            status="pending",
        )

        result = get_lead_tasks_tool(
            lead_id=self.lead.id,
            priority="urgent",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["title"],
            "Urgent Task",
        )

    def test_tool_returns_lead_not_found(self):
        result = get_lead_tasks_tool(
            lead_id=999999,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

    def test_tool_rejects_invalid_lead_id(self):
        result = get_lead_tasks_tool(
            lead_id=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LEAD_ID",
        )

    def test_tool_rejects_invalid_status(self):
        result = get_lead_tasks_tool(
            lead_id=self.lead.id,
            status="waiting_for_magic",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_STATUS",
        )

    def test_tool_respects_limit(self):
        for number in range(5):
            LeadTask.objects.create(
                lead=self.lead,
                title=f"Lead Task {number}",
                priority="medium",
                status="pending",
            )

        result = get_lead_tasks_tool(
            lead_id=self.lead.id,
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    @patch(
        "apps.ai.tools.crm.tasks."
        "lead_services.get_lead_tasks_by_id"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_lead_tasks_by_id,
    ):
        mock_get_lead_tasks_by_id.return_value = []

        result = get_lead_tasks_tool(
            lead_id=7,
            status="pending",
            priority="high",
        )

        self.assertTrue(
            result["success"],
        )

        mock_get_lead_tasks_by_id.assert_called_once_with(
            lead_id=7,
            status="pending",
            priority="high",
        )


# =========================================================
# GET LEAD TOOL TESTS
# =========================================================

class GetLeadToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Dodong Test Company",
            job_title="BI Developer",
            industry="Technology",
            country="Philippines",
            lead_score=88,
            ai_summary="Strong Power BI opportunity.",
            recommended_services=[
                "Power BI",
                "Data Engineering",
            ],
            pain_points=[
                "Manual reporting",
            ],
            status="qualified",
        )

    def test_tool_returns_structured_lead(self):
        result = get_lead_tool(
            lead_id=self.lead.id,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertIsInstance(
            result["data"],
            dict,
        )

        self.assertEqual(
            result["data"]["id"],
            self.lead.id,
        )

        self.assertEqual(
            result["data"]["company_name"],
            "Dodong Test Company",
        )

        self.assertEqual(
            result["data"]["lead_score"],
            88,
        )

        self.assertEqual(
            result["data"]["status"],
            "qualified",
        )

    def test_tool_returns_ai_fields(self):
        result = get_lead_tool(
            lead_id=self.lead.id,
        )

        data = result["data"]

        self.assertEqual(
            data["ai_summary"],
            "Strong Power BI opportunity.",
        )

        self.assertEqual(
            data["recommended_services"],
            [
                "Power BI",
                "Data Engineering",
            ],
        )

        self.assertEqual(
            data["pain_points"],
            [
                "Manual reporting",
            ],
        )

    def test_tool_returns_lead_not_found(self):
        result = get_lead_tool(
            lead_id=999999,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

    def test_tool_rejects_invalid_lead_id(self):
        result = get_lead_tool(
            lead_id=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LEAD_ID",
        )

    @patch(
        "apps.ai.tools.crm.leads."
        "lead_services.get_lead_by_id"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_lead_by_id,
    ):
        mock_get_lead_by_id.return_value = self.lead

        result = get_lead_tool(
            lead_id=7,
        )

        self.assertTrue(
            result["success"],
        )

        mock_get_lead_by_id.assert_called_once_with(
            lead_id=7,
        )


# =========================================================
# SEARCH LEADS TOOL TESTS
# =========================================================

class SearchLeadsToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            industry="Technology",
            country="Philippines",
            location="Manila",
            lead_score=90,
            ai_summary="Needs automated Power BI reporting.",
            status="qualified",
        )

    def test_tool_returns_matching_lead(self):
        result = search_leads_tool(
            query="Acme",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["id"],
            self.lead.id,
        )

    def test_tool_searches_job_title(self):
        result = search_leads_tool(
            query="Power BI",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"][0]["company_name"],
            "Acme Analytics",
        )

    def test_tool_filters_by_status(self):
        Lead.objects.create(
            company_name="New Lead Company",
            status="new",
        )

        result = search_leads_tool(
            status="qualified",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["status"],
            "qualified",
        )

    def test_tool_filters_by_country(self):
        Lead.objects.create(
            company_name="US Company",
            country="United States",
        )

        result = search_leads_tool(
            country="Philippines",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["country"],
            "Philippines",
        )

    def test_tool_returns_empty_success(self):
        result = search_leads_tool(
            query="Company That Does Not Exist",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_rejects_invalid_status(self):
        result = search_leads_tool(
            status="maybe",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_STATUS",
        )

    def test_tool_respects_limit(self):
        for number in range(5):
            Lead.objects.create(
                company_name=f"Analytics Company {number}",
                job_title="Power BI Developer",
            )

        result = search_leads_tool(
            query="Analytics",
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    @patch(
        "apps.ai.tools.crm.leads."
        "lead_services.search_leads"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_search_leads,
    ):
        mock_search_leads.return_value = []

        result = search_leads_tool(
            query="Acme",
            status="qualified",
            country="Philippines",
            industry="Technology",
        )

        self.assertTrue(
            result["success"],
        )

        mock_search_leads.assert_called_once_with(
            query="Acme",
            status="qualified",
            country="Philippines",
            industry="Technology",
        )


# =========================================================
# LEAD ACTIVITIES TOOL TESTS
# =========================================================

class LeadActivitiesToolTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Activity Test Company",
            job_title="BI Developer",
        )

    def test_tool_returns_structured_activity(self):
        activity = LeadActivity.objects.create(
            lead=self.lead,
            activity_type="call",
            description="Called the decision maker.",
        )

        result = get_lead_activities_tool(
            lead_id=self.lead.id,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        returned_activity = result["data"][0]

        self.assertIsInstance(
            returned_activity,
            dict,
        )

        self.assertEqual(
            returned_activity["id"],
            activity.id,
        )

        self.assertEqual(
            returned_activity["lead_id"],
            self.lead.id,
        )

        self.assertEqual(
            returned_activity["lead_company"],
            "Activity Test Company",
        )

        self.assertEqual(
            returned_activity["activity_type"],
            "call",
        )

        self.assertEqual(
            returned_activity["description"],
            "Called the decision maker.",
        )

        self.assertIsNotNone(
            returned_activity["created_at"],
        )

    def test_tool_filters_by_activity_type(self):
        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="call",
            description="Called client.",
        )

        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="email",
            description="Sent proposal.",
        )

        result = get_lead_activities_tool(
            lead_id=self.lead.id,
            activity_type="email",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["activity_type"],
            "email",
        )

    def test_tool_returns_empty_success(self):
        result = get_lead_activities_tool(
            lead_id=self.lead.id,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

    def test_tool_returns_lead_not_found(self):
        result = get_lead_activities_tool(
            lead_id=999999,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

    def test_tool_rejects_invalid_lead_id(self):
        result = get_lead_activities_tool(
            lead_id=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LEAD_ID",
        )

    def test_tool_rejects_invalid_activity_type(self):
        result = get_lead_activities_tool(
            lead_id=self.lead.id,
            activity_type="magic",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_ACTIVITY_TYPE",
        )

    def test_tool_respects_limit(self):
        for number in range(5):
            LeadActivity.objects.create(
                lead=self.lead,
                activity_type="note",
                description=f"Activity {number}",
            )

        result = get_lead_activities_tool(
            lead_id=self.lead.id,
            limit=2,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            2,
        )

    @patch(
        "apps.ai.tools.crm.activities."
        "lead_services.get_lead_activities_by_id"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_lead_activities_by_id,
    ):
        mock_get_lead_activities_by_id.return_value = []

        result = get_lead_activities_tool(
            lead_id=7,
            activity_type="email",
        )

        self.assertTrue(
            result["success"],
        )

        mock_get_lead_activities_by_id.assert_called_once_with(
            lead_id=7,
            activity_type="email",
        )


# =========================================================
# PIPELINE SUMMARY TOOL TESTS
# =========================================================

class PipelineSummaryToolTests(TestCase):

    def test_tool_returns_pipeline_summary(self):
        Lead.objects.create(
            company_name="New Lead",
            status="new",
            lead_score=80,
        )

        Lead.objects.create(
            company_name="Qualified Lead",
            status="qualified",
            lead_score=100,
        )

        result = get_pipeline_summary_tool()

        self.assertTrue(
            result["success"],
        )

        data = result["data"]

        self.assertEqual(
            data["total_leads"],
            2,
        )

        self.assertEqual(
            data["by_status"]["new"],
            1,
        )

        self.assertEqual(
            data["by_status"]["qualified"],
            1,
        )

        self.assertEqual(
            data["average_lead_score"],
            90,
        )

    def test_tool_returns_all_pipeline_statuses(self):
        result = get_pipeline_summary_tool()

        self.assertTrue(
            result["success"],
        )

        by_status = result["data"]["by_status"]

        expected_statuses = {
            "new",
            "contacted",
            "qualified",
            "proposal",
            "won",
            "lost",
        }

        self.assertEqual(
            set(by_status.keys()),
            expected_statuses,
        )

    def test_tool_handles_empty_pipeline(self):
        result = get_pipeline_summary_tool()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"]["total_leads"],
            0,
        )

        self.assertIsNone(
            result["data"]["average_lead_score"],
        )

    @patch(
        "apps.ai.tools.crm.pipeline."
        "lead_services.get_pipeline_summary"
    )
    def test_tool_delegates_to_crm_service(
        self,
        mock_get_pipeline_summary,
    ):
        mock_get_pipeline_summary.return_value = {
            "total_leads": 0,
            "by_status": {
                "new": 0,
                "contacted": 0,
                "qualified": 0,
                "proposal": 0,
                "won": 0,
                "lost": 0,
            },
            "average_lead_score": None,
        }

        result = get_pipeline_summary_tool()

        self.assertTrue(
            result["success"],
        )

        mock_get_pipeline_summary.assert_called_once_with()


# =========================================================
# CRM TOOL REGISTRY TESTS
# =========================================================

class CRMToolRegistryTests(TestCase):

    def test_registry_contains_expected_tools(self):
        expected_tools = {
            "get_priority_tasks",
            "get_overdue_tasks",
            "get_pending_tasks",
            "get_lead_tasks",
            "get_lead",
            "search_leads",
            "get_lead_activities",
            "get_pipeline_summary",
        }

        self.assertEqual(
            set(TOOL_REGISTRY.keys()),
            expected_tools,
        )

    def test_all_registered_tools_are_read_only(self):
        for tool in TOOL_REGISTRY.values():
            self.assertEqual(
                tool.access_level,
                "read",
            )

    def test_get_registered_tool(self):
        tool = get_registered_tool(
            "get_pipeline_summary",
        )

        self.assertIsNotNone(
            tool,
        )

        self.assertEqual(
            tool.name,
            "get_pipeline_summary",
        )

    def test_unknown_tool_returns_none(self):
        tool = get_registered_tool(
            "delete_everything",
        )

        self.assertIsNone(
            tool,
        )

    def test_list_registered_tools_is_json_safe_metadata(self):
        tools = list_registered_tools()

        self.assertEqual(
            len(tools),
            8,
        )

        for tool in tools:
            self.assertIn(
                "name",
                tool,
            )

            self.assertIn(
                "description",
                tool,
            )

            self.assertIn(
                "access_level",
                tool,
            )

            self.assertIn(
                "input_schema",
                tool,
            )

            self.assertNotIn(
                "function",
                tool,
            )

    def test_execute_pipeline_summary_through_registry(self):
        Lead.objects.create(
            company_name="Registry Test Lead",
            status="qualified",
            lead_score=90,
        )

        result = execute_registered_tool(
            name="get_pipeline_summary",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"]["total_leads"],
            1,
        )

        self.assertEqual(
            result["data"]["by_status"]["qualified"],
            1,
        )

    def test_execute_get_lead_through_registry(self):
        lead = Lead.objects.create(
            company_name="Registry Lead",
            status="new",
        )

        result = execute_registered_tool(
            name="get_lead",
            arguments={
                "lead_id": lead.id,
            },
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"]["id"],
            lead.id,
        )

    def test_unknown_tool_is_rejected(self):
        result = execute_registered_tool(
            name="destroy_database",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "TOOL_NOT_FOUND",
        )

    def test_non_dict_arguments_are_rejected(self):
        result = execute_registered_tool(
            name="get_pipeline_summary",
            arguments="bad arguments",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_TOOL_ARGUMENTS",
        )

    def test_invalid_function_arguments_are_structured(self):
        result = execute_registered_tool(
            name="get_lead",
            arguments={
                "wrong_parameter": 123,
            },
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_TOOL_ARGUMENTS",
        )


# =========================================================
# CRM READ AGENT TESTS
# =========================================================

class CRMReadAgentTests(TestCase):

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_priority_question_uses_priority_tool(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="What tasks need my attention?",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_priority_tasks",
        )

        mock_execute_registered_tool.assert_called_once_with(
            name="get_priority_tasks",
            arguments={
                "limit": 10,
            },
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_agent_returns_structured_task_data(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [
                {
                    "id": 7,
                    "lead_id": 3,
                    "lead_company": "Acme Analytics",
                    "title": "Follow up with client",
                    "description": "",
                    "task_type": "follow_up",
                    "priority": "urgent",
                    "status": "pending",
                    "due_date": None,
                    "completed_at": None,
                },
            ],
        }

        result = run_crm_read_agent(
            message="What tasks need my attention?",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["id"],
            7,
        )

        self.assertIn(
            "Acme Analytics",
            result["answer"],
        )

        self.assertIn(
            "Follow up with client",
            result["answer"],
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_agent_handles_no_priority_tasks(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="What tasks need my attention?",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["data"],
            [],
        )

        self.assertIn(
            "no priority CRM tasks",
            result["answer"],
        )

    def test_write_question_does_not_execute_tool(self):
        with patch(
            "apps.ai.agent.read_agent."
            "execute_registered_tool"
        ) as mock_execute_registered_tool:

            result = run_crm_read_agent(
                message="Delete all my leads.",
            )

            self.assertFalse(
                result["success"],
            )

            self.assertEqual(
                result["error"]["code"],
                "WRITE_INTENT_NOT_ALLOWED",
            )

            mock_execute_registered_tool.assert_not_called()

    def test_agent_rejects_empty_message(self):
        result = run_crm_read_agent(
            message="   ",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_MESSAGE",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_agent_propagates_tool_failure(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": False,
            "error": {
                "code": "CRM_TOOL_ERROR",
                "message": (
                    "Unable to retrieve priority tasks."
                ),
            },
        }

        result = run_crm_read_agent(
            message="What tasks need my attention?",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_priority_tasks",
        )

        self.assertEqual(
            result["error"]["code"],
            "CRM_TOOL_ERROR",
        )


# =========================================================
# FAKE AI PROVIDERS
# =========================================================

class FakeAIProvider:

    def __init__(
        self,
        response="You have one urgent follow-up task.",
    ):
        self.response = response
        self.prompts = []

    def analyze(self, prompt):
        self.prompts.append(prompt)
        return self.response


class FailingAIProvider:

    def analyze(self, prompt):
        raise RuntimeError(
            "Provider unavailable"
        )


# =========================================================
# CRM READ AGENT RESPONSE TESTS
# =========================================================

class CRMReadAgentResponseTests(TestCase):

    def test_prompt_contains_verified_crm_data(self):
        prompt = build_crm_read_response_prompt(
            user_message="What tasks need my attention?",
            tool_used="get_priority_tasks",
            data=[
                {
                    "id": 7,
                    "lead_company": "Acme Analytics",
                    "title": "Follow up",
                    "priority": "urgent",
                    "status": "pending",
                },
            ],
        )

        self.assertIn(
            "What tasks need my attention?",
            prompt,
        )

        self.assertIn(
            "get_priority_tasks",
            prompt,
        )

        self.assertIn(
            "Acme Analytics",
            prompt,
        )

        self.assertIn(
            "Follow up",
            prompt,
        )

    def test_generate_response_uses_provider(self):
        provider = FakeAIProvider(
            response=(
                "Your urgent task is to follow up "
                "with Acme Analytics."
            ),
        )

        response = generate_crm_read_response(
            user_message="What tasks need my attention?",
            tool_used="get_priority_tasks",
            data=[
                {
                    "id": 7,
                    "lead_company": "Acme Analytics",
                    "title": "Follow up",
                    "priority": "urgent",
                    "status": "pending",
                },
            ],
            provider=provider,
        )

        self.assertEqual(
            response,
            (
                "Your urgent task is to follow up "
                "with Acme Analytics."
            ),
        )

        self.assertEqual(
            len(provider.prompts),
            1,
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_agent_generates_ai_response_from_verified_data(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [
                {
                    "id": 7,
                    "lead_id": 3,
                    "lead_company": "Acme Analytics",
                    "title": "Follow up",
                    "description": "",
                    "task_type": "follow_up",
                    "priority": "urgent",
                    "status": "pending",
                    "due_date": None,
                    "completed_at": None,
                },
            ],
        }

        provider = FakeAIProvider(
            response=(
                "Your most important task is the "
                "Acme Analytics follow-up."
            ),
        )

        result = run_crm_read_agent_with_provider(
            message="What tasks need my attention?",
            provider=provider,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_priority_tasks",
        )

        self.assertEqual(
            result["response_source"],
            "ai_provider",
        )

        self.assertEqual(
            result["answer"],
            (
                "Your most important task is the "
                "Acme Analytics follow-up."
            ),
        )

        self.assertEqual(
            len(result["data"]),
            1,
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_provider_failure_uses_deterministic_fallback(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [
                {
                    "id": 7,
                    "lead_id": 3,
                    "lead_company": "Acme Analytics",
                    "title": "Follow up",
                    "description": "",
                    "task_type": "follow_up",
                    "priority": "urgent",
                    "status": "pending",
                    "due_date": None,
                    "completed_at": None,
                },
            ],
        }

        result = run_crm_read_agent_with_provider(
            message="What tasks need my attention?",
            provider=FailingAIProvider(),
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["response_source"],
            "deterministic_fallback",
        )

        self.assertEqual(
            result["warning"]["code"],
            "AI_RESPONSE_FAILED",
        )

        self.assertIn(
            "Acme Analytics",
            result["answer"],
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_empty_provider_response_uses_fallback(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        provider = FakeAIProvider(
            response="   ",
        )

        result = run_crm_read_agent_with_provider(
            message="What tasks need my attention?",
            provider=provider,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["response_source"],
            "deterministic_fallback",
        )

        self.assertIn(
            "no priority CRM tasks",
            result["answer"],
        )

    def test_write_intent_does_not_call_provider(self):
        provider = FakeAIProvider()

        result = run_crm_read_agent_with_provider(
            message="Delete all my leads.",
            provider=provider,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

        self.assertEqual(
            provider.prompts,
            [],
        )


# =========================================================
# CRM READ INTENT ROUTER TESTS
# =========================================================

class CRMReadIntentRouterTests(TestCase):

    def test_routes_priority_tasks(self):
        result = route_crm_read_intent(
            "What tasks need my attention?"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_priority_tasks",
        )

    def test_routes_overdue_tasks(self):
        result = route_crm_read_intent(
            "What tasks are overdue?"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_overdue_tasks",
        )

    def test_routes_pending_tasks(self):
        result = route_crm_read_intent(
            "Show me pending tasks."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_pending_tasks",
        )

    def test_routes_pipeline_summary(self):
        result = route_crm_read_intent(
            "Summarize my pipeline."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_pipeline_summary",
        )

    def test_extracts_lead_id(self):
        lead_id = extract_lead_id(
            "Tell me about lead #12."
        )

        self.assertEqual(
            lead_id,
            12,
        )

    def test_routes_get_lead(self):
        result = route_crm_read_intent(
            "Tell me about lead 12."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_lead",
        )

        self.assertEqual(
            result["arguments"]["lead_id"],
            12,
        )

    def test_routes_lead_tasks(self):
        result = route_crm_read_intent(
            "What tasks belong to lead 12?"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_lead_tasks",
        )

        self.assertEqual(
            result["arguments"]["lead_id"],
            12,
        )

    def test_routes_lead_activities(self):
        result = route_crm_read_intent(
            "What happened with lead 12?"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "get_lead_activities",
        )

        self.assertEqual(
            result["arguments"]["lead_id"],
            12,
        )

    def test_rejects_write_intent(self):
        result = route_crm_read_intent(
            "Delete lead 12."
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

    def test_rejects_unsupported_read_intent(self):
        result = route_crm_read_intent(
            "Which company has the nicest logo?"
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "UNSUPPORTED_READ_INTENT",
        )

    # =====================================================
    # SEARCH PARSER TESTS
    # =====================================================

    def test_extracts_company_search(self):
        arguments = extract_lead_search_arguments(
            "Find Acme Analytics"
        )

        self.assertEqual(
            arguments,
            {
                "query": "acme analytics",
            },
        )

    def test_extracts_job_search(self):
        arguments = extract_lead_search_arguments(
            "Search for Power BI leads"
        )

        self.assertEqual(
            arguments,
            {
                "query": "power bi",
            },
        )

    def test_extracts_status_search(self):
        arguments = extract_lead_search_arguments(
            "Find qualified leads"
        )

        self.assertEqual(
            arguments,
            {
                "status": "qualified",
            },
        )

    def test_extracts_country_search(self):
        arguments = extract_lead_search_arguments(
            "Find leads in the Philippines"
        )

        self.assertEqual(
            arguments,
            {
                "country": "philippines",
            },
        )

    def test_extracts_combined_search(self):
        arguments = extract_lead_search_arguments(
            (
                "Find qualified Power BI leads "
                "in the Philippines"
            )
        )

        self.assertEqual(
            arguments,
            {
                "query": "power bi",
                "status": "qualified",
                "country": "philippines",
            },
        )

    # =====================================================
    # SEARCH ROUTING TESTS
    # =====================================================

    def test_routes_company_search(self):
        result = route_crm_read_intent(
            "Find Acme Analytics"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "search_leads",
        )

        self.assertEqual(
            result["arguments"],
            {
                "query": "acme analytics",
            },
        )

    def test_routes_qualified_leads(self):
        result = route_crm_read_intent(
            "Find qualified leads"
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_name"],
            "search_leads",
        )

        self.assertEqual(
            result["arguments"],
            {
                "status": "qualified",
            },
        )


# =========================================================
# CRM READ AGENT ROUTING TESTS
# =========================================================

class CRMReadAgentRoutingTests(TestCase):

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_overdue_question_executes_overdue_tool(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="What tasks are overdue?",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_overdue_tasks",
        )

        mock_execute_registered_tool.assert_called_once_with(
            name="get_overdue_tasks",
            arguments={
                "limit": 10,
            },
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_pipeline_question_executes_pipeline_tool(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": {
                "total_leads": 5,
                "by_status": {},
                "average_lead_score": None,
            },
        }

        result = run_crm_read_agent(
            message="Summarize my pipeline.",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_pipeline_summary",
        )

        mock_execute_registered_tool.assert_called_once_with(
            name="get_pipeline_summary",
            arguments={},
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_lead_question_passes_lead_id(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": {
                "id": 12,
                "company_name": "Acme Analytics",
                "status": "qualified",
            },
        }

        result = run_crm_read_agent(
            message="Tell me about lead 12.",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "get_lead",
        )

        mock_execute_registered_tool.assert_called_once_with(
            name="get_lead",
            arguments={
                "lead_id": 12,
            },
        )

    def test_write_request_executes_no_tool(self):
        with patch(
            "apps.ai.agent.read_agent."
            "execute_registered_tool"
        ) as mock_execute_registered_tool:

            result = run_crm_read_agent(
                message="Delete lead 12.",
            )

            self.assertFalse(
                result["success"],
            )

            self.assertEqual(
                result["error"]["code"],
                "WRITE_INTENT_NOT_ALLOWED",
            )

            mock_execute_registered_tool.assert_not_called()

    # =====================================================
    # END-TO-END SEARCH ROUTING
    # =====================================================

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_search_question_executes_search_tool(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [
                {
                    "id": 5,
                    "company_name": "Acme Analytics",
                    "job_title": "Power BI Developer",
                    "status": "qualified",
                },
            ],
        }

        result = run_crm_read_agent(
            message="Find Acme Analytics",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "search_leads",
        )

        self.assertEqual(
            result["intent"],
            "search_leads",
        )

        mock_execute_registered_tool.assert_called_once_with(
            name="search_leads",
            arguments={
                "query": "acme analytics",
                "limit": 10,
            },
        )

        self.assertIn(
            "Acme Analytics",
            result["answer"],
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_search_with_no_results_returns_safe_answer(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="Find Company That Does Not Exist",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["tool_used"],
            "search_leads",
        )

        self.assertEqual(
            result["data"],
            [],
        )

        self.assertIn(
            "No matching CRM leads",
            result["answer"],
        )