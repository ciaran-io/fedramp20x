"""Validation methods for my ten GRC-type KSIs.

Each KSI needs two automated methods (rule FRC-CSX-VVK, Class C):
  static - checks what the policy or configuration says must happen
  live   - checks the records that show it did happen

I write the design for each KSI in docs/validator-design/ first. A KSI counts
only after both methods are registered in validators/registry.py. Functions that
still raise NotImplementedError are not registered, so they change no result.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from .base import Env, MethodResult, result

STATIC, LIVE = "static", "live"

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str) -> dict:
    """Read a JSON file from the repository, by path relative to the repo root."""
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _covering_requirements(policy_id: str, ksi: str) -> list[dict]:
    """Return the requirements of one policy that list the KSI (short form, e.g. "INR-RIR")."""
    pol = next((p for p in _load("policies/policy-set.json")["policies"] if p["id"] == policy_id), None)
    if pol is None:
        return []
    return [r for r in pol.get("requirements", []) if ksi in r.get("ksis", [])]


def _age_days(date_text: str | None, as_of: datetime.date) -> int | None:
    """Days from a YYYY-MM-DD date to as_of. None when no date is recorded."""
    if not date_text:
        return None
    return (as_of - datetime.date.fromisoformat(date_text)).days


def _is_positive_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _policy(policy_id: str) -> dict | None:
    return next((p for p in _load("policies/policy-set.json")["policies"] if p["id"] == policy_id), None)


def _effective_pain(incident: dict) -> int | None:
    """The incident's PAIN rating. A reportable incident with no rating counts as N5 (IEC-CSO-DPR)."""
    rating = incident.get("pain_rating")
    if rating is None and incident.get("reportable") is True:
        return 5
    return rating


def _needs_after_action_report(incident: dict) -> bool:
    """POL-INR INR-2: every FedRAMP Reportable Incident, and every incident rated N2 or above."""
    rating = _effective_pain(incident)
    return incident.get("reportable") is True or (rating is not None and rating >= 2)


def ced_rat_static(env: Env) -> MethodResult:
    """KSI-CED-RAT Reviewing All Training (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-CED requires general, role-specific, secure delivery and incident or recovery training, with a review at least quarterly (read policies/policy-set.json).
    Suggested method_id: "ced-rat-static"
    """
    raise NotImplementedError("Author to write: KSI-CED-RAT static")


def ced_rat_live(env: Env) -> MethodResult:
    """KSI-CED-RAT Reviewing All Training (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: Every person in grc-records training.people has all four training dates within training.cadence_days of as_of, and an effectiveness review exists within the last 100 days.
    Suggested method_id: "ced-rat-live"
    """
    raise NotImplementedError("Author to write: KSI-CED-RAT live")


def inr_aar_static(env: Env) -> MethodResult:
    """KSI-INR-AAR Generating After Action Reports (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-INR requires an after action report within 10 business days for incidents of moderate severity or higher, and the incident response plan has an after action section.
    Suggested method_id: "inr-aar-static"
    """
    raise NotImplementedError("Author to write: KSI-INR-AAR static")


def inr_aar_live(env: Env) -> MethodResult:
    """KSI-INR-AAR Generating After Action Reports (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: Every closed incident of moderate severity or higher has aar_completed within 10 business days of closed, and lessons_incorporated is true.
    Suggested method_id: "inr-aar-live"
    """
    raise NotImplementedError("Author to write: KSI-INR-AAR live")


def inr_rir_static(env: Env) -> MethodResult:
    """KSI-INR-RIR Reviewing Incident Response Procedures (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check: POL-INR covers INR-RIR and names an owner, ir_plan.review_cadence_days is 365 or less, and the plan has no TODO lines.
    Suggested method_id: "inr-rir-static"
    """
    findings: list[str] = []
    if not _covering_requirements("POL-INR", "INR-RIR"):
        findings.append("No POL-INR requirement covers KSI INR-RIR")
    pol = _policy("POL-INR") or {}
    if not pol.get("owner"):
        findings.append("POL-INR names no owner for the plan review")
    plan = env.grc.get("ir_plan", {})
    cadence = plan.get("review_cadence_days")
    if not _is_positive_number(cadence) or cadence > 365:
        findings.append(f"ir_plan.review_cadence_days must be a positive number of 365 or less (found {cadence!r})")
    doc = plan.get("doc")
    if not doc or not (ROOT / doc).exists():
        findings.append(f"The incident response plan document is missing (found {doc!r})")
    else:
        todo = [n for n, line in enumerate((ROOT / doc).read_text(encoding="utf-8").splitlines(), 1) if "TODO" in line]
        if todo:
            findings.append(f"The incident response plan is not finished: TODO on line(s) {', '.join(map(str, todo))}")
    return result("inr-rir-static", STATIC, "environment/grc-records.json#ir_plan",
                  "POL-INR requires a plan review with a named owner, the cadence is 365 days or less, and the plan is written",
                  "POL-INR covers INR-RIR; owner named; cadence <= 365 days; plan with no TODO", f"{len(findings)} gap(s)", findings)

def inr_rir_live(env: Env) -> MethodResult:
    """KSI-INR-RIR Reviewing Incident Response Procedures (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check: ir_plan.last_reviewed is inside the cadence, reviewed_by matches the POL-INR owner, and the review follows every report or review with plan_change_required.
    Suggested method_id: "inr-rir-live"
    """
    findings: list[str] = []
    plan = env.grc.get("ir_plan", {})
    cadence = plan.get("review_cadence_days")
    as_of = datetime.date.fromisoformat(env.grc["as_of"])
    last = plan.get("last_reviewed")
    age = _age_days(last, as_of)
    if age is None:
        findings.append("No review of the incident response plan is recorded")
    elif age < 0:
        findings.append(f"ir_plan.last_reviewed {last} is after the as_of date {as_of}")
    elif _is_positive_number(cadence) and age > cadence:
        findings.append(f"Last plan review was {age} days ago, cadence is {cadence} days")
    owner = (_policy("POL-INR") or {}).get("owner")
    if last and plan.get("reviewed_by") != owner:
        findings.append(f"The plan review was recorded by {plan.get('reviewed_by')!r}, POL-INR names {owner!r}")
    for inc in env.grc.get("incidents", []):
        if inc.get("plan_change_required") is True and inc.get("aar_completed") and (not last or last < inc["aar_completed"]):
            findings.append(f"After action report for {inc['id']} on {inc['aar_completed']} requires a plan change, and no plan review follows it")
    for rev in env.grc.get("incident_pattern_reviews", []):
        if rev.get("plan_change_required") is True and rev.get("date") and (not last or last < rev["date"]):
            findings.append(f"Incident pattern review on {rev['date']} requires a plan change, and no plan review follows it")
    return result("inr-rir-live", LIVE, "environment/grc-records.json#ir_plan",
                  "The plan was reviewed by its owner inside the cadence, and after every report or review that required a plan change",
                  f"<= {cadence} days; reviewed by {owner}; review after each required change", f"{age} days" if age is not None else "no review recorded", findings)

def inr_rpi_static(env: Env) -> MethodResult:
    """KSI-INR-RPI Reviewing Past Incidents (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-INR requires a quarterly review of past incidents.
    Suggested method_id: "inr-rpi-static"
    """
    raise NotImplementedError("Author to write: KSI-INR-RPI static")


def inr_rpi_live(env: Env) -> MethodResult:
    """KSI-INR-RPI Reviewing Past Incidents (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: The newest incident_pattern_reviews date is within 100 days of as_of.
    Suggested method_id: "inr-rpi-live"
    """
    raise NotImplementedError("Author to write: KSI-INR-RPI live")


def piy_res_static(env: Env) -> MethodResult:
    """KSI-PIY-RES Reviewing Executive Support (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-PIY requires a quarterly, minuted executive security review.
    Suggested method_id: "piy-res-static"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RES static")


def piy_res_live(env: Env) -> MethodResult:
    """KSI-PIY-RES Reviewing Executive Support (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: The newest exec_reviews date is within 100 days of as_of and has a minutes_ref.
    Suggested method_id: "piy-res-live"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RES live")


def piy_ris_static(env: Env) -> MethodResult:
    """KSI-PIY-RIS Reviewing Investments in Security (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-PIY requires an annual review of security spending against the risk register.
    Suggested method_id: "piy-ris-static"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RIS static")


def piy_ris_live(env: Env) -> MethodResult:
    """KSI-PIY-RIS Reviewing Investments in Security (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: The newest security_investment_reviews date is within 365 days of as_of.
    Suggested method_id: "piy-ris-live"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RIS live")


def piy_rvd_static(env: Env) -> MethodResult:
    """KSI-PIY-RVD Reviewing Vulnerability Disclosures (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: A disclosure policy URL and inbox are set, and the target response time is stated and matches POL-PIY.
    Suggested method_id: "piy-rvd-static"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RVD static")


def piy_rvd_live(env: Env) -> MethodResult:
    """KSI-PIY-RVD Reviewing Vulnerability Disclosures (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: Every report in vulnerability_disclosure.reports got a first response within response_target_business_days, and last_program_review is within 365 days.
    Suggested method_id: "piy-rvd-live"
    """
    raise NotImplementedError("Author to write: KSI-PIY-RVD live")


def cmt_rvp_static(env: Env) -> MethodResult:
    """KSI-CMT-RVP Reviewing Change Procedures (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-CMT requires an annual review of the change procedure and a review after a failed or emergency change.
    Suggested method_id: "cmt-rvp-static"
    """
    raise NotImplementedError("Author to write: KSI-CMT-RVP static")


def cmt_rvp_live(env: Env) -> MethodResult:
    """KSI-CMT-RVP Reviewing Change Procedures (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: change_procedure.last_reviewed is within review_cadence_days of as_of and later than every failed_or_emergency_changes date.
    Suggested method_id: "cmt-rvp-live"
    """
    raise NotImplementedError("Author to write: KSI-CMT-RVP live")


def cna_rvp_static(env: Env) -> MethodResult:
    """KSI-CNA-RVP Reviewing Protections (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: POL-CNA requires an annual review of protections.
    Suggested method_id: "cna-rvp-static"
    """
    raise NotImplementedError("Author to write: KSI-CNA-RVP static")


def cna_rvp_live(env: Env) -> MethodResult:
    """KSI-CNA-RVP Reviewing Protections (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: The newest protection_reviews date is within 365 days of as_of.
    Suggested method_id: "cna-rvp-live"
    """
    raise NotImplementedError("Author to write: KSI-CNA-RVP live")


def rpl_rro_static(env: Env) -> MethodResult:
    """KSI-RPL-RRO Reviewing Recovery Objectives (static).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: environment/recovery-objectives.json defines rto_hours, rpo_hours and review_cadence_days, and a POL-RPL requirement covers RPL-RRO.
    Suggested method_id: "rpl-rro-static"
    """
    findings: list[str] = []
    obj = _load("environment/recovery-objectives.json")
    for key in ("rto_hours", "rpo_hours", "review_cadence_days"):
        value = obj.get(key)
        if not isinstance(value, (int, float)) or value <= 0:
            findings.append(f"{key} is missing or not a positive number (found {value!r})")
    policies = _load("policies/policy-set.json")["policies"]
    pol = next((p for p in policies if p["id"] == "POL-RPL"), None)
    if pol is None:
        findings.append("POL-RPL is missing from policies/policy-set.json")
    elif not any("RPL-RRO" in req.get("ksis", []) for req in pol.get("requirements", [])):
        findings.append("No POL-RPL requirement covers KSI RPL-RRO")
    return result("rpl-rro-static", STATIC, "environment/recovery-objectives.json",
                  "Recovery time, recovery point and review cadence are defined, and policy POL-RPL requires the review",
                  "RTO, RPO and cadence set; POL-RPL covers RPL-RRO", f"{len(findings)} gap(s)", findings)


def rpl_rro_live(env: Env) -> MethodResult:
    """KSI-RPL-RRO Reviewing Recovery Objectives (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: last_reviewed in recovery-objectives.json is within review_cadence_days of the as_of date.
    Suggested method_id: "rpl-rro-live"
    """
    findings: list[str] = []
    obj = _load("environment/recovery-objectives.json")
    cadence = obj.get("review_cadence_days")
    as_of = datetime.date.fromisoformat(env.grc["as_of"])
    last = obj.get("last_reviewed")
    age = None
    if not last:
        findings.append("No last_reviewed date is recorded")
    else:
        age = (as_of - datetime.date.fromisoformat(last)).days
        if age < 0:
            findings.append(f"last_reviewed {last} is after the as_of date {as_of}")
        elif isinstance(cadence, (int, float)) and age > cadence:
            findings.append(f"Last review was {age} days ago, cadence is {cadence} days")
    return result("rpl-rro-live", LIVE, "environment/recovery-objectives.json",
                  "The last review of the recovery objectives is inside the review cadence",
                  f"<= {cadence} days since last review", f"{age} days" if age is not None else "no review recorded", findings)
