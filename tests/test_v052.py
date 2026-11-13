"""Public Release v0.52 (kit 10.0.3, generator 10.0.2): Nefarious City's story is started the way the
game starts it - the prologue complete first, the story and its train-station mission opened, and the
city loaded at its OPENING checkpoint (the arrival scene) instead of CHK_NEFCITY_START.

What each test rests on:
  * round 24 (tests/data/round24_rivet.log, v0.51's first run): the warp to CHK_NEFCITY_START with
    MIS_NEFCITY_01 active, then a reload there and three presses of /; OBJ_NEFCITY_GO_TO_NEFCITY
    went to 1 and never to 2; checkpoint hash 3046787773 never triggered
  * round 23 (tests/data/round23_rivet.log, the game's own order): MIS_INTRO 2 -> 4, then
    MIS_NEFCITY_01 0 -> 2 with MIS_NEFCITY_01_TRAINSTATION 0 -> 1, the rift to NefCity, checkpoint
    hash 3046787773, and only then CHK_NEFCITY_START (2052464476)
  * the simulator's opening rule is SIMULATED: the story's first step finishes on a load at the
    opening. The real name of hash 3046787773 is not known offline; the simulator lists a stand-in
    (OPENING_CP) and the tests point C.OPENINGS at its hash
Nothing here has run in the game.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v100 import py  # noqa: E402
from test_v100 import ENG, PARADE_CP, START_MENU, hub, hub_game, menu_ids, to_hub  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OPENING_HASH = 3046787773
START_HASH = 2052464476
OPENING_CP = "CHK_NEFCITY_OPENING_SIMULATED"     # SIMULATED stand-in for the name of hash 3046787773
TRAIN = "MIS_NEFCITY_01_TRAINSTATION"


def read_log(name):
    with open(os.path.join(DATA, name), encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def first(lines, pattern, start=0):
    for i in range(start, len(lines)):
        if re.search(pattern, lines[i]):
            return i
    return None


def opening_game(seed, settings=None, listed=True, name=OPENING_CP, train=0, goto_at=OPENING_CP):
    """A hub game whose city has an opening checkpoint (SIMULATED rule: the first step finishes on a
    load there, as the game's own rift does in round 23; CHK_NEFCITY_START does not, round 24)."""
    missions = {TRAIN: train} if train is not None else None
    g = hub_game(seed, settings, missions=missions)
    if listed:
        lst = g.sim.checkpoint_list
        lst[len(lst) + 1] = name
    g.g.RANDO_CAMPAIGN.OPENINGS.nefcity_1.hash = g.g.RANDO_TRAVEL.hash(name)
    g.sim.go_to["MIS_NEFCITY_01"].at = goto_at
    g.sim.chain["MIS_INTRO"].cp = OPENING_CP
    return g


def warps(g):
    return list(g.sim.warps.values())


def set_states(g):
    return [(c.name, c.state) for c in g.sim.set_state_calls.values()]


def log_index(g, text):
    for i, l in enumerate(g.logs()):
        if text in l:
            return i
    return None


class EvidenceTests(unittest.TestCase):
    """What the two logs say, read straight from them."""

    def test_round23_the_city_loads_at_the_opening_before_its_start(self):
        L = read_log("round23_rivet.log")
        intro_done = first(L, r"MissionName=MIS_INTRO MissionState=4 PreviousState=2")
        story = first(L, r"MissionName=MIS_NEFCITY_01 MissionState=2 PreviousState=0")
        train = first(L, r"MissionName=MIS_NEFCITY_01_TRAINSTATION MissionState=1 PreviousState=0")
        city = first(L, r"PlanetChangedEvent\tNewPlanetName=NefCity OldPlanetName=Ardolis")
        cps = [int(m.group(1)) for l in L[city:] for m in [re.search(r"CheckpointHash=(\d+)", l)] if m]
        self.assertTrue(intro_done < story < train < city)
        self.assertEqual(train, story + 2)                       # opened with the story (same frame)
        self.assertEqual(cps[:2], [OPENING_HASH, START_HASH])

    def test_round24_the_start_alone_never_finished_the_first_step(self):
        L = read_log("round24_rivet.log")
        warps24 = [l for l in L if l.startswith("[travel] warp to ")]
        self.assertEqual(len(warps24), 6)                       # the start, 2 stuck reloads, 3 presses of /
        self.assertTrue(all("CHK_NEFCITY_START" in l for l in warps24))
        self.assertIsNotNone(first(L, r"OBJ_NEFCITY_GO_TO_NEFCITY ObjectiveState=1"))
        self.assertIsNone(first(L, r"OBJ_NEFCITY_GO_TO_NEFCITY ObjectiveState=2"))
        self.assertIsNone(first(L, r"CheckpointHash=%d" % OPENING_HASH))
        self.assertIsNone(first(L, r"MIS_NEFCITY_01_TRAINSTATION"))
        # v0.51 wrote the prologue complete only after the story had started
        self.assertLess(first(L, r"start\tMIS_NEFCITY_01\tdone"), first(L, r"prologue:\tMIS_INTRO\twritten Complete Finished"))

    def test_the_kit_points_at_that_checkpoint(self):
        g = hub_game("v052-const")
        o = g.g.RANDO_CAMPAIGN.OPENINGS.nefcity_1
        self.assertEqual(o.hash, OPENING_HASH)
        self.assertEqual(list(py(o["with"])), [TRAIN])
        self.assertEqual(g.g.RANDO_TRAVEL.hash("CHK_NEFCITY_START"), START_HASH)

    def test_round24_seed_is_unchanged(self):
        # the generator stays 10.0.2: the seed of round 24 has the same fingerprint, so its progress carries over
        seed, preset, user = ENG.G.parse_share_code(
            "RA10|kit-bolt-kit-198|balanced|distribution=goldbolts_first,include_arsenal_restored=true,travel_lock=true")
        s, audit = ENG.generate(seed, py(user), preset)
        self.assertEqual(s.fingerprint, "2a5550ece053")
        self.assertEqual(audit, [])
        for d in py(s)["hub"]["destinations"]:
            self.assertNotIn("hash", d)                          # openings stay out of the seed


class OpeningTests(unittest.TestCase):
    def test_new_game_loads_the_city_at_its_opening_and_the_story_moves_on(self):
        g = to_hub(opening_game("v052-open"))
        h = hub(g)
        self.assertTrue(h["started"])
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(warps(g), [OPENING_CP])
        self.assertTrue(py(g.sim.go_to["MIS_NEFCITY_01"])["done"])
        # the game's order: prologue complete, story opened and started, the train station opened
        self.assertEqual(set_states(g), [("MIS_INTRO", 4), ("MIS_NEFCITY_01", 1), (TRAIN, 1)])
        self.assertEqual(g.sim.get_mission(TRAIN), 1)
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 2)
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 4)
        self.assertTrue(h["prologue_ended"])
        self.assertTrue(g.state.collected["planet:corson_v"])
        self.assertTrue(g.log_has("opening of nefcity_1: %s (hash" % OPENING_CP))
        self.assertTrue(g.log_has("opening of\tnefcity_1\tloaded:\t%s" % OPENING_CP))
        self.assertTrue(g.log_has("objective\tMIS_NEFCITY_01\tOBJ_NEFCITY_GO_TO_NEFCITY\t2"))
        self.assertTrue(g.log_has("RANDO-CHECKPOINT\t%s" % OPENING_CP))
        self.assertEqual(menu_ids(g), START_MENU)
        # the way home never plays the opening again
        self.assertNotIn(OPENING_CP, list(py(g.g.RANDO_HUB.home_candidates())))
        self.assertNotEqual(h.get("home_cp"), OPENING_CP)
        self.assertEqual(h["parade_cp"], PARADE_CP)
        self.assertIsNone(g.sim.hero_held)
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])
        # the order in rivet.log: the prologue, then the story, then the warp
        ended = log_index(g, "prologue:\tMIS_INTRO\twritten Complete Finished")
        started = log_index(g, "start\tMIS_NEFCITY_01\tdone (available -> active)")
        warped = log_index(g, "travel:\twarp\tto\t" + OPENING_CP)
        self.assertTrue(ended < started < warped)

    def test_control_round24_the_start_checkpoint_leaves_the_story_waiting(self):
        # hub_opening = false is v0.51's load point; with the SIMULATED rule the story stays at its
        # first step through the reload, as in round 24
        g = opening_game("v052-control", {"hub_opening": False})
        g.lua.execute("RANDO_HUB.STUCK_WAIT = 300")
        to_hub(g)
        g.step(400)
        self.assertEqual(warps(g), ["CHK_NEFCITY_START", "CHK_NEFCITY_START"])
        self.assertFalse(py(g.sim.go_to["MIS_NEFCITY_01"]).get("done"))
        self.assertTrue(g.log_has("[STORY RELOAD] nefcity_1 at CHK_NEFCITY_START"))

    def test_the_name_is_found_under_its_code_before_the_catalog_is_complete(self):
        g = to_hub(opening_game("v052-early"), catalog=False)
        self.assertEqual(warps(g), [OPENING_CP])
        self.assertTrue(g.log_has("opening of nefcity_1: %s (hash %d, NEFCITY)" % (OPENING_CP, g.g.RANDO_TRAVEL.hash(OPENING_CP))))

    def test_a_name_the_game_does_not_list_falls_back_to_the_start(self):
        g = to_hub(opening_game("v052-unlisted", listed=False, name="CHK_NEFCITY_NOT_LISTED_SIMULATED"))
        self.assertEqual(warps(g), ["CHK_NEFCITY_START"])
        self.assertTrue(g.log_has("is not among the checkpoints your game lists - loading CHK_NEFCITY_START"))
        self.assertTrue(g.log_has("checkpoints listed for\tnefarious_city:"))
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(hub(g)["started"])

    def test_without_a_catalog_the_wait_is_bounded(self):
        g = opening_game("v052-wait", listed=False, name="CHK_NEFCITY_NOT_LISTED_SIMULATED")
        H = g.g.RANDO_HUB
        g.g.RANDO_TRAVEL.catalog_wanted = g.lua.eval("function() return false end")   # the catalog never fills
        to_hub(g, catalog=False)
        g.step(H.OPENING_WAIT + 600)
        self.assertEqual(warps(g)[0], "CHK_NEFCITY_START")
        self.assertTrue(g.log_has("the catalog was not complete after %d frames" % H.OPENING_WAIT))

    def test_the_opening_is_given_time_then_loaded_once_more(self):
        g = opening_game("v052-stuck", goto_at="CHK_NEFCITY_ELSEWHERE_SIMULATED")
        H = g.g.RANDO_HUB
        to_hub(g)
        g.step(H.STUCK_WAIT + 100)
        self.assertEqual(warps(g), [OPENING_CP])                # no reload while a scene may still run
        g.step(H.OPENING_STUCK_WAIT)
        self.assertEqual(warps(g), [OPENING_CP, OPENING_CP])
        self.assertTrue(g.log_has("[STORY RELOAD] nefcity_1 at " + OPENING_CP))

    def test_the_story_key_loads_the_opening_only_while_the_first_step_waits(self):
        g = opening_game("v052-key", goto_at="CHK_NEFCITY_ELSEWHERE_SIMULATED")
        to_hub(g)
        g.press("/")
        g.step(600)
        self.assertEqual(warps(g), [OPENING_CP, OPENING_CP])
        # once the first step is done, / loads the story's start as before
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_NEFCITY_01", ObjectiveName="OBJ_NEFCITY_GO_TO_NEFCITY", ObjectiveState=2)
        g.press("/")
        g.step(600)
        self.assertEqual(warps(g)[-1], "CHK_NEFCITY_START")

    def test_v051_prologue_timing_is_kept_by_a_setting(self):
        g = to_hub(opening_game("v052-after", {"hub_prologue_timing": "after"}))
        self.assertEqual(set_states(g), [("MIS_NEFCITY_01", 1), (TRAIN, 1), ("MIS_INTRO", 4)])
        self.assertEqual(warps(g), [OPENING_CP])

    def test_an_open_train_station_is_left_alone(self):
        g = to_hub(opening_game("v052-train", train=1))
        self.assertEqual(set_states(g), [("MIS_INTRO", 4), ("MIS_NEFCITY_01", 1)])
        self.assertTrue(g.log_has("with\tnefcity_1:\t%s\tavailable" % TRAIN))

    def test_a_game_without_the_train_station_mission_goes_on(self):
        g = to_hub(opening_game("v052-notrain", train=None))
        self.assertEqual(warps(g), [OPENING_CP])
        self.assertTrue(g.log_has("with\tnefcity_1:\t%s\tnot a mission in your game" % TRAIN))
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_keep_mode_and_story_off_are_unchanged(self):
        g = to_hub(opening_game("v052-keep", {"hub_prologue": "keep"}))
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 2)
        self.assertEqual(warps(g), [OPENING_CP])
        g = to_hub(opening_game("v052-nostory", {"hub_start_story": False}))
        self.assertEqual(warps(g), ["CHK_NEFCITY_START"])
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 0)


if __name__ == "__main__":
    unittest.main()
