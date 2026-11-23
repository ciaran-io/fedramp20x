"""Starter validation methods for Orrinwick Beacon (fictional).

IMPORTANT: these checks are the demo author's *interpretation* of each KSI.
Before relying on any of them, read the KSI's Class C statement in
FedRAMP/rules (downloaded to frmr/ by `make frmr`) and confirm
the check actually demonstrates it. A passing check is evidence, not proof of
compliance.

Each KSI gets one static (IaC) method and one live (API snapshot) method.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from .base import Env, MethodResult, result, source_findings

WORLD = "0.0.0.0/0"
STATIC, LIVE = "static", "live"


# ---- KSI-CNA-RNT  Restricting Network Traffic --------------------------------
def rnt_static(env: Env) -> MethodResult:
    findings = source_findings(("aws_security_group resources in environment/iac-plan.json", env.iac_resources("aws_security_group"), False))
    for sg in env.iac_resources("aws_security_group"):
        for rule in sg["values"].get("ingress", []):
            if rule["cidr"] == WORLD and rule["port"] not in (443,):
                findings.append(f"IaC SG '{sg['name']}' allows {rule['port']} from the internet")
        for rule in sg["values"].get("egress", []):
            if rule["cidr"] == WORLD and rule["port"] not in (443,):
                findings.append(f"IaC SG '{sg['name']}' allows outbound {rule['port']} to the internet")
    return result("rnt-iac-traffic", STATIC, "environment/iac-plan.json",
                  "No IaC security group sends or accepts internet traffic on anything but 443",
                  "only 443 to or from 0.0.0.0/0", f"{len(findings)} violating rule(s)", findings)


def rnt_live(env: Env) -> MethodResult:
    findings = source_findings(("environment/live-state.json#security_groups", env.live.get("security_groups"), False))
    for sg in env.live.get("security_groups", []):
        for rule in sg["ingress"]:
            if rule["cidr"] == WORLD and rule["port"] not in (443,):
                findings.append(f"Live SG '{sg['name']}' allows {rule['port']} from the internet")
        for rule in sg.get("egress", []):
            if rule["cidr"] == WORLD and rule["port"] not in (443,):
                findings.append(f"Live SG '{sg['name']}' allows outbound {rule['port']} to the internet")
    return result("rnt-live-traffic", LIVE, "environment/live-state.json#security_groups",
                  "No live security group sends or accepts internet traffic on anything but 443",
                  "only 443 to or from 0.0.0.0/0", f"{len(findings)} violating rule(s)", findings)


# ---- KSI-CNA-EIS  Enforcing Intended State -----------------------------------
def eis_static(env: Env) -> MethodResult:
    rules = [r for r in env.iac_resources("aws_config_config_rule") if r["values"].get("enabled")]
    findings = [] if rules else ["No enabled drift-detection rule declared in IaC"]
    return result("eis-iac-drift-rule", STATIC, "environment/iac-plan.json",
                  "A drift-detection rule is declared and enabled in IaC",
                  ">=1 enabled drift rule", f"{len(rules)} rule(s)", findings)


def eis_live(env: Env) -> MethodResult:
    drift = env.live.get("drift") or {}
    # No unmanaged resources is the intended state, so an empty list is allowed; a missing drift scan is not.
    findings = source_findings(("environment/live-state.json#drift", env.live.get("drift"), False),
                               ("environment/live-state.json#drift.unmanaged_resources", drift.get("unmanaged_resources"), True))
    unmanaged = drift.get("unmanaged_resources") or []
    findings += [f"Unmanaged resource outside IaC: {u}" for u in unmanaged]
    return result("eis-live-drift", LIVE, "environment/live-state.json#drift",
                  "Live environment has no resources outside declared intended state",
                  "0 unmanaged resources", f"{len(unmanaged)} unmanaged", findings)


# ---- KSI-IAM-APM  Adopting Passwordless Methods ------------------------------
def apm_static(env: Env) -> MethodResult:
    findings = []
    pols = env.iac_resources("idp_policy")
    if not pols:
        findings.append("No IdP policy declared")
    for p in pols:
        v = p["values"]
        if not v.get("mfa_required") or v.get("password_only_allowed"):
            findings.append(f"IdP policy '{p['name']}' permits password-only sign-in")
        if not set(v.get("factor_types", [])) & {"webauthn", "platform_authenticator"}:
            findings.append(f"IdP policy '{p['name']}' lacks phishing-resistant factors")
    return result("apm-iac-idp-policy", STATIC, "environment/iac-plan.json",
                  "IdP policy requires phishing-resistant / passwordless factors",
                  "MFA required, WebAuthn-class factors, no password-only", f"{len(pols)} policy(ies)", findings)


def apm_live(env: Env) -> MethodResult:
    ident = env.live.get("identity", {})
    total, strong = ident.get("users_total", 0), ident.get("users_phishing_resistant_mfa", 0)
    findings = [] if total and total == strong else [f"{total - strong} of {total} users lack phishing-resistant MFA"]
    return result("apm-live-user-factors", LIVE, "environment/live-state.json#identity",
                  "Every workforce user is enrolled in a phishing-resistant factor",
                  "100% enrolled", f"{strong}/{total} enrolled", findings)


# ---- KSI-IAM-ELP  Ensuring Least Privilege -----------------------------------
def elp_static(env: Env) -> MethodResult:
    findings = source_findings(("aws_iam_policy resources in environment/iac-plan.json", env.iac_resources("aws_iam_policy"), False))
    for pol in env.iac_resources("aws_iam_policy"):
        v = pol["values"]
        for st in v.get("statements", []):
            if "*" in st["actions"] and "*" in st["resources"] and not v.get("breakglass"):
                findings.append(f"Policy '{pol['name']}' grants *:* without break-glass controls")
            if v.get("breakglass") and not st.get("condition"):
                findings.append(f"Break-glass policy '{pol['name']}' has no approval condition")
    return result("elp-iac-wildcards", STATIC, "environment/iac-plan.json",
                  "No standing wildcard admin; break-glass is approval-gated",
                  "0 ungated wildcard grants", f"{len(findings)} finding(s)", findings)


def elp_live(env: Env) -> MethodResult:
    iam = env.live.get("iam") or {}
    # No wildcard attachments is a good state, so an empty list is allowed; a missing list is not.
    findings = source_findings(("environment/live-state.json#iam", env.live.get("iam"), False),
                               ("environment/live-state.json#iam.wildcard_admin_attachments", iam.get("wildcard_admin_attachments"), True),
                               ("environment/live-state.json#iam.unused_permission_findings", iam.get("unused_permission_findings"), True),
                               ("environment/live-state.json#iam.unused_permission_threshold", iam.get("unused_permission_threshold"), True))
    findings += [f"Wildcard admin on {w['principal']} is not approval-gated"
                 for w in iam.get("wildcard_admin_attachments", []) if not w.get("approval_gated")]
    unused, limit = iam.get("unused_permission_findings", 0), iam.get("unused_permission_threshold", 0)
    if unused > limit:
        findings.append(f"{unused} unused-permission findings exceed threshold {limit}")
    return result("elp-live-unused-perms", LIVE, "environment/live-state.json#iam",
                  "Live IAM has no ungated wildcard admin and no unused-permission backlog",
                  f"<= {limit} unused-permission findings", f"{unused} findings", findings)


# ---- KSI-SVC-SIN  Securing Information (encryption at rest) ------------------
def sin_static(env: Env) -> MethodResult:
    storage = [r for t in ("aws_s3_bucket", "aws_db_instance", "aws_ebs_volume", "aws_sqs_queue", "aws_dynamodb_table")
               for r in env.iac_resources(t)]
    findings = source_findings(("storage resources in environment/iac-plan.json", storage, False))
    for b in env.iac_resources("aws_s3_bucket"):
        if not b["values"].get("encrypted"):
            findings.append(f"IaC bucket '{b['name']}' is not encrypted")
    for r in env.iac_resources("aws_db_instance"):
        if not r["values"].get("storage_encrypted"):
            findings.append(f"IaC DB '{r['name']}' is not encrypted")
    for v in env.iac_resources("aws_ebs_volume"):
        if not v["values"].get("encrypted"):
            findings.append(f"IaC volume '{v['name']}' is not encrypted")
    for q in env.iac_resources("aws_sqs_queue"):
        if not q["values"].get("sse_enabled"):
            findings.append(f"IaC queue '{q['name']}' is not encrypted")
    for t in env.iac_resources("aws_dynamodb_table"):
        if not t["values"].get("encrypted"):
            findings.append(f"IaC table '{t['name']}' is not encrypted")
    return result("sin-iac-encryption", STATIC, "environment/iac-plan.json",
                  "All declared storage resources are encrypted at rest",
                  "0 unencrypted resources", f"{len(findings)} unencrypted", findings)


def sin_live(env: Env) -> MethodResult:
    storage = [r for k in ("s3_buckets", "ebs_volumes", "rds_instances", "sqs_queues") for r in env.live.get(k) or []]
    findings = source_findings(("storage resources in environment/live-state.json", storage, False))
    findings += [f"Live bucket '{b['name']}' unencrypted" for b in env.live.get("s3_buckets", []) if not b["encrypted"]]
    findings += [f"Live volume '{v['id']}' unencrypted" for v in env.live.get("ebs_volumes", []) if not v["encrypted"]]
    findings += [f"Live DB '{d['id']}' unencrypted" for d in env.live.get("rds_instances", []) if not d["storage_encrypted"]]
    findings += [f"Live queue '{q['name']}' unencrypted" for q in env.live.get("sqs_queues", []) if not q["sse_enabled"]]
    return result("sin-live-encryption", LIVE, "environment/live-state.json",
                  "All live storage resources are encrypted at rest",
                  "0 unencrypted resources", f"{len(findings)} unencrypted", findings)


# ---- KSI-SVC-ASM  Automating Secret Management -------------------------------
def asm_static(env: Env) -> MethodResult:
    rots = env.iac_resources("aws_secretsmanager_secret_rotation")
    findings = [f"Secret '{r['name']}' rotation interval {r['values']['automatically_after_days']}d exceeds 90d"
                for r in rots if r["values"]["automatically_after_days"] > 90]
    if not rots:
        findings.append("No automatic secret rotation declared")
    return result("asm-iac-rotation", STATIC, "environment/iac-plan.json",
                  "Secrets declare automatic rotation at <= 90 days",
                  "all secrets rotate <= 90d", f"{len(rots)} rotation(s) declared", findings)


def asm_live(env: Env) -> MethodResult:
    findings = source_findings(("environment/live-state.json#secrets", env.live.get("secrets"), False))
    findings += [f"Secret '{s['name']}' last rotated {s['days_since_rotation']}d ago (limit 90d)"
                 for s in env.live.get("secrets", []) if s["days_since_rotation"] > 90 or not s["rotation_enabled"]]
    return result("asm-live-rotation-age", LIVE, "environment/live-state.json#secrets",
                  "No live secret is older than its rotation limit",
                  "all secrets rotated within 90d", f"{len(findings)} overdue", findings)


# ---- KSI-MLA-LET  Logging Event Types ----------------------------------------
def let_static(env: Env) -> MethodResult:
    trails = env.iac_resources("aws_cloudtrail")
    findings = []
    if not trails:
        findings.append("No CloudTrail declared")
    for t in trails:
        v = t["values"]
        if not (v.get("is_multi_region_trail") and v.get("enable_log_file_validation")):
            findings.append(f"Trail '{t['name']}' not multi-region with log-file validation")
    return result("let-iac-cloudtrail", STATIC, "environment/iac-plan.json",
                  "Multi-region audit trail with integrity validation is declared",
                  "multi-region + validation", f"{len(trails)} trail(s)", findings)


def let_live(env: Env) -> MethodResult:
    ct = env.live.get("cloudtrail", {})
    findings = []
    if not ct.get("is_logging"):
        findings.append("CloudTrail is not logging")
    if ct.get("last_delivery_age_minutes", 9999) > 60:
        findings.append("CloudTrail log delivery is stale (>60 min)")
    return result("let-live-cloudtrail", LIVE, "environment/live-state.json#cloudtrail",
                  "Audit trail is actively logging with fresh delivery",
                  "logging, delivery <= 60 min", f"logging={ct.get('is_logging')}, age={ct.get('last_delivery_age_minutes')}m", findings)


# ---- KSI-RPL-ABO  Aligning Backups with Objectives ---------------------------
def _objectives() -> dict:
    """Recovery objectives are defined once, in environment/recovery-objectives.json (SD-003)."""
    return json.loads((Path(__file__).resolve().parent.parent / "environment/recovery-objectives.json").read_text())


def abo_static(env: Env) -> MethodResult:
    o = _objectives()
    region, rpo = o["recovery_region"], o["rpo_hours"]
    interval = o.get("backup_interval_hours_max", rpo)
    findings = []
    vaults = {v["name"]: v for v in env.iac_resources("aws_backup_vault")}
    locks = {v["values"]["vault"]: v["values"] for v in env.iac_resources("aws_backup_vault_lock_configuration")}
    plans = env.iac_resources("aws_backup_plan")
    if not plans:
        findings.append("No AWS Backup plan is declared")
    covered = set()
    for sel in env.iac_resources("aws_backup_selection"):
        covered |= set(sel["values"]["resources"])
    for pl in plans:
        for rule in pl["values"]["rules"]:
            if rule["schedule_interval_hours"] > interval:
                findings.append(f"Rule '{rule['name']}' runs every {rule['schedule_interval_hours']}h (maximum {interval}h)")
            if rule["delete_after_days"] < o["backup_retention_days_min"]:
                findings.append(f"Rule '{rule['name']}' keeps recovery points {rule['delete_after_days']}d < {o['backup_retention_days_min']}d")
            copies = [c for c in rule.get("copy_actions", []) if c["destination_region"] == region]
            if not copies:
                findings.append(f"Rule '{rule['name']}' has no copy to {region}")
            for c in copies:
                if c["destination_vault"] not in locks:
                    findings.append(f"Destination vault '{c['destination_vault']}' has no vault lock")
                elif locks[c["destination_vault"]].get("mode") != "compliance":
                    findings.append(f"Destination vault '{c['destination_vault']}' lock is not in compliance mode")
                if c["delete_after_days"] < o["backup_retention_days_min"]:
                    findings.append(f"Copy to '{c['destination_vault']}' keeps recovery points {c['delete_after_days']}d < {o['backup_retention_days_min']}d")
    for name, v in vaults.items():
        if not v["values"].get("kms_key"):
            findings.append(f"Vault '{name}' is not encrypted with a customer-managed key")
    needed = {f"db:{d['name']}" for d in env.iac_resources("aws_db_instance")} | set(o.get("protected_resources", []))
    for n in sorted(needed - covered):
        findings.append(f"{n} is not in any AWS Backup selection")
    return result("abo-iac-backup-policy", STATIC, "environment/iac-plan.json",
                  f"Backup plan runs at least every {interval}h, keeps {o['backup_retention_days_min']}+ days, copies to a locked vault in {region} and covers every protected data store",
                  f"<= {interval}h interval, >= {o['backup_retention_days_min']}d, locked copy in {region}", f"{len(findings)} gap(s)", findings)


def abo_live(env: Env) -> MethodResult:
    o = _objectives()
    rpo, region = o["rpo_hours"], o["recovery_region"]
    ab = env.live.get("aws_backup", {})
    findings = [f"{p['resource']}: newest recovery point is {p['latest_recovery_point_age_hours']}h old (RPO {rpo}h)"
                for p in ab.get("protected_resources", []) if p["latest_recovery_point_age_hours"] > rpo]
    copies = ab.get("copy_jobs", [])
    for c in copies:
        if c["destination_region"] != region or c["status"] != "COMPLETED":
            findings.append(f"Copy of {c['resource']} is {c['status']} to {c['destination_region']} (expected COMPLETED to {region})")
        elif c["lag_hours"] > rpo:
            findings.append(f"Copy of {c['resource']} lags {c['lag_hours']}h (RPO {rpo}h)")
    for n in o.get("protected_resources", []):
        if not any(c["resource"] == n for c in copies):
            findings.append(f"No cross-region copy job observed for {n}")
    for v in ab.get("vaults", []):
        if v["region"] == region and not v.get("lock_enabled"):
            findings.append(f"Vault '{v['name']}' in {region} has no vault lock")
        elif v["region"] == region and v.get("lock_mode") != "compliance":
            findings.append(f"Vault '{v['name']}' in {region} lock is not in compliance mode")
    return result("abo-live-backup-currency", LIVE, "environment/live-state.json#aws_backup",
                  f"Newest recovery point and its cross-region copy are within the {rpo}h recovery point objective",
                  f"<= {rpo}h, copy to {region}", f"{len(findings)} breaching", findings)


def _timestamp(text: str) -> datetime.datetime:
    """An ISO 8601 UTC time such as 2026-11-17T03:09:00Z."""
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def abo_alert(env: Env) -> MethodResult:
    """KSI-RPL-ABO (live): backup and copy jobs ran in the last day, and every failed job in the window raised an alert
    in time that a person acknowledged (POL-RPL RPL-2). Only jobs on or before the run date count."""
    o = _objectives()
    limit = o.get("failed_job_alert_minutes_max", 60)
    window = o.get("job_history_window_days", 30)
    today = env.as_of
    past = [j for j in env.backup_jobs.get("jobs", []) if _timestamp(j["finished"]).date() <= today]
    findings = []
    for kind in ("backup", "copy"):
        newest = max((_timestamp(j["finished"]).date() for j in past if j.get("type") == kind and j.get("status") == "COMPLETED"), default=None)
        if newest is None or (today - newest).days > 1:
            findings.append(f"No completed {kind} job since {newest} (run date {today})")
    recent = [j for j in past if (today - _timestamp(j["finished"]).date()).days <= window]
    failed = [j for j in recent if j.get("status") == "FAILED"]
    for j in failed:
        label = f"Failed {j.get('type')} job {j.get('job_id')}"
        alert = j.get("alert") or {}
        if not alert.get("raised"):
            findings.append(f"{label} raised no alert")
            continue
        delay = (_timestamp(alert["raised"]) - _timestamp(j["finished"])).total_seconds() / 60
        if delay < 0 or delay > limit:
            findings.append(f"{label}: alert {alert.get('id')} raised {delay:.0f} minutes after the failure (limit {limit})")
        if not alert.get("acknowledged_by"):
            findings.append(f"{label}: alert {alert.get('id')} was not acknowledged")
    return result("abo-live-failed-job-alerts", LIVE, "environment/backup-jobs.json",
                  f"Backup and copy jobs completed in the last day, and every failed job in the last {window} days raised an alert within {limit} minutes that a person acknowledged",
                  f"jobs in the last day; alert <= {limit} min, acknowledged",
                  f"{len(recent)} job(s) in {window} days, {len(failed)} failed, {len(findings)} finding(s)", findings)


# ---- KSI-SVC-VCM  Validating Communications ----------------------------------
def vcm_static(env: Env) -> MethodResult:
    findings = source_findings(("aws_lb_listener resources in environment/iac-plan.json", env.iac_resources("aws_lb_listener"), False))
    findings += [f"Listener '{l['name']}' is not HTTPS" for l in env.iac_resources("aws_lb_listener") if l["values"]["protocol"] != "HTTPS"]
    findings += [f"Listener '{l['name']}' uses weak policy" for l in env.iac_resources("aws_lb_listener")
                 if "TLS13" not in l["values"].get("ssl_policy", "") and "TLS-1-2" not in l["values"].get("ssl_policy", "")]
    return result("vcm-iac-tls-policy", STATIC, "environment/iac-plan.json",
                  "Declared listeners enforce HTTPS with a modern TLS policy",
                  "HTTPS + TLS1.2+ policy", f"{len(findings)} weak listener(s)", findings)


def vcm_live(env: Env) -> MethodResult:
    findings = []
    for e in env.live.get("tls_scan", {}).get("endpoints", []):
        if e["min_protocol"] not in ("TLSv1.2", "TLSv1.3") or e["weak_ciphers"] > 0:
            findings.append(f"Endpoint {e['host']}: {e['min_protocol']}, {e['weak_ciphers']} weak ciphers")
    # every data flow in the scope record must have an observed TLS 1.2+ session with a valid certificate
    flows = [f for f in env.mas.get("information_flows", []) if f["type"] == "data"]
    seen = {o["flow"]: o for o in env.live.get("flow_tls", [])}
    for f in flows:
        o = seen.get(f["id"])
        if not o:
            findings.append(f"Flow {f['id']} ({f['source']} to {f['destination']}) has no observed TLS measurement")
        elif o["protocol"] not in ("TLSv1.2", "TLSv1.3") or not o["certificate_valid"]:
            findings.append(f"Flow {f['id']}: {o['protocol']}, certificate valid={o['certificate_valid']}")
    return result("vcm-live-tls-scan", LIVE, "environment/live-state.json#tls_scan,flow_tls",
                  "Public endpoints and every data flow in the scope record use TLS 1.2+ with valid certificates and no weak ciphers",
                  "TLS1.2+, valid certificates, 0 weak ciphers", f"{len(e_ := env.live.get('tls_scan', {}).get('endpoints', []))} endpoint(s), {len(flows)} flow(s) checked, {len(findings)} finding(s)", findings)
