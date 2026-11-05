import base64
import ipaddress
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CaptureEndpoint, Delivery
from .services import source_ip_from_request


class CaptureViewTests(TestCase):
    def setUp(self):
        self.endpoint = CaptureEndpoint.objects.create(name="Test integration")
        self.url = reverse("capture:receive", kwargs={"token": self.endpoint.public_token})

    def test_records_request_and_redacts_capture_token_from_target(self):
        response = self.client.generic(
            "PATCH",
            f"{self.url}?delivery_id=42",
            data=b'{"ok": true}',
            content_type="application/json",
            HTTP_X_DELIVERY_ID="abc",
        )

        self.assertEqual(response.status_code, 202)
        delivery = Delivery.objects.get(endpoint=self.endpoint)
        self.assertEqual(delivery.method, "PATCH")
        self.assertEqual(delivery.body_bytes, b'{"ok": true}')
        self.assertEqual(delivery.request_target, "/ingest/{endpoint}?delivery_id=42")
        self.assertIn({"name": "X-Delivery-Id", "value": "abc"}, delivery.headers)
        self.assertEqual(delivery.body_json, {"ok": True})

    def test_unknown_and_revoked_endpoints_return_the_same_not_found(self):
        unknown = self.client.post(reverse("capture:receive", kwargs={"token": uuid4()}))
        self.endpoint.revoke()
        revoked = self.client.post(self.url)

        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(revoked.status_code, 404)
        self.assertEqual(Delivery.objects.count(), 0)

    @override_settings(MAX_CAPTURE_BODY_BYTES=4, DATA_UPLOAD_MAX_MEMORY_SIZE=4)
    def test_rejects_body_over_configured_limit_without_recording(self):
        response = self.client.post(self.url, data=b"12345", content_type="text/plain")

        self.assertEqual(response.status_code, 413)
        self.assertEqual(Delivery.objects.count(), 0)

    def test_persistence_failure_returns_service_unavailable(self):
        with patch("capture.views.store_delivery", side_effect=DatabaseError("offline")):
            response = self.client.generic("POST", self.url, data=b"payload")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(Delivery.objects.count(), 0)

    def test_binary_body_is_preserved_and_exportable_as_base64(self):
        response = self.client.post(
            self.url,
            data=b"\x00\xff\xfe",
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 202)
        delivery = Delivery.objects.get(endpoint=self.endpoint)
        self.assertFalse(delivery.body_is_utf8)
        self.assertEqual(delivery.body_base64, base64.b64encode(b"\x00\xff\xfe").decode("ascii"))


class SourceAddressTests(TestCase):
    @override_settings(TRUSTED_PROXY_CIDRS=(ipaddress.ip_network("10.0.0.0/8"),))
    def test_uses_forwarded_client_ip_only_from_trusted_proxy(self):
        request = type(
            "Request",
            (),
            {
                "META": {"REMOTE_ADDR": "10.0.0.2"},
                "headers": {"X-Forwarded-For": "203.0.113.8, 10.0.0.1"},
            },
        )()

        self.assertEqual(source_ip_from_request(request), "203.0.113.8")

    @override_settings(TRUSTED_PROXY_CIDRS=(ipaddress.ip_network("10.0.0.0/8"),))
    def test_ignores_forwarded_header_from_untrusted_peer(self):
        request = type(
            "Request",
            (),
            {
                "META": {"REMOTE_ADDR": "192.0.2.3"},
                "headers": {"X-Forwarded-For": "203.0.113.8"},
            },
        )()

        self.assertEqual(source_ip_from_request(request), "192.0.2.3")
