from django.shortcuts import render
from django.utils import timezone


def home(request):
    return render(request, "dashboard/home.html")


def hello_htmx(request):
    return render(
        request,
        "dashboard/partials/hello.html",
    )


def server_time(request):
    return render(
        request,
        "dashboard/partials/server_time.html",
        {
            "current_time": timezone.now(),
        },
    )