"""Dev 10.24 (kit 10.0.17): after the dev 10.23 log of 2026-11-18 (tests/data/round34_rivet.log: NefCity, Zurkon arena
challenge A1 replayed and completed, NefCity; "Nothing changed").

  * RoundThirtyFourLogTests: facts read from the real game log - the planet fix worked; the experiment was blocked
    because the game folder still had rando_give.dll v6.
  * KitDllTests: the kit's rando_give.dll is now the v7 build (byte hashes; no compiler needed); the public package
    keeps the v6 binary.
  * BlockedOnScreenTests: dev(spawnproof).lua v4 in the SIMULATOR says on screen why it cannot work.
Nothing in this file is in-game verification.
"""
import hashlib
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402

LOG = ROOT / "tests" / "data" / "round34_rivet.log"
MOD = ROOT / "mod" / "RiftApartRandomizer"
V7 = "8055703e7dd7f48e16aa5a081d6795c15d515a52802bd0d70aafe88b54640744"
V6 = "efb927232f67b7740aec473afa3866dd50636e1c29d0b2822717116a40092c12"


def text():
    return LOG.read_text(encoding="utf-8")


class RoundThirtyFourLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_kit_10_0_17_and_spawnproof_v3_ran(self):
        t = text()
        self.assertIn("RANDO-KIT all 12 required scripts are 10.0.17", t)
        self.assertIn("RANDO-SPAWNPROOF\tv3 loaded:", t)
        self.assertIn("own events: planet yes, spawns yes", t)

    def test_the_planet_fix_worked(self):
        t = text()
        self.assertIn("RANDO-SPAWNPROOF\tlevel reset (planet Zurkon): ON ZURKON - active (event planet Zurkon", t)
        self.assertIn("RANDO-PLANET\tZurkon\tscarstu\trewards unlocked", t)
        on = re.findall(r"RANDO-CHECKPOINT\tCHK_ZURK\w+\thash \d+\ton\t(\w+)", t)
        self.assertTrue(on and all(p == "scarstu" for p in on), on)

    def test_the_experiment_was_blocked_by_the_v6_helper(self):
        t = text()
        lines = [l for l in t.splitlines() if "RANDO-SPAWNPROOF" in l]
        self.assertIn("RANDO-SPAWNPROOF\tno script variables:\trando_give.dll is v6, v7 is needed (copy the kit's)", t)
        self.assertFalse([l for l in lines if "\tscan " in l or "ARMED" in l or "\tspawn " in l])
        self.assertIn("MissionName=MIS_ZURK_ARENA_CHALLENGE_A1 MissionState=4 PreviousState=2", t)


class KitDllTests(unittest.TestCase):
    def test_the_kit_dll_is_v7(self):
        self.assertEqual(hashlib.sha256((MOD / "rando_give.dll").read_bytes()).hexdigest(), V7)

    def test_v6_is_kept_and_v060_packages_ship_v7(self):
        # v0.60: the public package ships v7 (the Enemy Randomizer needs it; it ran in the game from round32 on);
        # the v6 binary of v0.51-v0.55 stays in rando_give_source/release_v6 for reference
        v6 = MOD / "rando_give_source" / "release_v6" / "rando_give.dll"
        self.assertEqual(hashlib.sha256(v6.read_bytes()).hexdigest(), V6)
        import build_public_release as b
        dll = [src for src, dst in b.plan([]) if dst == "GAME_FOLDER/rando_give.dll"]
        self.assertEqual(dll, [b.RELEASE_DLL])
        self.assertEqual(b.DLL_SHA256, V7)

    def test_no_second_v7_copy_to_forget(self):
        self.assertFalse((MOD / "rando_give_source" / "dev_build").exists())

    def test_v7_ran_in_the_game_before(self):
        r32 = (ROOT / "tests" / "data" / "round32_rivet.log").read_text(encoding="utf-8")
        for line in ("SceneManager 7FF7A5857580 (signature matched 1 x)", "RANDO-ARMOR\thelper: armor give verified",
                     "direct delivery: helper at 7FEF00000000: ready", "mission helper:\tready"):
            self.assertIn(line, r32)


class BlockedOnScreenTests(unittest.TestCase):
    def test_an_old_helper_is_shown_on_screen(self):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True, dll_version=6)
        g.travel("Zurkon")
        g.step(200)
        self.assertTrue(g.note_has("SPAWNPROOF BLOCKED: rando_give.dll is v6, v7 is needed"), g.notes()[-4:])
        self.assertTrue(g.log_has("BLOCKED: no script variables:"))


if __name__ == "__main__":
    unittest.main()
