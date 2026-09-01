from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.liveness, name="health_liveness"),
    path("ready/", views.readiness, name="health_readiness"),
]
