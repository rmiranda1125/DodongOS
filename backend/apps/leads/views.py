from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from .forms import (
    LeadActivityForm,
    LeadForm,
    LeadNoteForm,
    LeadTaskForm,
)

from .models import (
    Lead,
    LeadActivity,
    LeadTask,
)

from .models import (
    Lead,
    LeadActivity,
    LeadTask,
)

from .services import (
    create_lead_task,
    complete_lead_task,
)

# =========================================================
# LEAD LIST
# =========================================================

def lead_list(request):

    search = request.GET.get("search", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "newest")

    leads = Lead.objects.all()

    # Search
    if search:

        leads = leads.filter(
            Q(company_name__icontains=search)
            | Q(job_title__icontains=search)
            | Q(industry__icontains=search)
            | Q(country__icontains=search)
        )

    # Status filter
    if status:

        leads = leads.filter(
            status=status
        )

    # Sorting
    if sort == "score":

        leads = leads.order_by(
            "-lead_score",
            "-created_at",
        )

    else:

        leads = leads.order_by(
            "-created_at"
        )

    # Pagination
    paginator = Paginator(
        leads,
        20,
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    context = {
        "leads": page_obj,
        "page_obj": page_obj,
        "search": search,
        "status": status,
        "sort": sort,
    }

    # HTMX table refresh
    if request.htmx:

        return render(
            request,
            "leads/partials/table.html",
            context,
        )

    return render(
        request,
        "leads/list.html",
        context,
    )


# =========================================================
# LEAD STATUS UPDATE
# =========================================================

def lead_status_update(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        new_status = request.POST.get(
            "status"
        )

        valid_statuses = dict(
            Lead.STATUS_CHOICES
        )

        if new_status in valid_statuses:

            lead.status = new_status

            lead.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

    return render(
        request,
        "leads/partials/status.html",
        {
            "lead": lead,
        },
    )


# =========================================================
# LEAD DETAIL
# =========================================================

def lead_detail(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    activities = LeadActivity.objects.filter(
        lead=lead
    ).order_by(
        "-created_at"
    )

    tasks = LeadTask.objects.filter(
        lead=lead
    ).order_by(
        "status",
        "due_date",
        "-created_at",
    )

    return render(
        request,
        "leads/detail.html",
        {
            "lead": lead,
            "activities": activities,
            "tasks": tasks,
        },
    )


# =========================================================
# ADD NOTE
# =========================================================

def lead_add_note(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        form = LeadNoteForm(
            request.POST
        )

        if form.is_valid():

            note = form.save(
                commit=False
            )

            note.lead = lead

            note.save()

            return render(
                request,
                "leads/partials/notes.html",
                {
                    "lead": lead,
                    "note_form": LeadNoteForm(),
                },
            )

    else:

        form = LeadNoteForm()

    return render(
        request,
        "leads/partials/note_form.html",
        {
            "lead": lead,
            "note_form": form,
        },
    )


# =========================================================
# LEAD DASHBOARD
# =========================================================

def lead_dashboard(request):

    # Total leads
    total_leads = Lead.objects.count()

    # Leads by status
    new_leads = Lead.objects.filter(
        status="new"
    ).count()

    contacted_leads = Lead.objects.filter(
        status="contacted"
    ).count()

    qualified_leads = Lead.objects.filter(
        status="qualified"
    ).count()

    proposal_leads = Lead.objects.filter(
        status="proposal"
    ).count()

    won_leads = Lead.objects.filter(
        status="won"
    ).count()

    lost_leads = Lead.objects.filter(
        status="lost"
    ).count()

    # Average AI lead score
    average_score = Lead.objects.aggregate(
        average=Avg("lead_score")
    )["average"]

    # Conversion metrics
    qualification_rate = (
        qualified_leads / total_leads * 100
        if total_leads
        else 0
    )

    contact_rate = (
        contacted_leads / total_leads * 100
        if total_leads
        else 0
    )

    proposal_rate = (
        proposal_leads / total_leads * 100
        if total_leads
        else 0
    )

    win_rate = (
        won_leads / total_leads * 100
        if total_leads
        else 0
    )

    # Recent leads
    recent_leads = Lead.objects.order_by(
        "-created_at"
    )[:5]

    context = {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "contacted_leads": contacted_leads,
        "qualified_leads": qualified_leads,
        "proposal_leads": proposal_leads,
        "won_leads": won_leads,
        "lost_leads": lost_leads,
        "average_score": average_score,
        "qualification_rate": qualification_rate,
        "contact_rate": contact_rate,
        "proposal_rate": proposal_rate,
        "win_rate": win_rate,
        "recent_leads": recent_leads,
    }

    return render(
        request,
        "leads/dashboard.html",
        context,
    )


# =========================================================
# UPDATE LEAD STATUS
# =========================================================

@require_POST
def update_lead_status(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    new_status = request.POST.get("status")

    valid_statuses = dict(
        Lead.STATUS_CHOICES
    )

    if new_status not in valid_statuses:

        return HttpResponseBadRequest(
            "Invalid status."
        )

    old_status = lead.status

    # Don't create an activity if nothing changed
    if old_status == new_status:

        return render(
            request,
            "leads/partials/status.html",
            {
                "lead": lead,
            },
        )

    # Update lead
    lead.status = new_status

    lead.save(
        update_fields=["status"]
    )

    # Create activity automatically
    LeadActivity.objects.create(
        lead=lead,
        activity_type="status_changed",
        description=(
            f"Status changed from "
            f"{old_status.replace('_', ' ').title()} "
            f"to "
            f"{new_status.replace('_', ' ').title()}."
        ),
    )

    return render(
        request,
        "leads/partials/status.html",
        {
            "lead": lead,
        },
    )


# =========================================================
# BULK UPDATE STATUS
# =========================================================

@require_POST
def bulk_update_status(request):

    lead_ids = request.POST.getlist(
        "lead_ids"
    )

    status = request.POST.get(
        "status"
    )

    valid_statuses = {
        choice[0]
        for choice in Lead.STATUS_CHOICES
    }

    if status not in valid_statuses:

        return HttpResponse(
            "Invalid status",
            status=400,
        )

    Lead.objects.filter(
        id__in=lead_ids
    ).update(
        status=status
    )

    leads = Lead.objects.all().order_by(
        "-created_at"
    )

    paginator = Paginator(
        leads,
        20,
    )

    page_obj = paginator.get_page(
        1
    )

    return render(
        request,
        "leads/partials/table.html",
        {
            "leads": page_obj,
            "page_obj": page_obj,
            "search": "",
            "status": "",
            "sort": "newest",
        },
    )


# =========================================================
# EDIT STATUS
# =========================================================

def edit_lead_status(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    return render(
        request,
        "leads/partials/status_edit.html",
        {
            "lead": lead,
        },
    )


# =========================================================
# EDIT LEAD
# =========================================================

def lead_edit(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        form = LeadForm(
            request.POST,
            instance=lead,
        )

        if form.is_valid():

            form.save()

            if request.htmx:

                return render(
                    request,
                    "leads/partials/edit_success.html",
                    {
                        "lead": lead,
                    },
                )

            return redirect(
                "leads:detail",
                pk=lead.pk,
            )

    else:

        form = LeadForm(
            instance=lead,
        )

    return render(
        request,
        "leads/partials/edit_form.html",
        {
            "lead": lead,
            "form": form,
        },
    )


# =========================================================
# ADD ACTIVITY
# =========================================================

def add_activity(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        form = LeadActivityForm(
            request.POST,
        )

        if form.is_valid():

            activity = form.save(
                commit=False
            )

            activity.lead = lead

            activity.save()

            if request.htmx:

                return render(
                    request,
                    "leads/partials/activity_success.html",
                    {
                        "lead": lead,
                    },
                )

            return redirect(
                "leads:detail",
                pk=lead.pk,
            )

    else:

        form = LeadActivityForm()

    return render(
        request,
        "leads/partials/activity_form.html",
        {
            "lead": lead,
            "form": form,
        },
    )


# =========================================================
# DELETE ACTIVITY
# =========================================================

def delete_activity(request, pk):

    activity = get_object_or_404(
        LeadActivity,
        pk=pk,
    )

    lead = activity.lead

    if request.method == "POST":

        activity.delete()

        return redirect(
            "leads:detail",
            pk=lead.pk,
        )

    return render(
        request,
        "leads/partials/activity_delete.html",
        {
            "activity": activity,
            "lead": lead,
        },
    )


# =========================================================
# DETAIL PAGE STATUS
# =========================================================

def update_status(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    # Show status dropdown
    if request.method == "GET":

        return render(
            request,
            "leads/partials/status_edit.html",
            {
                "lead": lead,
            },
        )

    # Save status
    if request.method == "POST":

        status = request.POST.get(
            "status"
        )

        valid_statuses = dict(
            Lead.STATUS_CHOICES
        )

        if status in valid_statuses:

            lead.status = status

            lead.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return render(
            request,
            "leads/partials/status.html",
            {
                "lead": lead,
            },
        )

    return HttpResponse(
        status=405
    )


# =========================================================
# LEAD PIPELINE
# =========================================================

def lead_pipeline(request):

    # Get all leads sorted by score
    leads = Lead.objects.all().order_by(
        "-lead_score",
        "-created_at",
    )

    # Pipeline containers
    pipeline = {
        "new": [],
        "contacted": [],
        "qualified": [],
        "proposal": [],
        "won": [],
        "lost": [],
    }

    # Organize leads by status
    for lead in leads:

        if lead.status in pipeline:

            pipeline[lead.status].append(
                lead
            )

    # =====================================================
    # PIPELINE METRICS
    # =====================================================

    total_leads = leads.count()

    # Won leads
    won_count = len(
        pipeline["won"]
    )

    # Hot leads: score 80+
    hot_count = leads.filter(
        lead_score__gte=80
    ).count()

    # Warm leads: score 60-79
    warm_count = leads.filter(
        lead_score__gte=60,
        lead_score__lt=80,
    ).count()

    # Cold leads: score below 60
    cold_count = leads.filter(
        lead_score__lt=60
    ).count()

    # Conversion rate
    conversion_rate = 0

    if total_leads:

        conversion_rate = round(
            (won_count / total_leads) * 100,
            1,
        )

    # =====================================================
    # PIPELINE CONTEXT
    # =====================================================

    context = {
        "pipeline": pipeline,
        "total_leads": total_leads,
        "conversion_rate": conversion_rate,
        "hot_count": hot_count,
        "warm_count": warm_count,
        "cold_count": cold_count,
    }

    return render(
        request,
        "leads/pipeline.html",
        context,
    )


# =========================================================
# UPDATE PIPELINE STATUS
# =========================================================

@require_POST
def update_pipeline_status(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    new_status = request.POST.get("status")

    valid_statuses = dict(
        Lead.STATUS_CHOICES
    )

    if new_status not in valid_statuses:
        return HttpResponseBadRequest(
            "Invalid status."
        )

    old_status = lead.status

    # Nothing changed
    if old_status == new_status:

        return render(
            request,
            "leads/partials/pipeline_card.html",
            {
                "lead": lead,
            },
        )

    # Update lead status
    lead.status = new_status

    lead.save(
        update_fields=["status"]
    )

    # Automatically create activity
    LeadActivity.objects.create(
        lead=lead,
        activity_type="status_changed",
        description=(
            f"Status changed from "
            f"{old_status.replace('_', ' ').title()} "
            f"to "
            f"{new_status.replace('_', ' ').title()}."
        ),
    )

    return render(
        request,
        "leads/partials/pipeline_card.html",
        {
            "lead": lead,
        },
    )

# =========================================================
# ADD ACTIVITY
# =========================================================

def add_activity(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        form = LeadActivityForm(
            request.POST,
        )

        if form.is_valid():

            activity = form.save(
                commit=False
            )

            activity.lead = lead

            activity.save()

            activities = LeadActivity.objects.filter(
                lead=lead
            ).order_by(
                "-created_at"
            )

            return render(
                request,
                "leads/partials/activity_timeline.html",
                {
                    "lead": lead,
                    "activities": activities,
                },
            )

    else:

        form = LeadActivityForm()

    return render(
        request,
        "leads/partials/activity_form.html",
        {
            "lead": lead,
            "form": form,
            "activity_types": LeadActivity.ACTIVITY_TYPES,
        },
    )

# =========================================================
# DELETE ACTIVITY
# =========================================================

@require_POST
def delete_activity(request, pk, activity_pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    activity = get_object_or_404(
        LeadActivity,
        pk=activity_pk,
        lead=lead,
    )

    activity.delete()

    activities = LeadActivity.objects.filter(
        lead=lead
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "leads/partials/activity_timeline.html",
        {
            "lead": lead,
            "activities": activities,
        },
    )

# =========================================================
# EDIT ACTIVITY
# =========================================================

def edit_activity(request, pk, activity_pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    activity = get_object_or_404(
        LeadActivity,
        pk=activity_pk,
        lead=lead,
    )

    # =====================================================
    # POST - SAVE CHANGES
    # =====================================================

    if request.method == "POST":

        activity_type = request.POST.get(
            "activity_type"
        )

        description = request.POST.get(
            "description",
            "",
        ).strip()

        # Validate activity type
        valid_activity_types = dict(
            LeadActivity.ACTIVITY_TYPES
        )

        if activity_type not in valid_activity_types:

            return HttpResponseBadRequest(
                "Invalid activity type."
            )

        # Update activity
        activity.activity_type = activity_type
        activity.description = description

        activity.save(
            update_fields=[
                "activity_type",
                "description",
            ]
        )

        # Reload activities
        activities = LeadActivity.objects.filter(
            lead=lead
        ).order_by(
            "-created_at"
        )

        # Return updated timeline
        return render(
            request,
            "leads/partials/activity_timeline.html",
            {
                "lead": lead,
                "activities": activities,
            },
        )

    # =====================================================
    # GET - SHOW EDIT FORM
    # =====================================================

    return render(
        request,
        "leads/partials/activity_edit.html",
        {
            "lead": lead,
            "activity": activity,
            "activity_types": LeadActivity.ACTIVITY_TYPES,
        },
    )

# =========================================================
# CREATE LEAD TASK
# =========================================================

def lead_task_create(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    if request.method == "POST":

        form = LeadTaskForm(
            request.POST,
        )

        if form.is_valid():

            create_lead_task(
                lead=lead,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                task_type=form.cleaned_data["task_type"],
                priority=form.cleaned_data["priority"],
                status=form.cleaned_data["status"],
                due_date=form.cleaned_data["due_date"],
            )

            return redirect(
                "leads:detail",
                pk=lead.pk,
            )

    else:

        form = LeadTaskForm()

    return render(
        request,
        "leads/task_form.html",
        {
            "lead": lead,
            "form": form,
        },
    )

# =========================================================
# UPDATE LEAD TASK STATUS
# =========================================================

@require_POST
def lead_task_update_status(request, pk, task_pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    task = get_object_or_404(
        LeadTask,
        pk=task_pk,
        lead=lead,
    )

    new_status = request.POST.get(
        "status"
    )

    valid_statuses = dict(
        LeadTask.STATUS_CHOICES
    )

    if new_status not in valid_statuses:

        return HttpResponseBadRequest(
            "Invalid task status."
        )

    old_status = task.status

    # =====================================================
    # NO CHANGE
    # =====================================================

    if old_status == new_status:

        return render(
            request,
            "leads/partials/task_status.html",
            {
                "lead": lead,
                "task": task,
            },
        )

    # =====================================================
    # COMPLETE TASK THROUGH SERVICE
    # =====================================================

    if new_status == "completed":

        complete_lead_task(
            task=task,
        )

    # =====================================================
    # OTHER STATUS CHANGES
    # =====================================================

    else:

        task.status = new_status

        task.completed_at = None

        task.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ],
        )

    # =====================================================
    # RETURN UPDATED STATUS
    # =====================================================

    return render(
        request,
        "leads/partials/task_status.html",
        {
            "lead": lead,
            "task": task,
        },
    )

    # =====================================================
    # CREATE ACTIVITY WHEN TASK IS COMPLETED
    # =====================================================

    if (
        new_status == "completed"
        and old_status != "completed"
    ):

        LeadActivity.objects.create(
            lead=lead,
            activity_type="status_changed",
            description=(
                f"Task completed: "
                f"{task.title}"
            ),
        )

    return render(
        request,
        "leads/partials/task_status.html",
        {
            "lead": lead,
            "task": task,
        },
    )