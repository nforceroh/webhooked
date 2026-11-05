---
status: accepted
---

# UUID Capture Endpoints and Request Retention

The single fixed capture path is replaced by operator-managed Capture Endpoints for intended integrations, each with a required label and a random UUIDv4 URL. Possession of that URL authorizes writes but does not verify sender identity; it is write-only, and endpoint history remains available only through the private review UI. Revocation permanently stops writes while preserving history, deletion removes the endpoint and its deliveries, and unknown or revoked URLs return the same 404. Deliveries retain raw bodies up to 1 MiB, all headers, and caller query strings indefinitely without rate limiting; the endpoint UUID is redacted from stored request targets and Traefik access logs.

The review UI and ingestion endpoint run in the same Django application. The UI has no application-level login and is intended only for a trusted homelab network; network exposure and proxy access-log redaction are deployment responsibilities. Local development defaults to SQLite, while deployment uses environment-configured MariaDB.
