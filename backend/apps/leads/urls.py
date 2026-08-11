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

    path(
    "dashboard/",
    views.lead_dashboard,
    name="dashboard",
    ),

    path(
    "<int:pk>/status/",
    views.update_lead_status,
    name="update_status",
    ),

    path(
    "bulk-status/",
    views.bulk_update_status,
    name="bulk_status_update",
    ),

    path(
    "<int:pk>/status/edit/",
    views.edit_lead_status,
    name="edit_status",
    ),

]