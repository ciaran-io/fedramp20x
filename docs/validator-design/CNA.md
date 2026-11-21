# CNA: Cloud native architecture

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented.

Policy: [POL-CNA](../policies/POL-CNA.md).

## KSI-CNA-RVP Reviewing Protections

| Field | Design |
|---|---|
| Requirement | Orrinwick must keep reviewing whether its protection against denial of service and other unwanted traffic still works |
| Policy requirement | POL-CNA / CNA-7 |
| Resource type | Non-machine (the review of protections, owned by the Platform Lead). The protections themselves are machine-based and are checked by other CNA KSIs |
| Validation cadence | Every build. VDR-TFR-NMV requires at least every 3 months |
| Static method | `cna-rvp-static`. Reads `policies/policy-set.json`. Passes when a POL-CNA requirement lists CNA-RVP and states how often the review happens |
| Live method | `cna-rvp-live`. Reads `protection_reviews` and `as_of` in `environment/grc-records.json`. Passes when the newest review is no older than 365 days, has a summary, and was recorded by the Platform Lead, as CNA-7 names |
| Fails when | No POL-CNA requirement covers CNA-RVP, or it states no interval. No review is recorded, the newest review is after `as_of`, is older than 365 days, has no summary, or was recorded by someone other than the Platform Lead |
| Break test | Unit test: a review dated 2024-05-01 fails the live method. Manual test not yet run. Planned: set the review date to null and check that the live method fails with "No protection review is recorded" |
| Production source | The Platform Lead's review record in the GRC tool, with links to the WAF and rate-limit settings that were reviewed |
| Gap | The methods prove that a dated review with a summary exists. They do not prove that the review judged the protections effective. CNA-7 also asks for a review after any significant change, and no method checks that against the significant change log |
| Status | Built |
