"""v0.60 (kit 10.0.23): WARP TO HUB does not depend on planet shuffle.

Until v0.59 a finished destination brought you back to the hub (Nefarious City) only with planet shuffle ON:
15_rando_hub.lua H.finish returned before scheduling the trip ("planet shuffle is off - 0 turns it on"), H.tick
returned before running it and H.on_arrival ignored the landing. Now:

  * shuffle ON and OFF: a destination off the hub planet finishes -> "Back to Nefarious City in 12 s" -> warp.
  * shuffle OFF keeps the game's own order: no travel locks, no level bits; only planetary travel is switched on at
    the hub when the game has it off (so the ship can leave), and taken back if one of the city's stories starts.
  * the same exceptions in both modes: a destination ON the hub planet (you are there), the parade (its own rift ends
    at the hub), the finale; your own planet-menu flight while the trip waits; the game's own story starting the next
    planet's FIRST visit (hub_follow_new: its arrival scene only plays there).
  * hub_auto_return = false switches the trip off in both modes.

Everything here runs against the simulator (tests/sim/rivet_sim.lua), NOT the real game.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from test_v055 import py, release_game, play_the_games_order  # noqa: E402
from test_v100 import hub, hub_game, to_hub, choose  # noqa: E402

HUB_PLANET = "nefarious_city"


def planet_name(g, pid):
    planets = {p.id: p for p in g.data.planets.values()}
    return list(planets[pid].event_names.values())[0]


def off_game(seed, settings=None):
    st = {"hub_return_delay": 12}                                   # the public default (hub_game's tests use 2)
    st.update(settings or {})
    g = release_game(seed, settings=st, planet_shuffle=False)
    g.companion_restore()
    g.sim.new_game()
    g.step(60)
    return g


def go(g, pid, frames=400):
    """the game's own travel (a load), as the story or a save does it"""
    g.travel(planet_name(g, pid))
    g.step(frames)


def finish(g, seg_id):
    seg = next(s for s in py(g.g.RANDO_CAMPAIGN.SEGMENTS) if s["id"] == seg_id)
    for m in seg["missions"]:
        g.fire("MissionStateChangedEvent", MissionName=m, MissionState=4)
        g.step(5)


def sub_has(g, text):
    """a note's text or its second line (opts.sub)"""
    for n in g.sim.notes.values():
        sub = n.opts and n.opts["sub"]
        if text in str(n.text) or (sub and text in str(sub)):
            return True
    return False


def warps(g):
    return list(g.sim.warps.values())


class ShuffleOffReturnTests(unittest.TestCase):
    def test_a_finished_planet_brings_you_back_to_the_hub(self):
        g = off_game("v060-off")
        self.assertFalse(g.g.RANDO.planet_shuffle_on())
        go(g, "sargasso")
        g.sim.travel_flag = 0                                       # the game has planetary travel off
        levels = g.sim.levels
        before = len(warps(g))
        finish(g, "sargasso_1")
        self.assertTrue(sub_has(g, "Back to Nefarious City in 12 s"), g.notes()[-3:])
        self.assertTrue(g.log_has("finished (planet shuffle off) - back to the hub in"))
        g.step(11 * 60)
        self.assertEqual(len(warps(g)), before)                    # not before the 12 s
        g.step(2 * 60 + 400)
        self.assertGreater(len(warps(g)), before, g.logs()[-5:])
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertTrue(g.log_has("back at the hub (Nefarious City)"), [l for l in g.logs() if "HUB" in l][-5:])
        self.assertTrue(sub_has(g, "Back at Nefarious City"))
        g.step(300)
        self.assertEqual(g.sim.travel_flag, 1)                      # the ship can leave
        self.assertEqual(g.sim.levels, levels)                      # the game's own order: no level bits
        self.assertIn("sargasso_1", hub(g)["done"])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_travel_already_on_is_left_alone_and_never_counted_as_ours(self):
        g = off_game("v060-off-on")
        go(g, "savali")
        g.sim.travel_flag = 1
        finish(g, "savali_1")
        g.step(13 * 60 + 700)
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertFalse(g.g.RANDO_HUB.session.world.travel)

    def test_a_city_story_starting_takes_the_travel_byte_back(self):
        # v0.53 / round 25: Nefarious City's own story must start with the game's world
        g = off_game("v060-off-city")
        go(g, "sargasso")
        g.sim.travel_flag = 0
        finish(g, "sargasso_1")
        g.step(13 * 60 + 700)
        self.assertEqual(g.sim.travel_flag, 1)
        g.fire("MissionStateChangedEvent", MissionName="MIS_NEFCITY_01", MissionState=2)
        g.step(5)
        self.assertEqual(g.sim.travel_flag, 0)
        self.assertTrue(g.log_has("nefcity_1 starts (planet shuffle off)"))

    def test_a_destination_on_the_hub_planet_or_the_parade_needs_no_trip(self):
        g = off_game("v060-off-city2")
        finish(g, "corson_intro")
        self.assertFalse(sub_has(g, "Back to Nefarious City"))
        go(g, HUB_PLANET)
        before = len(warps(g))
        finish(g, "nefcity_1")
        g.step(20 * 60)
        self.assertEqual(len(warps(g)), before)
        self.assertTrue(sub_has(g, "Fly on with the ship's planet menu"))

    def test_your_own_planet_menu_flight_replaces_the_trip_back(self):
        g = off_game("v060-off-menu")
        go(g, "sargasso")
        finish(g, "sargasso_1")
        g.step(120)
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING",
               InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        go(g, "savali", frames=20 * 60)
        self.assertEqual(g.state.current_planet, "savali")
        self.assertTrue(g.log_has("planet menu while the trip back waited"))

    def test_the_games_own_story_into_a_first_visit_plays_it_there(self):
        g = off_game("v060-off-follow")
        go(g, "sargasso")
        finish(g, "sargasso_1")
        g.step(120)
        go(g, "scarstu", frames=20 * 60)                            # scarstu_1 is still to come: its arrival scene
        self.assertEqual(g.state.current_planet, "scarstu")
        self.assertTrue(g.log_has("its first visit\tscarstu_1\tstarts there; no trip back (hub_follow_new)"),
                        [l for l in g.logs() if "HUB" in l][-4:])

    def test_the_games_own_travel_to_a_revisit_still_brings_you_back(self):
        g = off_game("v060-off-revisit")
        go(g, "scarstu")
        finish(g, "scarstu_1")                                      # scarstu_1 done: Zurkon has no first visit left
        go(g, "cordelion")
        finish(g, "cordelion_1")
        g.step(120)
        go(g, "scarstu", frames=20 * 60)
        self.assertEqual(g.state.current_planet, HUB_PLANET, [l for l in g.logs() if "HUB" in l][-4:])
        self.assertTrue(g.log_has("the trip back to the hub still comes"))

    def test_hub_auto_return_false_switches_it_off(self):
        g = off_game("v060-off-noauto", {"hub_auto_return": False})
        go(g, "sargasso")
        before = len(warps(g))
        finish(g, "sargasso_1")
        g.step(20 * 60)
        self.assertEqual(len(warps(g)), before)
        self.assertEqual(g.state.current_planet, "sargasso")

    def test_a_warp_that_does_not_land_is_tried_at_the_next_hub_checkpoint(self):
        g = off_game("v060-off-retry")
        go(g, "sargasso")
        g.sim.auto_travel = False                                   # the first warp never lands
        finish(g, "sargasso_1")
        g.step(13 * 60)
        first = len(warps(g))
        self.assertGreater(first, 0)
        g.sim.auto_travel = True
        g.step(g.g.RANDO_HUB.ARRIVE_TIMEOUT + 600)
        self.assertGreater(len(warps(g)), first)
        self.assertTrue(g.log_has("no arrival at the hub after"))


class ShuffleOnReturnTests(unittest.TestCase):
    def test_a_finished_planet_brings_you_back_to_the_hub(self):
        g = to_hub(hub_game("v060-on", {"hub_return_delay": 12}))
        self.assertTrue(g.g.RANDO.planet_shuffle_on())
        g.R.grant("access:savali")
        g.step(30)
        choose(g, "savali_1", frames=3000)
        self.assertEqual(g.state.current_planet, "savali")
        before = len(warps(g))
        finish(g, "savali_1")
        self.assertTrue(sub_has(g, "Back to Nefarious City in 12 s"))
        g.step(13 * 60 + 700)
        self.assertGreater(len(warps(g)), before)
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertIn("savali_1", hub(g)["done"])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_the_same_planet_finished_with_shuffle_off_returns_the_same_way(self):
        on = to_hub(hub_game("v060-same", {"hub_return_delay": 12}))
        on.R.grant("access:savali")
        on.step(30)
        choose(on, "savali_1", frames=3000)
        finish(on, "savali_1")
        on.step(13 * 60 + 700)
        off = off_game("v060-same")
        go(off, "savali")
        finish(off, "savali_1")
        off.step(13 * 60 + 700)
        self.assertEqual(on.state.current_planet, off.state.current_planet)
        self.assertEqual(off.state.current_planet, HUB_PLANET)


class ProgressionTests(unittest.TestCase):
    def test_the_games_order_with_shuffle_off_pays_every_location(self):
        # the planet menu between planets (the player flies on): nothing unpaid, nothing broken
        g = release_game("v060-run", planet_shuffle=False)
        self.assertEqual(play_the_games_order(self, g), [])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_the_games_order_by_story_travel_only_pays_every_location_and_returns_after_revisits(self):
        g = release_game("v060-story", planet_shuffle=False)
        C = g.g.RANDO_CAMPAIGN
        g.companion_restore()
        g.sim.new_game()
        g.step(60)
        current = "corson_v"
        for seg in py(C.SEGMENTS):
            pid = seg["planet"]
            if g.state.current_planet != pid:
                go(g, pid)
            finish(g, seg["id"])
            g.step(13 * 60 + 700)
            current = pid
        self.assertEqual(current, "corson_v")
        h = hub(g)
        self.assertEqual(sorted(h["done"]), sorted(s["id"] for s in py(C.SEGMENTS)))
        self.assertTrue(g.log_has("back at the hub (Nefarious City)"))
        self.assertTrue(g.state.finished or g.log_has("finale"), [l for l in g.logs() if "inale" in l][-3:])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])


if __name__ == "__main__":
    unittest.main()
