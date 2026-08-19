from datetime import timedelta

from django.utils import timezone

from .models import Lead, LeadTask, LeadActivity

from django.db.models import Q


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