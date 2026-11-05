from django.urls import include, path

urlpatterns = [
    path("ingest/", include("capture.urls")),
    path("", include("review.urls")),
]
