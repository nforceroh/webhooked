import csv
import json
from io import StringIO

from capture.models import CaptureEndpoint, Delivery
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ReviewViewTests(TestCase):
    def setUp(self):
        self.endpoint = CaptureEndpoint.objects.create(name="Home automation")
        self.delivery = Delivery.objects.create(
            endpoint=self.endpoint,
            method="POST",
            request_target="/ingest/{endpoint}?source=test",
            headers=[{"name": "Content-Type", "value": "application/json"}],
            body=b'{"event":"door-open"}',
        )

    def test_dashboard_lists_deliveries_and_creates_endpoints(self):
        response = self.client.get(reverse("review:dashboard"))

        self.assertContains(response, "Home automation")
        self.assertContains(response, "/ingest/")
        created = self.client.post(reverse("review:dashboard"), {"name": "Second"})

        self.assertEqual(created.status_code, 302)
        self.assertEqual(CaptureEndpoint.objects.count(), 2)

    def test_search_filters_request_data(self):
        response = self.client.get(reverse("review:dashboard"), {"q": "door-open"})

        self.assertContains(response, "door-open")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_delivery_detail_shows_headers_and_body(self):
        response = self.client.get(reverse("review:delivery-detail", args=[self.delivery.pk]))

        self.assertContains(response, "Content-Type")
        self.assertContains(response, "door-open")

    def test_json_export_preserves_original_body(self):
        response = self.client.get(reverse("review:delivery-export", args=[self.delivery.pk]))
        payload = json.loads(response.content)

        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(payload["body_text"], '{"event":"door-open"}')
        self.assertEqual(payload["body_json"], {"event": "door-open"})

    def test_csv_export_contains_selected_deliveries(self):
        response = self.client.post(
            reverse("review:delivery-bulk"),
            {"action": "export", "delivery_ids": [str(self.delivery.pk)]},
        )
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))

        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(rows[1][0], str(self.delivery.pk))
        self.assertEqual(rows[1][1], "Home automation")

    def test_bulk_delete_removes_selected_deliveries(self):
        response = self.client.post(
            reverse("review:delivery-bulk"),
            {"action": "delete", "delivery_ids": [str(self.delivery.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Delivery.objects.filter(pk=self.delivery.pk).exists())

    def test_endpoint_deletion_requires_exact_name_and_cascades_history(self):
        url = reverse("review:endpoint-delete", args=[self.endpoint.pk])
        rejected = self.client.post(url, {"confirm_name": "wrong"})
        self.assertEqual(rejected.status_code, 400)
        self.assertTrue(CaptureEndpoint.objects.filter(pk=self.endpoint.pk).exists())

        deleted = self.client.post(url, {"confirm_name": self.endpoint.name})
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse(CaptureEndpoint.objects.filter(pk=self.endpoint.pk).exists())
        self.assertFalse(Delivery.objects.filter(pk=self.delivery.pk).exists())

    def test_health_endpoints_report_success(self):
        live = self.client.get(reverse("review:health-live"))
        ready = self.client.get(reverse("review:health-ready"))

        self.assertEqual(live.status_code, 200)
        self.assertEqual(ready.status_code, 200)
