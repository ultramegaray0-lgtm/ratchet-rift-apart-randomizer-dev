"""Dev 10.23 (kit 10.0.17): after the dev 10.22 log of 2026-11-18 (tests/data/round33_rivet.log: companion started
late, NefCity, Zurkon arena challenges A1 and A2 replayed and completed; "Enemies/bosses didn't got randomized").

THREE KINDS OF TEST, kept apart:
  * RoundThirtyThreeLogTests: facts read from the real game log (no simulator) - why the Factories experiment never
    ran: spawnproof v2 stayed silent because the randomizer's event buffer dropped the PlanetChangedEvent to Zurkon.
  * EventBufferSimulatorTests: the kit fix (10_rando_runtime.lua) in the SIMULATOR.
  * SpawnProofThreeSimulatorTests: dev(spawnproof).lua v3 in the SIMULATOR (SYNTHETIC memory, as test_v1022).
Nothing in this file is in-game verification.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_v1022 import SpawnProofTwoSimulatorTests as V2, GRUNT, FLYER  # noqa: E402

LOG = ROOT / "tests" / "data" / "round33_rivet.log"


def text():
    return LOG.read_text(encoding="utf-8")


class RoundThirtyThreeLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_spawnproof_v2_loaded_and_then_said_nothing(self):
        lines = [l for l in text().splitlines() if "RANDO-SPAWNPROOF" in l]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("v2 loaded: Template and Factories replacements on Zurkon (on, at most 4)", lines[0])
        self.assertNotIn("dev(spawnprobe)", text().split("developer files loaded", 1)[1].splitlines()[0])   # removed as asked

    def test_the_buffer_was_full_and_the_planet_change_was_lost(self):
        t = text()
        self.assertIn("RANDO-SEED seed = \"random\" needs the companion to remember the seed - start the companion", t)
        self.assertIn("RANDO-SEED replaying 500 event(s) that came in while generating", t)
        self.assertIn("RANDO-DISCOVER\tPlanetChangedEvent\tNewPlanetName=Zurkon", t)          # it happened...
        planets = re.findall(r"RANDO-PLANET\t(\w+)\t(\w+)", t)
        self.assertEqual(planets, [("NefCity", "nefarious_city")])                            # ...and was never processed
        on_zurkon = re.findall(r"RANDO-CHECKPOINT\t(CHK_ZURK\w+)\thash \d+\ton\t(\w+)", t)
        self.assertGreaterEqual(len(on_zurkon), 4)
        self.assertTrue(all(p == "nefarious_city" for _, p in on_zurkon), on_zurkon)

    def test_the_challenges_ran_after_the_seed_was_ready(self):
        t = text()
        ready = t.index("RANDO-SEED ready")
        self.assertGreater(t.index("MissionName=MIS_ZURK_ARENA_CHALLENGE_A1 MissionState=4 PreviousState=2"), ready)
        self.assertGreater(t.index("MissionName=MIS_ZURK_ARENA_CHALLENGE_A2 MissionState=4 PreviousState=2"), ready)
        self.assertGreater(t.index("RANDO-SPAWNERS\tspawn: sender"), ready)                     # the layer's events did flow


class EventBufferSimulatorTests(unittest.TestCase):
    def test_a_planet_change_survives_a_full_buffer(self):
        g = Game(settings={"seed": "random"})                        # round33: the companion started late
        g.travel("NefCity")
        self.assertIsNone(g.g.RANDO_SEED)
        for i in range(620):
            g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=1, SpawnedHandle=50000 + i)
        g.step(1)
        g.fire("PlanetChangedEvent", NewPlanetName="Zurkon")
        g.step(1)
        self.assertIsNone(g.g.RANDO_SEED)
        g.bridge('return rando_use_seed("late-companion")')
        self.assertTrue(g.wait_seed())
        g.step(40)
        line = next(l for l in g.logs() if "came in while generating" in l)
        self.assertIn("dropped: SpawnerSpawnEvent", line)
        self.assertIn("kept in full", line)
        self.assertEqual(g.state.current_planet, "scarstu")

    def test_the_old_bound_still_holds_for_the_rest(self):
        g = Game(settings={"seed": "random"})
        for i in range(620):
            g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=1, SpawnedHandle=60000 + i)
        g.step(1)
        n = g.lua.eval("RANDO.buffer_dropped.SpawnerSpawnEvent")
        self.assertGreaterEqual(n, 100)


class SpawnProofThreeSimulatorTests(unittest.TestCase):
    """SYNTHETIC memory: shows the code's logic only."""
    game, spawn, lines = V2.game, V2.spawn, V2.lines

    def test_its_own_planet_event_wins_over_a_wrong_state(self):
        g = self.game()
        g.lua.execute('RANDO.state.current_planet = "nefarious_city"')       # what round33 had all session
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        self.assertTrue([l for l in self.lines(g) if "\tARMED " in l], self.lines(g)[-5:])
        self.assertTrue(any("level reset (planet Zurkon): ON ZURKON - active (event planet Zurkon" in l for l in self.lines(g)))

    def test_it_says_why_it_is_inactive(self):
        g = self.game(planet="NefCity")
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.assertTrue(any("inactive: 1 spawn(s) ignored on this level - not Zurkon (event planet NefCity" in l for l in self.lines(g)), self.lines(g)[-4:])

    def test_both_deliveries_of_a_spawn_count_once(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.assertEqual(len([l for l in self.lines(g) if "\tspawn 7001 " in l]), 1)

    def test_armed_and_verify_are_shown_on_screen(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        self.spawn(g, 2, 7003, FLYER, 8002)
        self.assertTrue(g.note_has("SPAWNPROOF ARMED: grunt should now come as flyer"), g.notes()[-4:])
        self.assertTrue(g.note_has("SPAWNPROOF: REPLACEMENT SPAWNED (flyer)"), g.notes()[-4:])

    def test_loaded_line_reports_its_own_subscriptions(self):
        g = self.game()
        self.assertTrue(any("Template and Factories replacements" in l and "own events: planet yes, spawns yes" in l for l in self.lines(g)))


if __name__ == "__main__":
    unittest.main()
