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
]