from django.urls import path

from . import views

app_name = "scanner"

urlpatterns = [
    path("", views.review_queue, name="review_queue"),
    path("upload/", views.upload_csv, name="upload_csv"),
    path("scan-url/", views.scan_job_url, name="scan_url"),
    path("runs/", views.scan_runs, name="scan_runs"),
    path("export.csv", views.export_csv, name="export_csv"),
    path("<int:candidate_id>/", views.candidate_detail, name="candidate_detail"),
    path(
        "<int:candidate_id>/import/",
        views.import_candidate,
        name="import_candidate",
    ),
    path(
        "<int:candidate_id>/reject/",
        views.reject_candidate,
        name="reject_candidate",
    ),
    path(
        "<int:candidate_id>/reviewed/",
        views.mark_reviewed,
        name="mark_reviewed",
    ),
]
