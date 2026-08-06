from django.shortcuts import render

from .forms import ScanURLForm
from .services.scanner import LeadScanner


def scan(request):
    """
    Display the scan page and process a URL.
    """

    result = None
    error = None

    if request.method == "POST":

        form = ScanURLForm(request.POST)

        if form.is_valid():

            url = form.cleaned_data["url"]

            try:

                scanner = LeadScanner()

                result = scanner.scan(url)

            except Exception as exc:

                error = str(exc)

    else:

        form = ScanURLForm()

    return render(
        request,
        "scanner/scan.html",
        {
            "form": form,
            "result": result,
            "error": error,
        },
    )