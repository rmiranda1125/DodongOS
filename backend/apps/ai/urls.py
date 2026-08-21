from django.urls import path

from . import views


app_name = "ai"


urlpatterns = [
    path(
        "",
        views.crm_assistant,
        name="crm_assistant",
    ),
    path(
        "ask/",
        views.crm_assistant_ask,
        name="crm_assistant_ask",
    ),
    path(
    "task/propose/",
    views.crm_assistant_task_proposal,
    name="crm_assistant_task_proposal",
    ),
    path(
    "task/confirm/",
    views.crm_assistant_task_confirm,
    name="crm_assistant_task_confirm",
    ),
]