# Validator design

> FICTIONAL DEMO PROJECT. Orrinwick Labs, Inc. and Orrinwick Beacon are invented.

Each file in this folder records the validation design for one KSI theme in Class C. A design states what a KSI requires, how the two automated methods test it (rule FRC-CSX-VVK), how a method fails, and where a method proves less than the official statement.

FedRAMP statement text is not copied into this repository. Each design describes the requirement in my own words and cites the KSI ID. Read the official statement in [FedRAMP/rules](https://github.com/FedRAMP/rules) or in `frmr/fedramp-consolidated-rules.json` after a build.

## Themes

| Theme | KSIs | File |
|---|---|---|
| CED | 1 | Not started |
| CMT | 4 | Not started |
| CNA | 8 | Not started |
| IAM | 6 | Not started |
| INR | 3 | Not started |
| MLA | 5 | Not started |
| PIY | 5 | Not started |
| RPL | 4 | Not started |
| SCR | 2 | Not started |
| SVC | 8 | Not started |

## Validation cadence

| Resource type | Minimum frequency | Rule |
|---|---|---|
| Machine-based (cloud, network, identity configuration) | Every 3 days | VDR-TFR-MVX |
| Non-machine (people, process, records) | Every 3 months | VDR-TFR-NMV |

## Design template

```markdown
## KSI-XXX-YYY Name

| Field | Design |
|---|---|
| Requirement | The requirement in my own words |
| Policy requirement | Policy ID and requirement ID from policies/policy-set.json |
| Resource type | Machine-based or non-machine |
| Validation cadence | Frequency and rule ID |
| Static method | Method ID, source file and pass condition |
| Live method | Method ID, source file and pass condition |
| Fails when | The conditions that produce a finding |
| Break test | The change that makes a method fail, and the observed finding |
| Production source | The system or API a real provider would query |
| Gap | Where the methods prove less than the official statement |
| Status | Designed, Built or Verified |
```

## Status

| Status | Meaning |
|---|---|
| Designed | The design is written. No method exists yet |
| Built | Both methods exist and are registered in `validators/registry.py` |
| Verified | A break test made each method fail, and the result is recorded in the design |
