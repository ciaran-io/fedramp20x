"""Validation methods for the technical KSIs in themes CMT, CNA, IAM and SVC (batch A).

Each KSI has one static method (what the IaC and policy-as-code declare) and one
live method (what the simulated cloud and identity snapshots observe). Read the
official statement in FedRAMP/rules before trusting a check. Gaps
between a check and its statement are recorded in KSI_GAPS (validators/registry.py).
"""
from __future__ import annotations

from datetime import date

from .base import Env, MethodResult, result, source_findings

STATIC, LIVE = "static", "live"
IAC, LIVE_SRC = "environment/iac-plan.json", "environment/live-state.json"


def _one(env: Env, rtype: str) -> dict:
    found = env.iac_resources(rtype)
    return found[0]["values"] if found else {}


def _out(mid, kind, src, desc, expected, findings, observed=None):
    return result(mid, kind, src, desc, expected, observed if observed is not None else f"{len(findings)} finding(s)", findings)


# ---- KSI-CMT-LMC  Logging Changes ---------------------------------------------
def lmc_static(env: Env) -> MethodResult:
    f = []
    ct = _one(env, "aws_cloudtrail")
    if not ct.get("is_multi_region_trail"):
        f.append("CloudTrail does not cover all regions")
    if not ct.get("enable_log_file_validation"):
        f.append("CloudTrail log file validation is off")
    if not env.iac_resources("aws_config_configuration_recorder"):
        f.append("No configuration recorder is declared")
    if _one(env, "ci_pipeline").get("audit_log_retention_days", 0) < 365:
        f.append("Pipeline audit log is kept under 365 days")
    return _out("lmc-iac-change-logging", STATIC, IAC, "Cloud, configuration and pipeline changes are recorded with at least 12 months of retention", "multi-region trail, recorder, pipeline log >= 365d", f)


def lmc_live(env: Env) -> MethodResult:
    ev = env.live["change_events"]["last_30_days"]
    f = []
    if ev["pipeline_changes_logged"] < ev["pipeline_changes"]:
        f.append(f"{ev['pipeline_changes'] - ev['pipeline_changes_logged']} pipeline change(s) have no log entry")
    if ev["manual_changes_alerted"] < ev["manual_console_changes"]:
        f.append(f"{ev['manual_console_changes'] - ev['manual_changes_alerted']} manual console change(s) raised no alert")
    return _out("lmc-live-change-coverage", LIVE, LIVE_SRC + "#change_events", "Every change in the last 30 days is logged and every manual change raised an alert", "100% logged, 100% of manual changes alerted", f,
                f"{ev['pipeline_changes_logged']}/{ev['pipeline_changes']} logged, {ev['manual_changes_alerted']}/{ev['manual_console_changes']} manual alerted")


# The same type names as mas/scope-changes.json and tools/check_scope_changes.py.
CHANGE_TYPES = ("routine", "not_significant", "adaptive", "transformative")


def lmc_change_types(env: Env) -> MethodResult:
    """KSI-CMT-LMC (live): every pipeline change in the last 30 days has one of the four change types (POL-CMT CMT-6)."""
    ev = env.live["change_events"]["last_30_days"]
    total, typed = ev["pipeline_changes"], ev.get("pipeline_changes_typed", 0)
    types = ev.get("change_types", {})
    f = []
    if typed < total:
        f.append(f"{total - typed} pipeline change(s) have no change type")
    unknown = sorted(set(types) - set(CHANGE_TYPES))
    if unknown:
        f.append(f"Unknown change type(s): {', '.join(unknown)}")
    if sum(types.values()) != typed:
        f.append(f"The change type counts add up to {sum(types.values())}, but {typed} change(s) are typed")
    return _out("lmc-live-change-types", LIVE, LIVE_SRC + "#change_events", "Every pipeline change in the last 30 days was assessed and given one of the four change types", "100% typed: routine recurring, not significant, adaptive or transformative", f,
                f"{typed}/{total} typed: " + ", ".join(f"{k} {v}" for k, v in types.items()))


# ---- KSI-CMT-RMV  Redeploying vs Modifying -------------------------------------
def rmv_static(env: Env) -> MethodResult:
    f = []
    if _one(env, "ci_pipeline").get("deploy_strategy") != "redeploy":
        f.append("Pipeline deploy strategy is not redeploy")
    for r in env.iac_resources("aws_ecr_repository"):
        if r["values"].get("image_tag_mutability") != "IMMUTABLE":
            f.append(f"Registry '{r['name']}' allows mutable tags")
    if _one(env, "aws_ssm_session_preferences").get("inbound_ssh_allowed"):
        f.append("Inbound SSH is allowed, so hosts can be changed by hand")
    return _out("rmv-iac-redeploy-policy", STATIC, IAC, "Machine-based resources are replaced from immutable, version-controlled images", "redeploy strategy, immutable tags, no inbound SSH", f)


def rmv_live(env: Env) -> MethodResult:
    f = source_findings((LIVE_SRC + "#compute", env.live.get("compute"), False))
    f += [f"{c['id']} does not match a registry image ({c.get('note', 'modified in place')})" for c in env.live.get("compute", []) if not c["image_digest_matches_registry"]]
    return _out("rmv-live-image-match", LIVE, LIVE_SRC + "#compute", "Every running compute resource matches an image in the registry", "all digests match", f)


# ---- KSI-CMT-VTD  Validating Throughout Deployment -----------------------------
def vtd_static(env: Env) -> MethodResult:
    p, f = _one(env, "ci_pipeline"), []
    for stage in ("test", "scan", "verify"):
        if stage not in p.get("stages", []):
            f.append(f"Pipeline has no '{stage}' stage")
    if not p.get("automated_tests"):
        f.append("Automated tests are not enabled")
    if not p.get("post_deploy_verification"):
        f.append("Post-deploy verification is not enabled")
    if not _one(env, "github_branch_protection").get("status_checks_required"):
        f.append("Status checks are not required before merge")
    return _out("vtd-iac-pipeline-stages", STATIC, IAC, "The pipeline tests, scans and verifies every change", "test, scan and verify stages enabled", f)


def vtd_live(env: Env) -> MethodResult:
    r, f = env.live["pipeline_runs_30d"], []
    for key, label in (("with_tests", "tests"), ("with_scans", "security scans"), ("with_post_deploy_verification", "post-deploy verification")):
        if r[key] < r["total"]:
            f.append(f"{r['total'] - r[key]} of {r['total']} runs skipped {label}")
    return _out("vtd-live-pipeline-runs", LIVE, LIVE_SRC + "#pipeline_runs_30d", "Every pipeline run in the last 30 days ran tests, scans and verification", "100% of runs", f)


# ---- KSI-CNA-DFP  Defining Functionality and Privileges -------------------------
def dfp_static(env: Env) -> MethodResult:
    f = source_findings(("aws_iam_role resources in environment/iac-plan.json", env.iac_resources("aws_iam_role"), False),
                        ("aws_ecs_service resources in environment/iac-plan.json", env.iac_resources("aws_ecs_service"), False))
    roles = {r["name"]: r["values"] for r in env.iac_resources("aws_iam_role")}
    used = [s["values"]["task_role"].split("/")[-1] for s in env.iac_resources("aws_ecs_service")]
    for u in set(used):
        if u not in roles:
            f.append(f"Task role '{u}' is not defined in IaC")
        elif not roles[u].get("function"):
            f.append(f"Role '{u}' has no stated function")
        elif roles[u].get("wildcard_actions_allowed"):
            f.append(f"Role '{u}' may use wildcard actions")
    if len(used) != len(set(used)):
        f.append("Two services share a task role")
    return _out("dfp-iac-role-definitions", STATIC, IAC, "Each service has its own role with a stated function and no wildcard actions", "one defined role per service", f)


def dfp_live(env: Env) -> MethodResult:
    f = source_findings((LIVE_SRC + "#iam_roles", env.live.get("iam_roles"), False))
    f += [f"{r['name']} grants {', '.join(r['wildcard_actions'])} ({r.get('note', 'not defined in IaC')})" for r in env.live.get("iam_roles", []) if r["wildcard_actions"]]
    return _out("dfp-live-role-privileges", LIVE, LIVE_SRC + "#iam_roles", "No live role holds wildcard actions", "0 wildcard actions", f)


# ---- KSI-CNA-IBP  Implementing Best Practices -----------------------------------
def ibp_static(env: Env) -> MethodResult:
    f = []
    packs = [p["values"] for p in env.iac_resources("aws_config_conformance_pack")]
    if not any(p.get("enabled") and "CIS" in p.get("benchmark", "") for p in packs):
        f.append("No CIS benchmark conformance pack is enabled")
    if not env.iac_resources("aws_guardduty_detector"):
        f.append("Threat detection service is not enabled")
    for w in env.iac_resources("aws_wafv2_web_acl"):
        if "CommonRuleSet" not in w["values"].get("managed_rules", []):
            f.append("WAF lacks the provider's common rule set")
    return _out("ibp-iac-provider-guidance", STATIC, IAC, "Provider best-practice benchmarks and managed rules are enabled", "CIS pack, threat detection, managed WAF rules", f)


def ibp_live(env: Env) -> MethodResult:
    b = env.live["benchmark_results"]["cis_aws_foundations"]
    return _out("ibp-live-benchmark-results", LIVE, LIVE_SRC + "#benchmark_results", "The latest benchmark scan has no failed controls", "0 failed controls", list(b["failing"]), f"{b['failed']} of {b['controls_total']} controls failed")


# ---- KSI-CNA-MAT  Minimizing Attack Surface -------------------------------------
def mat_static(env: Env) -> MethodResult:
    f = [f"Service '{s['name']}' gets a public IP" for s in env.iac_resources("aws_ecs_service") if s["values"].get("assign_public_ip")]
    if not env.iac_resources("aws_wafv2_web_acl"):
        f.append("No web application firewall is declared")
    for sg in env.iac_resources("aws_security_group"):
        for rule in sg["values"].get("ingress", []):
            if rule["cidr"] == "0.0.0.0/0" and rule["port"] != 443:
                f.append(f"Security group '{sg['name']}' opens port {rule['port']} to the internet")
    return _out("mat-iac-exposure", STATIC, IAC, "No service has a public IP, a WAF fronts the edge, and only 443 is open to the internet", "no public IPs, WAF present, only 443", f)


def mat_live(env: Env) -> MethodResult:
    e, f = env.live["exposed_endpoints"], []
    f += [f"Unexpected exposed endpoint {x}" for x in e["observed"] if x not in e["allowed"]]
    f += [f"Lateral path '{k}' has {v} path(s)" for k, v in e["lateral_paths"].items() if v]
    return _out("mat-live-exposed-endpoints", LIVE, LIVE_SRC + "#exposed_endpoints", "Only allowed endpoints are exposed and no unneeded lateral paths exist", "observed endpoints equal allowed, 0 lateral paths", f)


# ---- KSI-CNA-OFA  Optimizing for Availability -----------------------------------
def ofa_static(env: Env) -> MethodResult:
    f = []
    if _one(env, "aws_vpc").get("availability_zones", 1) < 2:
        f.append("VPC spans fewer than 2 availability zones")
    if not _one(env, "aws_db_instance").get("multi_az"):
        f.append("Database is not multi-AZ")
    f += [f"Service '{s['name']}' runs fewer than 2 tasks" for s in env.iac_resources("aws_ecs_service") if s["values"].get("desired_count", 1) < 2]
    if not env.iac_resources("aws_backup_plan"):
        f.append("No backup plan supports rapid recovery")
    return _out("ofa-iac-redundancy", STATIC, IAC, "Compute and database are redundant across zones and backed up", ">= 2 AZs, multi-AZ DB, >= 2 tasks, backup plan", f)


def ofa_live(env: Env) -> MethodResult:
    a, f = env.live["availability"], []
    f += [f"Service '{s['service']}' runs {s['running_tasks']} task(s) in {s['azs']} zone(s)" for s in a["services"] if s["running_tasks"] < 2 or s["azs"] < 2]
    if not a["rds_multi_az"]:
        f.append("Database is not running multi-AZ")
    if a["last_failover_test_days_ago"] > 90:
        f.append(f"Last failover test was {a['last_failover_test_days_ago']} days ago")
    return _out("ofa-live-availability", LIVE, LIVE_SRC + "#availability", "Every service runs in 2 or more zones and failover was tested in the last 90 days", ">= 2 tasks and zones, failover test <= 90d", f)


# ---- KSI-CNA-ULN  Using Logical Networking --------------------------------------
def uln_static(env: Env) -> MethodResult:
    f = []
    if not _one(env, "aws_vpc").get("flow_logs"):
        f.append("VPC flow logs are off")
    if len(env.iac_resources("aws_security_group")) < 3:
        f.append("Fewer than 3 security groups, so tiers are not separated")
    if not env.iac_resources("aws_nat_gateway"):
        f.append("No NAT gateway, so private subnets have no controlled egress")
    return _out("uln-iac-logical-network", STATIC, IAC, "A VPC with flow logs, tier security groups and controlled egress is declared", "flow logs, 3+ security groups, NAT", f)


def uln_live(env: Env) -> MethodResult:
    n, f = env.live["network"], []
    if not n["flow_logs"]["active"] or n["flow_logs"]["last_delivery_age_minutes"] > 60:
        f.append("VPC flow log delivery is inactive or stale")
    if n["data_subnets_with_internet_route"]:
        f.append(f"{n['data_subnets_with_internet_route']} data subnet(s) have an internet route")
    if n["nacl_changes_unreviewed"]:
        f.append(f"{n['nacl_changes_unreviewed']} network ACL change(s) are unreviewed")
    return _out("uln-live-network-controls", LIVE, LIVE_SRC + "#network", "Flow logs deliver, data subnets have no internet route and network changes are reviewed", "active logs, 0 routes, 0 unreviewed", f)


# ---- KSI-IAM-AAM  Automating Account Management ---------------------------------
def aam_static(env: Env) -> MethodResult:
    s, f = _one(env, "idp_lifecycle"), []
    if not s.get("scim_provisioning"):
        f.append("Automated provisioning is off")
    if not s.get("group_based_roles"):
        f.append("Roles are not assigned by group")
    if s.get("deprovision_sla_hours", 999) > 24:
        f.append("Deprovisioning target is over 24 hours")
    return _out("aam-iac-lifecycle-automation", STATIC, IAC, "Account lifecycle runs from the identity provider with a 24 hour removal target", "automated provisioning, group roles, <= 24h", f)


def aam_live(env: Env) -> MethodResult:
    f = [f"{d['user']} kept access for {d['access_removed_hours']}h after leaving" for d in env.live["identity"]["deprovisioning"] if d["access_removed_hours"] > 24]
    return _out("aam-live-deprovisioning", LIVE, LIVE_SRC + "#identity", "Leavers in the last 90 days lost access within 24 hours", "all <= 24h", f)


# ---- KSI-IAM-JIT  Authorizing Just-in-Time --------------------------------------
def jit_static(env: Env) -> MethodResult:
    g, f = _one(env, "access_gateway_policy"), []
    if g.get("standing_access"):
        f.append("Standing production access is allowed")
    if not g.get("approval_required"):
        f.append("Access needs no approval")
    if g.get("max_session_minutes", 9999) > 480:
        f.append("Sessions last over 8 hours")
    for p in env.iac_resources("aws_iam_policy"):
        for st in p["values"]["statements"]:
            if "*" in st["actions"] and not st.get("condition"):
                f.append(f"Policy '{p['name']}' grants all actions with no condition")
    return _out("jit-iac-access-model", STATIC, IAC, "Production access is approval-gated, time-limited and conditional", "no standing access, approval, <= 8h", f)


def jit_live(env: Env) -> MethodResult:
    f = [f"{a} holds standing privileged access" for a in env.live["standing_privileged_accounts"]]
    return _out("jit-live-standing-access", LIVE, LIVE_SRC + "#standing_privileged_accounts", "No account holds standing privileged access", "0 accounts", f)


# ---- KSI-IAM-SNU  Securing Non-User Authentication ------------------------------
def snu_static(env: Env) -> MethodResult:
    f = source_findings(("aws_iam_role resources in environment/iac-plan.json", env.iac_resources("aws_iam_role"), False))
    f += [f"Role '{r['name']}' uses long-lived keys" for r in env.iac_resources("aws_iam_role") if r["values"].get("long_lived_keys")]
    if not all(r["values"].get("long_lived_keys") is False for r in env.iac_resources("aws_iam_role") if "oidc_provider" in r["values"]):
        f.append("A pipeline role does not state that long-lived keys are off")
    return _out("snu-iac-workload-auth", STATIC, IAC, "Workload and pipeline identities use short-lived credentials", "no long-lived keys in IaC", f)


def snu_live(env: Env) -> MethodResult:
    f = [f"Access key for {k['principal']} is {k['age_days']} days old" for k in env.live["access_keys"] if k["age_days"] > 90]
    return _out("snu-live-access-key-age", LIVE, LIVE_SRC + "#access_keys", "No static access key is older than 90 days", "0 keys over 90d", f)


# ---- KSI-IAM-SUS  Responding to Suspicious Activity -----------------------------
def sus_static(env: Env) -> MethodResult:
    r, f = _one(env, "suspicious_activity_response"), []
    if not r.get("disable_on_alert"):
        f.append("Accounts are not disabled automatically on alert")
    for need in ("impossible_travel", "mfa_disabled", "new_access_key"):
        if need not in r.get("rules", []):
            f.append(f"No response rule for '{need}'")
    return _out("sus-iac-response-rules", STATIC, IAC, "Automated rules secure privileged accounts when activity looks suspicious", "auto-disable and 3 core rules", f)


def sus_live(env: Env) -> MethodResult:
    target = _one(env, "suspicious_activity_response").get("max_response_minutes", 15) if env.iac else 15
    f = [f"{e['id']} ({e['type']}) took {e['account_secured_minutes']} min to secure the account (target {target})" for e in env.live["suspicious_activity"] if e["account_secured_minutes"] > target]
    return _out("sus-live-response-time", LIVE, LIVE_SRC + "#suspicious_activity", "Each suspicious-activity event was secured within the target time", f"<= {target} min", f)


# ---- KSI-SVC-ACM  Automating Configuration Management ---------------------------
def acm_static(env: Env) -> MethodResult:
    f = []
    if not any(r["values"].get("enabled") for r in env.iac_resources("aws_config_config_rule")):
        f.append("No enabled drift rule is declared")
    if not env.iac_resources("aws_dynamodb_table"):
        f.append("No remote state lock table is declared")
    if _one(env, "ci_pipeline").get("deploy_strategy") != "redeploy":
        f.append("Configuration is not applied by the pipeline")
    return _out("acm-iac-config-automation", STATIC, IAC, "Configuration is applied by the pipeline and drift is evaluated", "drift rule, state lock, pipeline apply", f)


def acm_live(env: Env) -> MethodResult:
    d = env.live["drift"]
    f = [f"Unmanaged resource {u}" for u in d["unmanaged_resources"]]
    if d["scan_age_hours"] > 24:
        f.append(f"Drift scan is {d['scan_age_hours']}h old")
    return _out("acm-live-drift", LIVE, LIVE_SRC + "#drift", "No unmanaged resources exist and the drift scan is under 24 hours old", "0 unmanaged, scan <= 24h", f)


# ---- KSI-SVC-EIS  Evaluating and Improving Security -----------------------------
def eis_svc_static(env: Env) -> MethodResult:
    p, f = _one(env, "security_improvement_process"), []
    if p.get("review_cadence_days", 999) > 90:
        f.append("Improvement review is less often than quarterly")
    if p.get("max_open_item_age_days", 999) > 90:
        f.append("No 90 day limit on open improvement items")
    return _out("sei-iac-improvement-process", STATIC, IAC, "A quarterly improvement review with a 90 day item limit is defined", "quarterly, <= 90d items", f)


def eis_svc_live(env: Env) -> MethodResult:
    s = env.live["security_improvements"]
    f = [f"{i['id']} has been open {i['age_days']} days" for i in s["open_items"] if i["age_days"] > 90]
    if s["closed_last_90_days"] < 1:
        f.append("No improvement was closed in the last 90 days")
    return _out("sei-live-improvement-flow", LIVE, LIVE_SRC + "#security_improvements", "Improvements are being closed and none is older than 90 days", ">= 1 closed, 0 over 90d", f)


# ---- KSI-SVC-PRR  Preventing Residual Risk --------------------------------------
def prr_static(env: Env) -> MethodResult:
    f = []
    if not _one(env, "ci_pipeline").get("post_change_cleanup"):
        f.append("Pipeline has no post-change cleanup step")
    if not _one(env, "aws_ssm_session_preferences").get("session_logging"):
        f.append("Session logging is off, so residual access is not visible")
    return _out("prr-iac-cleanup-step", STATIC, IAC, "Changes end with a cleanup step and access sessions are logged", "cleanup step, session logging", f)


def prr_live(env: Env) -> MethodResult:
    r, f = env.live["residual"], []
    if r["unused_iam_roles"]:
        f.append(f"{r['unused_iam_roles']} unused IAM role(s)")
    f += [f"Orphaned volume {v}" for v in r["orphaned_volumes"]]
    if r["active_old_task_definitions"]:
        f.append(f"{r['active_old_task_definitions']} old task definition(s) still active")
    if r["stale_dns_records"]:
        f.append(f"{r['stale_dns_records']} stale DNS record(s)")
    if r["post_change_reviews_completed_pct"] < 100:
        f.append(f"Post-change reviews are {r['post_change_reviews_completed_pct']}% complete")
    return _out("prr-live-residual-elements", LIVE, LIVE_SRC + "#residual", "No unused roles, orphaned volumes, old task definitions or stale records remain", "0 residual elements", f)


# ---- KSI-SVC-RUD  Removing Unwanted Data ----------------------------------------
def rud_static(env: Env) -> MethodResult:
    p, f = _one(env, "data_removal_process"), []
    if p.get("sla_days", 999) > 30:
        f.append("Removal target is over 30 days")
    if not p.get("includes_backups"):
        f.append("Removal does not cover backups")
    if not p.get("audit_trail"):
        f.append("Removals leave no audit trail")
    return _out("rud-iac-removal-process", STATIC, IAC, "A removal process with a 30 day target covers backups and leaves an audit trail", "<= 30d, backups, audit trail", f)


def rud_live(env: Env) -> MethodResult:
    f = []
    for r in env.live["data_removal_requests"]:
        if r["completed_days"] > 30:
            f.append(f"{r['id']} took {r['completed_days']} days")
        if not r["backups_removed"]:
            f.append(f"{r['id']} was not removed from backups")
    return _out("rud-live-removal-requests", LIVE, LIVE_SRC + "#data_removal_requests", "Every removal request finished within 30 days, including backups", "all <= 30d", f)


# ---- KSI-SVC-VRI  Validating Resource Integrity ---------------------------------
def vri_static(env: Env) -> MethodResult:
    p, f = _one(env, "ci_pipeline"), []
    if not p.get("image_signing"):
        f.append("Images are not signed")
    if not p.get("verify_signature_on_deploy"):
        f.append("Signatures are not verified at deploy")
    if any(r["values"].get("image_tag_mutability") != "IMMUTABLE" for r in env.iac_resources("aws_ecr_repository")):
        f.append("A registry allows mutable tags")
    return _out("vri-iac-signing", STATIC, IAC, "Images are signed, verified at deploy and immutable", "signing, verification, immutable tags", f)


def vri_live(env: Env) -> MethodResult:
    i, f = env.live["image_integrity"], []
    if i["signed"] < i["images_running"]:
        f.append(f"{i['images_running'] - i['signed']} running image(s) are unsigned")
    if i["digest_verified"] < i["images_running"]:
        f.append(f"{i['images_running'] - i['digest_verified']} running image(s) were not digest-verified")
    if i["verification_failures_90d"]:
        f.append(f"{i['verification_failures_90d']} verification failure(s) in 90 days")
    return _out("vri-live-image-integrity", LIVE, LIVE_SRC + "#image_integrity", "Every running image is signed and digest-verified", "100% signed and verified", f)
