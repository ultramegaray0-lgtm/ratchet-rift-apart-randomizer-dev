"""The dev 10.26 test (tests/data/round37_rivet.log, 2026-11-18): the FIRST enemy replacements in the real game.

Facts read from the real game log only. The game itself named every actor it created (rivet.name of the spawned
handle, its bot class from rivet.components): after spawnproof v6 wrote the robot melee Templates value into three
not-yet-spawned robot-shooter factories, every enemy those factories created was a robot melee - in two separate runs
of challenge A1, which completed both times; every write was put back afterwards.
Not covered here: what the player saw on screen (to be confirmed by the player).
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "tests" / "data" / "round37_rivet.log"


def text():
    return LOG.read_text(encoding="utf-8")


class RoundThirtySevenLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_dev_10_26_ran(self):
        t = text()
        self.assertIn("RANDO-NOTIFY\tRandomizer dev 10.26 - seed", t)
        self.assertIn("RANDO-SPAWNPROOF\tv6 loaded (factory Templates route, fresh factories)", t)

    def test_two_experiments_on_fresh_factories(self):
        exps = re.findall(r"EXPERIMENT (\d): \S+enm_pirate_robot_sh -> \S+enm_pirate_robot_me on 3 factory\(ies\) that have not spawned yet", text())
        self.assertEqual(exps, ["1", "2"])
        armed = [l for l in text().splitlines() if "\tARMED " in l]
        self.assertEqual(len(armed), 6)
        self.assertTrue(all("spawned 0 time(s) so far" in l and "read back OK" in l for l in armed))

    def test_every_armed_factory_spawned_the_replacement(self):
        t = text()
        verify = [l for l in t.splitlines() if "\tVERIFY node factory" in l]
        self.assertEqual(len(verify), 6)
        self.assertTrue(all(l.endswith("REPLACEMENT SPAWNED") for l in verify))
        after = [l for l in t.splitlines() if "[ARMED factory variable" in l]
        self.assertEqual(len(after), 20)
        self.assertTrue(all("enm_pirate_robot_me" in l and "GameBotMeleeSwarmer" in l for l in after))
        self.assertNotIn("ORIGINAL SPAWNED", t)
        self.assertNotIn("SOMETHING ELSE SPAWNED", t)

    def test_the_challenge_completed_and_everything_was_put_back(self):
        t = text()
        self.assertEqual(len(re.findall(r"EndReason=0 IsReplay=true MissionDuration=2\d\d\.\d+ MissionName=MIS_ZURK_ARENA_CHALLENGE_A1", t)), 2)
        puts = re.findall(r"put back \(level changed: checkpoint loaded\): node factory \d+ ftemplate = \d+: variable OK", t)
        self.assertEqual(len(puts), 6)
        self.assertNotIn("RANDO-ERROR", t)


if __name__ == "__main__":
    unittest.main()
