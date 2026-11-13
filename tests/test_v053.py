"""Public Release v0.53 (kit 10.0.4, generator 10.0.2): Nefarious City's boss fight shifts Ratchet to
Savali / Sargasso and back; those shifts must find the world as the game has it during the city's
story - planetary travel off, the level bits untouched - or the game plays them as ship landings.

What each test rests on:
  * round 25 (tests/data/round25_rivet.log, v0.52's first run, seed pocket-pocket-zurkie-839): the
    city's story ran to its boss fight (CHK_NEFCITY_HEAVY_FIGHT); the hub had turned the travel byte
    on (0x0 -> 0x1) and set the level bits on arriving; the story's rift went to Savali
    (CHK_NEFCITY_HEAVYSHIFT_SAVALI); you report Ratchet came down WITH THE SHIP on ground that is
    not solid and fell to his death, several times. After each reload on Nefarious City the hub
    turned the byte on again (a load had cleared it) before the next shift
  * the cause is an inference: the travel byte (SetPlanetaryTravelAction's) is the only thing about
    ship travel the randomizer changes, and the game has it off during the city's story (no ship yet)
Nothing here has run in the game.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v100 import py  # noqa: E402
from test_v100 import hub, hub_game, to_hub  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LEVELS_AT_BOOT = 0x6          # the simulator's level mask before the randomizer touches it
ALL_LEVELS = 0x7FE


def read_log(name):
    with open(os.path.join(DATA, name), encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def all_at(lines, pattern):
    return [i for i, l in enumerate(lines) if re.search(pattern, l)]


def boss_shift(g, planet="Savali", cp="CHK_NEFCITY_HEAVYSHIFT_SAVALI", frames=400):
    """the boss fight's rift: to another planet and back, as the story does it (no warp of ours)"""
    g.sim.checkpoint("CHK_NEFCITY_HEAVY_FIGHT")
    g.sim.travel(planet)
    g.sim.checkpoint(cp)
    g.step(frames)
    flag_there = g.sim.travel_flag
    g.sim.travel("NefCity")
    g.step(frames)
    return flag_there


class EvidenceTests(unittest.TestCase):
    """What round 25's log says, read straight from it."""

    def test_round25_travel_was_on_at_every_shift(self):
        L = read_log("round25_rivet.log")
        heavy = all_at(L, r"RANDO-CHECKPOINT\tCHK_NEFCITY_HEAVY_FIGHT")
        shifts = all_at(L, r"RANDO-HUB\tarrived on\tsavali\tduring\tnefcity_1")
        on = all_at(L, r"planetary travel:\tdone \(0x[01] -> 0x1\)")
        self.assertEqual(len(heavy), 1)
        self.assertEqual(len(shifts), 3)                         # you report "multiple times"
        self.assertTrue(all_at(L, r"RANDO-CHECKPOINT\tCHK_NEFCITY_HEAVYSHIFT_SAVALI"))
        # before every shift the byte had been turned on since the previous one (or since the load)
        prev = 0
        for s in shifts:
            self.assertTrue(any(prev <= i < s for i in on), (prev, s))
            prev = s
        # the reloads in between had cleared it: the hub turned it on from 0x0 again
        self.assertGreaterEqual(len(all_at(L, r"planetary travel:\tdone \(0x0 -> 0x1\)")), 3)
        # and the level bits were set during the city's story
        self.assertTrue(all_at(L, r"level bits 0x0 - unlocking 1-10"))
        # the story was the hub's own (nefcity_1), still running at every shift
        self.assertFalse(all_at(L, r"MissionName=MIS_NEFCITY_01 MissionState=[34]"))

    def test_round25_the_hub_announced_itself_on_every_return(self):
        L = read_log("round25_rivet.log")
        first_shift = all_at(L, r"arrived on\tsavali")[0]
        self.assertGreaterEqual(len([i for i in all_at(L, r"RANDO-NOTIFY\tNefarious City: 2 destination") if i > first_shift]), 3)


class ShiftTests(unittest.TestCase):
    def test_the_city_story_runs_with_the_games_own_world(self):
        g = to_hub(hub_game("v053-start"))
        h = hub(g)
        self.assertEqual(h["current"], "nefcity_1")
        self.assertEqual(g.sim.travel_flag, 0)
        self.assertEqual(g.sim.levels, LEVELS_AT_BOOT)
        self.assertTrue(g.log_has("planetary travel and level bits left to the game while\tnefcity_1\truns"))
        self.assertFalse(g.log_has("planetary travel:\tdone"))
        self.assertFalse(g.log_has("unlocking 1-10"))

    def test_the_boss_fights_shift_finds_travel_off_and_the_return_is_quiet(self):
        g = to_hub(hub_game("v053-shift"))
        warps_before = list(g.sim.warps.values())
        notes_before = len(g.notes())
        for planet, cp in (("Savali", "CHK_NEFCITY_HEAVYSHIFT_SAVALI"), ("Sargasso", "CHK_NEFCITY_HEAVYSHIFT_SARGASSO")):
            self.assertEqual(boss_shift(g, planet, cp), 0, planet)   # off while Ratchet is on the shift's planet
            self.assertEqual(g.sim.travel_flag, 0)
            self.assertEqual(g.sim.levels, LEVELS_AT_BOOT)
        self.assertTrue(g.log_has("arrived on\tsavali\tduring\tnefcity_1\t- the story's own travel"))
        self.assertTrue(g.log_has("back on\tnefarious_city\tfrom\tsavali\tduring\tnefcity_1\t- the story's own travel"))
        self.assertTrue(g.log_has("back on\tnefarious_city\tfrom\tsargasso\tduring\tnefcity_1"))
        # the story's own travel is never touched: no warp, no hub message, the story stays current
        self.assertEqual(list(g.sim.warps.values()), warps_before)
        self.assertFalse(any("destination(s) open" in n for n in g.notes()[notes_before:]), g.notes()[notes_before:])
        self.assertEqual(hub(g)["current"], "nefcity_1")
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_a_reload_on_the_city_during_its_story_turns_nothing_on(self):
        # round 25: after each death the city loaded again and the hub set the byte (0x0 -> 0x1)
        g = to_hub(hub_game("v053-reload"))
        boss_shift(g)
        g.sim.travel("NefCity")                                  # the reload: same planet, a load
        g.step(400)
        self.assertEqual(g.sim.travel_flag, 0)
        self.assertEqual(g.sim.levels, LEVELS_AT_BOOT)
        self.assertEqual(boss_shift(g), 0)                       # the next try finds it off too

    def test_the_world_goes_on_once_the_citys_story_is_finished(self):
        g = to_hub(hub_game("v053-done"))
        boss_shift(g)
        g.sim.complete_mission("MIS_NEFCITY_01")                 # the game then rifts to Sargasso (round 16)
        g.step(3000)
        h = hub(g)
        self.assertIn("nefcity_1", h["done"])
        self.assertEqual(g.sim.planet, "NefCity")                # the hub kept the order
        self.assertEqual(g.sim.travel_flag, 1)
        self.assertEqual(g.sim.levels & ALL_LEVELS, ALL_LEVELS)

    def test_relaunching_the_citys_story_takes_back_what_the_hub_turned_on(self):
        g = to_hub(hub_game("v053-relaunch"))
        # the city's story left (not finished), the hub at rest: the world goes on there
        g.lua.execute("RANDO.state.hub.current = nil; RANDO_HUB.apply_world('test')")
        g.step(60)
        self.assertEqual(g.sim.travel_flag, 1)
        self.assertEqual(g.sim.levels & ALL_LEVELS, ALL_LEVELS)
        g.press("/")                                             # the story key: nefcity_1 again
        g.step(600)
        self.assertEqual(hub(g)["current"], "nefcity_1")
        self.assertEqual(g.sim.travel_flag, 0)
        self.assertEqual(g.sim.levels, LEVELS_AT_BOOT)           # only the bits the hub set are cleared
        self.assertTrue(g.log_has("planetary travel off (launch nefcity_1):"))
        self.assertTrue(g.log_has("level bits taken back (launch nefcity_1):"))
        self.assertEqual(boss_shift(g), 0)

    def test_other_destinations_and_the_settings_are_unchanged(self):
        # arriving at the hub with nothing running still turns the world on (round 17's planet menu)
        g = to_hub(hub_game("v053-off", {"hub_travel_flag": False, "hub_levels": "off"}))
        g.lua.execute("RANDO.state.hub.current = nil; RANDO_HUB.apply_world('test')")
        g.step(60)
        self.assertEqual((g.sim.travel_flag, g.sim.levels), (0, LEVELS_AT_BOOT))
        self.assertFalse(g.g.RANDO_HUB.take_back_world("test"))   # nothing was turned on


if __name__ == "__main__":
    unittest.main()
