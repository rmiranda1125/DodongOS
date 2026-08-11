from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from .forms import LeadNoteForm
from .models import Lead
from django.views.decorators.http import require_POST


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
    # Show 25 leads per page
    paginator = Paginator(
        leads,
        25,
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
        "status_choices": Lead.STATUS_CHOICES,
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


def lead_detail(request, pk):

    lead = get_object_or_404(
        Lead,
        pk=pk,
    )

    return render(
        request,
        "leads/detail.html",
        {
            "lead": lead,
        },
    )


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


def lead_dashboard(request):

    # Total leads
    total_leads = Lead.objects.count()

    # Leads by status
    new_leads = Lead.objects.filter(
        status="new"
    ).count()

    qualified_leads = Lead.objects.filter(
        status="qualified"
    ).count()

    contacted_leads = Lead.objects.filter(
        status="contacted"
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

        "qualified_leads": qualified_leads,

        "contacted_leads": contacted_leads,

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

def update_lead_status(request, pk):

    if request.method != "POST":
        return HttpResponse(status=405)

    lead = get_object_or_404(Lead, pk=pk)

    status = request.POST.get("status")

    valid_statuses = {
        choice[0]
        for choice in Lead.STATUS_CHOICES
    }

    if status not in valid_statuses:
        return HttpResponse(
            "Invalid status",
            status=400,
        )

    lead.status = status
    lead.save(update_fields=["status", "updated_at"])

    return render(
        request,
        "leads/partials/status.html",
        {
            "lead": lead,
        },
    )

def bulk_update_status(request):

    if request.method != "POST":
        return HttpResponse(status=405)

    lead_ids = request.POST.getlist("lead_ids")
    status = request.POST.get("status")

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

    return render(
        request,
        "leads/partials/table.html",
        {
            "leads": Lead.objects.all().order_by("-created_at"),
            "search": "",
        },
    )

@require_POST
def update_lead_status(request, pk):

    lead = get_object_or_404(Lead, pk=pk)

    status = request.POST.get("status")

    valid_statuses = dict(Lead.STATUS_CHOICES)

    if status in valid_statuses:
        lead.status = status
        lead.save(update_fields=["status", "updated_at"])

    return render(
        request,
        "leads/partials/status.html",
        {
            "lead": lead,
        },
    )

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