"""Shared types and helpers for KSI validation methods.

A *method* is one automated check that persistently verifies a KSI. FRC-CSX-VVK
requires at least two automated methods per KSI for Class C, so the registry
tracks methods per KSI and the runner rolls them up.

Method kinds:
  static - evaluates declared state (IaC, policy-as-code, configuration files)
  live   - evaluates observed state (cloud/IdP/SIEM API collectors)

Using one static and one live method per KSI gives two independent signals and
lets the demo show *disagreement* (e.g., IaC says closed, live says open).
"""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field, asdict
from typing import Callable

PASS, FAIL, ERROR = "pass", "fail", "error"


@dataclass
class MethodResult:
    method_id: str
    kind: str  # "static" | "live"
    source: str  # which artifact/collector the data came from
    description: str
    status: str  # pass | fail | error
    expected: str
    observed: str
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


AS_OF_VARIABLE = "FEDRAMP20X_AS_OF"


def run_date() -> datetime.date:
    """The date the GRC checks measure record ages against.

    It is the real run date (UTC), so reviews go overdue as time passes. Tests and break tests
    can fix it with the FEDRAMP20X_AS_OF environment variable (YYYY-MM-DD) or by passing as_of to Env.
    """
    pinned = os.environ.get(AS_OF_VARIABLE)
    if pinned:
        return datetime.date.fromisoformat(pinned)
    return datetime.datetime.now(datetime.timezone.utc).date()


@dataclass
class Env:
    """Everything a method may read. Swap fixtures for real collectors later."""

    company: dict
    iac: dict
    live: dict
    mas: dict = field(default_factory=dict)  # scope record (mas/mas-record.json), used by flow-aware checks
    grc: dict = field(default_factory=dict)  # GRC records (environment/grc-records.json): training, incidents, reviews
    backup_jobs: dict = field(default_factory=dict)  # prefilled AWS Backup job history (environment/backup-jobs.json)
    as_of: datetime.date = field(default_factory=run_date)  # the date record ages are measured against

    def iac_resources(self, rtype: str) -> list[dict]:
        return [r for r in self.iac.get("resources", []) if r["type"] == rtype]


Method = Callable[[Env], MethodResult]


def source_findings(*sources: tuple[str, object, bool]) -> list[str]:
    """Findings for each source a method reads that is missing or empty (issue #44, FRC-CSX-VVK).

    A method that finds nothing to check has proved nothing, so it must fail, never pass.
    Give each source as (label, value, empty_allowed). Set empty_allowed to True only when the
    method's design says an empty list means there is nothing to check (for example no drift).
    A missing source (None) always gives a finding.
    """
    findings = []
    for label, value, empty_allowed in sources:
        if value is None:
            findings.append(f"Source is missing: {label}")
        elif not empty_allowed and not value:
            findings.append(f"Source is empty: {label}")
    return findings


def result(
    method_id: str,
    kind: str,
    source: str,
    description: str,
    expected: str,
    observed: str,
    findings: list[str],
) -> MethodResult:
    return MethodResult(
        method_id=method_id,
        kind=kind,
        source=source,
        description=description,
        status=FAIL if findings else PASS,
        expected=expected,
        observed=observed,
        findings=findings,
    )
