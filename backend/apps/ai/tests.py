from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.leads.models import Lead, LeadTask
from apps.ai.tools.crm.tasks import (
    get_overdue_tasks_tool,
    get_pending_tasks_tool,
    get_priority_tasks_tool,
)


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

        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 1)

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

        self.assertTrue(result["success"])
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

        self.assertTrue(result["success"])
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

        self.assertTrue(result["success"])
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

        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 1)

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

        self.assertTrue(result["success"])

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

        self.assertTrue(result["success"])
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

        self.assertTrue(result["success"])
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

        self.assertTrue(result["success"])
        self.assertEqual(
            len(result["data"]),
            2,
        )

    def test_tool_rejects_invalid_priority(self):
        result = get_pending_tasks_tool(
            priority="super_important",
        )

        self.assertFalse(result["success"])

        self.assertEqual(
            result["error"]["code"],
            "INVALID_PRIORITY",
        )

    def test_tool_rejects_invalid_limit(self):
        result = get_pending_tasks_tool(
            limit=0,
        )

        self.assertFalse(result["success"])

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

        self.assertTrue(result["success"])

        mock_get_pending_tasks.assert_called_once_with(
            priority="high",
        )