"""Randomizer 8.2: test travel (16_rando_testtravel.lua) and the round 18 checkpoint catalog fix.

  * test_travel = true: F7 picks any planet, F8 its landing point, Ctrl+F7 warps, Ctrl+F8 flies
  * a test trip is not sent back by locked levels, and opens no Coordinates (9.0: no hub)
  * the ship's planet menu to a planet without Coordinates: you stay while test travel is on
  * test_travel = false (the default in the runtime): the keys only say so; 8.1 behaviour unchanged
  * round 18: the checkpoint catalog ran past rivet_hook's 8 ms frame budget (14_rando_travel.lua
    lines 115/140/141/197) and never finished. It is now time-sliced and looks codes up in a table;
    the planet it gives every checkpoint name your logs list is the same as 8.1's.
The game here is the simulator (tests/sim/rivet_sim.lua), NOT your game.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402
from story_helpers import level_game, started  # noqa: E402
from test_levels import LEVELS, locked_planet, menu_travel  # noqa: E402

DATA = os.path.join(ROOT, "tests", "data")

# 8.1's planet_of_checkpoint, kept here to compare the 8.2 lookup with
OLD_PLANET_OF_CHECKPOINT = """
return function(name)
  if type(name) ~= "string" then return nil end
  local up = name:upper()
  local best, blen = nil, 0
  for _, p in ipairs(RANDO_DATA.planets) do
    for _, code in ipairs((p.checkpoints and p.checkpoints.codes) or {}) do
      for tok in up:gmatch("[^_]+") do
        if tok:sub(1, #code) == code and #code > blen then best, blen = p.id, #code end
      end
    end
  end
  return best
end
"""


def logged_checkpoint_names():
    names = set()
    for f in os.listdir(DATA):
        if f.endswith(".log"):
            with open(os.path.join(DATA, f), encoding="utf-8", errors="replace") as fh:
                for m in re.finditer(r"\bCHK_[A-Za-z0-9_]+", fh.read()):
                    names.add(m.group(0))
    return sorted(names)


def test_game(seed="tt-1", settings=None, **kw):
    st = {"test_travel": True}
    st.update(settings or {})
    g = started(level_game(seed, st, **kw))
    g.step(1200)                     # the checkpoint catalog starts 600 frames in (as in the game)
    return g


def select(g, pid):
    TT = g.g.RANDO_TEST_TRAVEL
    for _ in range(12):
        g.press("F7")
        if TT.selected() == pid:
            return
    raise AssertionError("F7 never selected " + pid)


def land(g, frames=600):
    for _ in range(frames // 30):
        g.step(30)


class TestTravelTests(unittest.TestCase):
    def test_script_loads_and_is_on(self):
        g = test_game()
        self.assertTrue(g.g.RANDO_TEST_TRAVEL.on())
        self.assertTrue(g.log_has("RANDO-TEST\tloaded (10.0.17) - test travel is ON"))
        self.assertIn("TEST TRAVEL on", g.R.status_text())

    def test_warp_to_a_planet_without_coordinates_stays_there(self):
        g = test_game()
        locked = next(p["id"] for p in py(g.data.planets) if not g.state.access[p["id"]] and p["id"] not in ("scarstu", "corson_v"))
        select(g, locked)
        self.assertTrue(g.note_has("Test travel "))
        g.press("F7", ctrl=True)
        land(g)
        self.assertEqual(g.g.RANDO_TRAVEL.planet_of_checkpoint(g.sim.last_cp), locked)
        self.assertEqual(g.state.current_planet, locked)
        self.assertFalse(g.state.access[locked])                    # no Coordinates were given
        # 9.0: a test trip starts no story (the hub's story starter is gone)
        self.assertEqual([c.kind for c in g.sim.mission_calls.values() if c.kind != 1], [])
        land(g, 1200)
        self.assertEqual(g.state.current_planet, locked)            # nothing sent you back
        self.assertTrue(any("[TEST TRAVEL] warp to " + locked in x for x in py(g.state.history)))
        # 8.4: a test trip's landing is offered again by test travel, never used by the lock
        self.assertEqual(g.state.travel.test_landed[locked], g.sim.last_cp)
        self.assertIsNone(g.state.travel.landed[locked])
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_every_planet_can_be_reached(self):
        g = test_game("tt-all")
        for p in py(g.data.planets):
            pid = p["id"]
            if pid == g.state.current_planet:
                continue
            select(g, pid)
            g.press("F7", ctrl=True)
            land(g, 900)
            self.assertEqual(g.state.current_planet, pid, pid)
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_f8_cycles_landing_points(self):
        g = test_game("tt-points")
        TT = g.g.RANDO_TEST_TRAVEL
        select(g, "blizar_prime")
        pts = [x["cp"] for x in py(TT.points("blizar_prime"))]
        self.assertGreaterEqual(len(pts), 2)
        self.assertEqual(pts[0], "CHK_BLIZAR_A_LANDINGPAD")
        self.assertEqual(len(pts), len(set(pts)))
        self.assertFalse(any("TRANSITION_TO" in p for p in pts))
        g.press("F8")
        self.assertEqual(TT.point["blizar_prime"], 2)
        g.press("F7", ctrl=True)
        land(g)
        self.assertEqual(g.sim.last_cp, pts[1])

    def test_fly_needs_a_ship_and_says_so(self):
        g = test_game("tt-fly")
        g.sim.ship_near = False
        select(g, "savali")
        g.press("F8", ctrl=True)
        g.step(120)
        self.assertTrue(g.note_has("fly to"))
        self.assertTrue(g.note_has("Ctrl+. warps instead"))   # 8.3 keys
        g.sim.ship_near = True
        g.press("F8", ctrl=True)
        land(g)
        self.assertEqual(g.state.current_planet, "savali")
        self.assertEqual(g.sim.travels[len(g.sim.travels)].how, "fly")

    def test_planet_menu_without_coordinates_stays(self):
        g = test_game("tt-menu")
        locked = next(p["id"] for p in py(g.data.planets)
                      if not g.state.access[p["id"]] and p["id"] not in ("scarstu", "corson_v"))
        cps = {"nefarious_city": "CHK_NEFCITY_SHIP", "savali": "CHK_SAV_01_LANDING", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD",
               "sargasso": "CHK_SARG_GELFACTORY_LANDINGPAD", "torren_iv": "CHK_MOL_01_START", "cordelion": "CHK_STATION_01_START",
               "ardolis": "CHK_ARD_01_ARRIVAL", "viceron": "CHK_ZORD_01_START"}
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cps[locked], InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from(
            {"planet": g.sim.planet_of_cp(cps[locked]), "at": g.sim.frame + 2, "cp": cps[locked]})
        land(g, 1500)
        self.assertEqual(g.state.current_planet, locked)
        self.assertFalse(g.state.travel.sent_back)
        self.assertTrue(g.note_has("no Coordinates, but you stay"))

    def test_works_after_a_save_load(self):
        g = level_game("tt-pre", {"test_travel": True})
        g.companion_restore()
        g.sim.load_save("NefCity")
        g.step(900)
        select(g, "ardolis")
        g.press("F7", ctrl=True)
        land(g)
        self.assertEqual(g.state.current_planet, "ardolis")
        land(g, 900)
        self.assertEqual(g.state.current_planet, "ardolis")

    def test_locked_levels_seed_does_not_send_back(self):
        g = Game(settings=dict(LEVELS, test_travel=True)).ready()
        pid, ev, cp = locked_planet(g)
        menu_travel(g, ev, cp)
        g.step(400)
        self.assertEqual(len(g.sim.warps), 0)
        self.assertTrue(g.note_has("no Coordinates, but you stay"))
        self.assertFalse(g.state.access[pid])

    def test_off_by_default_and_8_1_behaviour_kept(self):
        g = started(level_game("tt-off"))
        self.assertFalse(g.g.RANDO_TEST_TRAVEL.on())
        g.press("F7")
        self.assertTrue(g.note_has("test travel is off"))
        self.assertEqual(g.g.RANDO_TEST_TRAVEL.sel, 0)
        g2 = Game(settings=LEVELS).ready()
        pid, ev, cp = locked_planet(g2)
        menu_travel(g2, ev, cp)
        g2.step(400)
        self.assertEqual(g2.state.travel.sent_back, 1)

    def test_seed_is_unchanged_by_test_travel(self):
        a = level_game("tt-same")
        b = level_game("tt-same", {"test_travel": True})
        for g in (a, b):
            g.companion_restore()
            g.wait_seed()
        self.assertEqual(a.seed.fingerprint, b.seed.fingerprint)

    def test_settings_file_has_it_off_for_a_real_run(self):
        g = Game(settings_file=True)
        self.assertEqual(g.R.config.test_travel, False)       # 8.4: off in the release kit
        self.assertEqual(g.R.config.key_test_travel, ".")   # 8.3 keys
        self.assertEqual(g.R.config.key_test_point, ",")


class CatalogTests(unittest.TestCase):
    def test_same_planet_as_8_1_for_every_logged_name(self):
        g = Game(settings=LEVELS)
        old = g.lua.execute(OLD_PLANET_OF_CHECKPOINT)
        T = g.g.RANDO_TRAVEL
        names = logged_checkpoint_names()
        self.assertGreater(len(names), 60)
        extra = ["CHK_TRANSITION_TO_ZURKIES", "CHK_MOLONOTH_X", "CHK_SAVALI_SVALI", "CHK_ARDOLIS_ARD", "chk_zord_lower",
                 "CHK_KEDARO_CORD", "CHK_SOMETHING_ELSE", "CHK_SAV_MOL_TIE", "CHK_MOL_SAV_TIE", "CHK_"]
        diffs = [n for n in names + extra if old(n) != T.planet_of_checkpoint(n)]
        self.assertEqual(diffs, [])

    def test_catalog_completes_in_slices_with_many_checkpoints(self):
        g = level_game("tt-big", {"test_travel": True})
        big = ["CHK_ZURK_%04d_X" % i for i in range(1200)] + ["CHK_MOL_%04d_START" % i for i in range(600)] + \
              ["CHK_SARG_%04d_CINE" % i for i in range(300)]
        g.sim.checkpoint_list = g.lua.table_from(list(py(g.sim.checkpoint_list)) + big)
        started(g)
        T = g.g.RANDO_TRAVEL
        for _ in range(200):
            if T.catalog and T.catalog.done:
                break
            g.step(60)
        self.assertTrue(T.catalog.done)
        self.assertTrue(g.log_has("checkpoint catalog:"))
        self.assertEqual(T.best_in_catalog("blizar_prime"), "CHK_BLIZAR_A_LANDINGPAD")
        ranked = list(py(T.ranked("torren_iv", 5)))
        self.assertEqual(len(ranked), 5)
        full = list(py(T.ranked("torren_iv")))
        self.assertEqual(ranked, full[:5])

    def test_a_slice_stops_at_its_time_budget(self):
        g = Game(settings=LEVELS)
        T = g.g.RANDO_TRAVEL
        T.catalog_reset()
        lst = g.lua.table_from(["CHK_SAV_%d" % i for i in range(500)])
        n, nxt = T.catalog_add(lst, 1, 500, 0)         # no time at all: one entry, then stop
        self.assertEqual((n, nxt), (1, 2))
        n, nxt = T.catalog_add(lst, nxt, 500)          # no budget: the rest
        self.assertEqual((n, nxt), (499, 501))


if __name__ == "__main__":
    unittest.main()
