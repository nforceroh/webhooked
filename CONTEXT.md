# Webhook Capture

The Webhook Capture context receives generic HTTP requests at operator-managed endpoints and makes recorded deliveries available for operator review. It preserves submitted requests rather than interpreting them as provider-specific events.

## Language

**Integration**:
The named service or environment for which an operator creates one or more Capture Endpoints. The name describes intended use, not verified identity.
_Avoid_: Authenticated sender

**Capture Endpoint**:
An operator-managed destination assigned to an Integration. It groups Deliveries for review, but does not establish who sent them.
_Avoid_: Sender

**Delivery**:
One incoming HTTP request that has been durably recorded against a Capture Endpoint. A retry or identical repeat is a separate Delivery.
_Avoid_: Event, deduplicated event

**Sender**:
The client that originates a Delivery. Its identity is unverified; an observed address or endpoint label is only a clue.
_Avoid_: Authenticated provider, trusted source

**Payload**:
The original body bytes carried by a Delivery, whether JSON, text, or binary.
_Avoid_: Normalized event

**Rejected Request**:
An incoming request that is not durably recorded and therefore does not appear in delivery history.
_Avoid_: Delivery
