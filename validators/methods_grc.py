"""Author-owned validation methods for GRC-type KSIs (stubs).

These ten KSIs are assigned to the project author. Each
KSI needs two automated methods (rule FRC-CSX-VVK, Class C):
  static - checks what the policy or configuration SAYS must happen
  live   - checks the records that show it DID happen

How to finish one stub:
  1. Fill in the matching data in environment/grc-records.json.
  2. Replace `raise NotImplementedError` with code. Copy the pattern of abo_static
     and abo_live in validators/methods.py. Use env.grc for the records.
  3. Add the two functions to KSI_METHODS in validators/registry.py.
  4. Run `make all` and read the result for your KSI in evidence/latest.json.

This module is not imported anywhere until you register a method, so the stubs
do not change any result.
"""
from __future__ import annotations

from .base import Env, MethodResult, result  # noqa: F401  (used once you write the methods)

STATIC, LIVE = "static", "live"


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

    Check to write: POL-INR requires an annual plan review, and ir_plan.review_cadence_days is 365 or less.
    Suggested method_id: "inr-rir-static"
    """
    raise NotImplementedError("Author to write: KSI-INR-RIR static")


def inr_rir_live(env: Env) -> MethodResult:
    """KSI-INR-RIR Reviewing Incident Response Procedures (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: ir_plan.last_reviewed is within review_cadence_days of as_of.
    Suggested method_id: "inr-rir-live"
    """
    raise NotImplementedError("Author to write: KSI-INR-RIR live")


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

    Check to write: environment/recovery-objectives.json defines rto_hours, rpo_hours and review_cadence_days, and POL-RPL requires an annual review.
    Suggested method_id: "rpl-rro-static"
    """
    raise NotImplementedError("Author to write: KSI-RPL-RRO static")


def rpl_rro_live(env: Env) -> MethodResult:
    """KSI-RPL-RRO Reviewing Recovery Objectives (live).

    Official statement: see FedRAMP/rules (after `make frmr`, also frmr/fedramp-consolidated-rules.json).

    Check to write: last_reviewed in recovery-objectives.json is within review_cadence_days of the as_of date.
    Suggested method_id: "rpl-rro-live"
    """
    raise NotImplementedError("Author to write: KSI-RPL-RRO live")
