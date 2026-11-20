# Cryptographic Module Inventory

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

| | |
|---|---|
| Status | Outline. Author to verify each row |
| Rules | `CMU-CSO-CMD` (document modules), `CMU-CSO-CAT` (tenant defaults), `CMU-CSO-UVM` (validated modules, Class C) |

Do not claim validated status until you have checked the module certificate against the CMU rules in `rules-matrix.md`.

| Use | Module or service | Validation status | Notes |
|---|---|---|---|
| Storage encryption | Cloud key management service keys | TODO verify | Rotation enabled |
| Transport (TLS) | Load balancer TLS policy | TODO verify | TLS 1.2 or later |
| Backup encryption | Backup vault keys (us-east-1 and us-west-2) | TODO verify | Separate key per region |
| Signing | Build and image signing | TODO verify | Used by SVC-VRI checks |
| TODO (author) | | | |

## Tenant defaults (`CMU-CSO-CAT`)
TODO (author): state whether new agency tenants use validated cryptographic services by default.

## Update stream (`CMU-CSO-UVM`)
TODO (author): how Orrinwick tracks module updates and certificate expiry.
