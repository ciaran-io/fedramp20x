"""Unit tests. Run with `make test` (python -m unittest)."""
import copy
import json
import unittest
from pathlib import Path

from tools import check_scope_changes as scl
from validators import methods as m
from validators import methods_ops as o
from validators.base import Env
from validators.registry import KSI_METHODS, KSI_GAPS, KSI_NOTES

ROOT = Path(__file__).resolve().parent.parent


def load(p):
    return json.loads((ROOT / p).read_text())


def env():
    return Env(company=load("environment/company.json"), iac=load("environment/iac-plan.json"),
               live=load("environment/live-state.json"), mas=load("mas/mas-record.json"),
               grc=load("environment/grc-records.json"))


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

    def test_password_only_user_fails_apm(self):
        e = env()
        e.live["identity"]["users_password_only"] = 1
        e.live["identity"]["users_phishing_resistant_mfa"] -= 1
        self.assertEqual(m.apm_live(e).status, "fail")


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
