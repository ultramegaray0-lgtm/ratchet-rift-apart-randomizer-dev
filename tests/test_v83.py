"""Randomizer 8.3: the story starts where you land, and keyboard keys instead of F1-F12.

Round 19 (rivet.log, 8.2): test trips to Viceron, Torren IV and Cordelion started no story (8.2's
test travel claimed the landing and did nothing else), and on Cordelion MIS_CORD_01_FIRST_VISIT
was "already active" from an earlier session, so the hub did nothing either. Round 17 shows why a
story can sit still while "active": its first objective is "go to <planet>"
(OBJ_NEFCITY_GO_TO_NEFCITY, OBJ_ZURK_01_GO_TO_ZURKONS). Started while you were on the planet, that
step finished in 2 seconds and the story played (MIS_ZURK_01_VISIT_01); started elsewhere, it
never finished (MIS_NEFCITY_01). 8.3:
  * landing on a planet (test travel, the ship's menu, a hub trip) starts that planet's story,
    whatever came before it (story_on_arrival)
  * an active story waiting at "go to <planet>" (or with no step seen) is started again on its
    planet: available (the v6 record write), then the game's start (story_restart_stuck)
  * the story key (/) starts the story of the planet you are on; Ctrl+/ twice starts it again
  * keys are keyboard keys (] [ . , ; / '), the old F keys still work (legacy_f_keys)
The game here is the simulator (tests/sim/rivet_sim.lua), NOT your game: what start, restart and
replay change in the real game, and whether rivet_hook passes these keys on, is for round 20.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402
from test_hub import hub_game, to_hub, hub  # noqa: E402

VK_F6 = 0x75


def game(seed="v83-1", settings=None, missions=None, **kw):
    st = {"test_travel": True}
    st.update(settings or {})
    g = to_hub(hub_game(seed, st, missions=missions, **kw))
    g.step(1200)                     # the checkpoint catalog (test travel's landing points)
    return g


def select(g, pid, key="."):
    TT = g.g.RANDO_TEST_TRAVEL
    for _ in range(12):
        g.press(key)
        if TT.selected() == pid:
            return
    raise AssertionError("never selected " + pid)


def settle(g, frames=900):
    for _ in range(frames // 30):
        g.step(30)


def warp(g, pid):
    select(g, pid)
    g.press(".", ctrl=True)
    settle(g)


class StoryOnArrivalTests(unittest.TestCase):
    def test_test_trip_starts_the_planets_story_out_of_order(self):
        g = game()
        # Viceron's story needs the Phantom Dash and the Hurlshot in the hub's order: started anyway
        self.assertNotIn("viceron_1", list(py(g.g.RANDO_HUB.available())))
        warp(g, "viceron")
        self.assertEqual(g.sim.get_mission("MIS_ZORD_01"), 2)
        self.assertEqual(hub(g)["current"], "viceron_1")
        # 8.4: started before the warp (story_prime_before_travel), running when it landed
        self.assertTrue(g.log_has("prime\tviceron_1:\thero rivet confirmed, MIS_ZORD_01 start: done"))
        self.assertIn("MIS_ZORD_01 already active", hub(g)["attempts"]["viceron_1"]["detail"])
        self.assertEqual(g.sim.playing, "rivet")                     # 8.4: Viceron is Rivet's
        self.assertTrue(g.log_has("story on arrival:\tviceron\t->\tviceron_1"))
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_rivets_story_swaps_the_hero(self):
        g = game("v83-hero")
        warp(g, "torren_iv")
        self.assertEqual(g.sim.get_mission("MIS_MOL_01_FIRST_VISIT"), 2)
        self.assertEqual(list(py(g.sim.heroes))[-1], "rivet")

    def test_second_visit_waits_for_the_first_on_the_same_planet(self):
        g = game("v83-visit")
        warp(g, "savali")
        self.assertEqual(hub(g)["current"], "savali_1")       # visit 1 first, whatever the hub's order

    def test_finished_planet_says_so(self):
        g = game("v83-done")
        g.g.RANDO_HUB.state().done["blizar_1"] = 1
        warp(g, "blizar_prime")
        self.assertTrue(g.note_has("its story is finished"))

    def test_off_switch(self):
        g = game("v83-off", {"story_on_arrival": False})
        warp(g, "viceron")
        self.assertEqual(g.sim.get_mission("MIS_ZORD_01"), 0)
        self.assertFalse(hub(g).get("current"))

    def test_menu_landing_starts_the_story_of_a_planet_without_coordinates(self):
        g = game("v83-menu")
        locked = py(g.seed.hub)["queue"][-1]
        cp = {"savali": "CHK_SAV_01_LANDING", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD", "torren_iv": "CHK_MOL_01_START",
              "cordelion": "CHK_STATION_01_START", "ardolis": "CHK_ARD_01_ARRIVAL", "viceron": "CHK_ZORD_01_START",
              "nefarious_city": "CHK_NEFCITY_SHIP", "sargasso": "CHK_SARG_GELFACTORY_LANDINGPAD"}[locked]
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cp, InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from({"planet": g.sim.planet_of_cp(cp), "at": g.sim.frame + 2, "cp": cp})
        settle(g, 1500)
        self.assertEqual(g.state.current_planet, locked)
        self.assertEqual(py(g.g.RANDO_HUB.dest(hub(g)["current"]))["planet"], locked)


class StuckStoryTests(unittest.TestCase):
    """8.4 replaced 8.3's automatic restart (round 20: it changed the state but never moved a story)
    with the hero check and a reload; these are the 8.3 cases with 8.4's answers."""
    def test_active_story_with_no_step_seen_gets_its_hero_and_runs(self):
        g = game("v83-stuck", missions={"MIS_CORD_01_FIRST_VISIT": 2})
        warp(g, "cordelion")
        self.assertEqual([c for c in py(g.sim.set_state_calls) if c["name"] == "MIS_CORD_01_FIRST_VISIT"], [])
        self.assertEqual(g.sim.get_mission("MIS_CORD_01_FIRST_VISIT"), 2)
        self.assertIn("already active", hub(g)["attempts"]["cordelion_1"]["detail"])
        self.assertTrue(g.log_has("hero:\tratchet\tconfirmed"))

    def test_active_story_waiting_at_go_to_is_reloaded(self):
        g = game("v83-goto", missions={"MIS_CORD_01_FIRST_VISIT": 2})
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_CORD_01_FIRST_VISIT",
               ObjectiveName="OBJ_CORD_01_GO_TO_CORDELION", ObjectiveState=1)
        warp(g, "cordelion")
        self.assertIn("already active", hub(g)["attempts"]["cordelion_1"]["detail"])
        settle(g, 2400)
        self.assertTrue(any("[STORY RELOAD] cordelion_1" in x for x in py(g.state.history)))
        self.assertEqual(g.state.current_planet, "cordelion")            # out to Zurkie's and back
        self.assertEqual([c for c in py(g.sim.set_state_calls) if c["name"] == "MIS_CORD_01_FIRST_VISIT"], [])

    def test_active_story_in_progress_is_left_alone(self):
        g = game("v83-busy", missions={"MIS_CORD_01_FIRST_VISIT": 2})
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_CORD_01_FIRST_VISIT",
               ObjectiveName="OBJ_CORD_04_FORGE_FIGHT", ObjectiveState=1)
        warp(g, "cordelion")
        self.assertEqual([c for c in py(g.sim.set_state_calls) if c["name"] == "MIS_CORD_01_FIRST_VISIT"], [])
        self.assertIn("already active", hub(g)["attempts"]["cordelion_1"]["detail"])
        settle(g, 2400)
        self.assertFalse(any("[STORY RELOAD]" in x for x in py(g.state.history)))

    def test_refused_restart_by_hand_goes_back_to_active_then_replays(self):
        g = game("v83-refuse", missions={"MIS_CORD_01_FIRST_VISIT": 2})
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_CORD_01_FIRST_VISIT",
               ObjectiveName="OBJ_CORD_04_FORGE_FIGHT", ObjectiveState=1)
        warp(g, "cordelion")
        g.sim.can_start = False
        g.sim.replay_effect = 2
        g.press("/", ctrl=True)
        g.press("/", ctrl=True)
        settle(g, 300)
        states = [c["state"] for c in py(g.sim.set_state_calls) if c["name"] == "MIS_CORD_01_FIRST_VISIT"]
        self.assertEqual(states, [1, 2])
        self.assertEqual(g.sim.get_mission("MIS_CORD_01_FIRST_VISIT"), 2)
        self.assertIn("replayed", hub(g)["attempts"]["cordelion_1"]["detail"])

    def test_off_switch_never_reloads(self):
        g = game("v83-nostuck", {"story_reload_stuck": False}, missions={"MIS_CORD_01_FIRST_VISIT": 2})
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_CORD_01_FIRST_VISIT",
               ObjectiveName="OBJ_CORD_01_GO_TO_CORDELION", ObjectiveState=1)
        warp(g, "cordelion")
        settle(g, 2400)
        self.assertIn("already active", hub(g)["attempts"]["cordelion_1"]["detail"])
        self.assertFalse(any("[STORY RELOAD]" in x for x in py(g.state.history)))
        self.assertTrue(g.note_has("leave the planet and come back"))

    def test_old_setting_name_still_switches_it_off(self):
        g = game("v83-oldname", {"story_restart_stuck": False})
        self.assertFalse(g.R.config.story_reload_stuck)
        self.assertTrue(g.log_has("is story_reload_stuck since 8.4"))

    def test_a_story_still_at_go_to_is_reloaded_then_the_key_reloads_again(self):
        g = game("v83-watch")
        warp(g, "viceron")
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_ZORD_01", ObjectiveName="OBJ_ZORD_01_GO_TO_ZORDOOM", ObjectiveState=1)
        settle(g, 2400)
        self.assertEqual(sum("[STORY RELOAD] viceron_1" in x for x in py(g.state.history)), 1)
        settle(g, 2400)                                     # still waiting: once per session
        self.assertEqual(sum("[STORY RELOAD] viceron_1" in x for x in py(g.state.history)), 1)
        self.assertTrue(g.note_has("press / to try again"))
        g.press("/")                                        # the player's own choice: again
        settle(g, 900)
        self.assertEqual(sum("[STORY RELOAD] viceron_1" in x for x in py(g.state.history)), 2)

    def test_a_story_that_moves_on_is_not_reported(self):
        g = game("v83-moves")
        warp(g, "viceron")
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_ZORD_01", ObjectiveName="OBJ_ZORD_01_GO_TO_ZORDOOM", ObjectiveState=1)
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_ZORD_01", ObjectiveName="OBJ_ZORD_01_GO_TO_ZORDOOM", ObjectiveState=2)
        settle(g, 1500)
        self.assertFalse(any("[STORY RELOAD]" in x for x in py(g.state.history)))


class StoryKeyTests(unittest.TestCase):
    def test_story_key_starts_the_story_here(self):
        g = game("v83-key", {"story_on_arrival": False})
        warp(g, "ardolis")
        self.assertEqual(g.sim.get_mission("MIS_ARD_01_FIRST_VISIT"), 0)
        g.press("/")
        settle(g, 300)
        self.assertEqual(g.sim.get_mission("MIS_ARD_01_FIRST_VISIT"), 2)
        self.assertEqual(hub(g)["current"], "ardolis_1")

    def test_story_key_at_zurkies_starts_zurkies_story(self):
        g = game("v83-zurk")
        g.press("/")
        settle(g, 300)
        self.assertEqual(g.sim.get_mission("MIS_ZURK_01_VISIT_01"), 2)

    def test_ctrl_story_key_twice_restarts_a_running_story(self):
        g = game("v83-force", missions={"MIS_CORD_01_FIRST_VISIT": 2})
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_CORD_01_FIRST_VISIT",
               ObjectiveName="OBJ_CORD_04_FORGE_FIGHT", ObjectiveState=1)
        warp(g, "cordelion")
        self.assertIn("already active", hub(g)["attempts"]["cordelion_1"]["detail"])
        g.press("/", ctrl=True)
        self.assertTrue(g.note_has("again to start"))
        g.press("/", ctrl=True)
        settle(g, 300)
        self.assertIn("restarted", hub(g)["attempts"]["cordelion_1"]["detail"])
        self.assertTrue(any("[STORY RESTART BY HAND] cordelion_1" in x for x in py(g.state.history)))


class KeyTests(unittest.TestCase):
    def test_keyboard_keys_and_the_old_f_keys(self):
        g = game("v83-keys")
        self.assertTrue(g.log_has("RANDO-KEYS\tkeyboard keys on"))
        g.press("]")
        self.assertTrue(g.note_has("Ctrl+] to go"))
        g.press(";")
        self.assertTrue(g.note_has("hub 0/13 done"))
        g.press("F6")                                    # legacy_f_keys
        self.assertTrue(g.log_has("RANDO-KEY\tF6"))
        warp(g, "ardolis")
        self.assertEqual(g.state.current_planet, "ardolis")
        self.assertTrue(g.log_has("RANDO-KEY\t.\twith Ctrl"))

    def test_legacy_keys_off(self):
        g = game("v83-nolegacy", {"legacy_f_keys": False})
        self.assertIsNone(g.R.bound[VK_F6])
        self.assertIsNotNone(g.R.bound[0xDD])            # ]

    def test_any_key_name(self):
        g = game("v83-names", {"key_hub": "K", "key_story": "NUMPAD5", "key_test_travel": "HOME"})
        self.assertEqual(g.R.vk("K"), 0x4B)
        self.assertEqual(g.R.vk("NUMPAD5"), 0x65)
        self.assertEqual(g.R.vk("HOME"), 0x24)
        self.assertEqual(g.R.vk("\\"), 0xDC)
        self.assertEqual(g.R.config.key_hub, "K")
        self.assertIsNotNone(g.R.bound[0x4B])

    def test_bad_key_name_keeps_the_default(self):
        g = game("v83-bad", {"key_hub": "NOPE"})
        self.assertEqual(g.R.config.key_hub, "]")
        self.assertTrue(g.log_has("is not a key name"))

    def test_rivet_key_without_windows_codes_falls_back_to_f_keys(self):
        g = Game(settings={"seed": "v83-old", "preset": "hub"},
                 before_scripts=lambda gm: gm.lua.execute(
                     "local k = rivet.key; rivet.key = function(n) local v = k(n); return v and (v + 1000) end"))
        self.assertFalse(g.R.keys_numeric)
        self.assertEqual(g.R.config.key_hub, "F6")
        self.assertEqual(g.R.config.key_story, "F4")
        self.assertTrue(g.log_has("cannot be bound here - using"))

    def test_settings_file_uses_keyboard_keys(self):
        g = Game(settings_file=True)
        c = g.R.config
        self.assertEqual((c.key_status, c.key_hub, c.key_hub_return, c.key_test_travel, c.key_test_point, c.key_story),
                         (";", "]", "[", ".", ",", "/"))
        self.assertTrue(c.story_on_arrival)
        self.assertTrue(c.story_reload_stuck)                  # 8.4 name
        self.assertTrue(c.story_prime_before_travel)
        self.assertFalse(c.test_travel)                         # 8.4: off for a real playthrough
        self.assertTrue(c.legacy_f_keys)

    def test_seed_is_unchanged(self):
        a = hub_game("v83-same")
        b = hub_game("v83-same", {"story_on_arrival": False, "key_hub": "K", "legacy_f_keys": False})
        for g in (a, b):
            g.companion_restore()
            g.wait_seed()
        self.assertEqual(a.seed.fingerprint, b.seed.fingerprint)


if __name__ == "__main__":
    unittest.main()
