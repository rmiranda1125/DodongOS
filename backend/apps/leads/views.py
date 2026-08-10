from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .forms import LeadNoteForm
from .models import Lead


def lead_list(request):
    search = request.GET.get("search", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "newest")
    page_number = request.GET.get("page", 1)

    leads = Lead.objects.all()

    if search:
        leads = leads.filter(
            Q(company_name__icontains=search)
            | Q(job_title__icontains=search)
            | Q(industry__icontains=search)
            | Q(country__icontains=search)
        )

    if status:
        leads = leads.filter(status=status)

    if sort == "score":
        leads = leads.order_by("-lead_score", "-created_at")
    else:
        leads = leads.order_by("-created_at")

    paginator = Paginator(leads, 10)
    page_obj = paginator.get_page(page_number)

    context = {
        "leads": page_obj.object_list,
        "page_obj": page_obj,
        "search": search,
        "status": status,
        "sort": sort,
        "status_choices": Lead.STATUS_CHOICES,
    }

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
    lead = get_object_or_404(Lead, pk=pk)

    if request.method == "POST":
        new_status = request.POST.get("status")

        valid_statuses = dict(Lead.STATUS_CHOICES)

        if new_status in valid_statuses:
            lead.status = new_status
            lead.save(update_fields=["status", "updated_at"])

    return render(
        request,
        "leads/partials/status.html",
        {
            "lead": lead,
        },
    )


def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    return render(
        request,
        "leads/detail.html",
        {
            "lead": lead,
        },
    )

def lead_add_note(request, pk):

    lead = get_object_or_404(Lead, pk=pk)

    if request.method == "POST":

        form = LeadNoteForm(request.POST)

        if form.is_valid():

            note = form.save(commit=False)

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