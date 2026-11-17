"""Dev 10.26 (kit 10.0.17): after the dev 10.25 log of 2026-11-18 (tests/data/round36_rivet.log: dev 10.25 scripts and
v7 helper; Zurkon arena challenge A1 replayed and completed).

RoundThirtySixLogTests: facts read from the real game log. The first in-game WRITE of an enemy Templates value happened
and read back OK - on a factory that had already spawned its enemies and never spawned again, so nothing could be
verified. (The simulator tests of v6's new choice - fresh factories only - are in tests/test_v1025.py.)
Nothing in this file is in-game verification of a replacement.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "tests" / "data" / "round36_rivet.log"


def text():
    return LOG.read_text(encoding="utf-8")


class RoundThirtySixLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_dev_10_25_ran(self):
        t = text()
        self.assertIn("RANDO-NOTIFY\tRandomizer dev 10.25 - seed", t)
        self.assertIn("RANDO-SPAWNPROOF\tv5 loaded (factory Templates route)", t)
        self.assertIn("RANDO-SPAWNPROOF\tSceneManager 7FF7A5857580 (signature matched 1 x)", t)

    def test_the_first_enemy_templates_write_read_back_ok(self):
        t = text()
        self.assertIn("factory 1109878 chosen (a factory that already spawned first; spawned 4 time(s) on this level", t)
        armed = next(l for l in t.splitlines() if "\tARMED 1/4 node factory 1109878" in l)
        self.assertIn("enm_pirate_robot_me (handle 1109383", armed)
        self.assertIn("-> characters\\enemy\\enm_pirate_robot_q4b\\actors\\enm_pirate_robot_sh (handle 1109378", armed)
        self.assertIn("read back OK", armed)
        self.assertIn("put back (level changed: checkpoint loaded): node factory 1109878 ftemplate = 1109383: variable OK", t)

    def test_the_armed_factory_never_spawned_again(self):
        t = text()
        before, after = t.split("\tARMED 1/4 node factory 1109878", 1)
        after = after.split("put back (level changed", 1)[0]
        self.assertEqual(len(re.findall(r"SpawnFactory 1109878,", before)), 4)
        self.assertEqual(len(re.findall(r"SpawnFactory 1109878,", after)), 0)
        self.assertNotIn("VERIFY", t)
        # the fight went on with OTHER factories; every factory still one kind
        self.assertGreater(len(re.findall(r"SpawnFactory 11098\d\d,", after)), 20)

    def test_the_challenge_still_completed(self):
        self.assertIn("MissionName=MIS_ZURK_ARENA_CHALLENGE_A1 MissionState=4 PreviousState=2", text())

    def test_same_templates_rule_as_round35(self):
        t = text()
        pairs = set(re.findall(r"SpawnFactory (11098\d\d), [^\n]*?factory Templates = (\d+); spawned (\S+) \(handle", t))
        by_tpl = {}
        for _, tpl, name in pairs:
            by_tpl.setdefault(tpl, set()).add(name)
        self.assertEqual(len(by_tpl), 3)
        self.assertTrue(all(len(v) == 1 for v in by_tpl.values()), by_tpl)


if __name__ == "__main__":
    unittest.main()
