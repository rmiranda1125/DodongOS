from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [

    path(
        "",
        views.lead_list,
        name="list",
    ),

    path(
        "<int:pk>/status/",
        views.lead_status_update,
        name="status_update",
    ),

    path(
        "<int:pk>/notes/",
        views.lead_add_note,
        name="add_note",
    ),

    path(
        "<int:pk>/",
        views.lead_detail,
        name="detail",
    ),

]