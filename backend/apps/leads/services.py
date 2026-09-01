from django.db.models import Q
from django.utils import timezone

from .models import Lead, LeadActivity, LeadTask


# =========================================================
# CREATE LEAD TASK
# =========================================================

def create_lead_task(
    *,
    lead,
    title,
    description="",
    task_type="follow_up",
    priority="medium",
    status="pending",
    due_date=None,
):
    """
    Create a CRM task for a lead.

    This service is the layer that future AI agent tools
    should call instead of writing directly to LeadTask.
    """

    return LeadTask.objects.create(
        lead=lead,
        title=title,
        description=description,
        task_type=task_type,
        priority=priority,
        status=status,
        due_date=due_date,
    )


# =========================================================
# GET LEAD BY ID
# =========================================================

def get_lead_by_id(
    *,
    lead_id,
):
    """
    Return one lead by ID.

    Returns None when the lead does not exist.

    AI tools should use this CRM service instead of querying
    the Lead model directly.
    """

    return Lead.objects.filter(
        pk=lead_id,
    ).first()


# =========================================================
# CHANGE LEAD STATUS
# =========================================================

def change_lead_status(
    *,
    lead,
    status,
):
    """
    Change one CRM lead's status and record the
    transition in the lead activity timeline.

    AI tools must use this service instead of
    modifying Lead directly.
    """

    if lead.status == status:
        return lead

    previous_status = lead.status

    lead.status = status

    lead.save(
        update_fields=[
            "status",
            "updated_at",
        ],
    )

    LeadActivity.objects.create(
        lead=lead,
        activity_type="status_changed",
        description=(
            f"Lead status changed from "
            f"{previous_status} to {status}"
        ),
    )

    return lead


# =========================================================
# SEARCH LEADS
# =========================================================

def search_leads(
    *,
    query=None,
    status=None,
    country=None,
    industry=None,
):
    """
    Search CRM leads using common business fields.

    All ORM search logic stays inside the CRM service layer.
    """

    leads = Lead.objects.all()

    if query:
        query = query.strip()

        if query:
            leads = leads.filter(
                Q(company_name__icontains=query)
                | Q(job_title__icontains=query)
                | Q(industry__icontains=query)
                | Q(country__icontains=query)
                | Q(location__icontains=query)
                | Q(ai_summary__icontains=query)
            )

    if status:
        leads = leads.filter(
            status=status,
        )

    if country:
        leads = leads.filter(
            country__icontains=country.strip(),
        )

    if industry:
        leads = leads.filter(
            industry__icontains=industry.strip(),
        )

    return leads.order_by(
        "-lead_score",
        "-updated_at",
    )


# =========================================================
# GET PIPELINE SUMMARY
# =========================================================

def get_pipeline_summary():
    """
    Return a summary of the current CRM pipeline.

    All ORM aggregation logic remains inside the CRM
    service layer.
    """

    leads = Lead.objects.all()

    statuses = [
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ]

    by_status = {
        status: leads.filter(
            status=status,
        ).count()
        for status in statuses
    }

    total_leads = leads.count()

    scored_leads = leads.filter(
        lead_score__gt=0,
    )

    average_lead_score = None

    if scored_leads.exists():
        scores = list(
            scored_leads.values_list(
                "lead_score",
                flat=True,
            )
        )

        average_lead_score = (
            sum(scores) / len(scores)
        )

    return {
        "total_leads": total_leads,
        "by_status": by_status,
        "average_lead_score": average_lead_score,
    }


# =========================================================
# GET LEAD TASKS
# =========================================================

def get_lead_tasks(
    *,
    lead,
    status=None,
    priority=None,
):
    """
    Return tasks belonging to a lead.

    Optional filters:
    - status
    - priority

    Future AI agent tools should use this service
    instead of querying LeadTask directly.
    """

    tasks = LeadTask.objects.filter(
        lead=lead,
    )

    if status:
        tasks = tasks.filter(
            status=status,
        )

    if priority:
        tasks = tasks.filter(
            priority=priority,
        )

    return tasks.order_by(
        "status",
        "due_date",
        "-created_at",
    )


# =========================================================
# GET LEAD TASKS BY ID
# =========================================================

def get_lead_tasks_by_id(
    *,
    lead_id,
    status=None,
    priority=None,
):
    """
    Resolve a lead ID inside the CRM service layer and return
    that lead's tasks.

    Returns None when the lead does not exist.

    AI tools should use this service instead of resolving
    Lead records directly.
    """

    lead = Lead.objects.filter(
        pk=lead_id,
    ).first()

    if lead is None:
        return None

    return get_lead_tasks(
        lead=lead,
        status=status,
        priority=priority,
    )


# =========================================================
# GET LEAD ACTIVITIES
# =========================================================

def get_lead_activities(
    *,
    lead,
    activity_type=None,
):
    """
    Return activities belonging to a lead.

    Optional filter:
    - activity_type

    Future AI tools should use this service instead of
    querying LeadActivity directly.
    """

    activities = LeadActivity.objects.filter(
        lead=lead,
    )

    if activity_type:
        activities = activities.filter(
            activity_type=activity_type,
        )

    return activities.order_by(
        "-created_at",
    )


# =========================================================
# GET LEAD ACTIVITIES BY ID
# =========================================================

def get_lead_activities_by_id(
    *,
    lead_id,
    activity_type=None,
):
    """
    Resolve the lead inside the CRM service layer and
    return that lead's activities.

    Returns None if the lead does not exist.
    """

    lead = Lead.objects.filter(
        pk=lead_id,
    ).first()

    if lead is None:
        return None

    return get_lead_activities(
        lead=lead,
        activity_type=activity_type,
    )


# =========================================================
# COMPLETE LEAD TASK
# =========================================================

def complete_lead_task(
    *,
    task,
):
    """
    Mark a CRM task as completed.

    This service:
    - updates the task status
    - records completed_at
    - creates a CRM activity

    Future AI agent tools should call this service
    instead of modifying LeadTask directly.
    """

    if task.status == "completed":
        return task

    task.status = "completed"
    task.completed_at = timezone.now()

    task.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ],
    )

    LeadActivity.objects.create(
        lead=task.lead,
        activity_type="status_changed",
        description=(
            f"Task completed: "
            f"{task.title}"
        ),
    )

    return task


# =========================================================
# GET PENDING LEAD TASKS
# =========================================================

def get_pending_tasks(
    *,
    lead=None,
    priority=None,
):
    """
    Return pending and in-progress CRM tasks.

    Optional filters:
    - lead
    - priority

    This service is intended to become a
    read tool for the future AI CRM agent.
    """

    tasks = LeadTask.objects.filter(
        status__in=[
            "pending",
            "in_progress",
        ],
    )

    if lead is not None:
        tasks = tasks.filter(
            lead=lead,
        )

    if priority:
        tasks = tasks.filter(
            priority=priority,
        )

    return tasks.order_by(
        "due_date",
        "-created_at",
    )


# =========================================================
# GET OVERDUE TASKS
# =========================================================

def get_overdue_tasks(
    *,
    lead=None,
    priority=None,
):
    """
    Return pending or in-progress tasks whose due date
    has passed.

    Optional filters:
    - lead
    - priority

    This service is intended to become a read tool
    for the future AI CRM agent.
    """

    now = timezone.now()

    tasks = LeadTask.objects.filter(
        status__in=[
            "pending",
            "in_progress",
        ],
        due_date__isnull=False,
        due_date__lt=now,
    )

    if lead is not None:
        tasks = tasks.filter(
            lead=lead,
        )

    if priority:
        tasks = tasks.filter(
            priority=priority,
        )

    return tasks.order_by(
        "due_date",
        "-created_at",
    )


# =========================================================
# GET PRIORITY TASKS
# =========================================================

def get_priority_tasks(
    *,
    lead=None,
    limit=10,
):
    """
    Return the highest-priority actionable CRM tasks.

    Ranking:
    1. Urgent
    2. High
    3. Medium
    4. Low

    Within the same priority:
    - overdue tasks first
    - earliest due date first
    - newest tasks last
    """

    priority_order = {
        "urgent": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    tasks = LeadTask.objects.filter(
        status__in=[
            "pending",
            "in_progress",
        ],
    )

    if lead is not None:
        tasks = tasks.filter(
            lead=lead,
        )

    tasks = list(tasks)

    now = timezone.now()

    def task_sort_key(task):
        priority_rank = priority_order.get(
            task.priority,
            99,
        )

        if task.due_date is None:
            overdue_rank = 1
            due_rank = now

        else:
            overdue_rank = (
                0
                if task.due_date < now
                else 1
            )

            due_rank = task.due_date

        return (
            priority_rank,
            overdue_rank,
            due_rank,
            -task.created_at.timestamp(),
        )

    tasks.sort(
        key=task_sort_key,
    )

    return tasks[:limit]


def test_get_pipeline_summary_ignores_zero_scores(self):
    Lead.objects.create(
        company_name="Unscored Lead",
        lead_score=0,
    )

    Lead.objects.create(
        company_name="Scored Lead",
        lead_score=80,
    )

    summary = get_pipeline_summary()

    self.assertEqual(
        summary["average_lead_score"],
        80,
    )


def get_lead_task_by_id(
    *,
    task_id,
):
    """
    Return one CRM task by ID.

    AI layers should use this service rather than
    accessing LeadTask.objects directly.
    """

    try:
        return LeadTask.objects.get(
            id=task_id,
        )

    except LeadTask.DoesNotExist:
        return None

def create_lead_note(
    *,
    lead,
    description,
):
    """
    Create one note activity for a CRM lead.
    """

    return LeadActivity.objects.create(
        lead=lead,
        activity_type="note",
        description=description,
    )


def get_lead_activity_by_id(
    *,
    activity_id,
):
    """
    Retrieve one lead activity by primary key.
    """

    try:
        return LeadActivity.objects.get(
            id=activity_id,
        )

    except LeadActivity.DoesNotExist:
        return None


# =========================================================
# SCANNER -> CRM IMPORT
# =========================================================

def find_duplicate_lead(*, company_name=None, source_url=None):
    """
    Return an existing CRM Lead that likely matches, or None.

    Deterministic identity only: exact (normalized) source_url,
    then case-insensitive exact company_name. Used to block a
    duplicate import from the lead scanner.
    """

    if source_url:
        source_url = source_url.strip()
        if source_url:
            match = Lead.objects.filter(source_url=source_url).first()
            if match is not None:
                return match

    if company_name:
        company_name = company_name.strip()
        if company_name:
            return Lead.objects.filter(
                company_name__iexact=company_name,
            ).first()

    return None


def import_scanner_candidate(*, mapping, context_note=""):
    """
    Create one CRM Lead from a scanner candidate mapping and, if
    provided, attach a context note. This is the ONLY entry point
    the lead scanner uses to create a Lead - the scanner never
    calls Lead.objects.create() itself.

    ``mapping`` keys (all optional except company_name):
    company_name, job_title, source_platform, source_url, location,
    work_setup, salary, lead_score.
    """

    company_name = (mapping.get("company_name") or "").strip()
    if not company_name:
        raise ValueError("company_name is required to import a lead.")

    source_url = (mapping.get("source_url") or "").strip() or None

    lead = Lead.objects.create(
        company_name=company_name,
        job_title=(mapping.get("job_title") or "").strip(),
        source_platform=(mapping.get("source_platform") or "").strip(),
        source_url=source_url,
        location=(mapping.get("location") or "").strip(),
        work_setup=(mapping.get("work_setup") or "").strip(),
        salary=(mapping.get("salary") or "").strip(),
        lead_score=int(mapping.get("lead_score") or 0),
        status="new",
    )

    if context_note:
        LeadActivity.objects.create(
            lead=lead,
            activity_type="note",
            description=context_note,
        )

    return lead