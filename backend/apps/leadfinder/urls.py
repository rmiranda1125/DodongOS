from django.urls import path

from . import views

app_name = "leadfinder"

urlpatterns = [

    path(
        "",
        views.index,
        name="index",
    ),

    path(
    "import/",
    views.import_company,
    name="import",
    ),

]