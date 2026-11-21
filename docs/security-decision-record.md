# Security Decision Record: Orrinwick Beacon

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

Class C replaces the narrative SSP with a persistently maintained record of security decisions (SDR rules, see `rules-matrix.md`). Each entry below is one decision. Add an entry whenever a design, tooling or risk decision is made.

| Field | Value |
|---|---|
| Offering | Orrinwick Beacon (fictional multi-tenant alert-routing SaaS) |
| Target | FedRAMP 20x Class C |
| Scope | `minimum-assessment-scope.md` |
| Owner | GRC Lead (fictional) |
| Last reviewed | 2026-11-21 |

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
- **Objectives:** RTO 8 hours, RPO 4 hours, backup retention at least 14 days, restore test every 90 days (`environment/recovery-objectives.json`). These are fictional numbers that I chose; FedRAMP leaves them to the provider (KSI-RPL-RRO). The objectives are reviewed at least every 90 days (POL-RPL RPL-1).
- **Options considered:** warm standby (rejected: doubles the assessed environment), pilot light (rejected: still a standing replica database and network to assess), backup and restore (chosen), multi-AZ only (rejected: no protection from a regional failure).
- **Scope consequences:** Backups hold every category of federal customer data (D10), so P12 is in scope. Using a recovery environment may be a significant change (OQ9). Agency data removal requests must reach backups in both regions (OQ10).
- **Related KSIs:** KSI-RPL-RRO, KSI-RPL-ABO, KSI-RPL-ARP, KSI-RPL-TRC, KSI-CNA-OFA, KSI-SVC-RUD
- **Verification:** `abo-iac-backup-policy` (static), `abo-live-backup-currency` (live). Since 2026-11-20 both check the 2-hour backup interval and a compliance-mode vault lock. Restore tests are checked under KSI-RPL-TRC.
- **Known gaps:** no check confirms the alert for a failed backup or copy job (POL-RPL RPL-2). The restore test interval differs between `environment/recovery-objectives.json` (90 days) and POL-RPL RPL-4 (6 months); I will decide it in the RPL design review.
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

### SD-006: Incidents are rated with PAIN, and the reporting clock starts at the reportability decision
- **Decision:** Each incident is marked reportable or not reportable to FedRAMP (IEC-CSO-EFR) and rated with the Potential Agency Impact N-rating, N0 to N5 (IEC-CSO-EFI). A reportable incident with no rating counts as N5 (IEC-CSO-DPR). An after action report is required for every reportable incident and every incident rated N2 or above. The reporting clock starts once the incident is evaluated, found reportable and rated or defaulted to N5, not at initial detection. The plan is reviewed each year, and when an after action report or a quarterly incident review finds that it needs to change.
- **Options considered:** an internal low, moderate, high and critical scale (rejected: it needs a mapping to FedRAMP's scale and splits incident and vulnerability response); a plan review after every incident (rejected: it repeats the after action report); starting the reporting clock at detection (rejected: the rules tie the initial report to identifying a reportable incident, and the default N5 rating stops the rating step from delaying it).
- **Why:** FedRAMP defines "persistently" (FRD-PER) as a documented, repeated cycle whose status is always known. POL-INR documents the cycle for the INR KSIs, and the checks test that cycle. Using PAIN for incidents and vulnerabilities gives one scale, so a likely exploitable vulnerability above N3 that is internet-reachable can become a reportable incident (VER-TFR-IRI) without a conversion.
- **Related KSIs:** KSI-INR-RIR, KSI-INR-RPI, KSI-INR-AAR
- **Related rules:** IEC-CSO-EFR, IEC-CSO-EFI, IEC-CSO-DPR, IEC-CSO-IIR, VER-TFR-IRI
- **Verification:** `inr-rir-static`, `inr-rir-live`. Design and break tests in `docs/validator-design/INR.md`. Plan: `docs/incident-response-plan.md`
- **Status:** implemented for INR-RIR; INR-RPI and INR-AAR checks in progress
