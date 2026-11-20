# FedRAMP rules data

This folder holds no FedRAMP files in the repository. `make frmr` (run by `make all`) downloads two files from
https://github.com/FedRAMP/rules at one pinned commit and checks their SHA-256 hashes (see `tools/fetch_frmr.py`).
The downloaded files are listed in `.gitignore`.

- commit: 64fa769510416fa75fd00a4689466094265b8083 (2026-11-02)
- dataset version (info.version): 2026.11.02.01
- files: `fedramp-consolidated-rules.json`, `schemas/fedramp-consolidated-rules.schema.json`

Why: the upstream repository has no licence file, so this project does not republish its content.
The committed outputs keep rule and indicator IDs, names and counts. They do not copy statement text.
Read the official text at the upstream repository.
