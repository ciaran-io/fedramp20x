"""Validation methods for logging, inventory, SDLC, recovery testing and supply chain KSIs (batch B).

Static methods read environment/iac-plan.json. Live methods read environment/live-state.json
and, for the inventory check, the scope record. Known gaps are in validators/registry.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import Env, MethodResult, result, source_findings

STATIC, LIVE = "static", "live"
IAC, LIVE_SRC = "environment/iac-plan.json", "environment/live-state.json"


def _one(env: Env, rtype: str) -> dict:
    found = env.iac_resources(rtype)
    return found[0]["values"] if found else {}


def _objectives() -> dict:
    return json.loads((Path(__file__).resolve().parent.parent / "environment/recovery-objectives.json").read_text())


def _r(mid, kind, src, desc, expected, findings, observed=None):
    return result(mid, kind, src, desc, expected, observed if observed is not None else f"{len(findings)} finding(s)", findings)


# ---- KSI-MLA-ALA  Authorizing Log Access ---------------------------------------
def ala_static(env: Env) -> MethodResult:
    p, f = _one(env, "log_access_policy"), []
    if not p:
        f.append("No log access policy is declared")
    if p.get("raw_log_access") != "just_in_time":
        f.append("Raw log access is not just-in-time")
    if p.get("max_grant_hours", 999) > 8:
        f.append("Access grants last over 8 hours")
    if not p.get("sensitive_fields_masked"):
        f.append("Sensitive log fields are not masked")
    if p.get("review_cadence_days", 999) > 30:
        f.append("Log access is reviewed less often than monthly")
    return _r("ala-iac-log-access-model", STATIC, IAC, "Log access is role-based, just-in-time for raw logs, masked and reviewed monthly", "JIT, <= 8h, masked, monthly review", f)


def ala_live(env: Env) -> MethodResult:
    a, f = env.live["log_access"], []
    f += [f"Standing raw log access for {x}" for x in a["raw_log_standing_access"]]
    if a["unmasked_sensitive_reads"]:
        f.append(f"{a['unmasked_sensitive_reads']} unmasked sensitive read(s)")
    if a["last_access_review_days_ago"] > 30:
        f.append(f"Last access review was {a['last_access_review_days_ago']} days ago")
    f += [f"Grant {g['id']} lasted {g['duration_hours']}h" for g in a["grants_last_90d"] if g.get("duration_hours", 0) > 8]
    return _r("ala-live-log-access-grants", LIVE, LIVE_SRC + "#log_access", "No standing raw log access, no unmasked reads and a review in the last 30 days", "0 standing, review <= 30d", f)


# ---- KSI-MLA-EVC  Evaluating Configurations ------------------------------------
def evc_static(env: Env) -> MethodResult:
    p, f = _one(env, "iac_evaluation"), []
    if not p.get("policy_as_code"):
        f.append("No policy-as-code checks on IaC")
    if not p.get("run_on_pull_request"):
        f.append("IaC checks do not run on pull requests")
    if not p.get("blocking"):
        f.append("IaC check failures do not block merge")
    if p.get("scheduled_scan_days", 999) > 1:
        f.append("No daily scheduled scan")
    return _r("evc-iac-config-testing", STATIC, IAC, "IaC is tested on every pull request and scanned daily, and failures block merge", "policy-as-code, PR checks, blocking, daily", f)


def evc_live(env: Env) -> MethodResult:
    e, f = env.live["iac_evaluation"], []
    if e["last_scan_age_hours"] > 24:
        f.append(f"Last scan is {e['last_scan_age_hours']}h old")
    if e["prs_with_checks"] < e["prs_merged_30d"]:
        f.append(f"{e['prs_merged_30d'] - e['prs_with_checks']} merged pull request(s) skipped checks")
    f += [f"Open high finding: {x}" for x in e["findings"]]
    return _r("evc-live-scan-results", LIVE, LIVE_SRC + "#iac_evaluation", "Scans are fresh, every merge was checked and no high finding is open", "scan <= 24h, 100% checked, 0 high", f)


# ---- KSI-MLA-OSM  Operating SIEM Capability ------------------------------------
def osm_static(env: Env) -> MethodResult:
    s, f = _one(env, "siem_config"), []
    if not s.get("centralized"):
        f.append("Logging is not centralized")
    if not s.get("tamper_protection"):
        f.append("No tamper protection on the log store")
    if s.get("retention_days", 0) < 365:
        f.append("Log retention is under 365 days")
    for need in ("cloudtrail", "idp", "pipeline", "app"):
        if need not in s.get("sources", []):
            f.append(f"SIEM does not declare source '{need}'")
    return _r("osm-iac-siem-config", STATIC, IAC, "A central, tamper-resistant log store with 12 months of retention and core sources", "central, tamper protection, >= 365d", f)


def osm_live(env: Env) -> MethodResult:
    s, f = env.live["siem"], []
    f += [f"Source '{x}' is not reporting" for x in s["sources_expected"] if x not in s["sources_reporting"]]
    if s["last_event_age_minutes"] > 15:
        f.append(f"Latest event is {s['last_event_age_minutes']} min old")
    if not s["object_lock_enabled"]:
        f.append("Object lock is off on the log store")
    if s["tamper_events_90d"]:
        f.append(f"{s['tamper_events_90d']} tamper event(s) in 90 days")
    return _r("osm-live-siem-health", LIVE, LIVE_SRC + "#siem", "All expected sources report, events are fresh and the store is locked", "all sources, <= 15 min, lock on", f)


# ---- KSI-MLA-RVL  Reviewing Logs -----------------------------------------------
def rvl_static(env: Env) -> MethodResult:
    p, f = _one(env, "log_review_process"), []
    if not p.get("automated_detections"):
        f.append("No automated detections")
    if p.get("triage_sla_minutes", 999) > 60:
        f.append("Triage target is over 60 minutes")
    if p.get("review_cadence_days", 999) > 7:
        f.append("Log review is less often than weekly")
    return _r("rvl-iac-review-process", STATIC, IAC, "Automated detections with a 60 minute triage target and a weekly review", "detections, <= 60 min, weekly", f)


def rvl_live(env: Env) -> MethodResult:
    r, f = env.live["log_review"], []
    if r["last_review_days_ago"] > 7:
        f.append(f"Last log review was {r['last_review_days_ago']} days ago")
    if r["triaged_within_sla"] < r["alerts_30d"]:
        f.append(f"{r['alerts_30d'] - r['triaged_within_sla']} of {r['alerts_30d']} alerts missed the triage target")
    if r["detections_failing"]:
        f.append(f"{r['detections_failing']} detection rule(s) are failing")
    return _r("rvl-live-review-activity", LIVE, LIVE_SRC + "#log_review", "Logs were reviewed this week, alerts met the triage target and detections run", "review <= 7d, 100% triaged, 0 failing", f)


# ---- KSI-PIY-GIV  Generating Inventories ---------------------------------------
def giv_static(env: Env) -> MethodResult:
    g, f = _one(env, "inventory_generator"), []
    if len(g.get("authoritative_sources", [])) < 2:
        f.append("Inventory uses fewer than 2 authoritative sources")
    if g.get("refresh_minutes", 9999) > 60:
        f.append("Inventory refreshes less often than hourly")
    if not g.get("requires_scope_id_tag"):
        f.append("Resources are not required to carry a scope ID")
    return _r("giv-iac-inventory-generator", STATIC, IAC, "The inventory is generated from authoritative sources every hour and ties to scope IDs", ">= 2 sources, <= 60 min, scope ID tag", f)


def giv_live(env: Env) -> MethodResult:
    """Flag live resources that carry no scope ID or name an ID the scope record does not hold (plan task 1.4)."""
    known = {r["id"] for r in env.mas.get("information_resources", [])}
    live = [r for k in ("security_groups", "ebs_volumes", "s3_buckets", "rds_instances", "sqs_queues", "compute") for r in env.live.get(k) or []]
    f = source_findings(("mas/mas-record.json#information_resources", env.mas.get("information_resources"), False),
                        ("cloud resources in environment/live-state.json", live, False))
    for kind, key in (("Security group", "security_groups"), ("Volume", "ebs_volumes"), ("Bucket", "s3_buckets"), ("Database", "rds_instances"), ("Queue", "sqs_queues")):
        for r in env.live.get(key, []):
            label = r.get("name") or r.get("id")
            if not r.get("scope"):
                f.append(f"{kind} '{label}' has no scope ID")
            elif r["scope"] not in known:
                f.append(f"{kind} '{label}' names scope ID {r['scope']}, which is not in the scope record")
    f += [f"Compute '{c['id']}' has no scope ID" for c in env.live.get("compute", []) if not c.get("scope")]
    return _r("giv-live-unscoped-resources", LIVE, LIVE_SRC, "Every live resource carries a scope ID that exists in the scope record", "0 unscoped resources", f)


# ---- KSI-PIY-RSD  Reviewing Security in the SDLC -------------------------------
def rsd_static(env: Env) -> MethodResult:
    p, f = _one(env, "sdlc_review"), []
    if p.get("review_cadence_days", 999) > 90:
        f.append("SDLC review is less often than quarterly")
    if len(p.get("secure_by_design_principles", [])) < 3:
        f.append("Fewer than 3 secure-by-design principles are defined")
    for k, label in (("threat_model_required", "Threat modeling"), ("sast_required", "Static analysis"), ("dependency_scan_required", "Dependency scanning")):
        if not p.get(k):
            f.append(f"{label} is not required")
    return _r("rsd-iac-sdlc-policy", STATIC, IAC, "A quarterly SDLC review with secure-by-design principles, threat models, SAST and dependency scans", "quarterly, >= 3 principles, 3 gates", f)


def rsd_live(env: Env) -> MethodResult:
    s, f = env.live["sdlc"], []
    if s["last_review_days_ago"] > 90:
        f.append(f"Last SDLC review was {s['last_review_days_ago']} days ago")
    if s["threat_models_new_features_pct"] < 90:
        f.append(f"Only {s['threat_models_new_features_pct']}% of new features have a threat model (target 90%)")
    if s["secure_by_design_exceptions_open"]:
        f.append(f"{s['secure_by_design_exceptions_open']} secure-by-design exception(s) are open")
    if s["sast_critical_open"] or s["dependency_critical_open"]:
        f.append(f"Critical findings open: {s['sast_critical_open']} static, {s['dependency_critical_open']} dependency")
    return _r("rsd-live-sdlc-metrics", LIVE, LIVE_SRC + "#sdlc", "The SDLC was reviewed this quarter, threat models cover 90% of features and no critical finding is open", "review <= 90d, >= 90%, 0 critical", f)


# ---- KSI-RPL-ARP  Aligning Recovery Plan ---------------------------------------
def arp_static(env: Env) -> MethodResult:
    o, p, f = _objectives(), _one(env, "recovery_plan_record"), []
    if not p:
        return _r("arp-iac-plan-alignment", STATIC, IAC, "The recovery plan record matches the recovery objectives", "plan record present", ["No recovery plan record is declared"])
    for k in ("rto_hours", "rpo_hours"):
        if p.get(k) != o[k]:
            f.append(f"Plan {k} {p.get(k)} differs from objective {o[k]}")
    if p.get("review_cadence_days", 999) > o["review_cadence_days"]:
        f.append("Plan review cadence is longer than the objective cadence")
    if p.get("restore_runbook") not in {r["name"] for r in env.iac_resources("terraform_recovery_module")}:
        f.append("Restore runbook does not point to a declared recovery module")
    return _r("arp-iac-plan-alignment", STATIC, IAC, "The recovery plan record matches the objectives and names a declared runbook", "RTO, RPO, cadence and runbook match", f)


def arp_live(env: Env) -> MethodResult:
    o, p, f = _objectives(), env.live["recovery_plan"], []
    for k in ("rto_hours", "rpo_hours"):
        if p[f"documented_{k}"] != o[k]:
            f.append(f"Documented {k} {p['documented_' + k]} differs from objective {o[k]}")
    if p["last_review_days_ago"] > o["review_cadence_days"]:
        f.append(f"Plan was last reviewed {p['last_review_days_ago']} days ago")
    return _r("arp-live-plan-review", LIVE, LIVE_SRC + "#recovery_plan", "The documented plan matches the objectives and was reviewed within the cadence", "match, review <= cadence", f)


# ---- KSI-RPL-TRC  Testing Recovery Capabilities --------------------------------
def trc_static(env: Env) -> MethodResult:
    o, f = _objectives(), []
    if not env.iac_resources("terraform_recovery_module"):
        f.append("No recovery module is declared to run a restore from")
    if _one(env, "recovery_plan_record").get("restore_test_cadence_days", 999) > o["restore_test_cadence_days"]:
        f.append("Restore test cadence is longer than the objective")
    return _r("trc-iac-restore-test-plan", STATIC, IAC, "A recovery module exists and a restore test cadence at or under the objective is set", "module declared, cadence <= objective", f)


def trc_live(env: Env) -> MethodResult:
    o, tests, f = _objectives(), env.live.get("restore_tests", []), []
    if not tests:
        return _r("trc-live-restore-results", LIVE, LIVE_SRC + "#restore_tests", "A restore test inside the cadence met the RTO and RPO", "a recent passing test", ["No restore test is recorded"])
    t = min(tests, key=lambda x: x["days_ago"])
    if t["days_ago"] > o["restore_test_cadence_days"]:
        f.append(f"Latest restore test {t['id']} was {t['days_ago']} days ago (cadence {o['restore_test_cadence_days']})")
    if t["result"] != "pass":
        f.append(f"Restore test {t['id']} result was {t['result']}")
    if t["achieved_rto_hours"] > o["rto_hours"]:
        f.append(f"Achieved RTO {t['achieved_rto_hours']}h exceeds {o['rto_hours']}h")
    if t["achieved_rpo_hours"] > o["rpo_hours"]:
        f.append(f"Achieved RPO {t['achieved_rpo_hours']}h exceeds {o['rpo_hours']}h")
    return _r("trc-live-restore-results", LIVE, LIVE_SRC + "#restore_tests", "A restore test inside the cadence met the RTO and RPO", "<= cadence, RTO and RPO met", f)


# ---- KSI-SCR-MIT  Mitigating Supply Chain Risk ---------------------------------
def mit_static(env: Env) -> MethodResult:
    p, f = _one(env, "supply_chain_policy"), []
    if not p.get("sbom_generated"):
        f.append("No SBOM is generated")
    if not p.get("vendor_notification_clause_required"):
        f.append("Vendor contracts are not required to include notification clauses")
    if p.get("review_cadence_days", 999) > 90:
        f.append("Supply chain risk review is less often than quarterly")
    return _r("mit-iac-supply-chain-policy", STATIC, IAC, "An SBOM, vendor notification clauses and a quarterly risk review are defined", "SBOM, clause, quarterly", f)


def mit_live(env: Env) -> MethodResult:
    s, f = env.live["supply_chain"], []
    if s["last_risk_review_days_ago"] > 90:
        f.append(f"Last risk review was {s['last_risk_review_days_ago']} days ago")
    if s["risks_open_over_90d"]:
        f.append(f"{s['risks_open_over_90d']} supply chain risk(s) open over 90 days")
    f += [f"Third party {t['id']} has no notification clause" for t in s["third_parties"] if not t["notification_clause"]]
    return _r("mit-live-supply-chain-risks", LIVE, LIVE_SRC + "#supply_chain", "Risks were reviewed this quarter, none is stale and every third party has a notification clause", "review <= 90d, 0 stale, all clauses", f)


# ---- KSI-SCR-MON  Monitoring Supply Chain Risk ---------------------------------
def mon_static(env: Env) -> MethodResult:
    p, f = _one(env, "supply_chain_policy"), []
    if not p.get("dependency_monitoring"):
        f.append("Dependency monitoring is off")
    if not env.iac_resources("aws_inspector2_enabler"):
        f.append("No automated vulnerability scanning of running images")
    return _r("mon-iac-upstream-monitoring", STATIC, IAC, "Dependencies are monitored and running images are scanned automatically", "monitoring on, scanner enabled", f)


def mon_live(env: Env) -> MethodResult:
    s, f = env.live["supply_chain"], []
    f += [f"Third party {t['id']} was last checked {t['last_advisory_check_hours']}h ago" for t in s["third_parties"] if t["last_advisory_check_hours"] > 24]
    if s["sbom_age_days"] > 7:
        f.append(f"SBOM is {s['sbom_age_days']} days old")
    if s["upstream_vulns_critical_open"]:
        f.append(f"{s['upstream_vulns_critical_open']} critical upstream vulnerabilit(y/ies) open")
    return _r("mon-live-upstream-advisories", LIVE, LIVE_SRC + "#supply_chain", "Every third party was checked within 24 hours, the SBOM is current and no critical upstream issue is open", "<= 24h, SBOM <= 7d, 0 critical", f)
