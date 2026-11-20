# Vulnerability Detection and Response report

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

Rules: VDR-* in `rules-matrix.md`. Findings below are the seeded demo findings that the validators surface in `evidence/latest.json`.

| ID | Finding | Scope resource | Source KSI | Severity (demo) | Detected | Target | Status |
|---|---|---|---|---|---|---|---|
| BCN-V-001 | Internet-open SSH (inbound and outbound) on `legacy-bastion`, created by hand during an incident. It bypasses the E6 access gateway and is not in infrastructure code | P1, E6 | KSI-CNA-RNT | High | seeded | TODO | Open |
| BCN-V-002 | Unencrypted volume `vol-legacy-1` attached to the bastion | P1 | KSI-SVC-SIN | Moderate | seeded | TODO | Open |
| BCN-V-003 | `notify_provider_keys` (credentials for T1 to T3) last rotated 143 days ago (limit 90) | P6 | KSI-SVC-ASM | Moderate | seeded | TODO | Open |
| BCN-V-004 | 3 unused IAM permission findings | E6 | KSI-IAM-ELP | Low | seeded | TODO | Open |
| BCN-V-005 | Resources outside intended IaC state (`legacy-bastion` security group, instance and volume) | P1 | KSI-CNA-EIS | Moderate | seeded | TODO | Open |
| BCN-V-006 | Newest database backup is 6 hours old against a 4 hour recovery point objective | P3 | KSI-RPL-ABO | Moderate | seeded | TODO | Open |

TODO: replace the placeholder severities with the VDR classification and timeframes from the official rules, and wire this table to a real scanner feed.
