from django.shortcuts import render
from .importer import CompanyImporter

def index(request):

    return render(
        request,
        "leadfinder/index.html",
    )


def import_company(request):

    if request.method == "POST":

        website = request.POST.get("website")

        importer = CompanyImporter()

        company = importer.import_company(
            website
        )

        return render(
            request,
            "leadfinder/partials/import_result.html",
            {
                "company": company,
            },
        )

    return render(
        request,
        "leadfinder/import.html",
    )