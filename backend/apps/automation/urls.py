from django.urls import path

from . import views


app_name = "automation"


urlpatterns = [
    path(
        "runs/",
        views.automation_run_history,
        name="run_history",
    ),
]
