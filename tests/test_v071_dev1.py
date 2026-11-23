"""v0.71-DEV1 (kit 10.0.36): the shop by config pointer, and Spybots / Lorbs as reward locations.

SHOP. Rounds 17-45 found an array at +0x48 of the vendor config but never a weapon's 64-bit id in it. rivet.config()
cannot show it (rivet_hook's values_of() skips arrays of structs). 12_rando_shop.lua now also matches the slots'
Item field against the ADDRESSES of the weapons' loaded *_item.config objects (rando_give.dll kind 7). The simulator's
S.vendor_item_pointers lays the vendor out that way: that layout is an ASSUMPTION under test, not seen in the game.

COLLECTIBLES. The Spybot / Lorb event classes exist in the game (round54: "events subscribed 23/23") but no pickup has
been logged yet. These test the binding, the dedupe by id, the watched-only classes and the developer keys (dev(keys).lua)
that pay a pickup the game did not report.

All of it runs the real scripts against tests/sim (a simulation, not the game).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game  # noqa: E402
from test_v100 import py  # noqa: E402

SHOP = {"seed": "v071-shop", "preset": "balanced", "shop": "shuffle"}
COLLECT = {"seed": "v071-collect", "preset": "balanced", "collectibles": True}


def shop_game(pointers_items=True, slot_objects=False, settings=SHOP, before=None):
    def setup(gm):
        gm.sim.vendor_item_pointers = pointers_items
        gm.sim.vendor_pointers = slot_objects
        if before:
            before(gm)
    return Game(settings=settings, before_scripts=setup).ready(frames=1500)


def check_slots(tc, g):
    by_id = {g.data["items"][k].id: k for k in g.data["items"].keys() if k.startswith("weapon:")}
    slots = {k: g.seed.shop.slots[k] for k in g.seed.shop.slots.keys()}
    closed = set(py(g.seed.shop.closed or {}).values()) if g.seed.shop.closed else set()
    authored = [by_id.get(v, v) for v in g.sim.vendor_mem[Game.VENDOR_ID].authored.values()]
    for i, a in enumerate(authored, start=1):
        now = g.sim.vendor_slot_item(Game.VENDOR_ID, i)
        now = by_id.get(now, now)
        if a in slots:
            tc.assertEqual(now, slots[a], (i, a))
        elif a in closed:
            tc.assertEqual(now, "weapon:burst_pistol", (i, a))


class ShopPointerTests(unittest.TestCase):
    def test_inline_elements_with_config_pointers_are_changed(self):
        g = shop_game(pointers_items=True)
        self.assertTrue(g.log_has("Item at +0x10 as a config pointer"), [l for l in g.logs() if "SHOP" in l][-8:])
        self.assertTrue(g.log_has("weapon configs in memory:"))
        check_slots(self, g)
        self.assertTrue(g.log_has("Price at +0x18"))
        # v0.71-DEV6: the field dump (EVIDENCE) is logged after every vendor write, so its presence says nothing here
        self.assertFalse([l for l in g.logs() if "RANDO-ERROR" in l])

    def test_slot_objects_with_config_pointers_are_changed(self):
        g = shop_game(pointers_items=True, slot_objects=True)
        self.assertTrue(g.log_has("slot objects by pointer, Item at +0x10 as a config pointer"))
        check_slots(self, g)

    def test_ids_still_work_as_before(self):
        g = shop_game(pointers_items=False)
        self.assertTrue(g.log_has("Item at +0x10 as an item id"))
        check_slots(self, g)

    def test_a_reload_is_applied_again_with_new_lookups(self):
        g = shop_game(pointers_items=True)
        n = g.count_logs("as a config pointer")
        g.travel("Savali", 60)
        g.step(1500)
        self.assertGreater(g.count_logs("as a config pointer"), n)
        check_slots(self, g)

    def test_nothing_found_logs_the_evidence_once(self):
        # pointers in the slots, but the helper cannot find any weapon config: neither form matches
        def drop_lookups(gm):
            gm.lua.execute("""
              local orig = SIM.item_config_addr
              SIM.item_config_addr = function(item) local a = orig(item); SIM.config_objects[item] = nil; return a end
            """)
        g = shop_game(pointers_items=True, before=drop_lookups)
        g.step(3000)
        self.assertEqual(g.count_logs("RANDO-SHOP\tEVIDENCE vendor config at"), 1)
        self.assertTrue(g.log_has("RANDO-SHOP\tEVIDENCE weapon configs looked up:\tnone found"))
        self.assertTrue(g.log_has("EVIDENCE array at +0x88 (21 entries)"))
        self.assertFalse(g.log_has("as a config pointer"))

    def test_a_weapon_without_a_loaded_config_keeps_its_slot_and_is_given(self):
        # the seed puts Pixelizer / Bouncer in the shop; their configs are not loaded here
        def hide(gm):
            gm.lua.execute("""
              local orig = SIM.item_config_addr
              SIM.item_config_addr = function(item)
                local a = orig(item)
                if item == RANDO_DATA.items["weapon:pixelizer"].id or item == RANDO_DATA.items["weapon:bouncer"].id then
                  SIM.config_objects[item] = nil
                end
                return a
              end""")
        g = shop_game(pointers_items=True, before=hide)
        sold = set(g.seed.shop.slots[k] for k in g.seed.shop.slots.keys())
        hidden = sold & {"weapon:pixelizer", "weapon:bouncer"}
        if not hidden:
            self.skipTest("this seed's shop sells neither Pixelizer nor Bouncer")
        self.assertTrue(g.log_has("has no loaded config to point to"))
        for w in hidden:
            self.assertTrue(g.owns(w), w)

    def test_a_load_drops_a_running_search(self):
        g = Game(settings=SHOP, before_scripts=lambda gm: setattr(gm.sim, "vendor_item_pointers", True))
        g.wait_seed()
        g.lua.execute("RANDO_SHOP.jobs = { { id = 'X', obj = '0', v = {}, co = coroutine.create(function() coroutine.yield() end) } }")
        g.R.update_loading(0.4)
        self.assertEqual(len(list(g.g.RANDO_SHOP.jobs.keys())), 0)
        self.assertTrue(g.log_has("a load began: the vendor search is dropped"))


class CollectibleTests(unittest.TestCase):
    def game(self, **kw):
        g = Game(settings=COLLECT, dev_tools=False, **kw)
        g.ready()
        return g

    def test_the_seed_holds_items_on_spybots_and_lorbs(self):
        g = self.game()
        self.assertEqual(g.R.collectible_total("spybot"), 10)
        self.assertEqual(g.R.collectible_total("lorb"), 12)

    def test_a_spybot_event_pays_once_per_id(self):
        g = self.game()
        g.fire("RYNOPlayPickedUpEvent", RynoId=11)
        g.step(5)
        self.assertTrue(g.state.collected["spybot:1"])
        g.fire("RYNOScriptPickupEvent", RynoId=11)        # the same Spybot, the other event
        g.step(5)
        self.assertFalse(g.state.collected["spybot:2"])
        g.fire("RYNOPlayPickedUpEvent", RynoId=12)
        g.step(5)
        self.assertTrue(g.state.collected["spybot:2"])
        self.assertIn("Spybots 2/10", g.R.collectible_status("spybot"))
        self.assertIn("event: 2", g.R.collectible_status("spybot"))

    def test_a_scripted_lorb_pickup_pays(self):
        g = self.game()
        g.fire("RuinScriptPickupEvent", RuinId=3)
        g.step(5)
        self.assertTrue(g.state.collected["lorb:1"])

    def test_claims_by_hand_stop_at_the_last_location(self):
        g = self.game()
        for _ in range(10):
            ok = g.R.claim_collectible("spybot")
            self.assertTrue(ok)
        ok, why = g.R.claim_collectible("spybot")
        self.assertFalse(ok)
        self.assertIn("all 10 already paid", why)
        self.assertTrue(all(g.state.collected[f"spybot:{i}"] for i in range(1, 11)))
        self.assertTrue(g.log_has("RANDO-COLLECTIBLE\tspybot\t-\t(by hand)"))

    def test_without_collectibles_nothing_is_claimed(self):
        g = Game(settings=dict(COLLECT, collectibles=False))
        g.ready()
        ok, why = g.R.claim_collectible("lorb")
        self.assertFalse(ok)
        self.assertIn("collectibles = false", why)

    def test_watched_classes_are_listed_and_never_pay(self):
        def missing(gm):
            gm.lua.execute('SIM.unknown_classes["CraiggerbearPickedUpEvent"] = true')
        g = Game(settings=COLLECT, before_scripts=missing)
        g.ready()
        self.assertTrue(g.log_has("event classes watched (logged, never paid)"))
        line = next(l for l in g.logs() if "event classes watched" in l)
        self.assertIn("not in this game:\tCraiggerbearPickedUpEvent", line)
        g.fire("CollectiblePickedUpEvent", Kind=1)
        g.step(5)
        self.assertTrue(g.log_has("RANDO-COLLECTIBLE watched\tCollectiblePickedUpEvent\tKind=1"))
        self.assertFalse(g.state.collected["spybot:1"])

    def test_developer_keys_show_and_pay_after_a_second_press(self):
        g = Game(settings=COLLECT, dev_tools=False)   # dev(keys).lua is always installed in the harness
        g.ready()
        g.press("F2")
        self.assertTrue(g.note_has("Spybots 0/10 paid"))
        g.press("F2", ctrl=True)
        g.step(2)
        self.assertFalse(g.state.collected["spybot:1"])
        self.assertTrue(g.note_has("press Ctrl+F2 again"))
        g.press("F2", ctrl=True)
        g.step(5)
        self.assertTrue(g.state.collected["spybot:1"])
        g.press("F3", ctrl=True)
        g.press("F3", ctrl=True)
        g.step(5)
        self.assertTrue(g.state.collected["lorb:1"])


if __name__ == "__main__":
    unittest.main()
