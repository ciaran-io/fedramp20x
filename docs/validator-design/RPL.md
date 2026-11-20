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

## KSI-RPL-ABO Aligning Backups with Objectives

| Field | Design |
|---|---|
| Requirement | The backups of machine resources must keep matching the recovery objectives, and Orrinwick must keep checking that they do |
| Policy requirement | POL-RPL / RPL-2 |
| Resource type | Machine-based (AWS Backup plans, vaults and recovery points) |
| Validation cadence | Every build. VDR-TFR-MVX requires at least every 3 days |
| Static method | `abo-iac-backup-policy`. Reads the AWS Backup resources in `environment/iac-plan.json` and the objectives in `environment/recovery-objectives.json`. Passes when every backup rule runs at least once per RPO, keeps recovery points for at least 14 days, copies to a locked vault in us-west-2, every vault uses a customer-managed key, and every protected data store is in a backup selection |
| Live method | `abo-live-backup-currency`. Reads `aws_backup` in `environment/live-state.json`. Passes when the newest recovery point of each protected resource is inside the RPO, each copy job to us-west-2 completed inside the RPO, and the us-west-2 vault is locked |
| Fails when | A rule runs less often than the RPO, keeps data too briefly or has no copy to us-west-2. A vault has no customer-managed key or no lock. A protected data store has no backup selection. A recovery point or copy is older than the RPO, or a copy job did not complete |
| Break test | Not yet run. Planned: set `schedule_interval_hours` to 6 in `iac-plan.json` (static), and set `latest_recovery_point_age_hours` for `db:primary` to 6 in `live-state.json` (live) |
| Production source | Static: the Terraform plan JSON for the AWS Backup resources. Live: AWS Backup `ListRecoveryPointsByResource`, `ListCopyJobs` and `DescribeBackupVault` |
| Gap | The methods do not prove that a backup can be restored or that a restore meets the RTO. RPL-TRC covers that. I also found three points where the checks are weaker than POL-RPL. (1) The static method compares the backup interval with the 4-hour RPO, but RPL-2 and `backup_interval_hours_max` require every 2 hours, so a 3-hour schedule would pass. (2) Both methods check that the vault is locked, but not that the lock is in compliance mode, which RPL-2 requires. (3) RPL-2 requires an alert when a backup or copy job fails, and no method checks that alert |
| Status | Built |

**Change requests.** Points (1) and (2) in the gap are small fixes to the existing methods. Point (3) needs alert data that the environment does not hold yet.
