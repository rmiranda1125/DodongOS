from django.shortcuts import render, redirect, get_object_or_404

from .models import Company
from .forms import CompanyForm

from apps.ai.schemas import CompanyAnalysisRequest
from apps.ai.services import AIService


def company_list(request):

    companies = Company.objects.all()

    form = CompanyForm()

    return render(
        request,
        "companies/list.html",
        {
            "companies": companies,
            "form": form,
        },
    )


def company_create(request):

    if request.method == "POST":

        form = CompanyForm(request.POST)

        if form.is_valid():

            form.save()

            companies = Company.objects.all()

            if request.htmx:
                return render(
                    request,
                    "companies/partials/company_table.html",
                    {
                        "companies": companies,
                    },
                )

            return redirect("companies:list")

    else:

        form = CompanyForm()

    return render(
        request,
        "companies/form.html",
        {
            "form": form,
        },
    )


def company_update(request, pk):

    company = get_object_or_404(
        Company,
        pk=pk
    )

    if request.method == "POST":

        form = CompanyForm(
            request.POST,
            instance=company
        )

        if form.is_valid():

            form.save()

            companies = Company.objects.all()

            if request.htmx:
                return render(
                    request,
                    "companies/partials/company_table.html",
                    {
                        "companies": companies,
                    },
                )

            return redirect("companies:list")

    else:

        form = CompanyForm(
            instance=company
        )

    return render(
        request,
        "companies/form.html",
        {
            "form": form,
        },
    )


def company_delete(request, pk):

    company = get_object_or_404(
        Company,
        pk=pk
    )

    if request.method == "POST":

        company.delete()

        companies = Company.objects.all()

        if request.htmx:
            return render(
                request,
                "companies/partials/company_table.html",
                {
                    "companies": companies,
                },
            )

        return redirect("companies:list")

    return render(
        request,
        "companies/delete.html",
        {
            "company": company,
        },
    )

from apps.ai.services import AIService


def company_analyze(request, pk):

    company = get_object_or_404(
        Company,
        pk=pk,
    )

    ai_service = AIService()

    analysis_result = ai_service.analyze_company(
        company
    )

    if request.htmx:
        return render(
            request,
            "companies/partials/analysis.html",
            {
                "company": company,
                "analysis_result": analysis_result,
            },
        )

    return render(
        request,
        "companies/analyze.html",
        {
            "company": company,
            "analysis_result": analysis_result,
        },
    )