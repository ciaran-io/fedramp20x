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


@dataclass
class Env:
    """Everything a method may read. Swap fixtures for real collectors later."""

    company: dict
    iac: dict
    live: dict
    mas: dict = field(default_factory=dict)  # scope record (mas/mas-record.json), used by flow-aware checks
    grc: dict = field(default_factory=dict)  # GRC records (environment/grc-records.json): training, incidents, reviews

    def iac_resources(self, rtype: str) -> list[dict]:
        return [r for r in self.iac.get("resources", []) if r["type"] == rtype]


Method = Callable[[Env], MethodResult]


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
