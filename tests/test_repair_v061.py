"""Regression coverage for fixes derived from rivet(3).log.

These tests exercise the private v0.60-based repair port. They do not claim in-game
verification for untested enemy pairs or the Omega runtime.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402


class EnemyCompatibilityRegressionTests(unittest.TestCase):
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
