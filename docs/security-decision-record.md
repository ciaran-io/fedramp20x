# Security Decision Record: Orrinwick Beacon

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

Class C replaces the narrative SSP with a persistently maintained record of security decisions (SDR rules, see `rules-matrix.md`). Each entry below is one decision. Add an entry whenever a design, tooling or risk decision is made.

| Field | Value |
|---|---|
| Offering | Orrinwick Beacon (fictional multi-tenant alert-routing SaaS) |
| Target | FedRAMP 20x Class C |
| Scope | `minimum-assessment-scope.md` |
| Owner | GRC Lead (fictional) |
| Last reviewed | 2026-11-19 |

## Decision log

### SD-001: Workforce authentication is passwordless-first
- **Decision:** WebAuthn / platform authenticators required for all workforce SSO; no password-only path.
- **Related KSI:** KSI-IAM-APM
- **Verification:** IdP policy as code (`environment/iac-plan.json`, `idp_policy`)
- **Validation:** live enrollment check (`apm-live-user-factors`)
- **Status:** implemented

### SD-002: Infrastructure is declared in code; manual resources are defects
- **Decision:** All production resources come from Terraform; unmanaged resources are findings.
- **Related KSI:** KSI-CNA-EIS
- **Known gap:** none open. A break-glass bastion built by hand during an incident was removed and its resources were brought under IaC review. A scheduled drift scan now checks that nothing exists outside IaC.
- **Status:** implemented

### SD-003: Recovery uses backup and restore with cross-region encrypted backups
- **Decision:** Production runs multi-AZ in us-east-1. AWS Backup (a native AWS service) takes recovery points of the database and the backup and export buckets every 2 hours and copies them to a vault in us-west-2 that uses a separate encryption key and a compliance-mode vault lock (resource P12, flow F43). No standing environment exists in the recovery region. Terraform builds one on demand from the copied recovery points. The scope record stays vendor-neutral; AWS Backup is the design choice for the fictional environment.
- **Objectives:** RTO 8 hours, RPO 4 hours, backup retention at least 14 days, restore test every 90 days (`environment/recovery-objectives.json`). These are fictional numbers chosen by the demo author; FedRAMP leaves them to the provider (KSI-RPL-RRO).
- **Options considered:** warm standby (rejected: doubles the assessed environment), pilot light (rejected: still a standing replica database and network to assess), backup and restore (chosen), multi-AZ only (rejected: no protection from a regional failure).
- **Scope consequences:** Backups hold every category of federal customer data (D10), so P12 is in scope. Using a recovery environment may be a significant change (OQ9). Agency data removal requests must reach backups in both regions (OQ10).
- **Related KSIs:** KSI-RPL-RRO, KSI-RPL-ABO, KSI-RPL-ARP, KSI-RPL-TRC, KSI-CNA-OFA, KSI-SVC-RUD
- **Verification:** `abo-iac-backup-policy` (static), `abo-live-backup-currency` (live)
- **Known gaps:** nothing yet tests an actual restore (KSI-RPL-TRC). The fixture's newest database recovery point is 6 hours old after two failed jobs, so the live check fails against the 4 hour objective (demo finding).
- **Status:** partial

### SD-004: Scope decisions accepted (OQ1 to OQ10)
- **Decision:** On 2026-11-19 all ten scope questions in `mas/mas-record.json` were resolved by accepting the stated leaning.
  - OQ1: telephony uses a content-free design, and the provider is documented as a third party.
  - OQ2: the mobile app is outside the boundary (supplement item).
  - OQ3: billing stays out, provided only per-tenant aggregates are exported.
  - OQ4: error tracking stays out, provided a pipeline test proves no identifiers leave.
  - OQ5: support ticketing, email and chat stay out, with structured intake, redaction and data loss prevention.
  - OQ6: routing and identity data are rated Moderate for integrity, to be revisited at the categorization review.
  - OQ7: agency-supplied content is federal customer data; service-generated records are metadata.
  - OQ8: each policy and staff role is listed and tied to the policy set.
  - OQ9: the recovery environment uses the same Terraform modules and controls, and each activation is logged as a significant change event.
  - OQ10: backup retention is the data removal window in customer agreements.
- **Related rules:** MAS-CSO-IIR, MAS-CSO-FLO, MAS-CSO-MDI, MAS-CSO-TPR, MAS-CSO-SUP
- **Verification:** conditions for OQ3, OQ4 and OQ5 are the prohibited flows PF6, PF4 and PF1; automated checks for them are not built yet.
- **Status:** accepted

### SD-005: TODO add decisions for logging, secrets, supply chain
