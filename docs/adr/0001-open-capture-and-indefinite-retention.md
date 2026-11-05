---
status: superseded by ADR-0002
---

# Open Capture and Indefinite Retention

The capture endpoint accepts requests without authenticating senders and retains complete requests, including headers and query strings, indefinitely so operators can inspect generic deliveries without provider-specific transformations. This deliberately accepts the risk of untrusted traffic consuming storage and request metadata containing secrets; the review interface remains private, bodies are limited to 1 MiB, and new deliveries are rejected rather than old ones being expired when storage is unavailable or full. Sender authentication, rate limiting, metadata redaction, and automatic expiration were rejected for the initial design.
