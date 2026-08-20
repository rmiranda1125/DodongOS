from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Lead, LeadActivity, LeadTask
from .services import (
    complete_lead_task,
    create_lead_task,
    get_lead_by_id,
    get_lead_tasks,
    get_lead_tasks_by_id,
    get_lead_activities,
    get_lead_activities_by_id,
    get_overdue_tasks,
    get_pending_tasks,
    get_pipeline_summary,
    get_priority_tasks,
    search_leads,
)


class LeadTaskServiceTests(TestCase):

    def setUp(self):
        self.lead = Lead.objects.create(
            company_name="Test Company",
            job_title="Data Analyst",
        )

    # =====================================================
    # CREATE LEAD TASK
    # =====================================================

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

    # =====================================================
    # GET LEAD TASKS
    # =====================================================

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

    # =====================================================
    # GET LEAD TASKS BY ID
    # =====================================================

    def test_get_lead_tasks_by_id(self):
        create_lead_task(
            lead=self.lead,
            title="Lead ID Task",
        )

        tasks = get_lead_tasks_by_id(
            lead_id=self.lead.id,
        )

        self.assertIsNotNone(
            tasks,
        )

        self.assertEqual(
            tasks.count(),
            1,
        )

        self.assertEqual(
            tasks.first().title,
            "Lead ID Task",
        )

    def test_get_lead_tasks_by_id_returns_none_for_missing_lead(self):
        tasks = get_lead_tasks_by_id(
            lead_id=999999,
        )

        self.assertIsNone(
            tasks,
        )

    # =====================================================
    # GET LEAD BY ID
    # =====================================================

    def test_get_lead_by_id(self):
        lead = get_lead_by_id(
            lead_id=self.lead.id,
        )

        self.assertIsNotNone(
            lead,
        )

        self.assertEqual(
            lead.id,
            self.lead.id,
        )

    def test_get_lead_by_id_returns_none_for_missing_lead(self):
        lead = get_lead_by_id(
            lead_id=999999,
        )

        self.assertIsNone(
            lead,
        )

    # =====================================================
    # GET PENDING TASKS
    # =====================================================

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

    # =====================================================
    # GET OVERDUE TASKS
    # =====================================================

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

    # =====================================================
    # GET PRIORITY TASKS
    # =====================================================

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

    # =====================================================
    # COMPLETE LEAD TASK
    # =====================================================

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

    # =====================================================
    # SEARCH LEADS
    # =====================================================

    def test_search_leads_by_company_name(self):
        matching_lead = Lead.objects.create(
            company_name="Acme Analytics",
            job_title="BI Developer",
        )

        Lead.objects.create(
            company_name="Other Company",
            job_title="Accountant",
        )

        leads = search_leads(
            query="Acme",
        )

        self.assertEqual(
            list(leads),
            [matching_lead],
        )

    def test_search_leads_by_job_title(self):
        matching_lead = Lead.objects.create(
            company_name="Data Company",
            job_title="Power BI Developer",
        )

        Lead.objects.create(
            company_name="Sales Company",
            job_title="Sales Manager",
        )

        leads = search_leads(
            query="Power BI",
        )

        self.assertEqual(
            list(leads),
            [matching_lead],
        )

    def test_search_leads_filters_by_status(self):
        qualified_lead = Lead.objects.create(
            company_name="Qualified Company",
            status="qualified",
        )

        Lead.objects.create(
            company_name="New Company",
            status="new",
        )

        leads = search_leads(
            status="qualified",
        )

        self.assertEqual(
            list(leads),
            [qualified_lead],
        )

    def test_search_leads_filters_by_country(self):
        ph_lead = Lead.objects.create(
            company_name="Philippines Company",
            country="Philippines",
        )

        Lead.objects.create(
            company_name="US Company",
            country="United States",
        )

        leads = search_leads(
            country="Philippines",
        )

        self.assertEqual(
            list(leads),
            [ph_lead],
        )

    def test_search_leads_can_combine_filters(self):
        matching_lead = Lead.objects.create(
            company_name="Analytics PH",
            job_title="BI Developer",
            country="Philippines",
            status="qualified",
        )

        Lead.objects.create(
            company_name="Analytics US",
            job_title="BI Developer",
            country="United States",
            status="qualified",
        )

        leads = search_leads(
            query="BI Developer",
            country="Philippines",
            status="qualified",
        )

        self.assertEqual(
            list(leads),
            [matching_lead],
        )

    # =====================================================
    # GET LEAD ACTIVITIES
    # =====================================================

    def test_get_lead_activities_by_id(self):
        activity = LeadActivity.objects.create(
            lead=self.lead,
            activity_type="call",
            description="Called the client.",
        )

        activities = get_lead_activities_by_id(
            lead_id=self.lead.id,
        )

        self.assertIsNotNone(
            activities,
        )

        self.assertEqual(
            activities.count(),
            1,
        )

        self.assertEqual(
            activities.first().id,
            activity.id,
        )

    def test_get_lead_activities_by_id_filters_activity_type(self):
        LeadActivity.objects.create(
            lead=self.lead,
            activity_type="call",
            description="Called client.",
        )

        email_activity = LeadActivity.objects.create(
            lead=self.lead,
            activity_type="email",
            description="Sent email.",
        )

        activities = get_lead_activities_by_id(
            lead_id=self.lead.id,
            activity_type="email",
        )

        self.assertEqual(
            activities.count(),
            1,
        )

        self.assertEqual(
            activities.first().id,
            email_activity.id,
        )

    def test_get_lead_activities_by_id_returns_none_for_missing_lead(self):
        activities = get_lead_activities_by_id(
            lead_id=999999,
        )

        self.assertIsNone(
            activities,
        )

    # =====================================================
    # GET PIPELINE SUMMARY
    # =====================================================

    def test_get_pipeline_summary_counts_statuses(self):
        Lead.objects.create(
            company_name="New Lead",
            status="new",
        )

        Lead.objects.create(
            company_name="Qualified Lead 1",
            status="qualified",
        )

        Lead.objects.create(
            company_name="Qualified Lead 2",
            status="qualified",
        )

        summary = get_pipeline_summary()

        self.assertEqual(
            summary["total_leads"],
            4,
        )

        self.assertEqual(
            summary["by_status"]["new"],
            2,
        )

        self.assertEqual(
            summary["by_status"]["qualified"],
            2,
        )

    def test_get_pipeline_summary_includes_zero_statuses(self):
        Lead.objects.create(
            company_name="Only Lead",
            status="new",
        )

        summary = get_pipeline_summary()

        self.assertEqual(
            summary["by_status"]["proposal"],
            0,
        )

        self.assertEqual(
            summary["by_status"]["won"],
            0,
        )

    def test_get_pipeline_summary_average_score(self):
        Lead.objects.create(
            company_name="Lead A",
            lead_score=80,
        )

        Lead.objects.create(
            company_name="Lead B",
            lead_score=100,
        )

        summary = get_pipeline_summary()

        self.assertEqual(
            summary["average_lead_score"],
            90,
        )

    def test_get_pipeline_summary_no_scores(self):
        Lead.objects.create(
            company_name="Lead Without Score",
        )

        summary = get_pipeline_summary()

        self.assertIsNone(
            summary["average_lead_score"],
        )