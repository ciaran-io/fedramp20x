# FedRAMP 20x Class C: a worked example

> **FICTIONAL.** Orrinwick Labs, Inc. and the Orrinwick Beacon product are invented. All environment data is made up and the validator outputs are simulated. This is a learning and portfolio project. It is **not** a FedRAMP certification, assessment or advice, and a passing check here is not proof of compliance.

This repository shows how a small, invented SaaS company could meet FedRAMP 20x Class C. It combines:

- the **official FedRAMP rules and Key Security Indicators (KSIs)**, read from FedRAMP's public data, which `make frmr` downloads at a pinned commit (the data is not stored in this repository)
- a **scope record** (the Minimum Assessment Scope) written as JSON, with documents and diagrams generated from it
- **validator results** (JSON files) from real checks run against the fictional data, which show what continuous validation results could look like
- a set of **documents** a provider would maintain, including ten policies that map to all 46 KSIs
- a **trust center** that reads the JSON from this repository and displays the current posture

## What this shows

[![ci](https://github.com/ciaran-io/fedramp20x/actions/workflows/ci.yml/badge.svg)](https://github.com/ciaran-io/fedramp20x/actions/workflows/ci.yml) [![scheduled-validation](https://github.com/ciaran-io/fedramp20x/actions/workflows/scheduled-validation.yml/badge.svg)](https://github.com/ciaran-io/fedramp20x/actions/workflows/scheduled-validation.yml)

- **Scoping.** A Minimum Assessment Scope written as one JSON record, with every information resource, third party and data flow identified (MAS-CSO-IIR, MAS-CSO-FLO, MAS-CSO-TPR). Documents and diagrams are generated from it, and CI fails when they drift. See [`mas/mas-record.json`](mas/mas-record.json) and [`docs/minimum-assessment-scope.md`](docs/minimum-assessment-scope.md).
- **KSI validation.** Each of the 46 Class C KSIs is checked by at least two automated methods (FRC-CSX-VVK): a static check of what is declared and a live check of what the records show. See [`validators/registry.py`](validators/registry.py).
- **Persistent validation.** The validators run every day and commit dated evidence, which meets the 3-day and 3-month validation rules (VDR-TFR-MVX, VDR-TFR-NMV) and builds the history the Security Decision Record needs. See [Persistent validation](#persistent-validation) and [`evidence/history/`](evidence/history/).
- **Design reviews against policy.** Each check has a written design that states what it proves and where it falls short of the KSI. My review of RPL-ABO found two checks that were weaker than the policy, and I fixed both. See [`docs/validator-design/`](docs/validator-design/).
- **Trust center and the certification package.** A trust center with access logging and an access inventory (CDS rules), and an example FedRAMP Certification Package as the end goal. See [Trust center](#trust-center) and the [Roadmap](#roadmap).

The latest result for every KSI is in [`evidence/latest.json`](evidence/latest.json). The scheduled run updates it every day.
## Trust center

The trust center shows the validator results for the fictional service. It reads `evidence/latest.json` from this repository.

![Trust center overview](docs/images/trust-center-overview.png)

Open [`trust-center/index.html`](trust-center/index.html) in a browser for the full page. The page and its data are fictional.

## The fictional company

**Orrinwick Beacon** is a cloud service that receives security alerts from an agency's tools, decides who should act, reaches that person (app push, email, SMS, voice), and keeps an audit trail. It holds federal employee contact details and alert information, which is why the company is going through FedRAMP. Read [`docs/company-and-offering.md`](docs/company-and-offering.md) first.

## System description

> **This system is fictional.** Orrinwick Labs, Inc. does not exist, and neither does the Orrinwick Beacon service. The description, diagrams and numbers below are written for this learning project.

Orrinwick Beacon is a multi-tenant SaaS service that routes security alerts for US federal agencies. An agency connects its monitoring tools to Beacon. Beacon receives each alert over HTTPS, applies the agency's on-call rules, and notifies the right responder by app push, email, SMS or voice. It records each step in an audit trail. Agency staff use a web console and a mobile app to manage tenants, schedules and escalation rules.

- **Hosting:** one production cloud account in `us-east-1`, across two availability zones. Compute runs as containers, data sits in a managed relational database and object storage. All of it is built from Terraform and deployed by a CI pipeline.
- **Recovery:** backup and restore. A backup service takes recovery points every 2 hours and copies them to a locked vault in `us-west-2`. No standing environment exists there; a recovery module builds one on demand. Objectives: RTO 8 hours, RPO 4 hours.
- **Third parties:** push, email, SMS and voice delivery providers, plus hosted tools for the identity provider, endpoint protection and source control. They are listed in the scope record with their authorization status.
- **Federal customer data:** responder contact details and alert content. The scope record classifies each data class and traces every flow (F01 to F44).

The three diagrams below come from the scope record and the pretend Terraform plan. Run `make mas` to regenerate them. Editable `.drawio` sources are in `docs/diagrams/`.

### Alert path (information flows)

![Alert path through the Beacon service](docs/diagrams/mas-alert-path.svg)

### Network architecture

![Network architecture of the fictional environment](docs/diagrams/network-architecture.svg)

### Authorization boundary

![Authorization boundary and trust zones](docs/diagrams/mas-boundary.svg)

## Persistent validation

FedRAMP 20x expects a provider to keep validating its KSIs and to show the results over time. At Class C, machine-based resources must be validated at least every 3 days (VDR-TFR-MVX) and non-machine resources at least every 3 months (VDR-TFR-NMV). This project copies that with `.github/workflows/scheduled-validation.yml`. It runs every day at 06:17 UTC, and anyone with write access can also start it from the Actions tab. Each run does the following:

1. GitHub starts a short-lived Linux machine.
2. It downloads the repository and the FedRAMP rules data.
3. It runs the same checks as CI: the rules data schema, the unit tests and `make all`, which runs every KSI validator against the fictional environment.
4. It writes the results to `evidence/latest.json`, adds a file for the day in `evidence/history/` and rebuilds the trust center page.
5. It commits those files to `main` with the date and the result counts, for example `Scheduled validation 2026-11-21: 35 pass, 2 fail, 0 partial, 9 not implemented`.

The daily history files are the source for the historical KSI metrics that the Security Decision Record needs (SDR-CSX-KMT). The environment is fictional, so most runs give the same results. For a real provider, the live methods would call the cloud and system APIs, and a daily run would find drift such as an expired key or a backup that stopped.

## Automatic checks on GitHub

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request. It does not use any cloud account. It checks the FedRAMP data against its schema, runs the unit tests, validates the scope record and rebuilds everything. A green tick next to a commit means the JSON is valid and consistent.

## Honest status model

Each KSI is rolled up as `pass` (two or more automated methods, all passing, no known gap), `fail`, `partial` (passing but fewer than two methods or a known gap against the official statement) or `not_implemented`. Nothing passes by default. Class C requires at least two automated methods per KSI (rule `FRC-CSX-VVK`). Current counts are in [`evidence/latest.json`](evidence/latest.json).

## What is real and what is not

| Piece | Status |
|---|---|
| KSI text, class variants, rules | Real: downloaded from [FedRAMP/rules](https://github.com/FedRAMP/rules) at a pinned commit and schema-checked by `make check`. Outputs keep IDs and names only; read the statement text upstream |
| Check logic | My interpretation of each KSI. My design for each check, and where it proves less than the official statement, is in [`docs/validator-design/`](docs/validator-design/). Read the official statement in FedRAMP/rules before trusting a check. Where a check is narrower than the official statement, `validators/registry.py` records a coverage note (shown on the indicator). A known gap in the same file holds a KSI at `partial` |
| Environment data | Fictional. The validators read simulated files, not a real cloud account |
| Validator output and history | Generated from the fictional data. History starts at the first run and grows with each run |
| Documents | Written for the fictional company. `TODO` marks sections still to be written |
| Cloud platform | AWS and Terraform are a design assumption for the fictional company. The scope record itself is vendor-neutral |

## How this project was built

An AI assistant (Claude) wrote much of the scaffolding and drafts the validator designs and the check code. I make the scope decisions, write the policies, decide what each KSI check must prove, and review, correct and test every design and check before I commit it. The design reviews are where my judgement shows: for example, my review of RPL-ABO found two checks that were weaker than the policy.

## Roadmap

1. Move access control from the demo (browser storage or Claude sign-in) to a real server.
2. Build the checks for my remaining nine GRC KSIs.
3. Write the validator design for all 46 KSIs in `docs/validator-design/` and close the gaps the reviews find.
4. Write the remaining documents: incident response plan, cryptographic modules, significant change log and secure configuration guide. Rewrite the vulnerability report and publish it as JSON.
5. Assemble an example FedRAMP Certification Package, the final submission to FedRAMP (FRC-CSO-PKG). It has three parts, each in Markdown and in JSON that validates against FedRAMP's published schema (FRC-CSO-JSN):
   - **Certification Package Overview** (CPO-CSO-OVR): metadata and the accountable official (CPO-CSO-MTD), public information and service list (CDS-CSO-PUB, CDS-CSO-SVC), relevant policies (CDS-CSO-IRP), the scope (MAS-CSO-IIR, MAS-CSO-FLO, MAS-CSO-TPR), cryptographic modules (CMU-CSO-CMD) and the independent assessment results (IVV-CSO-ICP, CPO-CSO-OSA).
   - **Security Decision Record** (SDR-CSO-FRR): for each applicable rule, how it is met, its verification, validation and artifacts, plus a summary (SDR-CSX-KSI) and historical metrics (SDR-CSX-KMT) for each KSI.
   - **An example Ongoing Certification Report** (CCM-OCR-AVL).

   A real package needs an independent assessment by a FedRAMP Recognized assessor within the previous 3 months (FRC-APP-FIA). This project includes only a labelled, empty template for the assessor's summary. A check will confirm that the package reflects validation within the previous 7 days (FRC-APP-FCP) and is updated at least every 2 weeks (CPO-CSX-CPM). The Marketplace listing (FRC-APP-MLF) and the application form (FRC-APP-AFC) are real-world steps and are out of scope.

## Visibility

This repository is public. Every document in it is readable by anyone, so the trust center's access gate is a demonstration only. GitHub Pages is not used. `trust-center/index.html` is a snapshot of the trust center as one HTML file. Download it and open it in a browser.

## Folder guide

| Folder | What is in it | Edit by hand? |
|---|---|---|
| `docs/` | The written documents: company overview, data and resource inventory, scope document, security decision record, templates. `docs/diagrams/` holds the diagrams (`.drawio` files open in diagrams.net) | Yes, except `minimum-assessment-scope.md`, `rules-matrix.md`, `policies-index.md` and `policies/`, which are generated |
| `policies/` | `policy-set.json`: the ten policies, one per KSI theme. `make policies` renders `docs/policies/` and `docs/policies-index.md` from it | Yes (this is the file to edit) |
| `mas/` | `mas-record.json`: the scope record. This is the source of truth for scope, data flows and open decisions | Yes (this is the file to edit) |
| `environment/` | The fictional company's data: company facts, recovery objectives, a pretend Terraform plan and a pretend live-state snapshot. Every resource names the scope-record ID it implements | Yes |
| `validators/` | The check logic for each KSI (Python) | Yes |
| `tools/` | Scripts that build everything else | Yes |
| `evidence/` | Generated JSON: the KSI registry, the latest validation result, scope summary, and a day-by-day history written by each run | No, generated |
| `frmr/` | Where `make frmr` downloads FedRAMP's rules data. Nothing from FedRAMP is committed. See `frmr/PROVENANCE.md` | No |
| `schemas/` | JSON Schemas that the project's own JSON files must follow | Rarely |
| `trust-center/` | The trust center. `src/page.html` is the page source. `index.html` is generated from it as one self-contained file (open it in a browser). The page reads `evidence/latest.json` from this repository when it can reach it, and otherwise shows the data embedded in the snapshot. `brand/` holds the logo | `src/page.html` yes |
| `.github/workflows/` | Automatic checks that run on GitHub | Rarely |

## How the pieces connect

Each row reads left to right: the source files, the script that reads them, and the files it creates.

| Source | Script | Output |
|---|---|---|
| Downloaded FedRAMP rules (`frmr/`) | `tools/build_registry.py` | `evidence/ksi-registry.json` |
| `mas/mas-record.json` | `tools/build_mas.py` | `docs/minimum-assessment-scope.md`, diagrams, `evidence/mas-summary.json` |
| `policies/policy-set.json` | `tools/build_policies.py` | `docs/policies/`, `docs/policies-index.md` |
| `environment/`, `mas/`, `validators/` | `tools/check_environment.py` | A pass or fail on whether the fictional environment matches the scope record |
| `environment/`, `mas/`, `validators/` | `tools/run_validators.py` | `evidence/latest.json` (validation result for the fictional data) |
| All of the above | `tools/build_trust_center.py` | `trust-center/index.html` |

Edit the source files, run `make all`, and every generated file is refreshed.

## Running it on your own computer

You need Python 3.10 or newer and an internet connection. The first run downloads FedRAMP's rules data from GitHub (`make frmr`).

```bash
pip install jsonschema
make all      # downloads the FedRAMP data, validates the scope record and rebuilds all generated files
make test     # runs the unit tests
make serve    # previews the trust center at http://localhost:8000
```

**Windows.** Windows does not include `make`. Run `build.ps1` from the repository folder instead. It runs the same steps as `make all`, then the unit tests, and stops at the first step that fails:

```powershell
pip install jsonschema
.\build.ps1          # build and test
.\build.ps1 -NoTest  # build only
```

If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. If you run the Python scripts yourself, set `$env:PYTHONUTF8 = "1"` first. Some scripts read files without naming UTF-8, and Windows then fails on characters such as curly quotes. `build.ps1` sets this for you. You can also install `make` (for example `winget install GnuWin32.Make`) or use WSL.

Then open `trust-center/index.html` in a browser.

## License

The code and documents written for this project use the MIT license (see `LICENSE`). FedRAMP's data is not in this repository. `make frmr` downloads it because upstream has no license file (see `frmr/PROVENANCE.md`).

## Updating the FedRAMP data

Change `COMMIT` and the two hashes in `tools/fetch_frmr.py`, update `frmr/PROVENANCE.md`, run `make check all`, and review the diff in `evidence/ksi-registry.json`.
