import logging

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

from .models import CaptureEndpoint
from .services import store_delivery

logger = logging.getLogger("capture")


@csrf_exempt
def receive(request, token):
    try:
        endpoint = CaptureEndpoint.objects.filter(
            public_token=token,
            revoked_at__isnull=True,
        ).first()
    except DatabaseError as exc:
        logger.error("endpoint lookup failed (%s)", type(exc).__name__)
        return HttpResponse(status=503)
    if endpoint is None:
        return HttpResponseNotFound()

    content_length = request.META.get("CONTENT_LENGTH")
    if content_length:
        try:
            if int(content_length) > settings.MAX_CAPTURE_BODY_BYTES:
                return HttpResponse(status=413)
        except ValueError:
            return HttpResponse(status=400)

    try:
        body = request.body
    except RequestDataTooBig:
        return HttpResponse(status=413)

    if len(body) > settings.MAX_CAPTURE_BODY_BYTES:
        return HttpResponse(status=413)

    try:
        delivery = store_delivery(endpoint, request, body)
    except DatabaseError as exc:
        logger.error("delivery persistence failed (%s)", type(exc).__name__)
        return HttpResponse(status=503)

    if delivery is None:
        return HttpResponseNotFound()

    logger.info("delivery stored id=%s method=%s", delivery.pk, delivery.method)
    return HttpResponse(status=202)
