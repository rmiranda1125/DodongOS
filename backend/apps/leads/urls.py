from django.urls import path

from . import views


app_name = "leads"


urlpatterns = [

    # =====================================================
    # LEAD LIST
    # =====================================================

    path(
        "",
        views.lead_list,
        name="list",
    ),


    # =====================================================
    # LEAD PIPELINE
    # =====================================================

    path(
        "pipeline/",
        views.lead_pipeline,
        name="pipeline",
    ),

    path(
        "<int:pk>/pipeline-status/",
        views.update_pipeline_status,
        name="update_pipeline_status",
    ),


    # =====================================================
    # LEAD DASHBOARD
    # =====================================================

    path(
        "dashboard/",
        views.lead_dashboard,
        name="dashboard",
    ),


    # =====================================================
    # LEAD STATUS
    # =====================================================

    path(
        "<int:pk>/status/",
        views.update_lead_status,
        name="update_lead_status",
    ),

    path(
        "<int:pk>/status/edit/",
        views.edit_lead_status,
        name="edit_status",
    ),

    path(
        "bulk-status/",
        views.bulk_update_status,
        name="bulk_status_update",
    ),


    # =====================================================
    # NOTES
    # =====================================================

    path(
        "<int:pk>/notes/",
        views.lead_add_note,
        name="add_note",
    ),


    # =====================================================
    # ACTIVITY
    # =====================================================

    path(
        "<int:pk>/activity/add/",
        views.add_activity,
        name="add_activity",
    ),

    path(
        "<int:pk>/activity/<int:activity_pk>/delete/",
        views.delete_activity,
        name="delete_activity",
    ),


    # =====================================================
    # EDIT LEAD
    # =====================================================

    path(
        "<int:pk>/edit/",
        views.lead_edit,
        name="edit",
    ),

    path(
    "<int:pk>/tasks/new/",
    views.lead_task_create,
    name="task_create",
    ),

    path(
    "<int:pk>/tasks/<int:task_pk>/status/",
    views.lead_task_update_status,
    name="task_update_status",
    ),

    # =====================================================
    # LEAD DETAIL
    # =====================================================

    path(
        "<int:pk>/",
        views.lead_detail,
        name="detail",
    ),

    path(
    "<int:pk>/activity/<int:activity_pk>/edit/",
    views.edit_activity,
    name="edit_activity",
    ),
]