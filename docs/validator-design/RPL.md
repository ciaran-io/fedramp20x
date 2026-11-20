# RPL: Recovery planning

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented.

Policy: [POL-RPL](../policies/POL-RPL.md). Recovery strategy: backup and restore (SD-003).

## KSI-RPL-RRO Reviewing Recovery Objectives

| Field | Design |
|---|---|
| Requirement | Orrinwick must set its own recovery time and recovery point objectives and keep reviewing them, so they stay correct as the service changes |
| Policy requirement | POL-RPL / RPL-1 |
| Resource type | Non-machine (a review process owned by the Platform Lead) |
| Validation cadence | Every build. VDR-TFR-NMV requires at least every 3 months |
| Static method | `rpl-rro-static`. Reads `environment/recovery-objectives.json` and `policies/policy-set.json`. Passes when `rto_hours`, `rpo_hours` and `review_cadence_days` are positive numbers and a POL-RPL requirement lists RPL-RRO |
| Live method | `rpl-rro-live`. Reads `last_reviewed` from `environment/recovery-objectives.json` and `as_of` from `environment/grc-records.json`. Passes when the review is no older than `review_cadence_days` |
| Fails when | An objective or the cadence is missing, zero or not a number. No POL-RPL requirement covers RPL-RRO. No review date exists, the review date is after `as_of`, or the review is older than the cadence |
| Break test | Live: I set `last_reviewed` to 2024-11-19. The method failed with "Last review was 730 days ago, cadence is 90 days". Static: not yet run |
| Production source | The review record in the GRC tool or change ticket system, with the Platform Lead's approval and date. The RTO and RPO values from the recovery plan |
| Gap | The methods prove that the objectives exist and that a review took place inside the cadence. They do not prove what the review concluded, or that the objectives still match the architecture and the restore test results (RPL-TRC) |
| Status | Built |

**Decision.** I set the review cadence to 90 days. This is my choice as the provider and is stricter than the annual review the policy first stated. VDR-TFR-NMV sets how often the status of a non-machine resource must be validated. It does not set how often the review itself must happen.
