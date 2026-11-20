# INR: Incident response

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented.

Policy: [POL-INR](../policies/POL-INR.md). Plan: [incident response plan](../incident-response-plan.md).

## KSI-INR-RIR Reviewing Incident Response Procedures

| Field | Design |
|---|---|
| Requirement | Orrinwick must keep reviewing whether its documented incident response procedures work |
| Policy requirement | POL-INR / INR-1 and INR-3 |
| Resource type | Non-machine (the incident response plan and its review, owned by the CISO) |
| Validation cadence | Every build. VDR-TFR-NMV requires at least every 3 months |
| Static method | `inr-rir-static`. Reads `ir_plan` in `environment/grc-records.json` and `policies/policy-set.json`. Passes when a POL-INR requirement lists INR-RIR, `review_cadence_days` is a positive number of 365 or less, and the plan document exists |
| Live method | `inr-rir-live`. Reads `ir_plan.last_reviewed` and `as_of` in `environment/grc-records.json`. Passes when the last review is no older than `review_cadence_days` |
| Fails when | No POL-INR requirement covers INR-RIR. The cadence is missing, zero or longer than 365 days. The plan document is missing. No review date exists, the date is after `as_of`, or the review is older than the cadence |
| Break test | Unit test: a review date of 2024-01-01 fails the live method. Manual test not yet run. Planned: set `ir_plan.last_reviewed` to null and check that the live method fails with "No review of the incident response plan is recorded" |
| Production source | The document management system or GRC tool: the plan's version history and the CISO's dated approval |
| Gap | The methods prove that a dated review took place inside the cadence. They do not prove that the review judged the procedures effective, which the KSI asks for. INR-3 also asks for a review after every incident, and no method checks that |
| Status | Built |

**Decision.** I kept the annual cadence that POL-INR states. VDR-TFR-NMV sets how often this check must run, and the daily run meets that. It does not set how often the plan itself must be reviewed.
