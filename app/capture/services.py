import ipaddress

from django.conf import settings
from django.db import transaction

from .models import CaptureEndpoint, Delivery


def _is_trusted_proxy(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return any(address in network for network in settings.TRUSTED_PROXY_CIDRS)


def source_ip_from_request(request) -> str | None:
    peer = request.META.get("REMOTE_ADDR", "")
    try:
        peer_address = ipaddress.ip_address(peer)
    except ValueError:
        return None

    if not settings.TRUSTED_PROXY_CIDRS or not _is_trusted_proxy(peer_address):
        return str(peer_address)

    forwarded = request.headers.get("X-Forwarded-For", "")
    addresses = []
    for candidate in forwarded.split(","):
        try:
            addresses.append(ipaddress.ip_address(candidate.strip()))
        except ValueError:
            continue

    for address in reversed(addresses):
        if not _is_trusted_proxy(address):
            return str(address)
    return str(addresses[0]) if addresses else str(peer_address)


def build_request_target(request) -> str:
    target = "/ingest/{endpoint}"
    query_string = request.META.get("QUERY_STRING", "")
    if query_string:
        target = f"{target}?{query_string}"
    return target


@transaction.atomic
def store_delivery(endpoint: CaptureEndpoint, request, body: bytes) -> Delivery | None:
    active_endpoint = (
        CaptureEndpoint.objects.select_for_update()
        .filter(
            pk=endpoint.pk,
            revoked_at__isnull=True,
        )
        .first()
    )
    if active_endpoint is None:
        return None

    headers = [{"name": name, "value": value} for name, value in request.headers.items()]
    return Delivery.objects.create(
        endpoint=active_endpoint,
        method=request.method,
        request_target=build_request_target(request),
        source_ip=source_ip_from_request(request),
        headers=headers,
        body=body,
    )
