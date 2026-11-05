from django.urls import path

from . import views

app_name = "capture"

urlpatterns = [
    path("<uuid:token>", views.receive, name="receive"),
]
