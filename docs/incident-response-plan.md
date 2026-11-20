# Incident Response Plan

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

| | |
|---|---|
| Owner | CISO (fictional) |
| Status | Outline. Author to write each section |
| Rules | `IEC-CSO-*` in `rules-matrix.md` |
| KSIs | KSI-INR-AAR, KSI-INR-RIR, KSI-INR-RPI |
| Policy | `POL-INR` |

## 1. Roles and contacts
TODO (author): who declares an incident, who leads it, who talks to agencies, who approves reports. Use the roles in `policies/policy-set.json`.

## 2. Severity levels
TODO (author): a table of severity levels (for example low, moderate, high, critical) with an example of each for Orrinwick Beacon. The after action report rule in POL-INR-2 applies from moderate upward.

## 3. Evaluation (`IEC-CSO-EFR`, `IEC-CSO-EFI`, `IEC-CSO-DPR`)
TODO (author): the steps that decide whether an incident affects confidentiality or integrity of federal customer data, and how you estimate the Potential Agency Impact N-rating. State what you do when the estimate is not ready (`IEC-CSO-DPR`).

## 4. Reporting to agencies (`IEC-CSO-IIR`, `IEC-CSO-OIR`, `IEC-CSO-FIR`)
TODO (author): what goes in the initial report, how updates are sent, and what the final report contains. Read the exact timelines in `rules-matrix.md` and copy them exactly.

## 5. Automation (`IEC-CSO-AIR`)
TODO (author): which parts of reporting are automated and which are manual.

## 6. After action reports (KSI-INR-AAR)
TODO (author): the report template, the deadline (10 business days in POL-INR-2) and how lessons reach the backlog.

## 7. Review (KSI-INR-RIR, KSI-INR-RPI)
TODO (author): annual plan review, quarterly review of past incidents and a tabletop exercise schedule. Record each review date in `environment/grc-records.json`.
