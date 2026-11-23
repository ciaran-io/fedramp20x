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


if __name__ == "__main__":
    unittest.main()
