# Orrinwick Labs, Inc. and Orrinwick Beacon

> **FICTIONAL DEMO DOCUMENT.** Orrinwick Labs, Inc. is an invented company created for a FedRAMP 20x learning project. Nothing here describes a real organization, product, customer or certification.

| | |
|---|---|
| Document | Company and offering overview (step 1 of the scoping sequence) |
| Status | Draft v0.2 (recovery model changed from warm standby to backup and restore) |
| Owner | GRC Lead (fictional) |
| Feeds into | Federal customer data identification (`MAS-CSO-IIR`), then information flows (`MAS-CSO-FLO`) |

---

## 1. The company

**Orrinwick Labs, Inc.** builds software that helps government security and IT operations teams get the right person's attention when something important happens.

**The name.** "Orrin" is an old given name, and "-wick" is the English place-name ending for a settlement or outpost. A wick is also what you light. The brand idea is a dependable outpost that sends up a signal. The tone is calm and understated, which suits a product people rely on at 3 a.m.

| Fact (fictional) | Value |
|---|---|
| Founded | 2022 |
| Headquarters | Remote-first, US-based staff only |
| Headcount | About 35 (engineering 16, security and compliance 4, support 5, go-to-market 6, other 4) |
| Customers | Federal civilian agencies and a small number of defense contractors |
| Funding | Seed funded, targeting first federal contracts |
| Leadership | CISO Alex Rivera, GRC Lead Sam Okafor, Platform Lead Jordan Lee (all fictional) |

**Why federal.** Government teams run on-call rotations for security incidents, vulnerability reports and outages, but many still manage them with spreadsheets, group chats and tools never designed for sensitive events. Orrinwick's founders came from federal security operations and built Beacon to answer two questions: who do we wake up, and how do we prove we did.

---

## 2. The offering: Orrinwick Beacon

**Beacon is a cloud service that receives security-relevant alerts from an agency's other tools, decides who needs to act, reaches that person reliably, and keeps a tamper-evident record of what happened.**

In one line: *on-call routing built for sensitive security events, with an audit trail.*

### 2.1 What Beacon does

| Capability | Description |
|---|---|
| Alert intake | Receives alert events from customer tools by API and webhook (scanners, ticketing systems, vulnerability disclosure platforms, SIEM and EDR alert outputs). |
| Routing rules | Maps an alert's type, severity and affected team to a responder or escalation policy. |
| On-call schedules | Rotations, overrides, handoffs and time-zone aware coverage. |
| Escalation | If nobody acknowledges within a set time, Beacon escalates to the next person or group. |
| Notification | Delivers through the Beacon mobile app (push), email, and, as content-free nudges, SMS and voice call (see 2.3). |
| Acknowledge and resolve | Responders acknowledge, reassign, annotate and resolve from the app or console. |
| Audit trail | Every receipt, routing decision, notification attempt, acknowledgement and administrative change is recorded and exportable. |
| Reporting | Response-time metrics and coverage reports by team, for agency leadership and audits. |
| Tenant administration | Agency admins manage users, roles, integrations, routing policy and retention through the console and API. |

### 2.2 What Beacon deliberately does not do

These limits keep the service small, and they keep the assessment boundary small too.

- **It does not ingest logs or telemetry.** Beacon receives discrete *alerts* that another tool has already decided are worth a human's attention. It is not a SIEM and stores no raw event streams.
- **It does not act on agency systems.** No remote commands, no automated remediation, no credentials to agency environments.
- **It does not store full incident records.** Beacon holds the alert and the response trail. The system of record for the incident stays in the agency's ticketing or case tool.
- **It does not send sensitive content over SMS or voice.** See 2.3.

### 2.3 Payload handling principle

Alert payloads can carry operational detail about agency systems, so Beacon treats them as sensitive. Each tenant chooses a payload mode per integration:

| Mode | What is stored and shown | Default |
|---|---|---|
| **Reference-only** | Alert ID, severity, category, link back to the source tool. No descriptive text. | Yes |
| **Standard** | Reference-only plus a short title and summary, shown only to authenticated users in the app and console. | No, opt-in |

Across all modes:

- Push, email, SMS and voice notifications never include the summary. SMS and voice say only that an alert needs attention and to open the app.
- Responder contact details (work and optional personal mobile numbers) are held for delivery and are visible only to tenant admins and the responder.
- This principle is the **first Security Decision Record entry** (SD-001) and drives the third-party telephony decision in the scoping document.

### 2.4 Users

| Persona | What they do in Beacon |
|---|---|
| **Responder** (SOC analyst, sysadmin, vulnerability triager) | Receives, acknowledges and resolves alerts; sets their own contact methods and availability. |
| **Team lead** | Owns schedules and escalation policies; reviews coverage. |
| **Tenant administrator** | Manages users, roles, integrations, payload modes, retention. |
| **Auditor or leadership viewer** | Read-only access to reports and the audit trail. |
| **Integration** (non-human) | A customer tool sending alerts by API key or signed webhook. |
| **Orrinwick operator** | Orrinwick staff who run the service. They have no routine access to tenant content. |

### 2.5 Illustrative scenario

1. An agency's vulnerability scanner flags a critical internet-facing finding and sends an alert to Beacon.
2. Beacon matches the routing rule "critical, external, web tier" to the on-call web security engineer.
3. The engineer's phone gets a push notification and, after two minutes without acknowledgement, a content-free SMS nudge.
4. Still no response, so Beacon escalates to the team lead and records each step.
5. The lead acknowledges in the app, reads the summary (standard mode, authenticated), and opens the ticket in the agency's own case tool through the link.
6. Later, the agency exports the audit trail to show how quickly a critical finding was owned.

---

## 3. How Beacon is delivered (high level)

The service is made of:

- **Web console and mobile app** for responders and administrators
- **Public API and webhook endpoints** for integrations
- **Routing and escalation engine**
- **Notification workers** that send push, email, SMS and voice
- **Tenant data store** for users, schedules, policies, alerts and audit records
- **Identity layer** for agency single sign-on and Orrinwick's own workforce access
- **Operations tooling:** logging, monitoring, backup, deployment pipeline, secrets management

**Hosting model (fictional):** multi-tenant SaaS on a US public cloud, multi-AZ production in a primary region, with encrypted backups replicated to a second US region. Recovery is by backup and restore: no standing environment exists in the second region, and one is built on demand from infrastructure code (decision SD-003). Objectives for the fictional service are an 8 hour recovery time and a 4 hour recovery point. All production data stays in the United States.

**Third parties Beacon depends on (to be assessed in the scoping document):** a mobile push service, an email delivery service, and a telephony provider for SMS and voice.

---

## 4. Why FedRAMP 20x

Federal agencies may only use cloud services that meet FedRAMP requirements when those services handle federal information. Beacon handles two kinds of information that agencies treat as sensitive:

1. **Personal contact information** for federal employees and contractors (names, work email, work and personal mobile numbers, on-call schedules).
2. **Operational security information**: alert metadata and, in standard mode, short descriptions that reveal which agency systems have problems and when.

Orrinwick is targeting **FedRAMP 20x Class C**, the third of four certification classes, which the official rules describe as rising from minimal assurance (Class A) to significant assurance (Class D). The rules do not map classes to FIPS 199 impact levels, so Class C is a risk and business judgment. The second category, security-relevant operational detail about agency systems, warrants more than minimal assurance. *This is a preliminary position. The next documents identify the federal customer data in detail and assign security categories separately before the target class is confirmed.*

---

## 5. Open questions for the next step

| # | Question | Why it matters |
|---|---|---|
| 1 | Which telephony provider handles SMS and voice, and is it inside or outside the assessed offering? | Third-party information resources (`MAS-CSO-TPR`) |
| 2 | Is reference-only payload mode enough to keep alert content out of the notification channels entirely? | Shapes information flows and categorization |
| 3 | Do integrations ever send attachments or raw artifacts, and if so, do we reject them? | Beacon must not become a general data store |
| 4 | How are customer-supplied personal mobile numbers protected and who can see them? | Confidentiality of the most personal data class |
| 5 | What availability does a customer need from an alerting service, and what does failure cost them? | Availability impact reasoning |
| 6 | Does the mobile app cache alert content on devices? | Extends the information resources to endpoints we do not control |

---

## Next document

`federal-data-and-information-resources.md` records the federal customer data categories and the decision for each information resource.
