"""Randomizer 7.0 runtime tests against the SIMULATED game (tests/sim/rivet_sim.lua):

  * locked levels (14_rando_travel.lua): a planet chosen in the planet menu without its
    Coordinates sends you back; the game's own planet changes are never blocked; fallbacks
  * the vendor's prices (12_rando_shop.lua): found by the slots' own vanilla prices, then written
  * start currency, variable currency amounts
  * restored_weapons = "auto": the seed waits for the companion's ARSENAL_RESTORED check

What these prove: the scripts' decisions. What they cannot prove: that your game's events, warp
and vendor memory behave like the simulation (docs/TESTING.md lists the in-game checks)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game  # noqa: E402

LEVELS = {"seed": "levels-1", "preset": "campaign"}


def locked_planet(g):
    """a planet whose Coordinates the start does not hold, and a checkpoint name for it"""
    cps = {"savali": ("Savali", "CHK_SAV_01_LANDING"), "blizar_prime": ("Blizar", "CHK_BLIZAR_A_LANDINGPAD"),
           "torren_iv": ("Torren", "CHK_MOL_01_LANDING"), "cordelion": ("Cordelion", "CHK_CORD_LANDINGPAD"),
           "ardolis": ("Ardolis", "CHK_ARD_LANDING_SHIP"), "viceron": ("Viceron", "CHK_ZORD_00_DEFAULT")}
    for pid, (ev, cp) in cps.items():
        if not g.state.access[pid]:
            return pid, ev, cp
    raise AssertionError("every planet is open")


def menu_travel(g, event_name, checkpoint, frames=30):
    """the ship's planet menu: PlanetMenuAcceptEvent, then the landing (round 14 lines 171-172)"""
    g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=checkpoint, InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
    g.travel(event_name, frames)


class LevelTests(unittest.TestCase):
    def test_start_opens_the_storys_own_planets(self):
        g = Game(settings=LEVELS).ready()
        self.assertTrue(g.seed.travel_lock)
        for pid in ("corson_v", "nefarious_city", "sargasso"):
            self.assertTrue(g.state.access[pid], pid)
        self.assertTrue(g.note_has("Randomizer start:"))
        self.assertFalse(any("Coordinates:" in n and "start" in n for n in g.notes()))  # start text lists items, not planets

    def test_menu_travel_to_a_locked_planet_sends_you_back(self):
        g = Game(settings=LEVELS).ready()
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(30)
        self.assertEqual(len(g.sim.warps), 0)                     # waits for the landing to settle
        self.assertTrue(g.note_has("no Coordinates for"))
        g.step(200)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_SHIP"])   # back to Nefarious City
        self.assertEqual(g.state.travel.sent_back, 1)
        self.assertTrue(g.log_has("warped back to"))
        # the warp's own landing is not a menu choice: never blocked
        g.travel("NefCity")
        g.step(300)
        self.assertEqual(len(g.sim.warps), 1)
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_the_games_own_planet_changes_are_never_blocked(self):
        g = Game(settings=LEVELS).ready()
        pid, ev, cp = locked_planet(g)
        g.travel(ev)                                              # the story / a rift / a load: no menu event
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        self.assertTrue(g.log_has("without the planet menu"))
        # its rewards pay: you are there legitimately
        lid = g.location_with(lambda l, it: g.data.locations[l].planet == pid and g.data.locations[l].kind == "planet")
        g.R.collect(lid, "test")
        self.assertTrue(g.state.paid[lid])

    def test_menu_travel_to_an_open_planet_is_remembered(self):
        g = Game(settings=LEVELS).ready()
        menu_travel(g, "Zurkon", "CHK_ZURK_00_DEFAULT")
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        self.assertEqual(g.state.travel.landed["scarstu"], "CHK_ZURK_00_DEFAULT")
        # from Zurkie's to a locked planet: back to where you landed on Zurkie's
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_ZURK_00_DEFAULT"])

    def test_coordinates_arriving_before_the_warp_keep_you_there(self):
        g = Game(settings=LEVELS).ready()
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.R.grant("access:" + pid)
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        self.assertTrue(g.note_has("you can fly to"))

    def test_no_checkpoint_or_a_failed_warp_banks_the_rewards(self):
        g = Game(settings=LEVELS)                                  # no Sargasso checkpoint in the data
        g.lua.execute("for _, p in ipairs(RANDO_DATA.planets) do if p.id == 'sargasso' then p.checkpoints.known = {} end end")
        g.ready(planet="Sargasso")
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        self.assertTrue(g.log_has("not sent back"))
        lid = g.location_with(lambda l, it: g.data.locations[l].planet == pid and g.data.locations[l].kind == "planet")
        g.R.collect(lid, "test")
        self.assertTrue(g.state.banked[lid])
        self.assertFalse(g.state.paid[lid])
        g.R.grant("access:" + pid)
        self.assertTrue(g.state.paid[lid])
        # a failed warp does the same
        g2 = Game(settings=LEVELS)
        g2.lua.execute("rivet.warp = function(cp) error('checkpoint not loaded') end")
        g2.ready()
        pid2, ev2, cp2 = locked_planet(g2)
        menu_travel(g2, ev2, cp2)
        g2.step(400)
        self.assertTrue(g2.log_has("failed"))
        self.assertTrue(g2.state.travel.banked_planets[pid2])

    def test_checkpoint_search_by_planet_code(self):
        g = Game(settings=LEVELS)
        # 8.1: no LANDING checkpoint (Torren IV and Cordelion in your game): the best scored one,
        # never a boss or a cinematic. Sargasso's logged checkpoint is taken out for the test.
        g.lua.execute("rivet.checkpoints = function(f) return { 'CHK_SARG_02_BOSS', 'CHK_SARG_01_INTRO_CINE', 'CHK_SARG_01_START', 'CHK_SAV_01_LANDING' } end")
        g.lua.execute("for _, p in ipairs(RANDO_DATA.planets) do if p.id == 'sargasso' then p.checkpoints.known = {} end end")
        g.ready(planet="Sargasso")
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        self.assertEqual(list(g.sim.warps.values()), ["CHK_SARG_01_START"])
        T = g.g.RANDO_TRAVEL
        self.assertEqual(T.planet_of_checkpoint("CHK_TRANSITION_TO_ZURKIES"), "scarstu")
        self.assertEqual(T.planet_of_checkpoint("CHK_NEFCITY_SHIP"), "nefarious_city")
        self.assertIsNone(T.planet_of_checkpoint("CHK_SOMETHING_ELSE"))

    def test_levels_runtime_off_banks_instead(self):
        g = Game(settings=dict(LEVELS, levels_runtime=False)).ready()
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        lid = g.location_with(lambda l, it: g.data.locations[l].planet == pid and g.data.locations[l].kind == "planet")
        g.R.collect(lid, "test")
        self.assertTrue(g.state.banked[lid])

    def test_ctrl_f9_twice_opens_the_planet_by_hand(self):
        g = Game(settings=LEVELS).ready()
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        g.press("F9", ctrl=True)
        self.assertFalse(g.state.access[pid])
        g.press("F9", ctrl=True)
        self.assertTrue(g.state.access[pid])
        self.assertTrue(any("[OPENED BY HAND]" in h for h in g.state.history.values()))
        g.press("F9")                                             # plain F9 is still the status
        self.assertTrue(g.note_has("planets open"))

    def test_travel_state_survives_a_restart(self):
        g = Game(settings=LEVELS).ready()
        menu_travel(g, "Zurkon", "CHK_ZURK_00_DEFAULT")
        g.step(400)
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        text = g.companion_export()
        g2 = Game(settings=LEVELS)
        g2.companion_restore(text)
        self.assertEqual(g2.state.travel.landed["scarstu"], "CHK_ZURK_00_DEFAULT")
        self.assertEqual(g2.state.travel.sent_back, 1)

    def test_levels_off_seed_never_warps(self):
        g = Game().ready()
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING")
        g.travel("Savali")
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)


class PriceTests(unittest.TestCase):
    def test_prices_are_found_and_written(self):
        g = Game().ready(frames=900)
        prices = g.seed.shop.prices
        self.assertIsNotNone(prices)
        self.assertTrue(g.log_has("Price at +0x18 (u32"))
        authored = list(g.sim.vendor_mem[Game.VENDOR_ID].authored.values())
        by_id = {g.data["items"][k].id: k for k in g.data["items"].keys() if g.data["items"][k].category == "weapon"}
        checked = 0
        for i, item_id in enumerate(authored, start=1):
            slot = by_id.get(item_id)
            if slot and prices[slot] is not None:
                self.assertEqual(g.sim.vendor_slot_price(Game.VENDOR_ID, i), prices[slot], slot)
                checked += 1
        self.assertEqual(checked, 15)
        # Shatterbomb's own slot keeps its price
        sb = authored.index(g.data["items"]["weapon:shatterbomb"].id) + 1
        self.assertEqual(g.sim.vendor_slot_price(Game.VENDOR_ID, sb), 1250)

    def test_prices_left_alone_when_the_field_is_not_found(self):
        g = Game()
        g.install_vendor(prices=None)                             # 6.0's made-up prices: nothing matches
        g.ready(frames=900)
        self.assertTrue(g.log_has("prices left as they are"))
        self.assertTrue(g.log_has("weapon slots, "))              # the weapons are still shuffled
        self.assertEqual(g.sim.vendor_slot_price(Game.VENDOR_ID, 2), 2000)
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_vanilla_prices_setting_writes_nothing(self):
        g = Game(settings={"shop_prices": "vanilla"}).ready(frames=900)
        self.assertFalse(g.log_has("Price at"))
        self.assertTrue(g.log_has("weapon slots, "))


class CurrencyStartTests(unittest.TestCase):
    def test_start_currency(self):
        g = Game(settings={"start_bolts": 4000, "start_raritanium": 30}).ready(frames=900)
        self.assertEqual(g.sim.currency[g.data["items"]["currency:bolts"].id], 4000)
        self.assertEqual(g.sim.currency[g.data["items"]["currency:raritanium"].id], 30)
        self.assertTrue(g.note_has("4000 Bolts"))

    def test_amounts_differ_per_location(self):
        g = Game(settings={"bolts_budget": 0}).ready()
        amounts = {int(str(g.seed.locations[l].item).split(":")[2]) for l in g.seed.locations.keys()
                   if str(g.seed.locations[l].item).startswith("filler:bolts:")}
        self.assertGreater(len(amounts), 8)


class ArsenalAutoTests(unittest.TestCase):
    def test_seed_waits_for_the_companions_check(self):
        g = Game(settings={"seed": "ar-auto", "restored_weapons": "auto"})
        g.step(120)
        self.assertIsNone(g.g.RANDO_SEED)
        self.assertEqual(g.bridge("return rando_arsenal_mode()"), "auto")
        self.assertEqual(g.bridge("return rando_set_arsenal(true)"), "ok")
        self.assertTrue(g.wait_seed())
        self.assertTrue(g.seed.settings.include_arsenal_restored)
        self.assertTrue(g.log_has("ARSENAL_RESTORED is installed"))
        names = set(g.seed.shop.slots.values()) | set(g.seed.start["items"].values()) | \
            {g.seed.locations[l].item for l in g.seed.locations.keys()}
        self.assertIn("weapon:predator_launcher", names)

    def test_no_companion_means_not_installed(self):
        g = Game(settings={"seed": "ar-auto", "restored_weapons": "auto"})
        g.step(3700)
        self.assertTrue(g.wait_seed())
        self.assertFalse(g.seed.settings.include_arsenal_restored)
        self.assertTrue(g.log_has("did not answer"))

    def test_random_seed_and_auto(self):
        g = Game(settings={"seed": "random", "restored_weapons": "auto"})
        g.step(10)
        self.assertEqual(g.bridge("return rando_set_arsenal(false)"), "ok")
        text = g.bridge('return rando_use_seed("")')
        self.assertTrue(g.wait_seed())
        self.assertEqual(g.seed.seed, text)
        self.assertFalse(g.seed.settings.include_arsenal_restored)

    def test_fixed_setting_does_not_wait(self):
        g = Game(settings={"seed": "ar-fixed", "restored_weapons": True})
        self.assertTrue(g.wait_seed())
        self.assertTrue(g.seed.settings.include_arsenal_restored)
        self.assertEqual(g.bridge("return rando_arsenal_mode()"), "fixed")


class SimulatedCampaignTests(unittest.TestCase):
    """New Game to finale on level-locked seeds, in the simulated game: the player follows the
    game's own story; before each visit to a locked planet they collect what the open planets
    offer until its Coordinates arrive, then fly there through the planet menu. The randomizer
    must never send them back from a planet the story needs, and nothing may stay locked."""

    PLANET_EVENT = {"corson_v": "Malinon", "nefarious_city": "NefCity", "sargasso": "Sargasso", "scarstu": "Zurkon",
                    "savali": "Savali", "blizar_prime": "Blizar", "torren_iv": "Torren", "cordelion": "Cordelion",
                    "ardolis": "Ardolis", "viceron": "Viceron"}
    CHECKPOINT = {"corson_v": "CHK_MEGA_00_DEFAULT", "nefarious_city": "CHK_NEFCITY_SHIP", "sargasso": "CHK_SARG_00_DEFAULT",
                  "scarstu": "CHK_ZURK_00_DEFAULT", "savali": "CHK_SAV_01_LANDING", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD",
                  "torren_iv": "CHK_MOL_00_DEFAULT", "cordelion": "CHK_CORD_00_DEFAULT", "ardolis": "CHK_ARD_00_DEFAULT",
                  "viceron": "CHK_ZORD_00_DEFAULT"}

    def play(self, seed, preset):
        g = Game(settings={"seed": seed, "preset": preset}).ready()
        C = g.g.RANDO_CAMPAIGN
        segs = [C.SEGMENTS[i] for i in range(1, len(C.SEGMENTS) + 1)]
        pos = {sg.id: i for i, sg in enumerate(segs)}
        here = "nefarious_city"
        story_done = 0                                           # visits finished so far
        waited = 0                                               # locations collected while a planet was locked

        def reachable(lid):
            loc = g.data.locations[lid]
            if g.state.collected[lid]:
                return False
            if not g.seed.locations[lid].in_logic:
                return False
            if loc.planet and not g.state.access[loc.planet]:
                return False
            sid = C.location_segment(lid, loc.planet)
            if sid and pos[sid] >= story_done and loc.kind != "armor_source":
                return False                                     # that part of the story is not reached yet
            for r in (loc.requires or {}).values():
                if not str(r).startswith("ability:") and r not in ("hoverboots", "map_o_matic") and not g.state.inventory[r]:
                    return False
            return True

        for i, sg in enumerate(segs):
            pid = sg.planet
            guard = 0
            while not g.state.access[pid]:
                cand = [l for l in sorted(g.seed.locations.keys()) if reachable(l)]
                self.assertTrue(cand, f"{seed}: stuck before {sg.id}: {pid} locked and nothing left to collect")
                g.R.collect(cand[0], "simulated player")
                g.step(5)
                guard += 1
                waited += 1
                self.assertLess(guard, 200)
            if pid != here:
                if sg.arrival == "story":
                    g.travel(self.PLANET_EVENT[pid])
                else:
                    menu_travel(g, self.PLANET_EVENT[pid], self.CHECKPOINT[pid])
                g.step(300)
                self.assertEqual(len(g.sim.warps), 0, f"{seed}: sent back from {pid}, which the story needs ({sg.id})")
                here = pid
            for m in sg.missions.values():
                g.fire("MissionStateChangedEvent", MissionName=m, MissionState=4)
            story_done = i + 1
        self.assertTrue(g.state.campaign_complete, seed)
        self.assertFalse(g.log_has("RANDO-ERROR"))
        g.waited = waited
        return g

    def test_campaign_and_everything_presets_to_the_finale(self):
        waited = 0
        for i in range(12):
            for preset in ("campaign", "everything", "chaos"):
                waited += self.play(f"simcamp-{i}", preset).waited
        self.assertGreater(waited, 36)                            # the story really waited for Coordinates


if __name__ == "__main__":
    unittest.main()
