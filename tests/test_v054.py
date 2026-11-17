"""Public Release v0.54 (kit 10.0.5, generator 10.0.2): round 26.

You report: [ (back to Nefarious City) is useless; after trips with ] / Ctrl+] the inventory was
gone; some levels "don't work" when you warp to them. You ask for a key that turns the planet
randomizer off and on, remembered between sessions.

What each test rests on:
  * round 26 (tests/data/round26_rivet.log, v0.53, seed pocket-pocket-zurkie-839, a restored save):
    the game booted on Nefarious City, then the save continued on Viceron. No key was pressed and
    no planet menu was used in that session, yet the hub logged "the game's own story took you to
    viceron - back to the hub" and announced the trip back. Its guard after a finished destination
    compared this session's frame with h.finished_at, a frame of an EARLIER session saved with the
    hub's state (frames start at 0 in every session)
  * the same load on Viceron replayed one gadget and no weapon at all, while the randomizer held
    15 items as given ("in inventory 15"): the save itself had lost them
  * the start banner read "Randomizer 10. - seed ..." (the kit version cut to 3 characters)
  * what empties the inventory is NOT known; the give-back works whatever the cause
Nothing here has run in the game.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v100 import py  # noqa: E402
from test_v100 import choose, hub, hub_game, to_hub  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LEVELS_AT_BOOT = 0x6
ALL_LEVELS = 0x7FE


def read_log(name):
    with open(os.path.join(DATA, name), encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def all_at(lines, pattern):
    return [i for i, l in enumerate(lines) if re.search(pattern, l)]


def finished_city(seed, settings=None):
    """a hub game whose city story is finished in this session (h.finished_at was set in v0.53)"""
    g = to_hub(hub_game(seed, settings))
    g.sim.complete_mission("MIS_NEFCITY_01")
    g.step(3000)
    assert "nefcity_1" in hub(g)["done"]
    return g


def next_session(g, seed):
    """the game closed and started again: the companion restores the save into a fresh session"""
    saved = g.companion_export()
    g2 = hub_game(seed)
    # the game's WeaponType numbers belong to the weapons, not to the session (round 13 / 20)
    for k, v in py(g.sim.weapon_type).items():
        g2.sim.weapon_type[k] = v
    g2.sim.next_weapon_type = g.sim.next_weapon_type
    g2.companion_restore(saved)
    return g2


def weapons_given(g):
    out = []
    for item, r in py(g.state.real or {}).items():
        info = g.data.real_items[item]
        if info is not None and info.kind == "weapon" and r["status"] in ("confirmed", "owned"):
            out.append(item)
    return sorted(out)


def wipe_inventory(g):
    g.sim.weapons_owned = g.lua.table()
    g.sim.gadgets_owned = g.lua.table()


class EvidenceTests(unittest.TestCase):
    """What round 26's log says, read straight from it."""

    def test_round26_the_hub_sent_a_save_load_home(self):
        L = read_log("round26_rivet.log")
        self.assertTrue(all_at(L, r"RANDO-KIT all 14 scripts are 10\.0\.4"))
        self.assertTrue(all_at(L, r"RANDO-SAVE restored:"))               # an earlier session's save
        undone = all_at(L, r"the game's own story took you to\tviceron\t- back to the hub")
        self.assertEqual(len(undone), 1)
        # nothing of the player's moved Ratchet: no key, no planet menu, no launch of the hub's
        self.assertFalse(all_at(L, r"RANDO-KEY\t"))
        self.assertFalse(all_at(L, r"PlanetMenuAcceptEvent|planet menu:"))
        self.assertFalse(all_at(L, r"RANDO-HUB\tlaunch\t"))
        # and no destination had finished in this session (the guard's frame was an old one)
        self.assertFalse(all_at(L, r"HUB: .* finished|Destination complete"))
        self.assertTrue(all_at(L, r"\[ORDER KEPT\] the game's own travel to viceron undone"))

    def test_round26_viceron_loaded_without_your_weapons(self):
        L = read_log("round26_rivet.log")
        self.assertTrue(all_at(L, r"RANDO-SAVE restored:.*in inventory 15"))
        vic = all_at(L, r"PlanetChangedEvent\tNewPlanetName=Viceron")[0]
        after = L[vic:]
        self.assertEqual(len(all_at(after, r"WeaponAddedEvent")), 0)
        self.assertEqual(len(all_at(after, r"GadgetItemAddedEvent")), 1)
        boot = L[:vic]
        self.assertGreaterEqual(len(all_at(boot, r"GadgetItemAddedEvent")), 5)

    def test_round26_banner(self):
        L = read_log("round26_rivet.log")
        self.assertTrue(all_at(L, r"RANDO-NOTIFY\tRandomizer 10\. - seed"))


class GuardTests(unittest.TestCase):
    def test_a_save_on_another_planet_is_left_alone_in_the_next_session(self):
        g = finished_city("v054-guard")
        self.assertIsNone(hub(g).get("finished_at"))          # nothing of the frame is saved any more
        g2 = next_session(g, "v054-guard")
        g2.sim.load_save("NefCity")
        g2.step(300)
        g2.travel("Viceron")                                  # the save continues there (round 26)
        g2.step(2000)
        self.assertEqual(g2.sim.planet, "Viceron")
        self.assertEqual(list(g2.sim.warps.values()), [])
        self.assertFalse(g2.log_has("the game's own story took you to"))
        self.assertTrue(g2.log_has("arrived on\tviceron\t(a load) - nothing changed"))

    def test_an_old_saved_frame_is_ignored(self):
        # a save written by v0.53 still carries h.finished_at: it must not hold the guard
        g = finished_city("v054-old")
        g.lua.execute("RANDO.state.hub.finished_at = 999999")
        g2 = next_session(g, "v054-old")
        self.assertIsNone(hub(g2).get("finished_at"))
        g2.sim.load_save("NefCity")
        g2.step(300)
        g2.travel("Viceron")
        g2.step(2000)
        self.assertEqual(g2.sim.planet, "Viceron")
        self.assertFalse(g2.log_has("ORDER KEPT"))

    def test_the_guard_still_keeps_the_order_right_after_a_finish(self):
        # the city's story ends with the game's own rift to Sargasso (round 16): undone, as before
        # (dev 10.11: when Sargasso's first visit is open that trip is played instead, hub_follow_new;
        # tests/test_v1011.py covers it)
        g = finished_city("v054-order", {"hub_follow_new": False})
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(g.log_has("[ORDER KEPT] the game's own travel to sargasso undone"))


class BackKeyTests(unittest.TestCase):
    def test_bracket_no_longer_goes_back_to_the_hub(self):
        g = to_hub(hub_game("v054-back"))
        g.R.grant("access:savali")
        g.step(30)
        choose(g, "savali_1")
        self.assertEqual(g.sim.planet, "Savali")
        warps = list(g.sim.warps.values())
        g.press("[")
        g.press("[")
        g.step(600)
        self.assertEqual(g.sim.planet, "Savali")
        self.assertEqual(list(g.sim.warps.values()), warps)
        self.assertEqual(hub(g)["current"], "savali_1")      # the destination is untouched
        self.assertTrue(g.note_has("only cancels the trip back"))

    def test_bracket_still_cancels_the_automatic_return(self):
        g = to_hub(hub_game("v054-stay"))
        g.R.grant("access:savali")
        g.step(30)
        choose(g, "savali_1")
        g.sim.complete_mission("MIS_SAV_01")
        g.step(30)
        self.assertIsNotNone(g.g.RANDO_HUB.return_at)
        g.press("[")
        g.step(600)
        self.assertEqual(g.sim.planet, "Savali")
        self.assertTrue(g.note_has("staying here"))

    def test_ctrl_bracket_still_finishes_by_hand(self):
        g = to_hub(hub_game("v054-finish"))
        g.press("[", ctrl=True)
        g.press("[", ctrl=True)
        g.step(30)
        self.assertIn("nefcity_1", hub(g)["done"])


class ShuffleKeyTests(unittest.TestCase):
    def test_zero_turns_planet_shuffle_off_and_on(self):
        g = to_hub(hub_game("v054-zero"))
        H = g.g.RANDO_HUB
        g.lua.execute("RANDO.state.hub.current = nil; RANDO_HUB.apply_world('test')")
        g.step(60)
        self.assertEqual(g.sim.travel_flag, 1)
        g.press("0")
        g.step(60)
        self.assertTrue(H.shuffle_off())
        self.assertFalse(H.enabled())
        self.assertIsNone(g.state.planet_shuffle)
        self.assertTrue(g.note_has("planet shuffle OFF"))
        # the travel byte and the level bits this session set are the game's again
        self.assertEqual(g.sim.travel_flag, 0)
        self.assertEqual(g.sim.levels, LEVELS_AT_BOOT)
        # the hub's keys say so and do nothing
        warps = list(g.sim.warps.values())
        g.press("]", ctrl=True)
        g.step(600)
        self.assertEqual(list(g.sim.warps.values()), warps)
        self.assertTrue(g.note_has("planet shuffle is off - 0 turns it on"))
        self.assertIn("planet shuffle OFF", g.R.status_text())
        g.press("0")
        g.step(400)
        self.assertFalse(H.shuffle_off())
        self.assertTrue(g.state.planet_shuffle)
        self.assertTrue(g.note_has("planet shuffle ON"))
        self.assertEqual(g.sim.travel_flag, 1)                # back on at the hub
        self.assertEqual(g.sim.levels & ALL_LEVELS, ALL_LEVELS)

    def test_off_the_games_own_travel_is_never_undone(self):
        g = to_hub(hub_game("v054-free"))
        g.press("0")
        g.sim.complete_mission("MIS_NEFCITY_01")             # the game rifts to Sargasso
        g.step(3000)
        self.assertEqual(g.sim.planet, "Sargasso")
        self.assertFalse(g.log_has("ORDER KEPT"))
        # a planet without Coordinates is not left either (no send-back)
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_BLIZAR_A_LANDINGPAD",
               InterplanetaryCheckpointName="CHK_TRANSITION_TO_BLIZAR")
        g.travel("Blizar")
        g.step(900)
        self.assertEqual(g.sim.planet, "Blizar")
        self.assertFalse(g.note_has("no Coordinates for Blizar Prime yet"))
        # the story's mission still finishes and pays (items stay randomized)
        self.assertIn("nefcity_1", hub(g)["done"])

    def test_off_nothing_scheduled_fires_later(self):
        g = to_hub(hub_game("v054-quiet"))
        g.R.grant("access:savali")
        g.step(30)
        choose(g, "savali_1")
        g.sim.complete_mission("MIS_SAV_01")
        g.step(30)
        self.assertIsNotNone(g.g.RANDO_HUB.return_at)
        g.press("0")
        g.step(1500)
        self.assertEqual(g.sim.planet, "Savali")              # no automatic trip back
        g.press("0")
        g.step(1500)
        self.assertEqual(g.sim.planet, "Savali")              # nor once it is on again

    def test_the_choice_is_saved_restored_and_kept_over_a_new_game(self):
        g = to_hub(hub_game("v054-save"))
        g.press("0")
        g.step(30)
        saved = g.companion_export()
        self.assertNotIn('["planet_shuffle"]', saved)
        g2 = hub_game("v054-save", planet_shuffle=False)
        g2.companion_restore(saved)
        g2.sim.load_save("NefCity")
        g2.step(400)
        self.assertTrue(g2.g.RANDO_HUB.shuffle_off())
        self.assertTrue(g2.log_has("planet shuffle is OFF in this save"))
        self.assertEqual(g2.sim.travel_flag, 0)               # the hub did not turn travel on
        # a New Game starts the seed over, but not your choice
        g2.sim.new_game()
        g2.step(120)
        self.assertIsNone(g2.state.planet_shuffle)
        self.assertTrue(g2.g.RANDO_HUB.shuffle_off())

    def test_a_choice_made_before_the_restore_wins(self):
        g = to_hub(hub_game("v054-early"))
        saved = g.companion_export()                          # saved with shuffle ON
        self.assertIn('["planet_shuffle"]=true', saved)
        g2 = hub_game("v054-early", planet_shuffle=False)
        g2.wait_seed()
        g2.press("0")                                         # pressed before the companion connected:
        g2.press("0")                                         # on, then off again
        g2.companion_restore(saved)
        self.assertTrue(g2.g.RANDO_HUB.shuffle_off())

    def test_after_a_load_elsewhere_the_saves_travel_is_left_on(self):
        # a load sets the save's own travel byte (a later save has the ship): nothing to take back
        g = to_hub(hub_game("v054-loaded"))
        g.lua.execute("RANDO.state.hub.current = nil; RANDO_HUB.apply_world('test')")
        g.step(60)
        self.assertEqual(g.sim.travel_flag, 1)
        g.R.grant("access:savali")
        g.sim.load_save("Savali")
        g.step(300)
        g.press("0")
        g.step(60)
        self.assertEqual(g.sim.travel_flag, 1)
        self.assertFalse(g.log_has("planetary travel off (planet shuffle off)"))

    def test_the_travel_byte_the_game_had_on_is_not_turned_off(self):
        g = to_hub(hub_game("v054-gameon"))
        g.lua.execute("RANDO.state.hub.current = nil")
        g.sim.travel_flag = 1                                # the game itself has travel on
        g.lua.execute("RANDO_HUB.apply_world('test')")
        g.step(60)
        g.press("0")
        g.step(60)
        self.assertEqual(g.sim.travel_flag, 1)


class RestoreTests(unittest.TestCase):
    def trip(self, seed, wipe):
        g = to_hub(hub_game(seed))
        g.step(1200)                                          # the start items arrive
        given = weapons_given(g)
        self.assertGreaterEqual(len(given), 2, given)
        g.R.grant("access:savali")
        g.step(30)
        if wipe:
            wipe_inventory(g)
        before = {it: g.give_count(it) for it in given}
        choose(g, "savali_1", frames=3000)
        self.assertEqual(g.sim.planet, "Savali")
        return g, given, before

    def test_an_emptied_inventory_comes_back_after_a_trip(self):
        g, given, _ = self.trip("v054-lost", wipe=True)
        self.assertTrue(g.log_has("giving your items back"))
        self.assertTrue(g.note_has("your inventory looks emptied"))
        for it in given:
            self.assertTrue(g.owns(it), it)
            self.assertEqual(g.item_status(it), "confirmed")
        self.assertTrue(any(n.startswith("Given back: ") for n in g.notes()))
        self.assertTrue(g.owns("hoverboots"))
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_an_intact_inventory_is_left_alone(self):
        g, given, before = self.trip("v054-kept", wipe=False)
        self.assertTrue(g.log_has("known as yours - nothing to do"))
        self.assertFalse(g.log_has("giving your items back"))
        for it in given:
            self.assertEqual(g.give_count(it), before[it], it)

    def test_ctrl_zero_twice_gives_everything_back_quietly(self):
        g = to_hub(hub_game("v054-hand"))
        g.step(1200)
        given = weapons_given(g)
        g.sim.weapons_owned[g.data.real_items[given[0]].id] = None
        g.sim.inv_changed_on_owned = True
        g.press("0", ctrl=True)
        self.assertTrue(g.note_has("press Ctrl+0 again"))
        self.assertFalse(g.g.RANDO_HUB.shuffle_off())          # Ctrl+0 is not the shuffle toggle
        g.press("0", ctrl=True)
        g.step(2400)
        self.assertTrue(g.log_has("RANDO-RESTORE"))
        self.assertTrue(g.owns(given[0]))
        self.assertTrue(g.note_has("Given back: "))
        # the ones you still had: owned, quietly (no "you probably have it already")
        for it in given[1:]:
            self.assertIn(g.item_status(it), ("owned", "confirmed"), it)
        self.assertFalse(g.note_has("you probably have it already"))
        self.assertFalse(g.note_has("has not answered yet"))

    def test_a_save_that_lost_its_items_gets_them_back_when_it_loads(self):
        # round 26: the save continued on Viceron with no weapon; the randomizer knew them as given
        g = finished_city("v054-loadlost")
        given = weapons_given(g)
        self.assertGreaterEqual(len(given), 2, given)
        g2 = next_session(g, "v054-loadlost")                  # a fresh game: the save owns none of them
        g2.sim.load_save("NefCity")
        g2.step(300)
        g2.travel("Viceron")
        g2.step(3000)
        self.assertTrue(g2.log_has("RANDO-RESTORE after\tthe load on viceron:"))
        for it in given:
            self.assertTrue(g2.owns(it), it)
        self.assertEqual(g2.sim.planet, "Viceron")

    def test_the_setting_turns_the_automatic_give_back_off(self):
        g = to_hub(hub_game("v054-noauto", {"restore_inventory": False}))
        g.step(1200)
        g.R.grant("access:savali")
        g.step(30)
        wipe_inventory(g)
        choose(g, "savali_1", frames=3000)
        self.assertFalse(g.log_has("giving your items back"))


class BannerTests(unittest.TestCase):
    def test_the_banner_names_the_release_and_the_kit(self):
        g = to_hub(hub_game("v054-banner"))
        self.assertTrue(g.note_has("Randomizer dev 10.24 - seed"))
        self.assertTrue(g.log_has("planet shuffle 0"))       # RANDO-KEYS lists the new key


if __name__ == "__main__":
    unittest.main()
