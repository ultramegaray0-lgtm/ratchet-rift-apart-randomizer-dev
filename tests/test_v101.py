"""Dev 10.1 (generator 10.1.0, data 5.1.0), asked for:

* Spybots and Lorbs are reward locations that hold items. The game has 10 Spybots and 12 Lorbs (all on
  Savali; guides: PowerPyx, Push Square). Their pickup event is not bound yet, so they are never in
  logic: they hold ordinary rewards (weapons, gadgets nothing needs, armor) or currency, never
  Coordinates or a gadget a location needs. collectibles = false turns them off.
* Burst Pistol, Shatterbomb and RYNO 8 are items of the pool (acquisition "reward"): always at a
  location, never sold in one of the 15 normal slots, never a random start weapon. The vendor slots
  Shatterbomb and RYNO 8 have in the normal game are closed by the runtime.

The rules are written here from that request, not read from 02_rando_generator.lua. The runtime part
runs against the simulator (tests/sim/rivet_sim.lua), not the real game.
"""
import collections
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_v100  # noqa: E402  (puts tools/ on the path)
from luajson import py  # noqa: E402
from test_v100 import DB, ENG, hub_game, verify_hub_seed  # noqa: E402
from test_generator import gating_gadgets  # noqa: E402

REWARD_ONLY = ("weapon:burst_pistol", "weapon:shatterbomb", "weapon:ryno_8")
COLLECTIBLES = {"spybot": (10, None), "lorb": (12, "savali")}


def gen(seed, user=None, preset="balanced"):
    s, audit = ENG.generate(seed, user or {}, preset)
    assert s is not None, audit
    assert list(audit) == [], (seed, list(audit))
    return py(s)


def collectible_lids(d):
    return sorted(lid for lid in d["locations"] if DB["locations"][lid]["kind"] == "collectible")


class DataTests(unittest.TestCase):
    def test_ten_spybots_and_twelve_lorbs(self):
        for key, (count, planet) in COLLECTIBLES.items():
            lids = sorted(l for l, loc in DB["locations"].items() if loc.get("collectible") == key)
            self.assertEqual(len(lids), count, key)
            self.assertEqual(set(lids), {f"{key}:{n}" for n in range(1, count + 1)})   # R.on_collectible's keys
            for lid in lids:
                loc = DB["locations"][lid]
                self.assertEqual(loc.get("planet"), planet, lid)
                self.assertEqual(loc.get("holds"), "any", lid)
                self.assertFalse(loc["progression"], lid)                  # never in logic
        # CraiggerBears stay out (their count is unknown)
        bears = [loc for loc in DB["locations"].values() if loc.get("collectible") == "craiggerbear"]
        self.assertTrue(bears)
        self.assertFalse(any(b.get("holds") for b in bears))

    def test_three_weapons_are_rewards(self):
        for k in REWARD_ONLY:
            self.assertEqual(DB["items"][k]["acquisition"], "reward", k)
            self.assertFalse(DB["items"][k].get("vendor"), k)            # not one of the 15 normal slots
        self.assertEqual(DB["version"], "5.1.0")


class CollectibleLocationTests(unittest.TestCase):
    def test_spybots_and_lorbs_hold_items_and_nothing_the_seed_needs(self):
        items = collections.Counter()
        cats = collections.Counter()
        gating = gating_gadgets()
        for dist in ("spread", "goldbolts_first"):
            for i in range(60):
                d = gen(f"v101-col-{dist}-{i}", {"distribution": dist})
                lids = collectible_lids(d)
                self.assertEqual(len(lids), 22, (dist, i))
                spheres = {lid for sp in d["spheres"] for lid in sp}
                for lid in lids:
                    self.assertNotIn(lid, spheres, (dist, i, lid))       # out of logic
                    it = d["locations"][lid].get("item")
                    self.assertIsNotNone(it, (dist, i, lid))             # an item or currency, never empty
                    if it in DB["items"]:
                        cat = DB["items"][it]["category"]
                        self.assertNotEqual(cat, "coordinates", (dist, i, lid))
                        self.assertNotIn(it, gating, (dist, i, lid))
                        items[(dist, DB["locations"][lid]["collectible"])] += 1
                        cats[cat] += 1
                if dist == "spread":
                    self.assertEqual(verify_hub_seed(d), [], i)
        # real items reach both kinds of collectible with both fills
        for dist in ("spread", "goldbolts_first"):
            for key in COLLECTIBLES:
                self.assertGreater(items[(dist, key)], 20, (dist, key, items))
        self.assertGreater(cats["weapon"], 30, cats)
        self.assertGreater(cats["armor"], 30, cats)

    def test_collectibles_false_turns_them_off(self):
        d = gen("v101-col-off", {"collectibles": False})
        self.assertEqual(collectible_lids(d), [])
        self.assertEqual(verify_hub_seed(d), [])
        d = gen("v101-col-on")
        self.assertTrue(d["settings"]["collectibles"])                    # on by default
        self.assertEqual(len(collectible_lids(d)), 22)

    def test_the_spoiler_says_they_pay_once_bound(self):
        text = ENG.G.spoiler(ENG.generate("v101-spoil", {}, "balanced")[0])
        self.assertIn("Spybot found #10", text)
        self.assertIn("Lorb found #12", text)
        self.assertIn("[out of logic: pays once its pickup event is bound]", text)


class RewardWeaponTests(unittest.TestCase):
    def test_always_at_a_location_never_sold_never_a_random_start(self):
        for dist in ("spread", "goldbolts_first"):
            for i in range(80):
                d = gen(f"v101-w-{dist}-{i}", {"distribution": dist, "shop_weapons": 15 if i % 2 else 8,
                                               "start_weapons": 4 if i % 3 == 0 else 2})
                sold = set((d["shop"]["slots"] or {}).values())
                at = {l["item"]: lid for lid, l in d["locations"].items() if l.get("item")}
                for k in REWARD_ONLY:
                    self.assertNotIn(k, sold, (dist, i, k))
                    self.assertNotIn(k, d["start"]["items"], (dist, i, k))
                    self.assertIn(k, at, (dist, i, k))
                    self.assertEqual(d["registry"][k], "location", (dist, i, k))
                # the Burst Pistol (the game hands one out anyway) never takes a Gold Bolt here
                self.assertNotEqual(DB["locations"][at["weapon:burst_pistol"]]["kind"], "goldbolt", (dist, i))
                # nor counts as one of the early weapons: the start's reach has early_weapons (2) others
                early = [d["locations"][lid].get("item") for lid in d["spheres"][0]]
                real = [w for w in early if w in DB["items"] and DB["items"][w]["category"] == "weapon"
                        and w != "weapon:burst_pistol"]
                self.assertGreaterEqual(len(real), 2, (dist, i, early))

    def test_start_items_and_exclude_still_decide(self):
        d = gen("v101-w-chosen", {"start_items": "weapon:ryno_8"})
        self.assertIn("weapon:ryno_8", d["start"]["items"])
        self.assertEqual(d["registry"]["weapon:ryno_8"], "start (chosen)")
        d = gen("v101-w-ex", {"exclude": "weapon:ryno_8,weapon:shatterbomb"})
        for k in ("weapon:ryno_8", "weapon:shatterbomb"):
            self.assertEqual(d["registry"][k], "excluded (setting)")
            self.assertNotIn(k, {l.get("item") for l in d["locations"].values()})

    def test_spoiler_shop_line(self):
        text = ENG.G.spoiler(ENG.generate("v101-shopline", {}, "balanced")[0])
        self.assertIn("Shatterbomb and RYNO 8 are rewards (listed below): their own vendor slots are closed", text)
        self.assertNotIn("stay in their own slots", text)


class RuntimeTests(unittest.TestCase):
    """the simulated vendor: Shatterbomb's and RYNO 8's own slots are closed; a Spybot/Lorb pays"""
    # test_v100's vendor helpers (its slots: the 15 normal ones, then Burst Pistol, Shatterbomb, RYNO 8)
    shop_game = test_v100.ShopTests.shop_game
    slots_after = test_v100.ShopTests.slots_after

    def test_shatterbomb_and_ryno_slots_are_closed(self):
        g, ids = self.shop_game(seed="v101-shop")
        after = self.slots_after(g, ids)
        data = g.g.RANDO_DATA
        burst = data["items"]["weapon:burst_pistol"]["id"].upper()
        for k in ("weapon:shatterbomb", "weapon:ryno_8"):
            i = ids.index(data["items"][k]["id"])
            self.assertEqual(after[i].upper(), burst, k)                   # shows the Burst Pistol: closed
            self.assertTrue(g.log_has(k.split(":")[1] + "->CLOSED"), k)
        # nothing left in the vendor sells them
        self.assertNotIn(data["items"]["weapon:ryno_8"]["id"].upper(), [x.upper() for x in after])
        self.assertNotIn(data["items"]["weapon:shatterbomb"]["id"].upper(), [x.upper() for x in after])

    def test_a_spybot_and_a_lorb_complete_their_locations(self):
        g = hub_game("v101-rt")
        g.ready()
        for kind in ("spybot", "spybot", "lorb"):
            g.R.on_collectible(kind)
        g.step(30)
        self.assertTrue(g.state.collected["spybot:1"])
        self.assertTrue(g.state.collected["spybot:2"])
        self.assertTrue(g.state.collected["lorb:1"])
        self.assertFalse(g.state.collected["spybot:3"])


if __name__ == "__main__":
    unittest.main()
