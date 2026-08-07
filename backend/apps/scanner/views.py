from django.shortcuts import redirect, render

from .forms import ScanURLForm
from .services.scanner import LeadScanner


def scan(request):
    """
    Display the scanner page and process a URL.
    """

    error = None

    if request.method == "POST":

        form = ScanURLForm(request.POST)

        if form.is_valid():

            url = form.cleaned_data["url"]

            try:

                scanner = LeadScanner()

                lead = scanner.scan(url)

                # Redirect to the newly created Lead
                return redirect(
                    "leads:detail",
                    pk=lead.pk,
                )

            except Exception as exc:

                error = str(exc)

    else:

        form = ScanURLForm()

    return render(
        request,
        "scanner/scan.html",
        {
            "form": form,
            "error": error,
        },
    )