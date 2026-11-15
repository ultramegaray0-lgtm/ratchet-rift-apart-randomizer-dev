"""Public Release v0.51 (build 10.0.2): the hub is Nefarious City, its story starts with the hub's
first warp, and Ratchet is not warped out of the parade in the middle of a scripted sequence.

What each test rests on:
  * the hub plan a seed carries: Nefarious City, CHK_NEFCITY_START then CHK_NEFCITY_SHIP, the city's
    story is the hub's own; placements are 10.0's (tests/test_v05.py compares them field by field)
  * WHEN the warp goes (hub_trigger = "parade"): round 23's log shows the wrench pickup starting
    OBJ_INTRO_GOING_DOWN in the same frame and the game answering nothing sent to the hero until it
    finished. The simulator holds the hero after a warp made during it (rivet_sim.lua S.hero_held,
    marked SIMULATED: your report "Ratchet doesn't walk right after the warp" is the evidence)
  * HOW: the story active first, then the warp to its start (round 23's order; round 17's calls);
    the prologue written complete only once on Nefarious City (round 17 did that after its warp)
Nothing here has run in the game.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v100 import py  # noqa: E402  (tools/luajson, put on the path by test_v100)
from test_v100 import ENG, KEEP, PARADE_CP, START_MENU, choose, hub, hub_game, menu_ids, to_hub  # noqa: E402


def to_wrench(g):
    """New game up to the wrench (GOING_DOWN starts with it); the hub has not moved yet."""
    g.companion_restore()
    g.sim.new_game()
    g.step(60)
    g.sim.parade_control()
    g.step(1500)
    g.sim.checkpoint(PARADE_CP)
    g.sim.parade_wrench()
    return g


def log_index(g, text):
    for i, l in enumerate(g.logs()):
        if text in l:
            return i
    return None


class HubPlanTests(unittest.TestCase):
    def test_the_plan_names_nefarious_city(self):
        s, _ = ENG.generate("v051-plan", {}, "balanced")
        h = py(s)["hub"]
        self.assertEqual(h["planet"], "nefarious_city")
        self.assertEqual(h["checkpoints"], ["CHK_NEFCITY_START", "CHK_NEFCITY_SHIP"])
        kinds = {d["id"]: d["kind"] for d in h["destinations"]}
        self.assertEqual(kinds["nefcity_1"], "hub")
        self.assertEqual(kinds["scarstu_1"], "planet")
        self.assertEqual(kinds["scarstu_2"], "planet")
        self.assertEqual(kinds["corson_intro"], "intro")
        self.assertEqual(py(s)["generator"], "10.11.0")         # 10.1: Spybots/Lorbs, reward-only weapons
        # the generator's start list (and so the starting Coordinates) is 10.0's
        self.assertEqual(h["start"], ["corson_intro", "scarstu_1", "nefcity_1"])
        self.assertEqual(py(ENG.G.audit(s)) or [], [])


class WhenTheWarpGoesTests(unittest.TestCase):
    def test_no_warp_while_going_down_runs(self):
        g = to_wrench(hub_game("v051-wait"))
        g.step(900)                                     # 15 s into GOING_DOWN: still in the parade
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertEqual(g.sim.planet, "Malinon")
        self.assertFalse(hub(g).get("started"))
        g.sim.parade_release()
        g.step(60)
        self.assertEqual(list(g.sim.warps.values()), [])   # the settle time
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertIsNone(g.sim.hero_held)
        self.assertTrue(g.log_has("the parade handed Ratchet back after his wrench"))

    def test_the_10_0_timing_is_what_held_ratchet(self):
        # control: hub_trigger = "wrench" (10.0-v0.5) warps in the middle of GOING_DOWN with the
        # prologue active, which the simulator (by its SIMULATED rule) leaves holding the hero
        # (v0.52: with v0.51's prologue timing; "before" ends the prologue before the warp, and the
        # SIMULATED rule holds the hero only while the prologue is active)
        g = to_wrench(hub_game("v051-wrench", {"hub_trigger": "wrench", "hub_prologue_timing": "after"}))
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertEqual(g.sim.hero_held, "OBJ_INTRO_GOING_DOWN")

    def test_a_parade_cutscene_holds_the_warp_until_it_ends(self):
        g = to_wrench(hub_game("v051-cine"))
        g.sim.parade_release()
        g.step(30)
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_INTRO",
               ObjectiveName="OBJ_INTRO_PARADE_HALL_OF_HEROES_CUTSCENE_THUG_INTRO_START", ObjectiveState=1)
        g.step(600)
        self.assertEqual(list(g.sim.warps.values()), [])
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_INTRO",
               ObjectiveName="OBJ_INTRO_PARADE_HALL_OF_HEROES_CUTSCENE_THUG_INTRO_START", ObjectiveState=2)
        g.step(60)
        self.assertEqual(list(g.sim.warps.values()), [])
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])

    def test_going_down_never_reported_goes_after_the_timeout(self):
        g = to_wrench(hub_game("v051-timeout"))
        R = g.g.RANDO_HUB
        g.step(R.RELEASE_TIMEOUT - 120)
        self.assertEqual(list(g.sim.warps.values()), [])
        g.step(600)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertTrue(g.log_has("OBJ_INTRO_GOING_DOWN was not reported done"))

    def test_a_save_load_never_starts_it(self):
        g = hub_game("v051-load")
        g.companion_restore()
        g.sim.load_save("Sargasso")
        g.step(3000)
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertFalse(hub(g).get("started"))


class TheStoryTests(unittest.TestCase):
    def test_the_story_is_active_before_the_city_loads(self):
        g = to_hub(hub_game("v051-order"))
        start = log_index(g, "start\tMIS_NEFCITY_01\tdone (available -> active)")
        warp = log_index(g, "travel:\twarp\tto\tCHK_NEFCITY_START")
        self.assertIsNotNone(start)
        self.assertIsNotNone(warp)
        self.assertLess(start, warp)
        self.assertEqual(g.sim.started_as["MIS_NEFCITY_01"], "ratchet")
        self.assertTrue(py(g.sim.go_to["MIS_NEFCITY_01"])["done"])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_the_prologue_ends_only_on_nefarious_city(self):
        # v0.51's order, kept by hub_prologue_timing = "after" (v0.52's default ends it before the
        # city's story starts: tests/test_v052.py)
        g = to_hub(hub_game("v051-prologue", {"hub_prologue_timing": "after"}))
        arrived = log_index(g, "RANDO-CHECKPOINT\tCHK_NEFCITY_START")
        ended = log_index(g, "prologue:\tMIS_INTRO\twritten Complete Finished")
        self.assertIsNotNone(ended)
        self.assertLess(arrived, ended)
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 4)
        self.assertTrue(hub(g)["prologue_ended"])
        self.assertTrue(g.state.collected["planet:corson_v"])
        # quiet: no "Destination complete" and no trip back for it
        self.assertFalse(g.note_has("Destination complete"))
        g.step(1500)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertEqual(menu_ids(g), START_MENU)

    def test_keep_leaves_the_prologue_to_choose(self):
        g = to_hub(hub_game("v051-keep", KEEP))
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 2)
        self.assertEqual(menu_ids(g), ["nefcity_1", "scarstu_1", "corson_intro"])
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 2)

    def test_a_refused_prologue_write_keeps_it_as_a_destination(self):
        g = hub_game("v051-refused")
        g.sim.v6_bits = 6                                # no mission-record writes (bit 1 off)
        g.sim.install_dll(1, 6)
        to_hub(g)
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 2)
        self.assertTrue(hub(g)["prologue_kept"])
        self.assertIn("corson_intro", menu_ids(g))
        # and the city still loads at its start (the story could not be forced: explore)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])

    def test_hub_start_story_off_only_travels(self):
        g = to_hub(hub_game("v051-nostory", {"hub_start_story": False}))
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 0)

    def test_a_story_still_at_its_first_step_is_loaded_once_more_in_the_city(self):
        g = hub_game("v051-stuck")
        g.lua.execute("RANDO_HUB.STUCK_WAIT = 300")
        # SIMULATED: this time the first step finishes only at a checkpoint the hub never loads
        g.sim.go_to["MIS_NEFCITY_01"].at = "CHK_NEFCITY_ELSEWHERE_SIMULATED"
        to_hub(g)
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START", "CHK_NEFCITY_START"])
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(g.log_has("[STORY RELOAD] nefcity_1 at CHK_NEFCITY_START"))


class WayHomeTests(unittest.TestCase):
    def test_home_is_the_story_start_then_the_pad(self):
        g = to_hub(hub_game("v051-home"))
        H = g.g.RANDO_HUB
        self.assertEqual(list(py(H.home_candidates()))[:2], ["CHK_NEFCITY_START", "CHK_NEFCITY_SHIP"])
        g.sim.complete_mission("MIS_NEFCITY_01")
        g.sim.checkpoint("CHK_SARG_OPENING_SIMULATED")
        g.step(1500)
        self.assertEqual(list(py(H.home_candidates()))[:2], ["CHK_NEFCITY_SHIP", "CHK_NEFCITY_START"])
        self.assertEqual(g.sim.planet, "NefCity")

    def test_going_home_from_the_city_waits_for_no_arrival(self):
        g = to_hub(hub_game("v051-same"))
        H = g.g.RANDO_HUB
        H.go_home("test")            # v0.54: [ no longer goes home; the auto-return still does this
        g.step(60)
        self.assertIsNone(H.expect)
        g.step(H.ARRIVE_TIMEOUT + 300)
        # one warp for the start and one for the key: no retries through other checkpoints
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START", "CHK_NEFCITY_START"])
        self.assertFalse(g.log_has("no arrival at the hub"))

    def test_messages_name_nefarious_city(self):
        g = to_hub(hub_game("v051-names"))
        g.R.grant("access:savali")
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_BLIZAR_A_LANDINGPAD",
               InterplanetaryCheckpointName="CHK_TRANSITION_TO_BLIZAR")
        g.travel("Blizar")
        g.step(600)
        self.assertTrue(g.note_has("back to Nefarious City"))
        texts = " ".join(g.notes())
        self.assertNotIn("Zurkie's Battleplex - choose", texts)
        self.assertNotIn("back to Zurkie's", texts)


if __name__ == "__main__":
    unittest.main()
