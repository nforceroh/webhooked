import csv
import json
import logging
from datetime import date

from capture.models import CaptureEndpoint, Delivery
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

PAGE_SIZE = 50
logger = logging.getLogger(__name__)


def _dashboard_context(request, **extra):
    endpoints = CaptureEndpoint.objects.annotate(delivery_count=Count("deliveries"))
    return {
        "endpoints": endpoints,
        "active_endpoints": endpoints.filter(revoked_at__isnull=True),
        "total_deliveries": Delivery.objects.count(),
        **extra,
    }


def _delivery_list(request, endpoint=None, form_error=""):
    deliveries = Delivery.objects.select_related("endpoint")
    if endpoint is not None:
        deliveries = deliveries.filter(endpoint=endpoint)

    selected_endpoint = request.GET.get("endpoint", "")
    if selected_endpoint:
        if not selected_endpoint.isdecimal():
            return HttpResponseBadRequest("Invalid endpoint filter.")
        deliveries = deliveries.filter(endpoint_id=int(selected_endpoint))

    search = request.GET.get("q", "").strip()
    if search:
        deliveries = deliveries.filter(search_document__icontains=search)

    method = request.GET.get("method", "").strip()
    if method:
        deliveries = deliveries.filter(method__iexact=method)

    source_ip = request.GET.get("source_ip", "").strip()
    if source_ip:
        deliveries = deliveries.filter(source_ip=source_ip)

    for key, lookup in (("after", "received_at__date__gte"), ("before", "received_at__date__lte")):
        raw_date = request.GET.get(key, "")
        if raw_date:
            try:
                date.fromisoformat(raw_date)
            except ValueError:
                return HttpResponseBadRequest(f"Invalid {key} date.")
            deliveries = deliveries.filter(**{lookup: raw_date})

    paginator = Paginator(deliveries, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    context = _dashboard_context(
        request,
        current_endpoint=endpoint,
        capture_url=endpoint.capture_url(request) if endpoint else "",
        page_obj=page_obj,
        deliveries=page_obj.object_list,
        search=search,
        method=method,
        source_ip=source_ip,
        selected_endpoint=selected_endpoint,
        after=request.GET.get("after", ""),
        before=request.GET.get("before", ""),
        base_query=query.urlencode(),
        form_error=form_error,
    )
    return render(request, "review/deliveries.html", context)


def dashboard(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name or len(name) > 120:
            response = _delivery_list(request, form_error="Endpoint name must be 1-120 characters.")
            response.status_code = 400
            return response
        endpoint = CaptureEndpoint.objects.create(name=name)
        return redirect("review:endpoint-detail", pk=endpoint.pk)
    return _delivery_list(request)


def endpoint_detail(request, pk):
    endpoint = get_object_or_404(CaptureEndpoint, pk=pk)
    return _delivery_list(request, endpoint=endpoint)


def delivery_detail(request, pk):
    delivery = get_object_or_404(Delivery.objects.select_related("endpoint"), pk=pk)
    return render(
        request,
        "review/delivery_detail.html",
        _dashboard_context(request, delivery=delivery, body_json=delivery.body_json),
    )


def delivery_export(request, pk):
    delivery = get_object_or_404(Delivery.objects.select_related("endpoint"), pk=pk)
    payload = {
        "id": delivery.pk,
        "endpoint": delivery.endpoint.name,
        "received_at": delivery.received_at.isoformat(),
        "method": delivery.method,
        "request_target": delivery.request_target,
        "source_ip": delivery.source_ip,
        "headers": delivery.headers,
        "body_is_utf8": delivery.body_is_utf8,
        "body_text": delivery.body_text,
        "body_base64": delivery.body_base64,
        "body_json": delivery.body_json,
    }
    response = JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "indent": 2})
    response["Content-Disposition"] = f'attachment; filename="delivery-{delivery.pk}.json"'
    return response


@require_POST
def endpoint_revoke(request, pk):
    endpoint = get_object_or_404(CaptureEndpoint, pk=pk)
    endpoint.revoke()
    return redirect("review:endpoint-detail", pk=endpoint.pk)


@require_POST
def endpoint_delete(request, pk):
    endpoint = get_object_or_404(CaptureEndpoint, pk=pk)
    if request.POST.get("confirm_name") != endpoint.name:
        return HttpResponseBadRequest("Endpoint name did not match; nothing was deleted.")
    endpoint.delete()
    return redirect("review:dashboard")


def _selected_deliveries(request):
    ids = request.POST.getlist("delivery_ids")
    if not ids or any(not item.isdecimal() for item in ids):
        return None
    return Delivery.objects.filter(pk__in={int(item) for item in ids})


@require_POST
def delivery_bulk_action(request):
    deliveries = _selected_deliveries(request)
    if deliveries is None:
        return HttpResponseBadRequest("Select at least one valid delivery.")

    action = request.POST.get("action")
    if action == "delete":
        deliveries.delete()
        return_to = request.POST.get("return_to", "")
        if url_has_allowed_host_and_scheme(
            return_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(return_to)
        return redirect("review:dashboard")
    if action != "export":
        return HttpResponseBadRequest("Unknown bulk action.")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="deliveries.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "endpoint",
            "received_at",
            "method",
            "request_target",
            "source_ip",
            "headers",
            "body_base64",
        ]
    )
    for delivery in deliveries.select_related("endpoint").order_by("received_at", "pk"):
        writer.writerow(
            [
                delivery.pk,
                delivery.endpoint.name,
                delivery.received_at.isoformat(),
                delivery.method,
                delivery.request_target,
                delivery.source_ip or "",
                json.dumps(delivery.headers, ensure_ascii=False),
                delivery.body_base64,
            ]
        )
    return response


@require_POST
def delivery_delete(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    delivery.delete()
    return redirect("review:endpoint-detail", pk=delivery.endpoint_id)


def health_live(request):
    return HttpResponse("ok", content_type="text/plain")


def health_ready(request):
    try:
        Delivery.objects.exists()
    except DatabaseError as exc:
        logger.error("readiness check failed (%s)", type(exc).__name__)
        return HttpResponse("unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")


# Create your views here.
