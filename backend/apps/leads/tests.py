from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Lead, LeadActivity, LeadTask
from .services import (
    create_lead_task,
    get_lead_tasks,
    get_pending_tasks,
    get_overdue_tasks,
    get_priority_tasks,
    complete_lead_task,
)


class LeadTaskServiceTests(TestCase):

    def setUp(self):

        self.lead = Lead.objects.create(
            company_name="Test Company",
            job_title="Data Analyst",
        )

    def test_create_lead_task(self):

        task = create_lead_task(
            lead=self.lead,
            title="Test follow up",
            task_type="follow_up",
            priority="high",
        )

        self.assertEqual(
            LeadTask.objects.count(),
            1,
        )

        self.assertEqual(
            task.title,
            "Test follow up",
        )

        self.assertEqual(
            task.status,
            "pending",
        )

    def test_get_lead_tasks(self):

        create_lead_task(
            lead=self.lead,
            title="Task A",
        )

        create_lead_task(
            lead=self.lead,
            title="Task B",
            priority="high",
        )

        tasks = get_lead_tasks(
            lead=self.lead,
        )

        self.assertEqual(
            tasks.count(),
            2,
        )

    def test_get_pending_tasks(self):

        create_lead_task(
            lead=self.lead,
            title="Pending Task",
            status="pending",
        )

        create_lead_task(
            lead=self.lead,
            title="Completed Task",
            status="completed",
        )

        tasks = get_pending_tasks(
            lead=self.lead,
        )

        self.assertEqual(
            tasks.count(),
            1,
        )

        self.assertEqual(
            tasks.first().title,
            "Pending Task",
        )

    def test_get_overdue_tasks(self):

        create_lead_task(
            lead=self.lead,
            title="Overdue Task",
            status="pending",
            due_date=(
                timezone.now()
                - timedelta(days=1)
            ),
        )

        create_lead_task(
            lead=self.lead,
            title="Future Task",
            status="pending",
            due_date=(
                timezone.now()
                + timedelta(days=1)
            ),
        )

        tasks = get_overdue_tasks(
            lead=self.lead,
        )

        self.assertEqual(
            tasks.count(),
            1,
        )

        self.assertEqual(
            tasks.first().title,
            "Overdue Task",
        )

    def test_get_priority_tasks(self):

        create_lead_task(
            lead=self.lead,
            title="Low Task",
            priority="low",
        )

        create_lead_task(
            lead=self.lead,
            title="Urgent Task",
            priority="urgent",
        )

        tasks = get_priority_tasks(
            lead=self.lead,
        )

        self.assertEqual(
            len(tasks),
            2,
        )

        self.assertEqual(
            tasks[0].title,
            "Urgent Task",
        )

    def test_complete_lead_task(self):

        task = create_lead_task(
            lead=self.lead,
            title="Complete Me",
        )

        completed_task = complete_lead_task(
            task=task,
        )

        self.assertEqual(
            completed_task.status,
            "completed",
        )

        self.assertIsNotNone(
            completed_task.completed_at,
        )

        self.assertTrue(
            LeadActivity.objects.filter(
                lead=self.lead,
                description=(
                    "Task completed: Complete Me"
                ),
            ).exists()
        )