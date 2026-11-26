#!/usr/bin/env python3
"""Offline regression tests for V2.0.1 runtime-evidence precedence.

These tests do not need game files or a real .stage. Run:
  python -I -m unittest discover -s tests -p "test_verdict_policy.py"
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "stage_enemies"))
import stage_allgame as SA  # noqa: E402

ARDOLIS = "AE530D22FE113E2B"
OLD_UID = "92C793D47A4657B6"
NEW_UID = "D78BDDE784EF233E"


class VerdictPolicyTests(unittest.TestCase):
    def test_latest_no_spawn_suppresses_historical_pin(self):
        verdicts = {ARDOLIS: {"FF06CCC2A9AC1EA2": ("NO SPAWN", OLD_UID)}}
        self.assertNotIn("FF06CCC2A9AC1EA2",
                         {k for k, _, _ in SA.effective_pins(ARDOLIS, verdicts)})

    def test_latest_worked_replaces_historical_pin_uid(self):
        verdicts = {ARDOLIS: {"FF06CCC2A9AC1EA2": ("WORKED", NEW_UID)}}
        pins = {k: uid for k, uid, _ in SA.effective_pins(ARDOLIS, verdicts)}
        self.assertEqual(pins["FF06CCC2A9AC1EA2"], NEW_UID)

    def test_new_worked_spawner_becomes_dynamic_pin(self):
        verdicts = {ARDOLIS: {"B2B978B5BC3D8A4D": ("WORKED", NEW_UID)}}
        pins = {k: uid for k, uid, _ in SA.effective_pins(ARDOLIS, verdicts)}
        self.assertEqual(pins["B2B978B5BC3D8A4D"], NEW_UID)

    def test_later_failure_overrides_earlier_worked(self):
        old = ("WORKED", OLD_UID)
        latest = ("NO SPAWN", NEW_UID)
        self.assertEqual(SA.merge_verdict_entry(old, latest), latest)

    def test_later_worked_overrides_earlier_failure(self):
        old = ("NO SPAWN", OLD_UID)
        latest = ("WORKED", NEW_UID)
        self.assertEqual(SA.merge_verdict_entry(old, latest), latest)

    def test_not_reached_does_not_erase_worked(self):
        old = ("WORKED", OLD_UID)
        self.assertEqual(SA.merge_verdict_entry(old, ("NOT REACHED", None)), old)

    def test_not_reached_does_not_erase_failure(self):
        old = ("NO SPAWN", OLD_UID)
        self.assertEqual(SA.merge_verdict_entry(old, ("NOT REACHED", None)), old)

    def test_no_pins_disables_static_and_dynamic_pins(self):
        verdicts = {ARDOLIS: {
            "FF06CCC2A9AC1EA2": ("WORKED", NEW_UID),
            "B2B978B5BC3D8A4D": ("WORKED", OLD_UID),
        }}
        self.assertEqual(SA.effective_pins(ARDOLIS, verdicts, no_pins=True), [])

    def test_bundled_latest_evidence_has_expected_170_verdicts(self):
        import json
        from collections import Counter
        path = os.path.join(SA.HERE, "evidence", "verdicts_2026-11-26_015324.json")
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        counts = Counter(v["verdict"] for v in payload["verdicts"].values())
        self.assertEqual(len(payload["verdicts"]), 170)
        self.assertEqual(counts, Counter({"WORKED": 5, "NO SPAWN": 31, "NOT REACHED": 134}))

    def test_external_factory_uid_is_preserved_for_force_mode(self):
        from stage_allgame import Zone
        z = Zone.__new__(Zone)
        node = {"key": 0x1234, "r": 7, "cls": SA.FACTORY_CLASS, "plugs": [0]}
        z.nodes = [node]
        z.plugs = [(SA.PLUG_TEMPLATES, 0, 0)]
        z.vars = [(5, 0, 0xFFFF, 0, 0, int("ABCDEF1234567890", 16), 0)]
        z.owners = {0: [(node, 0, SA.PLUG_TEMPLATES)]}
        z.dup_keys = set()
        z.actors = []
        z.rec_of = {}
        z.dup_uids = {}
        factory = z.factories()[0]
        self.assertEqual(factory["form"], "external")
        self.assertEqual(factory["uid"], "ABCDEF1234567890")
        self.assertEqual(factory["rec"], 0xFFFF)

    def test_force_mode_emits_global_external_enemy_replacement(self):
        from types import SimpleNamespace
        class Brain:
            def regular(self, kind, asset=None):
                return True, "ground", "test family"
            def pair(self, original, original_family, replacement, replacement_family):
                return True, "proven", "test compatible pair"
        original = "1111111111111111"
        replacement = "2222222222222222"
        candidate = {"uid": replacement, "kind": "enm_pirate_robot_melee", "asset": "enemy.actor",
                     "rec": 4, "zone_id": "BBBBBBBBBBBBBBBB", "zone": "foreign.zone",
                     "planet": "ardolis"}
        spawner = {"key": "AAAAAAAAAAAAAAAA", "action": 1, "problem": None, "form": "local",
                   "uid": original, "sv": 0, "rec": 2, "kind": "enm_pirate_robot_shooter",
                   "asset": "enemy.actor", "owners": 1, "locs": []}
        scan = SimpleNamespace(template_catalog={replacement: candidate}, actor_catalog={})
        rec = {"factories": [spawner], "zone_id": "CCCCCCCCCCCCCCCC",
               "zone": "target.zone", "planet": "savali"}
        opts = SimpleNamespace(verdict_map={})
        from unittest.mock import patch
        with patch.object(SA, "spawn_points_ok", return_value=(True, "volume", "verified test spawn point")):
            changes, decisions, _, _ = SA.plan_zone_force(scan, Brain(), rec, opts, __import__("random").Random(7))
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["replacement_uid"], replacement)
        self.assertEqual(changes[0]["replacement_index"], 0xFFFF)
        self.assertTrue(changes[0]["replacement_external"])
        self.assertTrue(changes[0]["tier"].startswith("FORCED-"))
        self.assertEqual(decisions[spawner["key"]][0], "changed")

    def test_force_mode_does_not_repeat_latest_failed_uid(self):
        from types import SimpleNamespace
        class Brain:
            def regular(self, kind, asset=None):
                return True, "ground", "test family"
            def pair(self, original, original_family, replacement, replacement_family):
                return True, "proven", "test compatible pair"
        replacement = "2222222222222222"
        candidate = {"uid": replacement, "kind": "enm_pirate_robot_melee", "asset": "enemy.actor",
                     "rec": 4, "zone_id": "BBBBBBBBBBBBBBBB", "zone": "foreign.zone",
                     "planet": "ardolis"}
        spawner = {"key": "AAAAAAAAAAAAAAAA", "action": 1, "problem": None, "form": "local",
                   "uid": "1111111111111111", "sv": 0, "rec": 2, "kind": "enm_pirate_robot_shooter",
                   "asset": "enemy.actor", "owners": 1, "locs": []}
        scan = SimpleNamespace(template_catalog={replacement: candidate}, actor_catalog={})
        rec = {"factories": [spawner], "zone_id": "CCCCCCCCCCCCCCCC",
               "zone": "target.zone", "planet": "savali"}
        opts = SimpleNamespace(verdict_map={"CCCCCCCCCCCCCCCC": {
            spawner["key"]: ("NO SPAWN", replacement)}})
        changes, decisions, _, _ = SA.plan_zone_force(scan, Brain(), rec, opts, __import__("random").Random(7))
        self.assertEqual(changes, [])
        self.assertEqual(decisions[spawner["key"]][0], "refused")
 
    def test_force_mode_never_replaces_boss_tier_originals(self):
        from types import SimpleNamespace
        class Brain:
            def regular(self, kind, asset=None):
                if "boss" in kind: return False, None, "boss-tier"
                return True, "ground", "regular enemy"
            def pair(self, *args): return True, "proven", "compatible"
        candidate = {"uid": "2222222222222222", "kind": "enm_pirate_robot_melee", "asset": "enemy.actor",
                     "rec": 4, "zone_id": "BBBBBBBBBBBBBBBB", "zone": "foreign.zone", "planet": "ardolis"}
        spawner = {"key": "AAAAAAAAAAAAAAAA", "action": 1, "problem": None, "form": "local",
                   "uid": "1111111111111111", "sv": 0, "rec": 2, "kind": "enm_seabase_boss",
                   "asset": "boss.actor", "owners": 1, "locs": [{"kind": "volume"}]}
        scan = SimpleNamespace(template_catalog={candidate["uid"]: candidate}, actor_catalog={})
        rec = {"factories": [spawner], "zone_id": "CCCCCCCCCCCCCCCC", "zone": "target.zone", "planet": "cordelion"}
        changes, decisions, _, _ = SA.plan_zone_force(scan, Brain(), rec,
            SimpleNamespace(verdict_map={}), __import__("random").Random(7))
        self.assertEqual(changes, [])
        self.assertEqual(decisions[spawner["key"]][0], "refused")

    def test_force_mode_refuses_unverified_spawn_points(self):
        from types import SimpleNamespace
        class Brain:
            def regular(self, kind, asset=None): return True, "ground", "regular enemy"
            def pair(self, *args): return True, "proven", "compatible"
        candidate = {"uid": "2222222222222222", "kind": "enm_pirate_robot_melee", "asset": "enemy.actor",
                     "rec": 4, "zone_id": "BBBBBBBBBBBBBBBB", "zone": "foreign.zone", "planet": "ardolis"}
        spawner = {"key": "AAAAAAAAAAAAAAAA", "action": 1, "problem": None, "form": "local",
                   "uid": "1111111111111111", "sv": 0, "rec": 2, "kind": "enm_pirate_robot_shooter",
                   "asset": "enemy.actor", "owners": 1, "locs": []}
        scan = SimpleNamespace(template_catalog={candidate["uid"]: candidate}, actor_catalog={})
        rec = {"factories": [spawner], "zone_id": "CCCCCCCCCCCCCCCC", "zone": "target.zone", "planet": "savali"}
        changes, decisions, _, _ = SA.plan_zone_force(scan, Brain(), rec,
            SimpleNamespace(verdict_map={}), __import__("random").Random(7))
        self.assertEqual(changes, [])
        self.assertEqual(decisions[spawner["key"]][0], "refused")

    def test_other_zone_pins_are_not_leaked(self):
        verdicts = {ARDOLIS: {"B2B978B5BC3D8A4D": ("WORKED", NEW_UID)}}
        self.assertEqual(SA.effective_pins("0000000000000000", verdicts), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
