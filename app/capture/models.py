import base64
import json
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class CaptureEndpoint(models.Model):
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        if self.is_active:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def capture_url(self, request=None) -> str:
        path = reverse("capture:receive", kwargs={"token": self.public_token})
        if settings.CAPTURE_BASE_URL:
            return f"{settings.CAPTURE_BASE_URL}{path}"
        if request is not None:
            return request.build_absolute_uri(path)
        return f"http://localhost:8000{path}"


class Delivery(models.Model):
    endpoint = models.ForeignKey(
        CaptureEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(max_length=32, db_index=True)
    request_target = models.TextField()
    source_ip = models.GenericIPAddressField(null=True, blank=True, unpack_ipv4=True)
    headers = models.JSONField(default=list)
    body = models.BinaryField(blank=True, default=bytes)
    body_is_utf8 = models.BooleanField(default=True)
    search_document = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-received_at", "-pk"]
        indexes = [
            models.Index(fields=["endpoint", "received_at"], name="delivery_endpoint_time"),
            models.Index(fields=["source_ip", "received_at"], name="delivery_source_time"),
            models.Index(fields=["method", "received_at"], name="delivery_method_time"),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.received_at.isoformat()}"

    def save(self, *args, **kwargs) -> None:
        body_bytes = self.body_bytes
        try:
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body_text = ""
            self.body_is_utf8 = False
        else:
            self.body_is_utf8 = True

        header_text = json.dumps(self.headers, ensure_ascii=False, sort_keys=True)
        indexed_parts = [
            body_text,
            header_text,
            self.request_target,
            self.method,
            self.source_ip or "",
            self.received_at.isoformat(),
        ]
        self.search_document = "\n".join(part for part in indexed_parts if part)
        super().save(*args, **kwargs)

    @property
    def body_bytes(self) -> bytes:
        return bytes(self.body)

    @property
    def body_text(self) -> str | None:
        if not self.body_is_utf8:
            return None
        return self.body_bytes.decode("utf-8")

    @property
    def body_base64(self) -> str:
        return base64.b64encode(self.body_bytes).decode("ascii")

    @property
    def body_json(self):
        body_text = self.body_text
        if body_text is None:
            return None
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            return None
