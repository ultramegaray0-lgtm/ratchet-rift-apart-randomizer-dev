"""Randomizer 8.5: the continuous-stabilization pass on 8.4 (no new features).

Each test pins down one defect the 8.5 audit found by reading the code; none of them was reported
from a game yet, so the scenarios are built in the simulator (tests/sim/rivet_sim.lua), NOT your
game:
  * a mission call that timed out stayed in rando_give.dll's mailbox: the helper could still run
    it later (a late start or state write the script had given up on). A loading screen also
    counted as a timeout.
  * an item or currency request that timed out, or was in flight at a New Game, stayed there too.
  * the companion's late restore dropped this session's currency payments, could put a delivery
    the game had confirmed back to "queued" (a second give), and lost the armor sources, the shop's
    direct gifts, the hub's objective record and the armor baseline gathered before it.
  * a New Game kept the hub's session record of the old run (a destination reloaded there could
    not be reloaded in the new run) and the delivery's weapon-type session state.
  * the history grew without bound in memory.
  * Ms. Zurkon: without rando_give.dll, with a helper that stopped, or with a vendor that was never
    found in memory, the seed's shop-only weapons had no route (the header promised a direct gift).
  * a planet-menu landing on an open planet was not saved until something else changed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_campaign import campaign_game  # noqa: E402
from test_hub import hub_game, to_hub  # noqa: E402

MB_REQ, MB_DONE, MB_STATUS = 0x10, 0x14, 0x0C


def mb(g, off):
    return g.sim.get_u32(g.sim.MB + off)


def filler_location(g, kind="bolts"):
    lid = g.location_with(lambda l, item: isinstance(item, str) and item.startswith(f"filler:{kind}:"))
    assert lid, "seed has no " + kind + " filler"
    return lid


def queue_whys(g):
    q = g.state.currency_queue
    return [str(c.why) for c in q.values()] if q is not None else []


class MissionCallTests(unittest.TestCase):
    def test_a_loading_screen_is_waited_through(self):
        g = campaign_game(caps=True, intro=4).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        g.sim.mailbox.pump = False                 # loading: the game's pump (and the helper) stop
        g.sim.scene = False
        got = []
        D.mission_call("query", "MIS_INTRO", lambda r: got.append(r.code))
        g.step(900)                                # 3x the old 300-frame timeout
        self.assertEqual(got, [])
        self.assertTrue(g.lua.eval("RANDO_REAL.mission_busy"))
        g.sim.mailbox.pump = True
        g.sim.scene = True
        g.step(3)
        self.assertEqual(got, [11])
        self.assertFalse(g.log_has("mission call timed out"))

    def test_a_request_the_helper_did_not_take_is_taken_back(self):
        g = campaign_game(caps=True, intro=4).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        g.sim.mailbox.hold = True                  # the hook pumps but does not serve requests
        got = []
        D.mission_call("start", "MIS_INTRO", lambda r: got.append(r.code))
        g.step(330)
        self.assertEqual(got, [-1])
        self.assertTrue(g.log_has("mission call timed out and was taken back"))
        g.sim.mailbox.hold = False                 # the helper comes back: the start never runs late
        g.step(30)
        starts = [c for c in g.sim.mission_calls.values() if c.kind == 3 and c.name == "MIS_INTRO"]
        self.assertEqual(starts, [])

    def test_a_load_that_never_ends_still_times_out(self):
        g = campaign_game(caps=True, intro=4).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        g.sim.mailbox.pump = False
        g.sim.scene = False
        got = []
        D.mission_call("query", "MIS_INTRO", lambda r: got.append(r.code))
        g.step(int(D.NATIVE_LOAD_WAIT) + 30)
        self.assertEqual(got, [-1])
        self.assertTrue(g.log_has("mission call timed out and was taken back"))


class DeliveryTakeBackTests(unittest.TestCase):
    def test_take_back_keeps_an_answer_that_came_in(self):
        g = Game().ready()
        G = g.real
        req = mb(g, MB_DONE)                       # answered already
        self.assertFalse(G.take_back(req))
        self.assertEqual(mb(g, MB_REQ), mb(g, MB_DONE))

    def test_take_back_withdraws_an_unanswered_request(self):
        g = Game().ready()
        G = g.real
        g.sim.put_u32(g.sim.MB + MB_STATUS, 0)
        done = mb(g, MB_DONE)
        g.sim.put_u32(g.sim.MB + MB_REQ, done + 1)
        self.assertTrue(G.take_back(done + 1))
        self.assertEqual(mb(g, MB_REQ), done)

    def test_a_currency_payment_in_flight_at_a_new_game_is_withdrawn(self):
        g = Game().ready(frames=1500)              # the start items are delivered first
        self.assertEqual(g.lua.eval("#RANDO_REAL.pending(false)"), 0)
        lid = filler_location(g)
        g.sim.mailbox.hold = True                  # the helper takes nothing
        g.R.collect(lid, "test")
        for _ in range(40):
            g.step(5)
            if g.lua.eval("RANDO_REAL.aux_busy") is not None:
                break
        self.assertIsNotNone(g.lua.eval("RANDO_REAL.aux_busy"))
        g.R.reset_for_new_game("test")
        self.assertIsNone(g.lua.eval("RANDO_REAL.aux_busy"))
        self.assertEqual(mb(g, MB_REQ), mb(g, MB_DONE))
        self.assertTrue(g.log_has("aux request withdrawn:\ta new game"))


    def test_an_item_the_helper_did_not_take_is_not_given_late(self):
        g = Game().ready(frames=1500)
        item = next(k for k in sorted(g.data.real_items.keys()) if k.startswith("weapon:")
                    and g.item_status(k) is None and not g.owns(k))
        g.sim.mailbox.hold = True
        g.R.grant(item, True)
        g.step(1200)
        self.assertTrue(g.log_has("direct delivery paused"))
        self.assertEqual(mb(g, MB_REQ), mb(g, MB_DONE))
        self.assertEqual(g.give_count(item), 0)
        self.assertEqual(g.item_status(item), "queued")
        g.sim.mailbox.hold = False
        g.travel("Sargasso")                       # the next planet tries again: one give
        g.step(1200)
        self.assertEqual(g.give_count(item), 1)


class RestoreMergeTests(unittest.TestCase):
    def test_a_currency_payment_made_before_the_restore_is_kept(self):
        g = Game().ready()
        saved = g.companion_export()
        lid = filler_location(g)
        g.sim.mailbox.pump = False                 # keep it queued
        g.R.collect(lid, "test")
        self.assertIn(lid, queue_whys(g))
        self.assertEqual(g.companion_restore(saved), "true")
        self.assertIn(lid, queue_whys(g))
        self.assertTrue(g.state.paid[lid])
        self.assertTrue(g.log_has("currency payment(s) from before the restore"))

    def test_a_payment_the_save_already_has_is_not_doubled(self):
        g = Game().ready()
        lid = filler_location(g)
        g.sim.mailbox.pump = False
        g.R.collect(lid, "test")
        saved = g.companion_export()               # the save has it queued
        self.assertEqual(g.companion_restore(saved), "true")
        self.assertEqual(queue_whys(g).count(lid), 1)

    def test_a_confirmed_delivery_is_not_put_back_to_queued(self):
        g = Game().ready(frames=900)
        start_weapon = next(k for k in g.seed.start["items"].values() if k.startswith("weapon:"))
        self.assertEqual(g.item_status(start_weapon), "confirmed")
        text = g.companion_export()
        ok = g.bridge("local t = (function() " + text + " end)(); t.real['" + start_weapon +
                      "'].status = 'queued'; return tostring(rando_import_state(t))")
        self.assertEqual(ok, "true")
        self.assertEqual(g.item_status(start_weapon), "confirmed")
        gives = g.give_count(start_weapon)
        g.step(900)
        self.assertEqual(g.give_count(start_weapon), gives)

    def test_session_records_survive_the_restore(self):
        g = Game().ready()
        saved = g.companion_export()
        g.lua.execute("SAVED_T = (function() " + saved + " end)(); SAVED_T.armor_baseline = nil")
        s = g.state
        g.lua.execute("RANDO.state.armor_sources = { ['armor:x'] = 'intercepted' };"
                      "RANDO.state.shop_given = { ['weapon:pixelizer'] = 'test' };"
                      "RANDO.state.armor_baseline = { ['armor:y'] = true }")
        self.assertIsNotNone(s.armor_sources)
        self.assertEqual(g.bridge("return tostring(rando_import_state(SAVED_T))"), "true")
        self.assertEqual(g.state.armor_sources["armor:x"], "intercepted")
        self.assertEqual(g.state.shop_given["weapon:pixelizer"], "test")
        self.assertTrue(g.state.armor_baseline["armor:y"])

    def test_restored_baseline_wins(self):
        g = Game().ready()
        g.lua.execute("RANDO.state.armor_baseline = { ['armor:saved'] = true }")
        saved = g.companion_export()
        g.lua.execute("RANDO.state.armor_baseline = { ['armor:live'] = true }")
        self.assertEqual(g.companion_restore(saved), "true")
        self.assertTrue(g.state.armor_baseline["armor:saved"])
        self.assertIsNone(g.state.armor_baseline["armor:live"])


class NewGameTests(unittest.TestCase):
    def test_delivery_session_state_is_cleared(self):
        g = Game().ready()
        g.lua.execute("RANDO_REAL.wseen = { [1001] = true }; RANDO_REAL.baseline = true;"
                      "RANDO_REAL.last_unknown = { t = 1001, frame = 1 }; RANDO_REAL.last_bought = { item = 'x', frame = 1 }")
        g.R.reset_for_new_game("test")
        G = g.real
        self.assertEqual(len(list(G.wseen.keys())), 0)
        self.assertFalse(G.baseline)
        self.assertIsNone(G.last_unknown)
        self.assertIsNone(G.last_bought)

    def test_hub_session_record_is_cleared(self):
        g = to_hub(hub_game("v85-ng"))
        H = g.g.RANDO_HUB
        g.lua.execute("RANDO_HUB.session.reloaded = { x = 5 }; RANDO_HUB.session.started = { MIS_X = 5 };"
                      "RANDO_HUB.session.keeper = 3; RANDO_HUB.return_at = 99999")
        g.R.reset_for_new_game("test")
        self.assertEqual(len(list(H.session.reloaded.keys())), 0)
        self.assertEqual(len(list(H.session.started.keys())), 0)
        self.assertEqual(H.session.keeper, 0)
        self.assertIsNone(H.return_at)


class HistoryTests(unittest.TestCase):
    def test_history_is_capped_in_memory(self):
        g = Game().ready()
        for i in range(1200):
            g.R.history(f"entry {i}")
        h = list(g.state.history.values())
        self.assertLessEqual(len(h), int(g.R.HISTORY_KEEP) + 100)
        self.assertTrue(h[-1].endswith("entry 1199"))
        self.assertFalse(any(x.endswith("entry 0") for x in h))


class ShopRouteTests(unittest.TestCase):
    def extra(self, g):
        return sorted(w for w in (g.seed.shop.slots[k] for k in g.seed.shop.slots.keys()) if not g.data["items"][w].vendor)

    def test_no_helper_at_all_gives_the_extra_weapons(self):
        g = Game(dll=False).ready(frames=600)
        g.step(7800)
        extra = self.extra(g)
        self.assertTrue(extra)
        for w in extra:
            self.assertEqual(g.state.shop_given[w], "rando_give.dll is not loaded")
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_a_helper_that_stopped_gives_the_extra_weapons(self):
        g = Game()
        g.sim.config_objects[Game.VENDOR_ID] = None   # the vendor is never found: nothing applied
        g.ready(frames=60)
        g.real.native_disable("test")
        g.step(7800)
        for w in self.extra(g):
            self.assertIn(g.state.shop_given[w], ("rando_give.dll stopped working", "the vendor could not be found in memory"))

    def test_a_vendor_never_found_in_memory_gives_the_extra_weapons(self):
        g = Game()
        g.sim.config_objects[Game.VENDOR_ID] = None
        g.ready(frames=600)
        g.step(120 * 12)
        self.assertTrue(g.log_has("not found in memory"))
        for w in self.extra(g):
            self.assertEqual(g.state.shop_given[w], "the vendor could not be found in memory")

    def test_a_working_shop_gives_nothing_directly(self):
        g = Game().ready(frames=600)
        g.step(7800)
        self.assertFalse(g.state.shop_given and len(list(g.state.shop_given.keys())) > 0)


class TravelTests(unittest.TestCase):
    def test_a_menu_landing_on_an_open_planet_is_saved(self):
        g = Game(settings={"seed": "levels-1", "preset": "campaign"}).ready()
        T = g.g.RANDO_TRAVEL
        if not T.active():
            self.skipTest("this seed has no travel lock")
        pid = next(p for p in g.state.access.keys() if g.state.access[p])
        v = g.R.version if g.R.version is not None else 0
        T.pending = g.lua.table_from({"dest": "CHK_TEST_START", "planet": pid, "at": 0})
        self.assertFalse(T.on_arrival(pid, None))
        self.assertEqual(g.state.travel.landed[pid], "CHK_TEST_START")
        self.assertGreater(g.R.version, v)
        T.pending = g.lua.table_from({"dest": "CHK_TRANSITION_TO_X", "planet": pid, "at": 0})
        T.on_arrival(pid, None)
        self.assertEqual(g.state.travel.landed[pid], "CHK_TEST_START")


if __name__ == "__main__":
    unittest.main()
