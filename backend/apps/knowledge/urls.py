from django.urls import path

from . import views


app_name = "knowledge"


urlpatterns = [
    path(
        "",
        views.knowledge_assistant,
        name="assistant",
    ),
    path(
        "ask/",
        views.knowledge_assistant_ask,
        name="assistant_ask",
    ),
]
