# Secure Configuration Guide (agency-facing)

> FICTIONAL DEMO DOCUMENT. Orrinwick Labs, Inc. is invented. Nothing here is a real security record or FedRAMP certification.

| | |
|---|---|
| Audience | Agency administrators of Orrinwick Beacon |
| Status | Outline. Author to write each section |
| Rules | `SCG-CSO-RSC`, `SCG-CSO-AUP`, `SCG-CSO-PUB`, `SCG-CSO-SDF`, `SCG-ENH-*` |

Rule `SCG-CSO-RSC` requires recommendations for securely configuring the service. Write each section as an instruction an agency administrator can follow.

## 1. Sign-in and single sign-on
1. Enforce single sign-on with a phishing-resistant factor for all agency users.
2. TODO (author): where the setting is, the recommended value and the risk of the default.

## 2. Roles and permissions
TODO (author): the administrator, responder and read-only roles, and which permissions each one holds.

## 3. API and webhook access
1. Restrict API access to agency egress ranges.
2. TODO (author): token lifetime, rotation and scopes.

## 4. Notification content
TODO (author): the reference-only payload mode (alert summaries never travel in push, email, SMS or voice) and how to enable it.

## 5. Audit trail and export
1. Enable audit export to your SIEM.
2. TODO (author): retention settings and export format.

## 6. Recommended defaults (`SCG-CSO-SDF`)
TODO (author): a table of every security setting, its default and the recommended value.

## 7. Access to this guide (`SCG-CSO-AUP`, `SCG-CSO-PUB`)
TODO (author): how an agency obtains and uses the guide, and whether it is public.
