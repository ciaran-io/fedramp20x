# CMT: Change management

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented.

Policy: [POL-CMT](../policies/POL-CMT.md).

## KSI-CMT-LMC Logging Changes

| Field | Design |
|---|---|
| Requirement | Every change to the offering must be logged and monitored |
| Policy requirement | POL-CMT / CMT-1 (every production change goes through the pipeline and is logged), CMT-6 (every pipeline change gets a change type) |
| Resource type | Machine-based (CloudTrail, the configuration recorder and the CI/CD pipeline log) |
| Validation cadence | Every build. VDR-TFR-MVX requires at least every 3 days |
| Static method | `lmc-iac-change-logging`. Reads `environment/iac-plan.json`. Passes when CloudTrail covers all regions with log file validation, a configuration recorder is declared, and the pipeline audit log is kept for at least 365 days |
| Live method | `lmc-live-change-coverage`. Reads `change_events` in `environment/live-state.json`. Passes when every pipeline change in the last 30 days has a log entry and every manual console change raised an alert |
| Change type method | `lmc-live-change-types`. Reads `change_events` in `environment/live-state.json`. Passes when every pipeline change in the last 30 days has one of the four change types (routine recurring, not significant, adaptive, transformative), no other type is used, and the type counts add up to the number of typed changes |
| Fails when | The trail misses a region or has no log file validation. No configuration recorder exists. The pipeline log is kept under 365 days. A pipeline change has no log entry. A manual change raised no alert. A pipeline change has no change type, or a type outside the four is used |
| Break test | Unit tests: 210 of 212 changes typed fails the change type method, and a "not_applicable" type fails it. Manual test on 2026-11-22: with 211 typed, the method failed with "1 pipeline change(s) have no change type" |
| Production source | Static: the Terraform plan JSON. Live: the CI/CD pipeline's audit log API with the change type field on each run, CloudTrail and the alerting rule for console changes |
| Gap | The methods check counts for the last 30 days, not each change. They do not prove that the change type was correct, that an adaptive or transformative change got its notice (CMT-5), or that anyone reviews the logs. The first two methods have not had a design review yet |
| Status | Built |

**Decisions.**
- Every pipeline change gets one of the four change types, and there is no "not applicable" type. A recurring change is "routine recurring" and any other change with no effect on the security posture is "not significant". Both need no notice, but both record that someone made the decision (SCN-CSO-EVA).
- The change type check is a third method, so the evidence shows logging and classification separately.


## KSI-CMT-RVP Reviewing Change Procedures

| Field | Design |
|---|---|
| Requirement | Orrinwick must keep reviewing whether its documented change procedure works, including after a change goes wrong |
| Policy requirement | POL-CMT / CMT-3 |
| Resource type | Non-machine (the change procedure and its reviews, owned by the Platform Lead) |
| Validation cadence | Every build. VDR-TFR-NMV requires at least every 3 months |
| Static method | `cmt-rvp-static`. Reads `change_procedure` in `environment/grc-records.json` and `policies/policy-set.json`. Passes when a POL-CMT requirement lists CMT-RVP and sets a yearly review and a review after a failed or emergency change, the review cadence is 365 days or less, and the procedure it points to exists |
| Live method | `cmt-rvp-live`. Reads `change_procedure.reviews` and measures the newest review's age against the run date. Passes when that review is no older than `review_cadence_days` and its `reviewed_by` matches the POL-CMT owner (Platform Lead) |
| Change method | `cmt-rvp-change`. Reads `change_procedure.failed_or_emergency_changes` and the review dates. Passes when every failed or emergency change has a review of the procedure within 10 business days. A review that is still due shows as a "due by" note, not a failure |
| Fails when | No POL-CMT requirement covers CMT-RVP, or it sets no yearly review or no review after a failed or emergency change. The cadence is missing or longer than 365 days. The procedure reference does not resolve. No review exists, the newest review is dated after the run date, is older than the cadence or was recorded by someone other than the Platform Lead. A failed or emergency change has no review within 10 business days |
| Break test | Unit tests: a review older than the cadence fails, a review by the GRC Lead fails, and an emergency change shows "due by 2026-11-30" and fails from 2026-12-01. Manual test on 2026-11-22: with the reviews removed, the live method failed with "No change procedure review is recorded" and the change method failed with "CHG-0412 (failed, 2026-09-24) has no change procedure review by the deadline 2026-10-08" |
| Production source | Change tickets marked failed or emergency in the change system, and the dated review records for the procedure in the GRC tool |
| Gap | The methods prove that reviews happen on time, by the right person and after each failed or emergency change. They do not prove that a review changed anything or judged the procedure effective. |
| Status | Built |

**Decisions.**
- A failed or emergency change triggers an extra review, as CMT-3 says. It is checked by its own method, so the evidence shows the yearly review and the follow-up reviews separately, as for KSI-CNA-RVP.
- The follow-up review is due within 10 business days, using the shared change-review method. Before, the check failed on the first day after the change.
- Reviews are kept as a list, and each review is a new entry, so the history shows every review.
