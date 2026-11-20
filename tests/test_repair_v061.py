"""Regression coverage for fixes derived from rivet(3).log.

These tests exercise the private v0.60-based repair port. They do not claim in-game
verification for untested enemy pairs or the Omega runtime.
"""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402


class EnemyCompatibilityRegressionTests(unittest.TestCase):
    def test_omega_probe_is_hero_scoped_and_contains_no_write_api(self):
        path = ROOT / "mod" / "RiftApartRandomizer" / "dev_scripts" / "dev(omega_inventory_probe).lua"
        source = path.read_text(encoding="utf-8")
        self.assertIn("local hero = rivet.hero and rivet.hero()", source)
        self.assertIn("pcall(rivet.components, hero)", source)
        self.assertIn("pcall(rivet.component, hero, class)", source)
        self.assertNotIn("rivet.write", source)
        self.assertNotIn("rivet.set_field", source)
        self.assertNotIn("rivet.find_component", source)


    def test_live_censused_templates_are_known_before_their_first_spawn(self):
        game = Game(settings={"enemy_randomizer": True, "enemy_compat": "all"})
        lua = game.lua
        cases = {
            "A947C2837C809670": "enm_indigenous_hornedtoad|swarmer|GameBotMeleeSwarmerJumper|enemy",
            "BCC5D8017879250F": "enm_thugs4less_shooterjetpack|flyer|GameBotShooterJetPack|enemy",
            "B55799EA1763D5DE": "enm_neo_nefarious_swarmer|swarmer|GameBotMeleeSwarmer|enemy",
            "82A9B65DDBA84005": "enm_indigenous_puffoid_blizar|swarmer|GameBotMeleeSwarmer|enemy",
            "9070B46C6C14744E": "enm_indigenous_sandshark|swarmer|GameBotMeleeSwarmerBurrower|enemy",
        }
        for uid, expected in cases.items():
            got = lua.eval('(RANDO_SPAWNERS.V.REG_BUILTIN["%s"])' % uid)
            self.assertEqual(got, expected, uid)

    def test_viceron_sandshark_pair_is_rejected_even_in_all_mode(self):
        pair = "factory|enm_neo_nefarious_s/swarmer>enm_indigenous_sand/swarmer"
        game = Game(settings={"enemy_randomizer": True, "enemy_compat": "all"})
        status = game.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % pair)
        self.assertEqual(status, "rejected")

        game.lua.execute("""
        function repair_v061_pair_check()
          local V = RANDO_SPAWNERS.V
          local allowed, _, why = V.compat_allows(
            { kind = "factory" },
            { name = "enm_indigenous_sandshark", family = "swarmer" },
            { { name = "enm_neo_nefarious_swarmer", family = "swarmer" } }
          )
          return allowed, why
        end
        """)
        allowed, why = game.lua.eval("repair_v061_pair_check")()
        self.assertFalse(allowed)
        self.assertEqual(why, "rejected")


if __name__ == "__main__":
    unittest.main()
