from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Lead


def lead_list(request):
    search = request.GET.get("search", "")
    status = request.GET.get("status", "")
    sort = request.GET.get("sort", "newest")

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

    context = {
        "leads": leads,
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


def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    return render(
        request,
        "leads/detail.html",
        {
            "lead": lead,
        },
    )