from django.urls import path

from . import views

app_name = "review"

urlpatterns = [
    path("health/live", views.health_live, name="health-live"),
    path("health/ready", views.health_ready, name="health-ready"),
    path("endpoints/<int:pk>", views.endpoint_detail, name="endpoint-detail"),
    path("endpoints/<int:pk>/revoke", views.endpoint_revoke, name="endpoint-revoke"),
    path("endpoints/<int:pk>/delete", views.endpoint_delete, name="endpoint-delete"),
    path("deliveries/<int:pk>", views.delivery_detail, name="delivery-detail"),
    path("deliveries/<int:pk>/export", views.delivery_export, name="delivery-export"),
    path("deliveries/<int:pk>/delete", views.delivery_delete, name="delivery-delete"),
    path("deliveries/bulk", views.delivery_bulk_action, name="delivery-bulk"),
    path("", views.dashboard, name="dashboard"),
]
