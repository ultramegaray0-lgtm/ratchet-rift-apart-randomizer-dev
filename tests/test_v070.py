"""v0.70 (kit 10.0.35 = v0.62-DEV14 released): the crash on death / retry / load.

round54 (DEV13 in the game): the game died on every death. Cause (rivet_hook 2.0.0 source): during a load the
scripts are pumped from the render thread while the game frees the level; DEV13's Omega census read the component
index then. 10_rando_runtime.lua's R.loading_now() (rivet.script_node(0) refuses off the game thread) now stops
Omega, the spawner layer and the shop from reading or writing during a load, and deliveries wait for its end.
These run the real scripts against tests/sim (a simulation, not the game) and tests/omega_sims (Omega's own sims).
"""
import os
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game, MOD  # noqa: E402

SIMS = pathlib.Path(__file__).resolve().parent / "omega_sims"


class LoadGuardTests(unittest.TestCase):
    def test_a_load_is_seen_and_ends(self):
        g = Game()
        g.ready()
        g.step(60)
        self.assertFalse(g.R.loading)
        g.travel("NefCity", 60)
        g.step(200)
        self.assertTrue(g.log_has("RANDO-LOAD a load began (the game thread stopped pumping)"), g.logs()[-20:])
        self.assertTrue(g.log_has("RANDO-LOAD the load is over"))
        self.assertFalse(g.R.loading)
        self.assertFalse([l for l in g.logs() if "RANDO-ERROR" in l])

    def test_nothing_is_sent_during_a_load(self):
        g = Game()
        g.ready()
        g.lua.execute("SIM.loading = true")
        g.step(1)
        self.assertTrue(g.R.loading)
        self.assertFalse(g.real.game_running())
        g.lua.execute("SIM.loading = false")
        g.step(1)
        self.assertFalse(g.R.loading)

    def test_a_long_gap_counts_as_a_load(self):
        g = Game()
        g.ready()
        g.R.update_loading(0.4)
        self.assertTrue(g.R.loading)
        g.R.update_loading(1 / 60)
        self.assertFalse(g.R.loading)

    def test_omega_drops_its_addresses_on_a_load(self):
        g = Game()
        g.ready()
        O = g.g.RANDO_OMEGA
        g.lua.execute("RANDO_OMEGA.inv = { records = {} }; RANDO_OMEGA.jobs = { { name = 'search' } }")
        g.R.update_loading(0.4)
        self.assertIsNone(O.inv)
        self.assertEqual(len(list(O.jobs.keys())), 0)
        self.assertGreaterEqual(O.next_search, O.frame + O.SETTLE)


class OmegaSimTests(unittest.TestCase):
    def run_sim(self, mode, seed=1):
        r = subprocess.run([sys.executable, "-I", str(SIMS / "sim_omega_dev14.py"), str(MOD), str(seed), mode],
                           capture_output=True, text=True, timeout=600)
        fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
        self.assertEqual(r.returncode, 0, "\n".join(fails) or r.stderr[-2000:])
        return r.stdout

    def test_death_in_the_middle_of_the_census(self):
        out = self.run_sim("death")
        self.assertIn("PASS nothing read during the load", out)
        self.assertIn("PASS the Omega was applied", out)

    def test_a_hitch(self):
        self.assertIn("PASS nothing read during the load", self.run_sim("hitch"))

    def test_dev13_modes_unchanged(self):
        for mode in ("round53", "checkpoint", "ngplus", "ngplus_xp0"):
            self.run_sim(mode)


if __name__ == "__main__":
    unittest.main()
