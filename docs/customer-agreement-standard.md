# Standard customer agreement: data terms (extract)

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented. This is not a real agreement and is not legal text.

Status: Draft, pending review by the demo author. Version 2026-11.

This extract records the data terms that the validators check. The machine-readable copy is `environment/customer-terms.json`.

## Data deletion

| Term | Value |
|---|---|
| Deletion deadline | 30 calendar days from the customer's written request |
| Retention after contract end | Orrinwick deletes all customer data 30 calendar days after the contract ends, with no request needed. After that date the customer does not need to take any action to have its data removed |
| Scope | Customer data in production stores and in backups |
| Backups | Copies in backup vaults are deleted by the deadline or expire under the backup retention period, whichever is sooner |
| Confirmation | Orrinwick confirms deletion in writing and keeps a record of the request |
| Record location | `environment/live-state.json#data_removal_requests` (demo) |

## Checks

KSI-SVC-RUD method `rud-terms-agreement` compares the removal process target and every recorded request with the deletion deadline above.
