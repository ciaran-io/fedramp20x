"""Unit tests. Run with `make test` (python -m unittest)."""
import copy
import datetime
import os
import json
import unittest
from pathlib import Path

from tools import check_scope_changes as scl
from validators import methods as m
from validators import methods_grc as g
from validators import methods_ops as o
from validators import methods_tech as t
from validators.base import AS_OF_VARIABLE, Env, run_date
from validators.registry import KSI_METHODS, KSI_GAPS, KSI_NOTES

ROOT = Path(__file__).resolve().parent.parent


def load(p):
    return json.loads((ROOT / p).read_text())


# Tests use a fixed date so their results do not change as the records age.
TEST_DATE = datetime.date(2026, 11, 22)


def env():
    return Env(company=load("environment/company.json"), iac=load("environment/iac-plan.json"),
               live=load("environment/live-state.json"), backup_jobs=load("environment/backup-jobs.json"), mas=load("mas/mas-record.json"),
               grc=load("environment/grc-records.json"), as_of=TEST_DATE)


class Registry(unittest.TestCase):
    def test_every_registered_ksi_exists_and_has_two_methods(self):
        ids = {k["id"] for k in load("evidence/ksi-registry.json")["indicators"]}
        for ksi, fns in KSI_METHODS.items():
            self.assertIn(ksi, ids)
            self.assertGreaterEqual(len(fns), 2, ksi)

    def test_every_note_belongs_to_a_registered_ksi(self):
        for ksi in KSI_NOTES:
            self.assertIn(ksi, KSI_METHODS)

    def test_every_gap_belongs_to_a_registered_ksi(self):
        for ksi in KSI_GAPS:
            self.assertIn(ksi, KSI_METHODS)

    def test_a_gap_blocks_a_pass(self):
        # Issue #39: a KSI with a known gap cannot pass, even when every method passes.
        from tools.run_validators import roll_up
        passing = [{"status": "pass"}, {"status": "pass"}]
        self.assertEqual(roll_up(passing), "pass")
        for ksi, gap in KSI_GAPS.items():
            self.assertEqual(roll_up(passing, gap), "partial", ksi)

    def test_no_ksi_has_both_a_gap_and_a_limit_note_that_says_nothing_is_missing(self):
        for ksi in KSI_GAPS:
            self.assertFalse(KSI_NOTES.get(ksi, "").startswith("Limit:"), ksi)

    def test_method_ids_are_unique(self):
        e = env()
        ids = [fn(e).method_id for fns in KSI_METHODS.values() for fn in fns]
        self.assertEqual(len(ids), len(set(ids)))


class Methods(unittest.TestCase):
    def test_methods_return_a_known_status(self):
        e = env()
        for ksi, fns in KSI_METHODS.items():
            for fn in fns:
                r = fn(e)
                self.assertIn(r.status, ("pass", "fail"), f"{ksi} {fn.__name__}")
                self.assertEqual(r.status == "pass", not r.findings, f"{ksi} {fn.__name__}: status and findings disagree")

    def test_open_ssh_is_found(self):
        e = env()
        self.assertEqual(m.rnt_live(e).status, "pass")
        e.live["security_groups"].append({"name": "hand-built", "ingress": [{"port": 22, "cidr": "0.0.0.0/0"}], "egress": []})
        self.assertEqual(m.rnt_live(e).status, "fail")

    def test_unscoped_resource_is_flagged(self):
        e = env()
        self.assertEqual(o.giv_live(e).status, "pass")
        e.live["ebs_volumes"].append({"id": "vol-stray", "encrypted": True})
        r = o.giv_live(e)
        self.assertEqual(r.status, "fail")
        self.assertIn("vol-stray", r.findings[0])
        e.live["ebs_volumes"][-1]["scope"] = "P99"
        self.assertIn("not in the scope record", o.giv_live(e).findings[0])

    def test_backup_check_fails_when_plan_removed(self):
        e = env()
        e.iac["resources"] = [r for r in e.iac["resources"] if r["type"] != "aws_backup_plan"]
        self.assertEqual(m.abo_static(e).status, "fail")

    def test_backup_interval_above_policy_maximum_fails(self):
        e = env()
        for r in e.iac["resources"]:
            if r["type"] == "aws_backup_plan":
                r["values"]["rules"][0]["schedule_interval_hours"] = 3
        self.assertEqual(m.abo_static(e).status, "fail")

    def test_governance_mode_vault_lock_fails(self):
        e = env()
        for r in e.iac["resources"]:
            if r["type"] == "aws_backup_vault_lock_configuration":
                r["values"]["mode"] = "governance"
        for v in e.live["aws_backup"]["vaults"]:
            if v.get("lock_enabled"):
                v["lock_mode"] = "governance"
        self.assertEqual(m.abo_static(e).status, "fail")
        self.assertEqual(m.abo_live(e).status, "fail")

    def test_failed_backup_job_without_alert_fails(self):
        e = env()
        self.assertEqual(m.abo_alert(e).status, "pass")
        e.as_of = datetime.date(2027, 5, 22)
        self.assertIn("raised no alert", " ".join(m.abo_alert(e).findings))

    def test_late_or_unacknowledged_backup_alert_fails(self):
        e = env()
        failed = next(j for j in e.backup_jobs["jobs"] if j.get("alert"))
        failed["alert"]["raised"] = "2026-11-17T05:00:00Z"
        self.assertEqual(m.abo_alert(e).status, "fail")
        e = env()
        failed = next(j for j in e.backup_jobs["jobs"] if j.get("alert"))
        failed["alert"]["acknowledged_by"] = None
        self.assertEqual(m.abo_alert(e).status, "fail")

    def test_backup_history_must_be_recent(self):
        e = env()
        e.as_of = datetime.date(2027, 11, 25)
        self.assertIn("No completed backup job", " ".join(m.abo_alert(e).findings))

    def test_overdue_ir_plan_review_fails_inr_rir(self):
        e = env()
        e.grc["ir_plan"]["reviews"] = [{"date": "2024-01-01", "reviewed_by": "CISO"}]
        self.assertEqual(g.inr_rir_live(e).status, "fail")

    def test_plan_review_by_wrong_person_fails_inr_rir(self):
        e = env()
        e.grc["ir_plan"]["reviews"].append({"date": "2026-11-22", "reviewed_by": "GRC Lead"})
        self.assertEqual(g.inr_rir_live(e).status, "fail")

    def test_plan_change_without_later_review_fails_inr_rir(self):
        e = env()
        e.grc["incidents"] = [{"id": "INC-T", "pain_rating": 3, "reportable": True, "opened": "2026-11-20", "closed": "2026-11-21",
                               "aar_completed": "2026-11-22", "lessons_incorporated": True, "plan_change_required": True}]
        self.assertEqual(g.inr_rir_live(e).status, "fail")

    def test_unrated_reportable_incident_counts_as_n5(self):
        self.assertEqual(g._effective_pain({"reportable": True, "pain_rating": None}), 5)
        self.assertTrue(g._needs_after_action_report({"reportable": True, "pain_rating": None}))
        self.assertFalse(g._needs_after_action_report({"reportable": False, "pain_rating": 1}))

    def test_old_protection_review_fails_cna_rvp(self):
        e = env()
        e.grc["protection_reviews"] = [{"date": "2024-05-01", "summary": "old"}]
        self.assertEqual(g.cna_rvp_live(e).status, "fail")

    def test_review_missing_a_protection_resource_fails_cna_rvp(self):
        e = env()
        e.grc["protection_reviews"][-1]["resources_covered"] = ["aws_wafv2_web_acl.edge"]
        self.assertEqual(g.cna_rvp_live(e).status, "fail")

    def test_run_date_is_today_unless_pinned(self):
        saved = os.environ.pop(AS_OF_VARIABLE, None)
        try:
            self.assertEqual(run_date(), datetime.datetime.now(datetime.timezone.utc).date())
            os.environ[AS_OF_VARIABLE] = "2027-03-01"
            self.assertEqual(run_date(), datetime.date(2027, 3, 1))
        finally:
            os.environ.pop(AS_OF_VARIABLE, None)
            if saved:
                os.environ[AS_OF_VARIABLE] = saved

    def test_records_go_overdue_as_the_run_date_moves(self):
        e = env()
        e.as_of = datetime.date(2028, 1, 1)
        self.assertEqual(g.inr_rir_live(e).status, "fail")
        self.assertEqual(g.cna_rvp_live(e).status, "fail")
        self.assertEqual(g.rpl_rro_live(e).status, "fail")

    def test_recovery_objectives_review_by_wrong_person_fails_rpl_rro(self):
        obj = g._load("environment/recovery-objectives.json")
        obj["reviews"] = [{"date": "2026-11-22", "reviewed_by": "GRC Lead"}]
        original = g._load
        g._load = lambda rel: obj if rel == "environment/recovery-objectives.json" else original(rel)
        try:
            self.assertEqual(g.rpl_rro_live(env()).status, "fail")
        finally:
            g._load = original

    def test_overdue_or_wrong_person_change_procedure_review_fails_cmt_rvp(self):
        e = env()
        self.assertEqual(g.cmt_rvp_live(e).status, "pass")
        e.as_of = datetime.date(2027, 10, 3)
        self.assertEqual(g.cmt_rvp_live(e).status, "fail")
        e = env()
        e.grc["change_procedure"]["reviews"].append({"date": "2026-11-20", "reviewed_by": "GRC Lead"})
        self.assertEqual(g.cmt_rvp_live(e).status, "fail")

    def test_failed_change_needs_a_review_within_10_business_days(self):
        e = env()
        self.assertEqual(g.cmt_rvp_change(e).status, "pass")
        e.grc["change_procedure"]["failed_or_emergency_changes"].append({"id": "CHG-T", "date": "2026-11-16", "type": "emergency"})
        r = g.cmt_rvp_change(e)
        self.assertEqual(r.status, "pass")
        self.assertIn("due by 2026-11-30", r.observed)
        e.as_of = datetime.date(2026, 12, 1)
        self.assertEqual(g.cmt_rvp_change(e).status, "fail")

    def test_untyped_or_unknown_change_type_fails_lmc(self):
        from validators import methods_tech as t
        e = env()
        self.assertEqual(t.lmc_change_types(e).status, "pass")
        e.live["change_events"]["last_30_days"]["pipeline_changes_typed"] = 210
        self.assertEqual(t.lmc_change_types(e).status, "fail")
        e = env()
        e.live["change_events"]["last_30_days"]["change_types"]["not_applicable"] = 0
        self.assertEqual(t.lmc_change_types(e).status, "fail")

    def test_change_review_deadlines_by_type(self):
        as_of = g.datetime.date(2026, 11, 19)
        late = [{"id": "SC-T1", "date": "2026-10-01", "scn_category": "adaptive"}]
        f, n = g._change_review_findings("review", late, ["2026-09-01"], as_of)
        self.assertTrue(f and not n)
        pending = [{"id": "SC-T2", "date": "2026-11-18", "scn_category": "not_significant"}]
        f, n = g._change_review_findings("review", pending, [], as_of)
        self.assertTrue(n and not f)
        transformative = [{"id": "SC-T3", "date": "2026-11-02", "scn_category": "transformative"}]
        f, n = g._change_review_findings("review", transformative, ["2026-11-03"], as_of)
        self.assertTrue(any("before the change" in x for x in f))
        routine = [{"id": "SC-T4", "date": "2026-01-01", "scn_category": "routine"}]
        self.assertEqual(g._change_review_findings("review", routine, [], as_of), ([], []))

    def test_password_only_user_fails_apm(self):
        e = env()
        e.live["identity"]["users_password_only"] = 1
        e.live["identity"]["users_phishing_resistant_mfa"] -= 1
        self.assertEqual(m.apm_live(e).status, "fail")


class EmptySource(unittest.TestCase):
    """Issue #44: a method must fail when the source it reads is missing or empty (FRC-CSX-VVK)."""

    # (method, the Env field that holds its source, the key to empty, or None to empty the whole field)
    CASES = [
        (m.rnt_static, "iac", None), (m.rnt_live, "live", "security_groups"),
        (m.elp_static, "iac", None), (m.elp_live, "live", "iam"),
        (m.sin_static, "iac", None), (m.sin_live, "live", None),
        (m.eis_live, "live", "drift"), (m.asm_live, "live", "secrets"),
        (m.vcm_static, "iac", None),
        (t.dfp_static, "iac", None), (t.dfp_live, "live", "iam_roles"),
        (t.rmv_live, "live", "compute"), (t.snu_static, "iac", None),
        (o.giv_live, "live", None),
    ]

    def test_each_method_passes_on_its_real_source(self):
        e = env()
        for fn, _, _ in self.CASES:
            self.assertFalse(any(f.startswith("Source is") for f in fn(e).findings), fn.__name__)

    def test_each_method_fails_when_its_source_is_empty(self):
        for fn, field_name, key in self.CASES:
            for blank in ({}, []) if key else ({},):
                e = env()
                if key is None:
                    setattr(e, field_name, {})
                else:
                    getattr(e, field_name)[key] = blank
                r = fn(e)
                self.assertEqual(r.status, "fail", f"{fn.__name__} passed with {field_name}.{key or '*'} = {blank!r}")

    def test_each_method_fails_when_its_source_is_missing(self):
        for fn, field_name, key in self.CASES:
            if key is None:
                continue
            e = env()
            del getattr(e, field_name)[key]
            self.assertEqual(fn(e).status, "fail", f"{fn.__name__} passed with {field_name}.{key} missing")

    def test_allowed_empty_list_still_passes(self):
        # No unmanaged resources and no wildcard attachments are good states, not missing data.
        e = env()
        e.live["drift"]["unmanaged_resources"] = []
        e.live["iam"]["wildcard_admin_attachments"] = []
        self.assertFalse(any(f.startswith("Source is") for f in m.eis_live(e).findings))
        self.assertFalse(any(f.startswith("Source is") for f in m.elp_live(e).findings))


class CoverageMethods(unittest.TestCase):
    """Issue #39: the methods that close the coverage gaps. Each passes on the demo data, fails on an
    empty source, and fails on each recorded break test."""

    def setUp(self):
        from unittest import mock
        from validators import methods_cover as c
        self.c, self.mock = c, mock
        self.files = {}  # file overrides for methods that read their own file

    def run_method(self, fn, e, files=None):
        real = self.c._file
        files = files or {}
        with self.mock.patch.object(self.c, "_file", side_effect=lambda rel: copy.deepcopy(files[rel]) if rel in files else real(rel)):
            return fn(e)

    def f(self, rel):
        return copy.deepcopy(self.c._file(rel))

    def assert_fails(self, fn, change, files_change=None, label=""):
        e, files = env(), {}
        if change:
            change(e)
        if files_change:
            rel, edit = files_change
            d = self.f(rel)
            edit(d)
            files[rel] = d
        r = self.run_method(fn, e, files)
        self.assertEqual(r.status, "fail", f"{fn.__name__} did not fail: {label}")
        return r

    def methods(self):
        c = self.c
        return [c.osm_review, c.uln_review, c.ofa_recovery, c.prr_plans, c.asm_keys_certs, c.trc_history, c.rud_terms,
                c.aam_role_group_lifecycle, c.jit_non_user, c.eis_remediation, c.dfp_network_data, c.let_list, c.giv_people,
                c.vri_artifacts, c.sin_modification, c.ala_classes, c.evc_saas, c.ibp_saas, c.vcm_client_auth]

    def test_each_method_passes_on_the_demo_data(self):
        e = env()
        for fn in self.methods():
            r = self.run_method(fn, e)
            self.assertEqual(r.status, "pass", f"{fn.__name__}: {r.findings}")

    def test_each_method_fails_on_empty_sources(self):
        # Blank everything a method can read: the live snapshot, the GRC records, the IaC plan and its own files.
        empty_files = {rel: {} for rel in ("environment/recovery-objectives.json", "environment/customer-terms.json",
                       "environment/network-privileges.json", "environment/logging-list.json", "environment/log-classes.json",
                       "environment/saas-config.json", "mas/scope-changes.json")}
        for fn in self.methods():
            e = env()
            e.live, e.grc, e.iac = {}, {}, {}
            self.assertEqual(self.run_method(fn, e, empty_files).status, "fail", fn.__name__)

    # ---- break tests: one or more changes per method that must make it fail ----
    def test_break_osm(self):
        def age(e): e.live["siem_reviews"][-1]["days_ago"] = 120; e.live["siem_reviews"][1]["days_ago"] = 121; e.live["siem_reviews"][0]["days_ago"] = 150
        self.assert_fails(self.c.osm_review, age, label="review past cycle")
        self.assert_fails(self.c.osm_review, lambda e: e.live["siem_reviews"][-1].update(reviewed_by="Platform Lead"), label="wrong reviewer")
        self.assert_fails(self.c.osm_review, lambda e: e.live["siem_reviews"][-1].update(sources_checked=4), label="sources missed")

    def test_break_uln(self):
        self.assert_fails(self.c.uln_review, lambda e: e.live["traffic_flow_reviews"][-1].update(days_ago=100), label="review past cycle")
        self.assert_fails(self.c.uln_review, lambda e: e.live["traffic_flow_reviews"][-1].update(reviewed_by="CISO"), label="wrong reviewer")

    def test_break_ofa(self):
        self.assert_fails(self.c.ofa_recovery, lambda e: e.live["restore_tests"][-1].update(achieved_rto_hours=9.5), label="RTO missed")
        self.assert_fails(self.c.ofa_recovery, lambda e: e.live["restore_tests"][-1].update(from_vault="primary"), label="same-region restore")

    def test_break_prr(self):
        self.assert_fails(self.c.prr_plans, lambda e: e.grc["change_plan_reviews"][0].update(plans_reviewed=[]), label="no plans reviewed")
        e = env()
        e.grc["change_plan_reviews"] = []
        e.as_of = datetime.date(2026, 12, 31)
        self.assertEqual(self.run_method(self.c.prr_plans, e).status, "fail", "change unreviewed after 28 days")

    def test_break_asm(self):
        self.assert_fails(self.c.asm_keys_certs, lambda e: e.live["kms_keys"][0].update(rotation_enabled=False), label="rotation off")
        self.assert_fails(self.c.asm_keys_certs, lambda e: e.live["certificates"][0].update(expires_in_days=10), label="certificate near expiry")
        self.assert_fails(self.c.asm_keys_certs, lambda e: e.live["certificates"][0].update(auto_renew=False), label="no auto renew")

    def test_break_trc(self):
        self.assert_fails(self.c.trc_history, lambda e: e.live["restore_tests"].pop(1), label="a missed cycle")
        self.assert_fails(self.c.trc_history, lambda e: e.live["restore_tests"][0].update(achieved_rto_hours=12), label="RTO missed in history")

    def test_break_rud(self):
        self.assert_fails(self.c.rud_terms, lambda e: e.live["data_removal_requests"][0].update(completed_days=31), label="request on day 31")
        self.assert_fails(self.c.rud_terms, None, ("environment/customer-terms.json", lambda d: d.update(deletion_days=10)), label="process longer than term")

    def test_break_aam(self):
        self.assert_fails(self.c.aam_role_group_lifecycle, lambda e: e.live["iam_change_events"].append(
            {"target": "role/console-test", "kind": "role", "action": "create", "actor": "user:eng-04", "days_ago": 3}), label="console-made role")
        self.assert_fails(self.c.aam_role_group_lifecycle, lambda e: e.live["iam_roles"].append(
            {"name": "role/shadow", "scope": "P1", "wildcard_actions": []}), label="undeclared live role")

    def test_break_jit(self):
        self.assert_fails(self.c.jit_non_user, lambda e: e.live["service_accounts"][0].update(standing_admin=True), label="standing admin")
        self.assert_fails(self.c.jit_non_user, lambda e: e.live["jit_reviews"][-1].update(days_ago=200), label="review past cycle")

    def test_break_eis(self):
        def drop(e): e.iac["resources"] = [r for r in e.iac["resources"] if not (r["type"] == "aws_config_remediation_configuration" and r["name"] == "sg_no_open_admin_ports")]
        self.assert_fails(self.c.eis_remediation, drop, label="rule with no remediation")
        self.assert_fails(self.c.eis_remediation, lambda e: e.live["remediation_log"][0].update(corrected_minutes=120), label="drift not corrected in time")

    def test_break_dfp(self):
        self.assert_fails(self.c.dfp_network_data, lambda e: e.live["security_groups"][2]["ingress"].append({"port": 22, "cidr": "0.0.0.0/0"}), label="SSH open")
        self.assert_fails(self.c.dfp_network_data, lambda e: e.live["s3_buckets"][0]["policy_principals"].append("*"), label="wildcard principal")

    def test_break_let(self):
        self.assert_fails(self.c.let_list, None, ("environment/logging-list.json", lambda d: d["resources"].pop(0)), label="resource dropped")
        self.assert_fails(self.c.let_list, None, ("environment/logging-list.json", lambda d: d.update(last_review_days_ago=400)), label="review past cycle")
        self.assert_fails(self.c.let_list, lambda e: e.live["siem"]["sources_reporting"].remove("cloudtrail"), label="source off")

    def test_break_giv(self):
        self.assert_fails(self.c.giv_people, lambda e: e.live["idp_users"].append({"id": "u-9999", "people_resource": "N9", "status": "active"}), label="unmapped user")
        self.assert_fails(self.c.giv_people, lambda e: e.grc["third_party_register"].pop(), label="vendor removed")

    def test_break_vri(self):
        self.assert_fails(self.c.vri_artifacts, lambda e: e.live["artifact_signatures"][0].update(signed=False), label="unsigned module")

    def test_break_sin(self):
        self.assert_fails(self.c.sin_modification, lambda e: e.live["s3_buckets"][0].update(versioning=False), label="versioning off")
        self.assert_fails(self.c.sin_modification, lambda e: e.live["rds_instances"][0].update(deletion_protection=False), label="no deletion protection")

    def test_break_ala(self):
        self.assert_fails(self.c.ala_classes, lambda e: e.live["log_access"]["grants_last_90d"][0].update(classes=["C1", "C3"]), label="broad grant on C3")
        self.assert_fails(self.c.ala_classes, None, ("environment/log-classes.json", lambda d: d["access_map"].update({"auditor": ["C1"]})), label="grant outside map")
        self.assert_fails(self.c.ala_classes, lambda e: e.live["log_access"]["grants_last_90d"][1].update(type="standing_read"), label="C3 without JIT")

    def test_break_evc_and_ibp(self):
        saas = "environment/saas-config.json"
        self.assert_fails(self.c.evc_saas, None, (saas, lambda d: d["exports"]["E1"].update(collected_days_ago=9)), label="stale export")
        self.assert_fails(self.c.evc_saas, None, (saas, lambda d: d["exports"]["E9"].update(settings=[])), label="empty export")
        self.assert_fails(self.c.evc_saas, None, (saas, lambda d: d["exports"]["E7"]["settings"][-1].pop("exception")), label="deviation with no exception")
        self.assert_fails(self.c.ibp_saas, None, (saas, lambda d: d["exports"]["E7"].update(last_review_days_ago=120)), label="comparison past cycle")
        self.assert_fails(self.c.ibp_saas, None, (saas, lambda d: d["exceptions"][0].update(expires_days=0)), label="expired exception")

    def test_break_vcm(self):
        self.assert_fails(self.c.vcm_client_auth, lambda e: e.live["flow_auth"][0].update(client_authenticated=False), label="no client auth")
        self.assert_fails(self.c.vcm_client_auth, lambda e: e.live["flow_auth"].pop(), label="flow not observed")


class History(unittest.TestCase):
    """Issue #47: a later run on the same day must not replace the record of an earlier run."""

    def _ksis(self, status):
        method = {"method_id": "rnt-live-traffic", "status": "fail" if status == "fail" else "pass"}
        return [{"id": "KSI-CNA-RNT", "status": status, "methods": [method]}]

    def test_two_runs_on_one_day_keep_both_records(self):
        import tempfile
        from datetime import datetime, timezone
        from tools.run_validators import write_history
        with tempfile.TemporaryDirectory() as d:
            hist = Path(d)
            morning = datetime(2026, 11, 23, 6, 17, tzinfo=timezone.utc)
            afternoon = datetime(2026, 11, 23, 15, 0, tzinfo=timezone.utc)
            first = write_history(hist, morning, self._ksis("fail"))
            write_history(hist, afternoon, self._ksis("pass"))
            self.assertEqual(len(list((hist / "runs").glob("*.json"))), 2)
            kept = json.loads(first.read_text())
            self.assertEqual(kept["ksi_status"]["KSI-CNA-RNT"], "fail")
            self.assertEqual(kept["methods_not_passing"], {"KSI-CNA-RNT": ["rnt-live-traffic"]})
            day = json.loads((hist / "2026-11-23.json").read_text())
            self.assertEqual(day["ksi_status"]["KSI-CNA-RNT"], "pass")
            self.assertEqual(len(day["runs"]), 2)
            self.assertEqual(day["not_passing_in_any_run"], ["KSI-CNA-RNT"])

    def test_two_runs_in_one_second_do_not_overwrite(self):
        import tempfile
        from datetime import datetime, timezone
        from tools.run_validators import write_history
        with tempfile.TemporaryDirectory() as d:
            now = datetime(2026, 11, 23, 6, 17, tzinfo=timezone.utc)
            a = write_history(Path(d), now, self._ksis("fail"))
            b = write_history(Path(d), now, self._ksis("pass"))
            self.assertNotEqual(a, b)
            self.assertEqual(json.loads(a.read_text())["ksi_status"]["KSI-CNA-RNT"], "fail")


class ScopeLog(unittest.TestCase):
    def test_fingerprint_changes_when_a_resource_moves_out(self):
        rec = load("mas/mas-record.json")
        before = scl.fingerprint(rec)
        rec2 = copy.deepcopy(rec)
        rec2["information_resources"][0]["decision"] = "out_of_scope"
        self.assertNotEqual(before, scl.fingerprint(rec2))

    def test_fingerprint_is_stable(self):
        rec = load("mas/mas-record.json")
        self.assertEqual(scl.fingerprint(rec), scl.fingerprint(copy.deepcopy(rec)))

    def _condition(self, rec, cond_id):
        return next(c for r in rec["information_resources"] for c in (r.get("conditions") or []) if c["id"] == cond_id)

    def test_fingerprint_changes_when_condition_text_changes(self):
        # Issue #38: the test of 2026-11-22 changed COND-S1-1 to allow alert content in tickets.
        rec = load("mas/mas-record.json")
        before = scl.fingerprint(rec)
        self._condition(rec, "COND-S1-1")["text"] = "Structured intake accepts alert content in tickets."
        self.assertNotEqual(before, scl.fingerprint(rec))
        self.assertEqual(scl.fingerprint(load("mas/mas-record.json"), 1), scl.fingerprint(rec, 1),
                         "method 1 is blind to this change, which is why method 2 exists")

    def test_fingerprint_changes_when_condition_evidence_is_removed(self):
        rec = load("mas/mas-record.json")
        before = scl.fingerprint(rec)
        self._condition(rec, "COND-S1-1")["evidence"] = ""
        self.assertNotEqual(before, scl.fingerprint(rec))

    def test_current_log_matches_the_record(self):
        ref, method, problems = scl.reference(load("mas/scope-changes.json"))
        self.assertEqual(problems, [])
        self.assertEqual(method, scl.CURRENT_METHOD)
        self.assertEqual(ref, scl.fingerprint(load("mas/mas-record.json")))

    def test_rebaseline_cannot_hide_a_scope_change(self):
        log = load("mas/scope-changes.json")
        log["rebaselines"][0]["fingerprint_before"] = "0000000000000000"
        _, _, problems = scl.reference(log)
        self.assertTrue(any("fingerprint_before" in p for p in problems))

    def test_log_without_rebaseline_is_flagged(self):
        log = load("mas/scope-changes.json")
        del log["rebaselines"]
        _, _, problems = scl.reference(log)
        self.assertTrue(any("add a rebaseline" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
