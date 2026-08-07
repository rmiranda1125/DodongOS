from django.shortcuts import get_object_or_404, render

from .models import Lead


def lead_list(request):
    leads = Lead.objects.all().order_by("-created_at")
    return render(
        request,
        "leads/list.html",
        {
            "leads": leads,
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