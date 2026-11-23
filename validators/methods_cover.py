"""Methods that close the coverage gaps found in issue #39.

Each method covers the part of a KSI's official statement that the KSI's first two methods did not
prove (the gap recorded in KSI_GAPS on 23 Nov 2026). A KSI's gap entry is removed only when its method
here is registered. Every method fails on a missing or empty source (issue #44).

The data is fictional and is a snapshot, like the rest of environment/live-state.json: ages are given
as days_ago and do not change from run to run. Dated records in environment/grc-records.json do age.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from .base import Env, MethodResult, result, source_findings

STATIC, LIVE = "static", "live"
ROOT = Path(__file__).resolve().parent.parent
IAC, LIVE_SRC, GRC = "environment/iac-plan.json", "environment/live-state.json", "environment/grc-records.json"


def _file(rel: str) -> dict | None:
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _one(env: Env, rtype: str, name: str | None = None) -> dict:
    r = next((x for x in env.iac_resources(rtype) if name is None or x["name"] == name), None)
    return r["values"] if r else {}


def _out(mid, kind, src, desc, expected, findings):
    return result(mid, kind, src, desc, expected, f"{len(findings)} finding(s)", findings)


def _review_findings(reviews, label, owner, cadence_days) -> list[str]:
    """Latest review is within the cycle and was done by the named owner."""
    f = source_findings((label, reviews, False))
    if not owner or not cadence_days:
        f.append(f"No review owner or cycle is declared for {label}")
    if f:
        return f
    latest = min(reviews, key=lambda r: r["days_ago"])
    if latest["days_ago"] > cadence_days:
        f.append(f"Latest review {latest['id']} was {latest['days_ago']} days ago (cycle {cadence_days} days)")
    if latest.get("reviewed_by") != owner:
        f.append(f"Latest review {latest['id']} was done by {latest.get('reviewed_by')}, not the owner ({owner})")
    return f


# ---- KSI-MLA-OSM: the SIEM itself is reviewed ---------------------------------
def osm_review(env: Env) -> MethodResult:
    s = _one(env, "siem_config")
    f = _review_findings(env.live.get("siem_reviews"), LIVE_SRC + "#siem_reviews", s.get("review_owner"), s.get("review_cadence_days"))
    if not f:
        latest = min(env.live["siem_reviews"], key=lambda r: r["days_ago"])
        expected = len(env.live.get("siem", {}).get("sources_expected", []))
        if latest.get("sources_checked", 0) < expected:
            f.append(f"Latest SIEM review checked {latest.get('sources_checked', 0)} of {expected} expected sources")
    return _out("osm-live-siem-review", LIVE, LIVE_SRC + "#siem_reviews",
                "The SIEM was reviewed by its owner within the review cycle, covering every expected source",
                "review within siem_config.review_cadence_days, by review_owner, all sources", f)


# ---- KSI-CNA-ULN: traffic flow controls are reviewed --------------------------
def uln_review(env: Env) -> MethodResult:
    v = _one(env, "aws_vpc")
    f = _review_findings(env.live.get("traffic_flow_reviews"), LIVE_SRC + "#traffic_flow_reviews",
                         v.get("flow_review_owner"), v.get("flow_review_cadence_days"))
    return _out("uln-live-flow-review", LIVE, LIVE_SRC + "#traffic_flow_reviews",
                "Traffic flow controls were reviewed by their owner within the review cycle",
                "review within aws_vpc.flow_review_cadence_days, by flow_review_owner", f)


# ---- KSI-CNA-OFA: rapid recovery ---------------------------------------------
def ofa_recovery(env: Env) -> MethodResult:
    o = _file("environment/recovery-objectives.json")
    tests = env.live.get("restore_tests")
    f = source_findings(("environment/recovery-objectives.json", o, False), (LIVE_SRC + "#restore_tests", tests, False))
    if not f:
        t = min(tests, key=lambda x: x["days_ago"])
        if t["result"] != "pass":
            f.append(f"Latest restore test {t['id']} did not pass")
        if t["achieved_rto_hours"] > o["rto_hours"]:
            f.append(f"Latest restore test {t['id']} took {t['achieved_rto_hours']}h (RTO {o['rto_hours']}h)")
        if t.get("from_vault") != "recovery":
            f.append(f"Latest restore test {t['id']} did not restore from the {o['recovery_region']} recovery vault")
    return _out("ofa-live-recovery-time", LIVE, LIVE_SRC + "#restore_tests",
                "The latest restore from the second-region recovery vault passed within the RTO",
                "pass, achieved RTO <= rto_hours, from the recovery vault", f)


# ---- KSI-SVC-PRR: plans and procedures reviewed after each change -------------
def prr_plans(env: Env) -> MethodResult:
    log = _file("mas/scope-changes.json") or {}
    entries, reviews = log.get("entries"), env.grc.get("change_plan_reviews")
    f = source_findings(("mas/scope-changes.json#entries", entries, False), (GRC + "#change_plan_reviews", reviews, True))
    for e in entries or []:
        r = next((x for x in reviews or [] if e["id"] in x.get("changes_reviewed", []) and x["date"] >= e["date"]), None)
        age = (env.as_of - datetime.date.fromisoformat(e["date"])).days
        if r is None:
            if age > 28:  # 20 business days, the same deadline as the protection review after a change
                f.append(f"{e['id']} ({e['date']}) has no plan and procedure review after {age} days")
            continue
        if not r.get("plans_reviewed") or not r.get("procedures_reviewed"):
            f.append(f"Review of {e['id']} on {r['date']} does not list both plans and procedures reviewed")
    return _out("prr-grc-plan-review", LIVE, GRC + "#change_plan_reviews",
                "Plans and procedures were reviewed after every scope change",
                "a review with plans and procedures for each change, within 28 days", f)


# ---- KSI-SVC-ASM: keys and certificates ---------------------------------------
def asm_keys_certs(env: Env) -> MethodResult:
    keys, certs = env.live.get("kms_keys"), env.live.get("certificates")
    f = source_findings((LIVE_SRC + "#kms_keys", keys, False), (LIVE_SRC + "#certificates", certs, False),
                        ("aws_kms_key resources in " + IAC, env.iac_resources("aws_kms_key"), False))
    f += [f"IaC key '{k['name']}' does not enable rotation" for k in env.iac_resources("aws_kms_key") if not k["values"].get("enable_key_rotation")]
    f += [f"Key '{k['alias']}' rotation is off" for k in keys or [] if not k.get("rotation_enabled")]
    for c in certs or []:
        if not c.get("auto_renew"):
            f.append(f"Certificate '{c['name']}' does not renew automatically")
        if c.get("expires_in_days", 0) <= 30:
            f.append(f"Certificate '{c['name']}' expires in {c.get('expires_in_days')} days")
    return _out("asm-live-keys-certificates", LIVE, LIVE_SRC + "#kms_keys, #certificates",
                "Every key rotates and every certificate renews automatically with more than 30 days left",
                "rotation on, auto renew, > 30 days to expiry", f)


# ---- KSI-RPL-TRC (hardening): restore testing is persistent -------------------
def trc_history(env: Env) -> MethodResult:
    o = _file("environment/recovery-objectives.json")
    tests = env.live.get("restore_tests")
    f = source_findings(("environment/recovery-objectives.json", o, False), (LIVE_SRC + "#restore_tests", tests, False))
    if not f:
        cycle = o["restore_test_cadence_days"]
        days = sorted(t["days_ago"] for t in tests if t["days_ago"] <= 365)
        if len(days) < 365 // cycle:
            f.append(f"{len(days)} restore test(s) in the last 365 days (expected {365 // cycle} at a {cycle} day cycle)")
        gaps = [b - a for a, b in zip([0] + days, days)]
        if gaps and max(gaps) > cycle + 2:
            f.append(f"A gap of {max(gaps)} days between restore tests (cycle {cycle} days)")
        f += [f"Restore test {t['id']} failed or exceeded the RTO" for t in tests
              if t["days_ago"] <= 365 and (t["result"] != "pass" or t["achieved_rto_hours"] > o["rto_hours"])]
    return _out("trc-live-test-history", LIVE, LIVE_SRC + "#restore_tests",
                "Restore tests ran every cycle for the last year, each passing within the RTO",
                "one test per restore_test_cadence_days, no gap over the cycle, all within RTO", f)


# ---- KSI-SVC-RUD (hardening): the removal target is the customer term ----------
def rud_terms(env: Env) -> MethodResult:
    t = _file("environment/customer-terms.json")
    reqs = env.live.get("data_removal_requests")
    f = source_findings(("environment/customer-terms.json", t, False), (LIVE_SRC + "#data_removal_requests", reqs, False))
    if not f:
        if not (ROOT / t["agreement"]).exists():
            f.append(f"Agreement {t['agreement']} is missing")
        if _one(env, "data_removal_process").get("sla_days", 999) > t["deletion_days"]:
            f.append("The removal process target is longer than the customer term")
        if t.get("includes_backups") and not _one(env, "data_removal_process").get("includes_backups"):
            f.append("The customer term covers backups but the removal process does not")
        f += [f"{r['id']} took {r['completed_days']} days (customer term {t['deletion_days']} days)" for r in reqs if r["completed_days"] > t["deletion_days"]]
    return _out("rud-terms-agreement", STATIC, "environment/customer-terms.json",
                "The removal process and every request meet the standard customer term",
                "process target and requests <= deletion_days", f)


# ---- KSI-IAM-AAM: role and group lifecycle -----------------------------------
def aam_role_group_lifecycle(env: Env) -> MethodResult:
    events, roles = env.live.get("iam_change_events"), env.live.get("iam_roles")
    actors = _one(env, "idp_lifecycle").get("lifecycle_actors")
    f = source_findings((LIVE_SRC + "#iam_change_events", events, False), (LIVE_SRC + "#iam_roles", roles, False),
                        ("idp_lifecycle.lifecycle_actors in " + IAC, actors, False))
    f += [f"{e['action']} of {e['kind']} {e['target']} {e['days_ago']} days ago was done by {e['actor']}, not lifecycle automation"
          for e in events or [] if e.get("actor") not in (actors or [])]
    declared = {r["name"] for r in env.iac_resources("aws_iam_role")}
    f += [f"Live role {r['name']} is not declared in IaC" for r in roles or [] if r["name"].removeprefix("role/") not in declared]
    return _out("aam-live-role-group-lifecycle", LIVE, LIVE_SRC + "#iam_change_events",
                "Every role and group change came from lifecycle automation, and every live role is declared in IaC",
                "all actors in lifecycle_actors, 0 undeclared roles", f)


# ---- KSI-IAM-JIT: non-user accounts and review ---------------------------------
def jit_non_user(env: Env) -> MethodResult:
    accts = env.live.get("service_accounts")
    p = _one(env, "idp_lifecycle")
    f = source_findings((LIVE_SRC + "#service_accounts", accts, False))
    f += [f"Non-user account {a['name']} holds standing admin" for a in accts or [] if a.get("standing_admin")]
    f += [f"Non-user account {a['name']} sessions last {a['max_session_minutes']} minutes (limit 60)" for a in accts or [] if a.get("max_session_minutes", 9999) > 60]
    f += _review_findings(env.live.get("jit_reviews"), LIVE_SRC + "#jit_reviews", p.get("jit_review_owner"), p.get("jit_review_cadence_days"))
    return _out("jit-live-non-user-accounts", LIVE, LIVE_SRC + "#service_accounts, #jit_reviews",
                "No non-user account holds standing admin or long sessions, and access was reviewed within the cycle",
                "0 standing admin, sessions <= 60 min, review in cycle by owner", f)


# ---- KSI-CNA-EIS: intended state is enforced automatically --------------------
def eis_remediation(env: Env) -> MethodResult:
    rules = [r["name"] for r in env.iac_resources("aws_config_config_rule") if r["values"].get("enabled")]
    rem = {r["values"]["config_rule"]: r["values"] for r in env.iac_resources("aws_config_remediation_configuration")}
    log = env.live.get("remediation_log")
    f = source_findings(("enabled aws_config_config_rule resources in " + IAC, rules, False),
                        (LIVE_SRC + "#remediation_log", log, True))  # no drift in 30 days is a good state
    f += [f"Rule {r} has no automatic remediation" for r in rules if not rem.get(r, {}).get("automatic")]
    for e in log or []:
        limit = rem.get(e["rule"], {}).get("max_minutes", 15)
        if e.get("corrected_minutes") is None or e["corrected_minutes"] > limit:
            f.append(f"Drift on {e['resource']} ({e['rule']}) was not corrected within {limit} minutes")
    return _out("eis-live-auto-remediation", LIVE, LIVE_SRC + "#remediation_log",
                "Every enabled rule has automatic remediation, and every drift in the last 30 days was corrected in time",
                "remediation for every rule, corrections within max_minutes", f)


# ---- KSI-CNA-DFP: network and data-store privileges ----------------------------
def dfp_network_data(env: Env) -> MethodResult:
    allowed = _file("environment/network-privileges.json")
    sgs, buckets = env.live.get("security_groups"), env.live.get("s3_buckets")
    f = source_findings(("environment/network-privileges.json", allowed, False), (LIVE_SRC + "#security_groups", sgs, False),
                        (LIVE_SRC + "#s3_buckets", buckets, False))
    if not f:
        def rules(x): return sorted((d, r["port"], r["cidr"]) for d in ("ingress", "egress") for r in x.get(d, []))
        for g in sgs:
            a = allowed["security_groups"].get(g["name"])
            if a is None:
                f.append(f"Security group {g['name']} has no allowed-rule entry")
            else:
                f += [f"Security group {g['name']} allows {d} port {p} from {c}, which is not on the allowed list"
                      for d, p, c in set(rules(g)) - set(rules(a))]
        for b in buckets:
            extra = set(b.get("policy_principals") or ["*"]) - set(allowed["bucket_principals"].get(b["name"], []))
            f += [f"Bucket {b['name']} policy grants {p}, which is not on the allowed list" for p in sorted(extra)]
    return _out("dfp-live-network-data-privileges", LIVE, LIVE_SRC + "#security_groups, #s3_buckets",
                "Live network rules and bucket policy principals match the allowed list",
                "0 rules or principals outside environment/network-privileges.json", f)


# ---- KSI-MLA-LET: maintained list of what is logged ----------------------------
def let_list(env: Env) -> MethodResult:
    lst = _file("environment/logging-list.json")
    siem = env.live.get("siem")
    f = source_findings(("environment/logging-list.json", lst, False), (LIVE_SRC + "#siem", siem, False))
    if not f:
        need = {r["id"] for r in env.mas.get("information_resources", []) if r["decision"] == "in_scope" and r["kind"] == "machine_based"}
        listed = {r["scope"] for r in lst.get("resources", [])}
        f += [f"In-scope resource {r} is not on the logging list" for r in sorted(need - listed)]
        f += [f"Logging list entry {r['scope']} has no event types" for r in lst["resources"] if not r.get("event_types")]
        f += [f"Log source {s} for {r['scope']} is not reporting to the SIEM" for r in lst["resources"]
              for s in [r["log_source"]] if s not in siem.get("sources_reporting", [])]
        if lst.get("last_review_days_ago", 9999) > lst.get("review_cadence_days", 0):
            f.append(f"Logging list was last reviewed {lst.get('last_review_days_ago')} days ago (cycle {lst.get('review_cadence_days')} days)")
        if not lst.get("owner"):
            f.append("Logging list has no owner")
    return _out("let-list-coverage", LIVE, "environment/logging-list.json",
                "Every in-scope resource is on the reviewed logging list and its log source is reporting",
                "all in-scope resources listed, sources reporting, review in cycle", f)


# ---- KSI-PIY-GIV: people and third-party inventory -----------------------------
def giv_people(env: Env) -> MethodResult:
    users, reg = env.live.get("idp_users"), env.grc.get("third_party_register")
    people = {r["id"] for r in env.mas.get("information_resources", []) if r["kind"] == "non_machine_based"}
    tpr = {t["id"] for t in env.mas.get("third_party_resources", [])}
    f = source_findings((LIVE_SRC + "#idp_users", users, False), (GRC + "#third_party_register", reg, False),
                        ("mas/mas-record.json#third_party_resources", tpr, False))
    total = env.live.get("identity", {}).get("users_total")
    if users and total is not None and len([u for u in users if u["status"] == "active"]) != total:
        f.append(f"Workforce export has {len(users)} active users but the identity provider reports {total}")
    f += [f"User {u['id']} maps to {u.get('people_resource')}, which is not a people resource in the scope record"
          for u in users or [] if u.get("people_resource") not in people]
    have = {r["id"] for r in reg or []}
    f += [f"Third-party resource {t} is not in the register" for t in sorted(tpr - have)]
    f += [f"Register entry {t} is not in the scope record" for t in sorted(have - tpr)]
    return _out("giv-live-people-third-parties", LIVE, LIVE_SRC + "#idp_users, " + GRC + "#third_party_register",
                "Every workforce user maps to a people resource and the third-party register matches the scope record",
                "user count matches, 0 unmapped users, register equals scope record", f)


# ---- KSI-SVC-VRI: integrity of IaC modules -------------------------------------
def vri_artifacts(env: Env) -> MethodResult:
    req = _one(env, "ci_pipeline").get("signing_required_for")
    arts = env.live.get("artifact_signatures")
    f = source_findings(("ci_pipeline.signing_required_for in " + IAC, req, False), (LIVE_SRC + "#artifact_signatures", arts, False))
    if req and "iac_module" not in req:
        f.append("The pipeline does not require signing for IaC modules")
    f += [f"{a['artifact']} is not signed and digest-verified" for a in arts or [] if not (a.get("signed") and a.get("digest_verified"))]
    return _out("vri-live-artifact-signatures", LIVE, LIVE_SRC + "#artifact_signatures",
                "Signing is required for every artifact type and every deployed IaC module is signed and verified",
                "iac_module in signing_required_for, all signed and verified", f)


# ---- KSI-SVC-SIN: protection from unwanted modification ------------------------
FEDERAL_STORES = {"P3", "P4", "P12"}


def sin_modification(env: Env) -> MethodResult:
    buckets, dbs = env.live.get("s3_buckets"), env.live.get("rds_instances")
    f = source_findings((LIVE_SRC + "#s3_buckets", buckets, False), (LIVE_SRC + "#rds_instances", dbs, False))
    for b in env.iac_resources("aws_s3_bucket"):
        if b["scope"] in FEDERAL_STORES and not (b["values"].get("versioning") and b["values"].get("object_lock")):
            f.append(f"IaC bucket {b['name']} does not set versioning and object lock")
    f += [f"Live bucket {b['name']} does not have versioning and object lock on" for b in buckets or []
          if b["scope"] in FEDERAL_STORES and not (b.get("versioning") and b.get("object_lock"))]
    f += [f"Database {d['id']} has no deletion protection" for d in dbs or [] if d["scope"] in FEDERAL_STORES and not d.get("deletion_protection")]
    return _out("sin-live-modification-protection", LIVE, LIVE_SRC + "#s3_buckets, #rds_instances",
                "Stores that hold federal data are protected from modification and deletion",
                "versioning and object lock on federal buckets, deletion protection on the database", f)


# ---- KSI-MLA-ALA: access by data sensitivity ------------------------------------
def ala_classes(env: Env) -> MethodResult:
    c = _file("environment/log-classes.json")
    grants = (env.live.get("log_access") or {}).get("grants_last_90d")
    groups = env.iac_resources("aws_cloudwatch_log_group")
    f = source_findings(("environment/log-classes.json", c, False), (LIVE_SRC + "#log_access.grants_last_90d", grants, False),
                        ("aws_cloudwatch_log_group resources in " + IAC, groups, False))
    if not f:
        f += [f"Log group {g['name']} has no valid sensitivity class" for g in groups
              if not g["values"].get("sensitivity_classes") or set(g["values"]["sensitivity_classes"]) - set(c["classes"])]
        for g in grants:
            allowed = set(c["access_map"].get(g["role"], []))
            f += [f"Grant {g['id']} gives {g['role']} class {x}, which its access map does not allow" for x in g.get("classes", []) if x not in allowed]
            if not g.get("classes"):
                f.append(f"Grant {g['id']} names no sensitivity class")
            if set(g.get("classes", [])) & set(c["jit_required"]) and g["type"] != "jit":
                f.append(f"Grant {g['id']} reaches a JIT-only class without JIT")
    return _out("ala-live-sensitivity-classes", LIVE, "environment/log-classes.json",
                "Every log group has a sensitivity class and every grant matches the role's access map, with JIT for C3",
                "0 unclassified groups, 0 grants outside the map, JIT for C3", f)


# ---- KSI-MLA-EVC and KSI-CNA-IBP: SaaS configuration ----------------------------
SAAS = ("E1", "E7", "E9")


def _saas() -> dict | None:
    return _file("environment/saas-config.json")


def _saas_setting_findings(s: dict) -> list[str]:
    ex = {e["id"]: e for e in s.get("exceptions", [])}
    f = []
    for tool in SAAS:
        x = s.get("exports", {}).get(tool)
        if not x:
            f.append(f"No configuration export for {tool}")
            continue
        if not x.get("settings"):
            f.append(f"Configuration export for {tool} is empty")
        f += [f"{tool} setting {st['id']} ({st['setting']}) differs from guidance with no approved exception"
              for st in x.get("settings", []) if st["observed"] != st["expected"]
              and not (st.get("exception") in ex and ex[st["exception"]].get("approved_by") and ex[st["exception"]].get("expires_days", 0) > 0)]
    return f


def evc_saas(env: Env) -> MethodResult:
    s = _saas()
    f = source_findings(("environment/saas-config.json", s, False))
    if not f:
        f += [f"Configuration export for {t} is {s['exports'][t]['collected_days_ago']} days old (limit {s['max_export_age_days']})"
              for t in SAAS if t in s["exports"] and s["exports"][t]["collected_days_ago"] > s["max_export_age_days"]]
        f += _saas_setting_findings(s)
    return _out("evc-live-saas-configuration", LIVE, "environment/saas-config.json",
                "A fresh configuration export exists for each SaaS tool and every setting meets guidance or has an approved exception",
                "export <= max_export_age_days, 0 unexcepted deviations", f)


def ibp_saas(env: Env) -> MethodResult:
    s = _saas()
    f = source_findings(("environment/saas-config.json", s, False))
    if not f:
        if not s.get("review_owner"):
            f.append("No owner is named for the SaaS comparison reviews")
        f += [f"SaaS comparison for {t} was last reviewed {s['exports'][t]['last_review_days_ago']} days ago (cycle {s['review_cadence_days']})"
              for t in SAAS if t in s["exports"] and s["exports"][t].get("last_review_days_ago", 9999) > s["review_cadence_days"]]
        f += [f"SaaS comparison for {t} names no provider guidance" for t in SAAS if t in s["exports"] and not s["exports"][t].get("guidance")]
        f += _saas_setting_findings(s)
    return _out("ibp-live-saas-guidance", LIVE, "environment/saas-config.json",
                "Each SaaS tool was compared with its provider's guidance within the cycle",
                "review within review_cadence_days, guidance named, 0 unexcepted deviations", f)


# ---- KSI-SVC-VCM: client authentication between machine-based resources ---------
SERVICES = {"P2", "P8", "P10"}


def vcm_client_auth(env: Env) -> MethodResult:
    flows = [x for x in env.mas.get("information_flows", []) if x["source"][0] == "P" and x["destination"][0] == "P"]
    auth = env.live.get("flow_auth")
    f = source_findings(("internal flows in mas/mas-record.json", flows, False), (LIVE_SRC + "#flow_auth", auth, False))
    seen = {a["flow"]: a for a in auth or []}
    for x in flows:
        a = seen.get(x["id"])
        want = "mutual_tls" if x["source"] in SERVICES and x["destination"] in SERVICES else "iam_signed"
        if a is None:
            f.append(f"Flow {x['id']} ({x['source']} to {x['destination']}) has no observed client authentication")
        elif not a.get("client_authenticated") or a.get("method") != want:
            f.append(f"Flow {x['id']} uses {a.get('method')} with client_authenticated={a.get('client_authenticated')} (expected {want})")
    return _out("vcm-live-client-authentication", LIVE, LIVE_SRC + "#flow_auth",
                "Every internal flow authenticates its client: mutual TLS between services, IAM-signed requests to AWS services",
                "every internal flow authenticated by the expected method", f)
