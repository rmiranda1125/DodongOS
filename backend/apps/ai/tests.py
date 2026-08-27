from datetime import timedelta
import token
from unittest.mock import patch
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from pathlib import Path
from apps.leads.models import Lead, LeadActivity, LeadTask
from apps.leads import services as lead_services
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
    execute_confirmed_write_tool,
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

from apps.ai.agent.write_proposals import (
    build_complete_lead_task_proposal,
    build_create_lead_task_proposal,
    build_change_lead_status_proposal,
    build_write_proposal_from_message,
)

from apps.ai.agent.write_executor import (
    execute_confirmed_proposal,
)

from apps.ai.agent.proposal_tokens import (
    load_action_proposal,
    sign_action_proposal,
)
from apps.ai.models import AIActionAudit
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
import uuid

from apps.ai import audit_services
from apps.ai.agent.write_router import (
    route_crm_write_proposal_intent,
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
            "create_lead_task",
            "complete_lead_task",
            "change_lead_status",
        }

        self.assertEqual(
            set(TOOL_REGISTRY.keys()),
            expected_tools,
        )

    def test_registered_tools_have_expected_access_levels(self):
        expected_access_levels = {
            "get_priority_tasks": "read",
            "get_overdue_tasks": "read",
            "get_pending_tasks": "read",
            "get_lead_tasks": "read",
            "get_lead": "read",
            "search_leads": "read",
            "get_lead_activities": "read",
            "get_pipeline_summary": "read",
            "create_lead_task": "write",
            "complete_lead_task": "write",
            "change_lead_status": "write",
        }

        actual_access_levels = {
            name: tool.access_level
            for name, tool in TOOL_REGISTRY.items()
        }

        self.assertEqual(
            actual_access_levels,
            expected_access_levels,
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
            11,
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

    def test_read_executor_cannot_complete_task(self):
        result = execute_registered_tool(
            name="complete_lead_task",
            arguments={
                "task_id": 1,
            },
        )

        self.assertFalse(
            result["success"],
        )

    def test_read_executor_cannot_change_lead_status(self):
        result = execute_registered_tool(
            name="change_lead_status",
            arguments={
                "lead_id": 1,
                "status": "qualified",
                "expected_status": "contacted",
            },
        )

        self.assertFalse(
            result["success"],
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

    def test_unknown_read_request_is_rejected(self):
        result = route_crm_read_intent(
            "Which lead has the prettiest website?"
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "UNSUPPORTED_READ_INTENT",
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

class CRMAssistantUITests(TestCase):

    def test_assistant_page_loads(self):
        response = self.client.get(
            reverse(
                "ai:crm_assistant",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Dodong CRM Assistant",
        )

        self.assertContains(
            response,
            "Read-only mode",
        )

    def test_assistant_page_contains_htmx_form(self):
        response = self.client.get(
            reverse(
                "ai:crm_assistant",
            )
        )

        self.assertContains(
            response,
            reverse(
                "ai:crm_assistant_ask",
            ),
        )

        self.assertContains(
            response,
            'hx-target="#assistant-response"',
        )

    def test_empty_question_returns_validation_error(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "   ",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Please enter a CRM question.",
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_question_calls_read_agent(
        self,
        mock_run_agent,
    ):
        mock_run_agent.return_value = {
            "success": True,
            "tool_used": "get_priority_tasks",
            "answer": (
                "You have one urgent task "
                "requiring attention."
            ),
            "data": [],
            "response_source": "ai_provider",
        }

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "What tasks need my attention?"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_run_agent.assert_called_once_with(
            message=(
                "What tasks need my attention?"
            ),
        )

        self.assertContains(
            response,
            "You have one urgent task",
        )

        self.assertContains(
            response,
            "get_priority_tasks",
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_write_request_error_is_rendered(
        self,
        mock_run_agent,
    ):
        mock_run_agent.return_value = {
            "success": False,
            "error": {
                "code": "WRITE_INTENT_NOT_ALLOWED",
                "message": (
                    "CRM write requests are not available "
                    "in the read-only agent."
                ),
            },
        }

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "Delete lead 12.",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "WRITE_INTENT_NOT_ALLOWED",
        )

        self.assertContains(
            response,
            "CRM write requests are not available",
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_provider_fallback_is_rendered(
        self,
        mock_run_agent,
    ):
        mock_run_agent.return_value = {
            "success": True,
            "tool_used": "get_priority_tasks",
            "answer": (
                "You have no priority CRM tasks "
                "requiring attention."
            ),
            "data": [],
            "response_source": (
                "deterministic_fallback"
            ),
            "warning": {
                "code": "AI_RESPONSE_FAILED",
                "message": (
                    "CRM data was retrieved successfully, "
                    "but the AI response could not "
                    "be generated."
                ),
            },
        }

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "What tasks need my attention?"
                ),
            },
        )

        self.assertContains(
            response,
            "Fallback response",
        )

        self.assertContains(
            response,
            "CRM data was retrieved successfully",
        )

    def test_assistant_page_contains_example_questions(self):
        response = self.client.get(
            reverse("ai:crm_assistant")
        )

        self.assertContains(
            response,
            "What tasks need my attention?"
        )

        self.assertContains(
            response,
            "What tasks are overdue?"
        )

        self.assertContains(
            response,
            "Summarize my pipeline."
        )

        self.assertContains(
            response,
            "Find qualified leads."
     )


    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_response_displays_user_question(
        self,
        mock_run_agent,
    ):
        mock_run_agent.return_value = {
            "success": True,
            "tool_used": "get_pipeline_summary",
            "answer": "Your CRM currently contains 10 leads.",
            "data": {},
            "response_source": "ai_provider",
        }

        response = self.client.post(
            reverse("ai:crm_assistant_ask"),
            {
            "message": "Summarize my pipeline.",
            },
        )

        self.assertContains(
            response,
            "You asked",
        )

        self.assertContains(
            response,
            "Summarize my pipeline.",
        )

        self.assertContains(
            response,
            "get_pipeline_summary",
        )

        self.assertContains(
            response,
            "ai_provider",
        )

class CRMReadAgentAcceptanceTests(TestCase):

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_priority_tasks(
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

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_priority_tasks",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_overdue_tasks(
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

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_overdue_tasks",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_pending_tasks(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="Show me pending tasks.",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_pending_tasks",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_pipeline_summary(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": {
                "total_leads": 0,
                "by_status": {},
                "average_lead_score": None,
            },
        }

        result = run_crm_read_agent(
            message="Summarize my pipeline.",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_pipeline_summary",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_get_lead(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": {
                "id": 12,
                "company_name": "Acme",
                "status": "qualified",
            },
        }

        result = run_crm_read_agent(
            message="Tell me about lead 12.",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_lead",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_lead_tasks(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="What tasks belong to lead 12?",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_lead_tasks",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_lead_activities(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="What happened with lead 12?",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "get_lead_activities",
        )

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_acceptance_search_leads(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [],
        }

        result = run_crm_read_agent(
            message="Find qualified leads.",
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            result["tool_used"],
            "search_leads",
        )

class CRMReadAgentWriteSafetyTests(TestCase):

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_delete_lead_is_blocked(
        self,
        mock_execute_registered_tool,
    ):
        result = run_crm_read_agent(
            message="Delete lead 12.",
        )

        self.assertFalse(result["success"])

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

        mock_execute_registered_tool.assert_not_called()

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_complete_task_is_blocked(
        self,
        mock_execute_registered_tool,
    ):
        result = run_crm_read_agent(
            message="Complete task 15.",
        )

        self.assertFalse(result["success"])

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

        mock_execute_registered_tool.assert_not_called()

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_create_task_is_blocked(
        self,
        mock_execute_registered_tool,
    ):
        result = run_crm_read_agent(
            message="Create a follow-up task.",
        )

        self.assertFalse(result["success"])

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

        mock_execute_registered_tool.assert_not_called()

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_change_status_is_blocked(
        self,
        mock_execute_registered_tool,
    ):
        result = run_crm_read_agent(
            message="Change status of lead 12 to won.",
        )

        self.assertFalse(result["success"])

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

        mock_execute_registered_tool.assert_not_called()

class CRMReadAgentRegistrySafetyTests(TestCase):

    def test_registry_contains_expected_access_levels(self):
        write_tools = {
            name
            for name, tool
            in TOOL_REGISTRY.items()
            if tool.access_level == "write"
        }

        self.assertEqual(
            write_tools,
            {
                "create_lead_task",
                "complete_lead_task",
                "change_lead_status",
            },
        )

    def test_registry_contains_no_unapproved_write_tools(self):
        prohibited_tools = {
            "update_lead_status",
            "create_activity",
            "delete_lead",
        }

        registered = set(
            TOOL_REGISTRY.keys()
        )

        self.assertTrue(
            prohibited_tools.isdisjoint(
                registered,
            )
        )

class CRMReadAgentArchitectureSafetyTests(TestCase):

    def test_agent_modules_do_not_access_django_orm(self):
        agent_directory = (
            Path(__file__).resolve().parent
            / "agent"
        )

        forbidden_patterns = (
            "Lead.objects",
            "LeadTask.objects",
            "LeadActivity.objects",
            ".objects.filter(",
            ".objects.create(",
            ".objects.get(",
            ".objects.update(",
            ".objects.delete(",
        )

        violations = []

        for file_path in agent_directory.glob(
            "*.py"
        ):
            source = file_path.read_text(
                encoding="utf-8",
            )

            for pattern in forbidden_patterns:
                if pattern in source:
                    violations.append(
                        (
                            file_path.name,
                            pattern,
                        )
                    )

        self.assertEqual(
            violations,
            [],
            msg=(
                "CRM Read Agent must not access "
                f"Django ORM directly: {violations}"
            ),
        )

    def test_read_executor_cannot_execute_write_tool(self):
        result = execute_registered_tool(
            name="create_lead_task",
            arguments={
                "lead_id": 1,
                "title": "Should never execute",
            },
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "TOOL_ACCESS_DENIED",
     )

class CRMReadAgentProviderSafetyTests(TestCase):

    @patch(
        "apps.ai.agent.read_agent."
        "execute_registered_tool"
    )
    def test_provider_failure_preserves_verified_crm_result(
        self,
        mock_execute_registered_tool,
    ):
        mock_execute_registered_tool.return_value = {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "lead_id": 2,
                    "lead_company": "Acme",
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
            len(result["data"]),
            1,
        )

        self.assertEqual(
            result["data"][0]["id"],
            1,
        )

        self.assertIn(
            "Acme",
            result["answer"],
        )

class CreateLeadTaskProposalTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def test_builds_follow_up_task_proposal(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Follow up with Acme",
            description="Discuss Power BI requirements.",
            priority="high",
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "create_lead_task",
        )

        self.assertEqual(
            proposal["access_level"],
            "write",
        )

        self.assertEqual(
            proposal["status"],
            "awaiting_confirmation",
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

        self.assertEqual(
            proposal["lead"]["id"],
            self.lead.id,
        )

        self.assertEqual(
            proposal["lead"]["company_name"],
            "Acme Analytics",
        )

        self.assertEqual(
            proposal["arguments"]["task_type"],
            "follow_up",
        )

        self.assertEqual(
            proposal["arguments"]["priority"],
            "high",
        )

    def test_proposal_does_not_create_task(self):
        before_count = LeadTask.objects.count()

        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Follow up tomorrow",
        )

        after_count = LeadTask.objects.count()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            before_count,
            after_count,
        )

    def test_missing_lead_is_rejected(self):
        result = build_create_lead_task_proposal(
            lead_id=999999,
            title="Follow up",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

    def test_invalid_lead_id_is_rejected(self):
        result = build_create_lead_task_proposal(
            lead_id=0,
            title="Follow up",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_LEAD_ID",
        )

    def test_empty_title_is_rejected(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="   ",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_TASK_TITLE",
        )

    def test_invalid_priority_is_rejected(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Follow up",
            priority="extreme",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_PRIORITY",
        )

    def test_valid_due_date_is_normalized(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Scheduled follow up",
            due_date="2026-08-25T09:00:00+08:00",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["proposal"]["arguments"]["due_date"],
            "2026-08-25T09:00:00+08:00",
        )

    def test_invalid_due_date_is_rejected(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Follow up",
            due_date="next Tuesday maybe",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_DUE_DATE",
        )

    def test_each_proposal_has_unique_proposal_id(self):
        first = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="First follow up",
        )

        second = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Second follow up",
        )

        self.assertTrue(
            first["success"],
        )

        self.assertTrue(
            second["success"],
        )

        first_id = first["proposal"][
            "proposal_id"
        ]

        second_id = second["proposal"][
            "proposal_id"
        ]

        self.assertNotEqual(
            first_id,
            second_id,
        )

class ConfirmedWriteExecutorTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def _build_proposal(self):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title="Follow up with Acme",
            description=(
                "Discuss Power BI requirements."
            ),
            priority="high",
        )

        self.assertTrue(
            result["success"],
        )

        return result["proposal"]

    def test_unconfirmed_proposal_does_not_write(self):
        proposal = self._build_proposal()

        before_count = LeadTask.objects.count()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=False,
        )

        after_count = LeadTask.objects.count()

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "CONFIRMATION_REQUIRED",
        )

        self.assertEqual(
            before_count,
            after_count,
        )

    def test_confirmed_proposal_creates_task(self):
        proposal = self._build_proposal()

        before_count = LeadTask.objects.count()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        after_count = LeadTask.objects.count()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            after_count,
            before_count + 1,
        )

        self.assertEqual(
            result["action"],
            "create_lead_task",
        )

        self.assertEqual(
            result["status"],
            "executed",
        )

        self.assertEqual(
            result["data"]["lead_id"],
            self.lead.id,
        )

        self.assertEqual(
            result["data"]["title"],
            "Follow up with Acme",
        )

    def test_created_task_is_verified(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        task_id = result["data"]["id"]

        tasks = (
            lead_services.get_lead_tasks_by_id(
                lead_id=self.lead.id,
            )
        )

        matching_tasks = [
            task
            for task in tasks
            if task.id == task_id
        ]

        self.assertEqual(
            len(matching_tasks),
            1,
        )

    def test_only_enabled_write_action_is_allowed(self):
        proposal = self._build_proposal()

        proposal["action"] = "delete_lead"

        before_count = LeadTask.objects.count()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        after_count = LeadTask.objects.count()

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "UNSUPPORTED_WRITE_ACTION",
        )

        self.assertEqual(
            before_count,
            after_count,
        )   

    def test_write_registry_requires_confirmation(self):
        result = execute_confirmed_write_tool(
            name="create_lead_task",
            arguments={
                "lead_id": self.lead.id,
                "title": "Follow up",
            },
            confirmed=False,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "CONFIRMATION_REQUIRED",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    def test_confirmed_execution_creates_audit_record(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            str(audit.proposal_id),
            proposal["proposal_id"],
        )

        self.assertEqual(
            audit.action,
            "create_lead_task",
        )

        self.assertEqual(
            audit.status,
            "executed",
        )

        self.assertEqual(
            audit.lead_id,
            self.lead.id,
        )

        self.assertEqual(
            audit.result_task_id,
            result["data"]["id"],
        )

        self.assertEqual(
            audit.proposal_data["title"],
            "Follow up with Acme",
        )

    def test_same_proposal_cannot_execute_twice(self):
        proposal = self._build_proposal()

        first_result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            first_result["success"],
        )

        task_count_after_first = (
            LeadTask.objects.count()
        )

        second_result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertFalse(
            second_result["success"],
        )

        self.assertEqual(
            second_result["error"]["code"],
            "PROPOSAL_ALREADY_USED",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            task_count_after_first,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

    def test_confirmed_proposal_requires_valid_proposal_id(self):
        proposal = self._build_proposal()

        proposal["proposal_id"] = "not-a-uuid"

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_PROPOSAL_ID",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_audit_points_to_verified_created_task(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )   

        self.assertTrue(
            result["success"],
        )

        audit = AIActionAudit.objects.get(
            id=result["audit_id"],
        )

        task = LeadTask.objects.get(
            id=result["data"]["id"],
        )

        self.assertEqual(
            audit.result_task_id,
            task.id,
        )

        self.assertEqual(
            audit.lead_id,
            task.lead_id,
        )   

class ConfirmedTaskCompletionExecutorTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

        self.task = LeadTask.objects.create(
            lead=self.lead,
            title="Send pricing proposal",
            task_type="follow_up",
            priority="high",
            status="pending",
        )

    def _build_proposal(self):
        result = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        self.assertTrue(
            result["success"],
        )

        return result["proposal"]


    def test_unconfirmed_completion_does_not_write(self):
        proposal = self._build_proposal()

        before_activity_count = (
            LeadActivity.objects.count()
        )

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=False,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "CONFIRMATION_REQUIRED",
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertIsNone(
            self.task.completed_at,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            before_activity_count,
        )


    def test_confirmed_completion_completes_task(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "completed",
        )

        self.assertIsNotNone(
            self.task.completed_at,
        )

        self.assertEqual(
            result["action"],
            "complete_lead_task",
        )

        self.assertEqual(
            result["status"],
            "executed",
        )


    def test_completion_creates_activity(self):
        proposal = self._build_proposal()

        before_count = LeadActivity.objects.count()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            before_count + 1,
        )


    def test_completion_creates_executed_audit(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            audit.action,
            "complete_lead_task",
        )

        self.assertEqual(
            audit.status,
            "executed",
        )

        self.assertEqual(
            audit.result_task_id,
            self.task.id,
        )

        self.assertEqual(
            str(audit.proposal_id),
            proposal["proposal_id"],
        )


    def test_completion_proposal_cannot_execute_twice(self):
        proposal = self._build_proposal()

        first = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            first["success"],
        )

        activity_count = (
            LeadActivity.objects.count()
        )

        second = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertFalse(
            second["success"],
        )

        self.assertEqual(
            second["error"]["code"],
            "PROPOSAL_ALREADY_USED",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        ) 

class CRMActionProposalTokenTests(TestCase):

    def test_signed_proposal_round_trip(self):
        proposal = {
            "action": "create_lead_task",
            "status": "awaiting_confirmation",
            "requires_confirmation": True,
            "arguments": {
                "lead_id": 12,
                "title": "Follow up",
            },
        }

        token = sign_action_proposal(
            proposal,
        )

        result = load_action_proposal(
            token,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["proposal"],
            proposal,
        )

    def test_modified_token_is_rejected(self):
        proposal = {
            "action": "create_lead_task",
            "arguments": {
                "lead_id": 12,
                "title": "Follow up",
            },
        }

        token = sign_action_proposal(
            proposal,
        )

        tampered_token = (
            token[:-1]
            + (
                "A"
                if token[-1] != "A"
                else "B"
            )
        )

        result = load_action_proposal(
            tampered_token,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_PROPOSAL_TOKEN",
        )

class CRMTaskProposalViewTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def test_proposal_endpoint_returns_review_card(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
            {
                "lead_id": self.lead.id,
                "title": "Follow up with Acme",
                "description": (
                    "Discuss Power BI requirements."
                ),
                "priority": "high",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Proposed CRM Change",
        )

        self.assertContains(
            response,
            "Acme Analytics",
        )

        self.assertContains(
            response,
            "Follow up with Acme",
        )

        self.assertContains(
            response,
            "No CRM change has been made yet.",
        )

    def test_proposal_endpoint_does_not_create_task(self):
        before_count = LeadTask.objects.count()

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
            {
                "lead_id": self.lead.id,
                "title": "Follow up with Acme",
                "priority": "medium",
            },
        )

        after_count = LeadTask.objects.count()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            before_count,
            after_count,
        )

    def test_proposal_endpoint_returns_signed_token(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
            {
                "lead_id": self.lead.id,
                "title": "Follow up with Acme",
                "priority": "medium",
            },
        )

        token = response.context[
            "proposal_token"
        ]

        result = load_action_proposal(
            token,
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "create_lead_task",
        )

        self.assertEqual(
            proposal["arguments"]["lead_id"],
            self.lead.id,
        )

        self.assertEqual(
            proposal["arguments"]["title"],
            "Follow up with Acme",
        )

    def test_invalid_proposal_does_not_return_token(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
            {
                "lead_id": self.lead.id,
                "title": "",
            },
        )

        self.assertContains(
            response,
            "INVALID_TASK_TITLE",
        )

        self.assertNotIn(
            "proposal_token",
            response.context,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    def test_proposal_contains_explicit_confirm_control(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
            {
                "lead_id": self.lead.id,
                "title": "Follow up",
                "priority": "medium",
            },
        )

        self.assertContains(
            response,
            "Confirm Create Task",
        )

        self.assertContains(
            response,
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
        ),

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

class CRMTaskConfirmationViewTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def _build_token(
        self,
        *,
        title="Follow up with Acme",
    ):
        result = build_create_lead_task_proposal(
            lead_id=self.lead.id,
            title=title,
            priority="high",
        )

        self.assertTrue(
            result["success"],
        )

        return sign_action_proposal(
            result["proposal"],
        )

    def test_confirm_valid_proposal_creates_task(self):
        token = self._build_token()

        before_count = LeadTask.objects.count()

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        after_count = LeadTask.objects.count()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            after_count,
            before_count + 1,
        )

        self.assertContains(
            response,
            "CRM Task Created",
        )

        self.assertContains(
            response,
            "Follow up with Acme",
        )

    def test_missing_token_does_not_write(self):
        before_count = LeadTask.objects.count()

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {},
        )

        after_count = LeadTask.objects.count()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            before_count,
            after_count,
        )

        self.assertContains(
            response,
            "MISSING_PROPOSAL_TOKEN",
        )

    def test_tampered_token_does_not_write(self):
        token = self._build_token()

        tampered_token = (
            token[:-1]
            + (
                "A"
                if token[-1] != "A"
                else "B"
            )
        )

        before_count = LeadTask.objects.count()

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": tampered_token,
            },
        )

        after_count = LeadTask.objects.count()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            before_count,
            after_count,
        )

        self.assertContains(
            response,
            "INVALID_PROPOSAL_TOKEN",
        )

    def test_confirm_uses_signed_values_not_forged_post_fields(
        self,
    ):
        token = self._build_token(
            title="Approved signed task",
        )

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,

                # These fields must be ignored.
                "lead_id": 999999,
                "title": "FORGED TASK",
                "priority": "urgent",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        task = LeadTask.objects.get()

        self.assertEqual(
            task.lead_id,
            self.lead.id,
        )

        self.assertEqual(
            task.title,
            "Approved signed task",
        )

        self.assertNotEqual(
            task.title,
            "FORGED TASK",
        )

    def test_assistant_page_contains_controlled_task_form(self):
        response = self.client.get(
            reverse(
                "ai:crm_assistant",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Create Follow-Up Task",
        )

        self.assertContains(
            response,
            "Controlled write action.",
        )

        self.assertContains(
            response,
            "Review Task Proposal",
        )

        self.assertContains(
            response,
            reverse(
                "ai:crm_assistant_task_proposal",
            ),
        ),

    def test_same_confirmation_token_cannot_create_two_tasks(self):
        token = self._build_token(
            title="One-time task",
        )

        first_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        second_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        self.assertContains(
            second_response,
            "PROPOSAL_ALREADY_USED",
        )

    def test_successful_confirmation_shows_verified_message(self):
        token = self._build_token(
            title="Follow up with Acme",
        )

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "CRM Task Created",
        )

        self.assertContains(
            response,
            "Dodong verified that the new task",
        )

        self.assertContains(
            response,
            "Follow up with Acme",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

    def test_replayed_confirmation_has_clear_message(self):
        token = self._build_token(
            title="One-time follow up",
        )

        first_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        second_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertContains(
            second_response,
            "This action was already processed.",
        )

        self.assertContains(
            second_response,
            "Dodong did not create another task.",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

    def test_invalid_confirmation_token_has_safe_message(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": (
                    "this-is-not-a-valid-token"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "This proposal could not be verified.",
        )

        self.assertContains(
            response,
            "No CRM change was made.",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

class AIActionAuditAdminTests(TestCase):

    def test_action_audit_is_registered_with_admin(self):
        self.assertIn(
            AIActionAudit,
            site._registry,
        )

    def test_action_audit_admin_disallows_add(self):
        model_admin = site._registry[
            AIActionAudit
        ]

        request = self.client.request()

        self.assertFalse(
            model_admin.has_add_permission(
                request,
            )
        )

    def test_recent_action_audits_returns_json_safe_data(self):
        proposal_id = uuid.uuid4()

        audit_services.create_action_audit(
            proposal_id=proposal_id,
            action="create_lead_task",
            lead_id=12,
            proposal_data={
                "title": "Follow up",
            },
        )

        audits = (
            audit_services.get_recent_action_audits()
        )

        self.assertEqual(
            len(audits),
            1,
        )

        self.assertEqual(
            audits[0]["proposal_id"],
            str(proposal_id),
        )

        self.assertEqual(
            audits[0]["action"],
            "create_lead_task",
        )    

class CRMActionAuditViewTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.staff_user = User.objects.create_user(
            username="auditstaff",
            password="test-password",
            is_staff=True,
        )

    def test_non_staff_user_cannot_view_audit_page(self):
        response = self.client.get(
            reverse(
                "ai:crm_action_audit",
            )
        )

        self.assertNotEqual(
            response.status_code,
            200,
        )

    def test_staff_user_can_view_audit_page(self):
        self.client.force_login(
            self.staff_user,
        )

        response = self.client.get(
            reverse(
                "ai:crm_action_audit",
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Dodong Action Audit",
        )

    def test_audit_page_displays_execution_record(self):
        proposal = {
            "lead_id": 12,
            "title": "Follow up",
        }

        audit_services.create_action_audit(
            proposal_id=uuid.uuid4(),
            action="create_lead_task",
            lead_id=12,
            proposal_data=proposal,
        )

        audit = AIActionAudit.objects.get()

        audit_services.mark_action_audit_executed(
            audit=audit,
            result_task_id=99,
        )

        self.client.force_login(
            self.staff_user,
        )

        response = self.client.get(
            reverse(
                "ai:crm_action_audit",
            )
        )

        self.assertContains(
            response,
            "create_lead_task",
        )

        self.assertContains(
            response,
            "12",
        )

        self.assertContains(
            response,
            "99",
        )

        self.assertContains(
            response,
            "Executed",
        )

class CRMWriteProposalRouterTests(TestCase):

    def test_routes_basic_follow_up_task_request(self):
        result = route_crm_write_proposal_intent(
            "Create a follow-up task for lead 12."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["intent"],
            "create_lead_task_proposal",
        )

        self.assertEqual(
            result["action"],
            "create_lead_task",
        )

        self.assertEqual(
            result["arguments"]["lead_id"],
            12,
        )

        self.assertEqual(
            result["arguments"]["priority"],
            "medium",
        )

    def test_extracts_priority(self):
        result = route_crm_write_proposal_intent(
            "Create a high priority follow-up "
            "task for lead 12."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["arguments"]["priority"],
            "high",
        )

    def test_extracts_requested_task_title(self):
        result = route_crm_write_proposal_intent(
            "Create a follow-up task for lead 12 "
            "to Send the proposal."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["arguments"]["title"],
            "Send the proposal",
        )

    def test_unsupported_write_request_is_rejected(self):
        result = route_crm_write_proposal_intent(
            "Delete lead 12."
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "UNSUPPORTED_WRITE_PROPOSAL_INTENT",
        )

    def test_accepts_follow_up_with_space(self):
        result = route_crm_write_proposal_intent(
            "Create a follow up task for lead 12."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["arguments"]["lead_id"],
            12,
        )


    def test_accepts_followup_as_one_word(self):
        result = route_crm_write_proposal_intent(
            "Create a followup task for lead 12."
        )

        self.assertTrue(
            result["success"],
        )


    def test_accepts_polite_create_request(self):
        result = route_crm_write_proposal_intent(
            "Please create a follow-up task for lead 12."
        )

        self.assertTrue(
            result["success"],
        )

    def test_routes_complete_task_request(self):
        result = route_crm_write_proposal_intent(
            "Complete task 15."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["intent"],
            "complete_lead_task_proposal",
        )

        self.assertEqual(
            result["action"],
            "complete_lead_task",
        )

        self.assertEqual(
            result["arguments"]["task_id"],
            15,
        )

    def test_routes_polite_complete_task_request(self):
        result = route_crm_write_proposal_intent(
            "Please complete task #15."
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["arguments"]["task_id"],
            15,
        )

class CRMNaturalLanguageTaskProposalTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def test_natural_language_builds_task_proposal(self):
        result = build_write_proposal_from_message(
            (
                "Create a high priority follow-up "
                f"task for lead {self.lead.id}."
            )
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "create_lead_task",
        )

        self.assertEqual(
            proposal["lead"]["id"],
            self.lead.id,
        )

        self.assertEqual(
            proposal["arguments"]["priority"],
            "high",
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

        self.assertEqual(
            proposal["status"],
            "awaiting_confirmation",
        )

        self.assertIn(
            "proposal_id",
            proposal,
        )

    def test_natural_language_proposal_does_not_write(self):
        before_count = LeadTask.objects.count()

        result = build_write_proposal_from_message(
            (
                "Create a follow-up task "
                f"for lead {self.lead.id}."
            )
        )

        after_count = LeadTask.objects.count()

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            before_count,
            after_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_missing_lead_is_rejected_without_write(self):
        result = build_write_proposal_from_message(
            "Create a follow-up task for lead 999999."
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    def test_read_agent_still_blocks_write_request(self):
        result = run_crm_read_agent(
            message=(
                "Create a follow-up task for lead 12."
            ),
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "WRITE_INTENT_NOT_ALLOWED",
        )

    def test_default_task_title_uses_company_name(self):
        result = build_write_proposal_from_message(
            (
                "Create a follow-up task "
                f"for lead {self.lead.id}."
            )
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["proposal"]["arguments"]["title"],
            "Follow up with Acme Analytics",
        )

    def test_explicit_task_title_is_preserved(self):
        result = build_write_proposal_from_message(
            (
                "Create a follow-up task "
                f"for lead {self.lead.id} "
                "to Send pricing proposal."
            )
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["proposal"]["arguments"]["title"],
            "Send pricing proposal",
        )

class CRMAssistantNaturalLanguageWriteTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def test_supported_write_request_returns_proposal_card(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a high priority "
                    "follow-up task for lead "
                    f"{self.lead.id}."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Proposed CRM Change",
        )

        self.assertContains(
            response,
            "Acme Analytics",
        )

        self.assertContains(
            response,
            "Confirm Create Task",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_supported_write_proposal_does_not_call_read_agent(
        self,
        mock_read_agent,
    ):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id}."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_read_agent.assert_not_called()

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    def test_natural_language_proposal_returns_signed_token(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id}."
                ),
            },
        )

        token = response.context[
            "proposal_token"
        ]

        loaded = load_action_proposal(
            token,
        )

        self.assertTrue(
            loaded["success"],
        )

        proposal = loaded[
            "proposal"
        ]

        self.assertEqual(
            proposal["action"],
            "create_lead_task",
        )

        self.assertEqual(
            proposal["arguments"]["lead_id"],
            self.lead.id,
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

    def test_missing_lead_returns_proposal_error_without_write(
        self,
    ):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    "for lead 999999."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "LEAD_NOT_FOUND",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_unsupported_write_request_remains_blocked(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Delete lead {self.lead.id}."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "WRITE_INTENT_NOT_ALLOWED",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_read_request_still_uses_read_agent(
        self,
        mock_read_agent,
    ):
        mock_read_agent.return_value = {
            "success": True,
            "tool_used": "get_pipeline_summary",
            "answer": (
                "Your CRM pipeline contains 5 leads."
            ),
            "data": {
                "total_leads": 5,
            },
            "response_source": "ai_provider",
        }

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Summarize my pipeline."
                ),
            },
        )

        mock_read_agent.assert_called_once_with(
            message="Summarize my pipeline.",
        )

        self.assertContains(
            response,
            "Your CRM pipeline contains 5 leads.",
        )

    def test_natural_language_proposal_requires_separate_confirmation(
        self,
    ):
        #
        # Step 1:
        # Natural language creates proposal only.
        #

        proposal_response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id} "
                    "to Send proposal."
                ),
            },
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        #
        # Step 2:
        # Explicit confirmation executes it.
        #

        confirm_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            confirm_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        task = LeadTask.objects.get()

        self.assertEqual(
            task.title,
            "Send proposal",
        )

        self.assertContains(
            confirm_response,
            "CRM Task Created",
        )

    def test_typing_yes_does_not_confirm_previous_proposal(
        self,
    ):
        proposal_response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id}."
                ),
            },
        )

        self.assertEqual(
            proposal_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "Yes.",
            },
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_go_ahead_does_not_execute_write(self):
        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id}."
                ),
            },
        )

        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "Go ahead.",
            },
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_do_it_does_not_execute_write(self):
        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id}."
                ),
            },
        )

        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "Do it.",
            },
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

class CRMNaturalLanguageWriteAcceptanceTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

    def _ask_for_task(
        self,
        message=None,
    ):
        if message is None:
            message = (
                "Create a high priority follow-up task "
                f"for lead {self.lead.id} "
                "to Send pricing proposal."
            )

        return self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": message,
            },
        )

    def test_acceptance_proposal_stage_performs_no_write(self):
        response = self._ask_for_task()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Proposed CRM Change",
        )

        self.assertContains(
            response,
            "Confirm Create Task",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_acceptance_confirmation_creates_one_verified_task_and_audit(
        self,
    ):
        proposal_response = self._ask_for_task()

        token = proposal_response.context[
            "proposal_token"
        ]

        confirm_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            confirm_response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        task = LeadTask.objects.get()

        self.assertEqual(
            task.lead_id,
            self.lead.id,
        )

        self.assertEqual(
            task.title,
            "Send pricing proposal",
        )

        self.assertEqual(
            task.priority,
            "high",
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            audit.status,
            "executed",
        )

        self.assertEqual(
            audit.result_task_id,
            task.id,
        )

        self.assertContains(
            confirm_response,
            "CRM Task Created",
        )

    def test_acceptance_same_token_cannot_execute_twice(self):
        proposal_response = self._ask_for_task()

        token = proposal_response.context[
            "proposal_token"
        ]

        first = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        second = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        self.assertContains(
            second,
            "PROPOSAL_ALREADY_USED",
        )

    def test_acceptance_tampered_token_cannot_write(self):
        proposal_response = self._ask_for_task()

        token = proposal_response.context[
            "proposal_token"
        ]

        tampered = (
            token[:-1]
            + (
                "A"
                if token[-1] != "A"
                else "B"
            )
        )

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": tampered,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

        self.assertContains(
            response,
            "INVALID_PROPOSAL_TOKEN",
        )

    def test_acceptance_delete_request_remains_blocked(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Delete lead {self.lead.id}."
                ),
            },
        )

        self.assertContains(
            response,
            "WRITE_INTENT_NOT_ALLOWED",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_acceptance_status_change_remains_blocked(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Change status of lead "
                    f"{self.lead.id} to won."
                ),
            },
        )

        self.assertContains(
            response,
            "WRITE_INTENT_NOT_ALLOWED",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

    def test_acceptance_chat_confirmation_words_never_execute(
        self,
    ):
        self._ask_for_task()

        for message in (
            "Yes.",
            "Confirm.",
            "Go ahead.",
            "Do it.",
        ):
            self.client.post(
                reverse(
                    "ai:crm_assistant_ask",
                ),
                {
                    "message": message,
                },
            )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    @patch(
        "apps.ai.views."
        "run_crm_read_agent_with_provider"
    )
    def test_acceptance_read_requests_still_use_read_agent(
        self,
        mock_read_agent,
    ):
        mock_read_agent.return_value = {
            "success": True,
            "tool_used": "get_pipeline_summary",
            "answer": (
                "Your CRM pipeline contains 5 leads."
            ),
            "data": {
                "total_leads": 5,
            },
            "response_source": "ai_provider",
        }

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Summarize my pipeline."
                ),
            },
        )

        mock_read_agent.assert_called_once_with(
            message="Summarize my pipeline.",
        )

        self.assertContains(
            response,
            "Your CRM pipeline contains 5 leads.",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            0,
        )

class CompleteLeadTaskProposalTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

        self.task = LeadTask.objects.create(
            lead=self.lead,
            title="Send pricing proposal",
            task_type="follow_up",
            priority="high",
            status="pending",
        )

    def test_builds_task_completion_proposal(self):
        result = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "complete_lead_task",
        )

        self.assertEqual(
            proposal["access_level"],
            "write",
        )

        self.assertEqual(
            proposal["status"],
            "awaiting_confirmation",
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

        self.assertEqual(
            proposal["task"]["id"],
            self.task.id,
        )

        self.assertEqual(
            proposal["task"]["title"],
            "Send pricing proposal",
        )

        self.assertEqual(
            proposal["lead"]["id"],
            self.lead.id,
        )

        self.assertEqual(
            proposal["arguments"]["task_id"],
            self.task.id,
        )

        self.assertIn(
            "proposal_id",
            proposal,
        )

    def test_proposal_does_not_complete_task(self):
        before_activity_count = (
            LeadActivity.objects.count()
        )

        result = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        self.assertTrue(
            result["success"],
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertIsNone(
            self.task.completed_at,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            before_activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_proposal_contains_task_and_lead_snapshot(self):
        result = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["task"]["priority"],
            "high",
        )

        self.assertEqual(
            proposal["task"]["task_type"],
            "follow_up",
        )

        self.assertEqual(
            proposal["task"]["status"],
            "pending",
        )

        self.assertEqual(
            proposal["lead"]["company_name"],
            "Acme Analytics",
        )

    def test_missing_task_is_rejected(self):
        result = build_complete_lead_task_proposal(
            task_id=999999,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "TASK_NOT_FOUND",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

    def test_invalid_task_id_is_rejected(self):
        result = build_complete_lead_task_proposal(
            task_id=0,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "INVALID_TASK_ID",
        )

    def test_already_completed_task_is_rejected(self):
        self.task.status = "completed"
        self.task.save(
            update_fields=[
                "status",
            ]
        )

        result = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "TASK_ALREADY_COMPLETED",
        )

    def test_completion_proposals_have_unique_ids(self):
        first = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        second = build_complete_lead_task_proposal(
            task_id=self.task.id,
        )

        self.assertNotEqual(
            first["proposal"]["proposal_id"],
            second["proposal"]["proposal_id"],
        )

class ChangeLeadStatusProposalTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

    def test_builds_change_lead_status_proposal(self):
        result = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="qualified",
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "change_lead_status",
        )

        self.assertEqual(
            proposal["access_level"],
            "write",
        )

        self.assertEqual(
            proposal["status"],
            "awaiting_confirmation",
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

        self.assertEqual(
            proposal["arguments"],
            {
                "lead_id": self.lead.id,
                "status": "qualified",
                "expected_status": "contacted",
            },
        )

    def test_proposal_contains_lead_snapshot(self):
        result = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="qualified",
        )

        self.assertTrue(
            result["success"],
        )

        lead_snapshot = result[
            "proposal"
        ]["lead"]

        self.assertEqual(
            lead_snapshot["id"],
            self.lead.id,
        )

        self.assertEqual(
            lead_snapshot["company_name"],
            "Acme Analytics",
        )

        self.assertEqual(
            lead_snapshot["status"],
            "contacted",
        )

    def test_proposal_does_not_change_lead_status(self):
        before_activity_count = (
            LeadActivity.objects.count()
        )

        before_audit_count = (
            AIActionAudit.objects.count()
        )

        result = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="qualified",
        )

        self.assertTrue(
            result["success"],
        )

        self.lead.refresh_from_db()

        self.assertEqual(
            self.lead.status,
            "contacted",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            before_activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            before_audit_count,
        )

    def test_rejects_invalid_lead_id(self):
        invalid_ids = (
            0,
            -1,
            True,
            "1",
            None,
        )

        for invalid_id in invalid_ids:
            with self.subTest(
                lead_id=invalid_id,
            ):
                result = (
                    build_change_lead_status_proposal(
                        lead_id=invalid_id,
                        status="qualified",
                    )
                )

                self.assertFalse(
                    result["success"],
                )

                self.assertEqual(
                    result["error"]["code"],
                    "INVALID_LEAD_ID",
                )

    def test_rejects_missing_lead(self):
        result = build_change_lead_status_proposal(
            lead_id=999999,
            status="qualified",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_NOT_FOUND",
        )

    def test_rejects_invalid_status(self):
        invalid_statuses = (
            "",
            "archived",
            "deleted",
            None,
            123,
        )

        for invalid_status in invalid_statuses:
            with self.subTest(
                status=invalid_status,
            ):
                result = (
                    build_change_lead_status_proposal(
                        lead_id=self.lead.id,
                        status=invalid_status,
                    )
                )

                self.assertFalse(
                    result["success"],
                )

                self.assertEqual(
                    result["error"]["code"],
                    "INVALID_LEAD_STATUS",
                )

    def test_rejects_status_that_is_already_current(self):
        result = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="contacted",
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_ALREADY_IN_STATUS",
        )

        self.lead.refresh_from_db()

        self.assertEqual(
            self.lead.status,
            "contacted",
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_normalizes_status_to_lowercase(self):
        result = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="QUALIFIED",
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            result["proposal"]["arguments"]["status"],
            "qualified",
        )

    def test_proposal_ids_are_unique(self):
        first = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="qualified",
        )

        second = build_change_lead_status_proposal(
            lead_id=self.lead.id,
            status="qualified",
        )

        self.assertTrue(
            first["success"],
        )

        self.assertTrue(
            second["success"],
        )

        self.assertNotEqual(
            first["proposal"]["proposal_id"],
            second["proposal"]["proposal_id"],
        )

class CRMNaturalLanguageTaskCompletionTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

        self.task = LeadTask.objects.create(
            lead=self.lead,
            title="Send pricing proposal",
            task_type="follow_up",
            priority="high",
            status="pending",
        )

    def test_natural_language_builds_completion_proposal(self):
        result = build_write_proposal_from_message(
            f"Complete task {self.task.id}."
        )

        self.assertTrue(
            result["success"],
        )

        proposal = result["proposal"]

        self.assertEqual(
            proposal["action"],
            "complete_lead_task",
        )

        self.assertEqual(
            proposal["task"]["id"],
            self.task.id,
        )

        self.assertTrue(
            proposal["requires_confirmation"],
        )

        self.assertEqual(
            proposal["status"],
            "awaiting_confirmation",
        )

    def test_completion_proposal_does_not_change_task(self):
        result = build_write_proposal_from_message(
            f"Complete task {self.task.id}."
        )

        self.assertTrue(
            result["success"],
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertIsNone(
            self.task.completed_at,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_assistant_returns_completion_proposal_card(self):
        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Complete task {self.task.id}."
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Proposed CRM Change",
        )

        self.assertContains(
            response,
            "Send pricing proposal",
        )

        self.assertContains(
            response,
            "Confirm Complete Task",
        )

        self.assertEqual(
            LeadTask.objects.get(
                id=self.task.id
            ).status,
            "pending",
        )

    def test_completion_requires_explicit_confirm_post(self):
        proposal_response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Complete task {self.task.id}."
                ),
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        confirm_response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            confirm_response.status_code,
            200,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "completed",
        )

        self.assertIsNotNone(
            self.task.completed_at,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        self.assertContains(
            confirm_response,
            "CRM Task Completed",
        )

    def test_complete_it_does_not_confirm_previous_proposal(self):
        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Complete task {self.task.id}."
                ),
            },
        )

        self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": "Complete it.",
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_already_completed_task_returns_safe_error(self):
        self.task.status = "completed"

        self.task.save(
            update_fields=[
                "status",
            ]
        )

        response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Complete task {self.task.id}."
                ),
            },
        )

        self.assertContains(
            response,
            "TASK_ALREADY_COMPLETED",
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

class CRMTaskCompletionAcceptanceTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
        )

        self.task = LeadTask.objects.create(
            lead=self.lead,
            title="Send pricing proposal",
            task_type="follow_up",
            priority="high",
            status="pending",
        )

    def _request_completion(self):
        return self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    f"Complete task {self.task.id}."
                ),
            },
        )

    def test_acceptance_completion_proposal_performs_no_write(
        self,
    ):
        response = self._request_completion()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Confirm Complete Task",
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertIsNone(
            self.task.completed_at,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_acceptance_confirm_completes_verified_task(
        self,
    ):
        proposal_response = (
            self._request_completion()
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "completed",
        )

        self.assertIsNotNone(
            self.task.completed_at,
        )

        self.assertContains(
            response,
            "CRM Task Completed",
        )

    def test_acceptance_completion_creates_activity_and_audit(
        self,
    ):
        proposal_response = (
            self._request_completion()
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            1,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            audit.action,
            "complete_lead_task",
        )

        self.assertEqual(
            audit.status,
            "executed",
        )

        self.assertEqual(
            audit.result_task_id,
            self.task.id,
        )

    def test_acceptance_completion_replay_is_blocked(
        self,
    ):
        proposal_response = (
            self._request_completion()
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        first = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        activity_count = (
            LeadActivity.objects.count()
        )

        second = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            second.status_code,
            200,
        )

        self.assertContains(
            second,
            "PROPOSAL_ALREADY_USED",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )   

    def test_acceptance_tampered_completion_token_is_blocked(
        self,
    ):
        proposal_response = (
            self._request_completion()
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        tampered = (
            token[:-1]
            + (
                "A"
                if token[-1] != "A"
                else "B"
            )
        )

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": tampered,
            },
        )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertIsNone(
            self.task.completed_at,
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

        self.assertContains(
            response,
            "INVALID_PROPOSAL_TOKEN",
        )   

    def test_acceptance_chat_words_cannot_confirm_completion(
        self,
    ):
        self._request_completion()

        for message in (
            "Yes.",
            "Confirm.",
            "Go ahead.",
            "Complete it.",
            "Do it.",
        ):
            self.client.post(
                reverse(
                    "ai:crm_assistant_ask",
                ),
                {
                    "message": message,
                },
            )

        self.task.refresh_from_db()

        self.assertEqual(
            self.task.status,
            "pending",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_acceptance_completed_task_cannot_be_completed_again(
        self,
    ):
        self.task.status = "completed"

        self.task.save(
            update_fields=[
                "status",
            ]
        )

        response = self._request_completion()

        self.assertContains(
            response,
            "TASK_ALREADY_COMPLETED",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_acceptance_create_task_flow_still_works(
        self,
    ):
        proposal_response = self.client.post(
            reverse(
                "ai:crm_assistant_ask",
            ),
            {
                "message": (
                    "Create a follow-up task "
                    f"for lead {self.lead.id} "
                    "to Call customer."
                ),
            },
        )

        token = proposal_response.context[
            "proposal_token"
        ]

        response = self.client.post(
            reverse(
                "ai:crm_assistant_task_confirm",
            ),
            {
                "proposal_token": token,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        created_task = (
            LeadTask.objects
            .exclude(
                id=self.task.id,
            )
            .get()
        )

        self.assertEqual(
            created_task.title,
            "Call customer",
        )

        self.assertEqual(
            created_task.status,
            "pending",
        )

class ConfirmedLeadStatusChangeExecutorTests(
    TestCase
):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="Power BI Developer",
            status="contacted",
        )

    def _build_proposal(self):
        result = (
            build_change_lead_status_proposal(
                lead_id=self.lead.id,
                status="qualified",
            )
        )

        self.assertTrue(
            result["success"],
        )

        return result["proposal"]

    def test_unconfirmed_status_change_does_not_write(
        self,
    ):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=False,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "CONFIRMATION_REQUIRED",
        )

        self.lead.refresh_from_db()

        self.assertEqual(
            self.lead.status,
            "contacted",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            0,
        )

    def test_confirmed_status_change_updates_lead(
        self,
    ):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.lead.refresh_from_db()

        self.assertEqual(
            self.lead.status,
            "qualified",
        )

        self.assertEqual(
            result["action"],
            "change_lead_status",
        )

        self.assertEqual(
            result["status"],
            "executed",
        )

        self.assertEqual(
            result["data"]["lead_id"],
            self.lead.id,
        )

        self.assertEqual(
            result["data"]["previous_status"],
            "contacted",
        )

        self.assertEqual(
            result["data"]["status"],
            "qualified",
        )

    def test_status_change_creates_activity(self):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            1,
        )

        activity = LeadActivity.objects.get()

        self.assertEqual(
            activity.lead_id,
            self.lead.id,
        )

        self.assertEqual(
            activity.activity_type,
            "status_changed",
        )

    def test_status_change_creates_executed_audit(
        self,
    ):
        proposal = self._build_proposal()

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            result["success"],
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            audit.action,
            "change_lead_status",
        )

        self.assertEqual(
            audit.status,
            "executed",
        )

        self.assertEqual(
            audit.lead_id,
            self.lead.id,
        )

        self.assertIsNone(
            audit.result_task_id,
        )

        self.assertEqual(
            str(audit.proposal_id),
            proposal["proposal_id"],
        )

    def test_status_change_proposal_cannot_execute_twice(
        self,
    ):
        proposal = self._build_proposal()

        first = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertTrue(
            first["success"],
        )

        activity_count = (
            LeadActivity.objects.count()
        )

        second = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertFalse(
            second["success"],
        )

        self.assertEqual(
            second["error"]["code"],
            "PROPOSAL_ALREADY_USED",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            activity_count,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

    def test_stale_status_proposal_is_rejected(self):
        proposal = self._build_proposal()

        #
        # Simulate another user/process changing the lead
        # after the proposal was prepared.
        #
        self.lead.status = "proposal"

        self.lead.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        result = execute_confirmed_proposal(
            proposal=proposal,
            confirmed=True,
        )

        self.assertFalse(
            result["success"],
        )

        self.assertEqual(
            result["error"]["code"],
            "LEAD_STATUS_CHANGED_SINCE_PROPOSAL",
        )

        self.lead.refresh_from_db()

        self.assertEqual(
            self.lead.status,
            "proposal",
        )

        self.assertEqual(
            LeadActivity.objects.count(),
            0,
        )

        self.assertEqual(
            AIActionAudit.objects.count(),
            1,
        )

        audit = AIActionAudit.objects.get()

        self.assertEqual(
            audit.status,
            "failed",
        )

        self.assertEqual(
            audit.error_code,
            "LEAD_STATUS_CHANGED_SINCE_PROPOSAL",
        )