from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="dashboard"),
    path("hello-htmx/", views.hello_htmx, name="hello_htmx"),
    path("server-time/", views.server_time, name="server_time"),
]