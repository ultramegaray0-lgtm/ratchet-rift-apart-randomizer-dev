"""Offline tests of the real generator code (02_rando_generator.lua, run through lupa) plus an
INDEPENDENT verifier written here in Python from the rules in docs/DESIGN.md. Every batch seed
must pass both the generator's own audit and this verifier."""
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rando  # noqa: E402
from harness import pre10_engine  # noqa: E402  (10.0: the 4.0-9.0 rules, see harness.py)
from luajson import py  # noqa: E402

with open(os.path.join(ROOT, "data", "game_db.json"), encoding="utf-8") as f:
    DB = json.load(f)
with open(os.path.join(ROOT, "data", "sources", "dag_item_ids.json"), encoding="utf-8") as f:
    DAG = json.load(f)

with open(os.path.join(ROOT, "data", "weapon_registry.json"), encoding="utf-8") as f:
    REG = json.load(f)["weapons"]

# 4.0-7.0 rules, written here from docs/DESIGN.md, docs/WEAPONS.md and docs/CONFIGURATION.md (not taken
# from the Lua code)
ALWAYS_START = {"hoverboots", "map_o_matic"}
VENDOR = sorted(k for k, w in REG.items() if w["vendor"])          # the 15 normal vendor slots
GAME_GIVEN = {"weapon:burst_pistol"}


def weapon_pool(s):
    """6.0: weapons the seed splits over the shop's slots, the start and reward locations"""
    return {k for k, w in REG.items()
            if w["acquisition"] == "pool" or (w["acquisition"] == "arsenal_restored" and s["include_arsenal_restored"])}


def reward_weapons(s):
    """(weapons left for reward locations, weapons at the start) after the shop's slots"""
    if not s["weapons"]:
        return 0, 0
    ex = {k for k in s["exclude"].replace(" ", "").split(",") if k}
    shuffle = s["shop"] == "shuffle"
    fixed = {k for k in VENDOR if not shuffle or k in ex}
    avail = len([k for k in weapon_pool(s) if k not in ex and k not in fixed])
    free = len(VENDOR) - len(fixed)
    start = max(0, min(s["start_weapons"], avail - free))
    return avail - free - start, start
GAME_KIT = set(DB["start_kit"])


def gating_gadgets():
    out = set()
    for loc in DB["locations"].values():
        for r in loc.get("requires", []):
            if DB["items"].get(r, {}).get("category") == "gadget" and r not in ALWAYS_START:
                out.add(r)
    return out


def weapons_needed(s, i):
    if s["weapon_logic"] == "none" or not s["weapons"]:
        return 0
    if s["weapon_logic"] == "light":
        return max(0, (i - 2) // 2)
    return max(0, i - 2)


def grantable(key):
    it = DB["items"].get(key)
    if not it:
        return False
    if it["category"] == "coordinates":
        return True
    if it["category"] == "armor":                     # 5.0: through the game's armor code
        return it.get("grant") == "vanity" and it.get("randomizable") is True
    return it["category"] in ("weapon", "gadget") and it.get("grant") == "inventory" and not it.get("experimental")


def filler_of(key):
    """'filler:bolts:5000' -> ('bolts', 5000), else None"""
    parts = str(key).split(":")
    if len(parts) == 3 and parts[0] == "filler" and parts[2].isdigit():
        return parts[1], int(parts[2])
    return None


def pool_size(s):
    """how many grantable items these settings put in the pool (before the start takes some)"""
    ex = {k for k in s["exclude"].replace(" ", "").split(",") if k}
    n = 0
    for key, it in DB["items"].items():
        if key in ex or key in ALWAYS_START or key in GAME_GIVEN or key in GAME_KIT:
            continue
        if it["category"] == "weapon":
            continue                                   # counted below, after the shop and the start
        elif it["category"] == "armor" and s["armor"] and it["randomizable"]:
            n += 1
        elif it["category"] == "gadget" and s["gadgets"]:
            n += 1
        elif it["category"] == "coordinates" and s["planet_locks"]:
            n += 1
    return n + reward_weapons(s)[0]


def honest_refusal(eng, preset, user, audit, extra_start=0):
    """True when a refused seed really cannot fill 25 Gold Bolts, counted independently.
    extra_start: items a campaign may also start with (its first visits' Coordinates)"""
    if "too few items for one per Gold Bolt" not in str(audit):
        return False
    d = eng.defaults()
    eff = dict(d)
    eff.update(py(eng.lua.eval("RANDO_GEN.PRESETS")[preset]) or {})
    ranges = py(eng.lua.eval("RANDO_GEN.RANGES"))
    for k, v in user.items():
        if k not in d or type(v) is not type(d[k]):
            continue
        if k in ranges and not (ranges[k][0] <= v <= ranges[k][1]):
            continue                                # out of range: the generator keeps the default
        eff[k] = v
    for alias, key in (("restored_weapons", "include_arsenal_restored"), ("mission_order", "campaign_mode")):
        if alias in user and key not in user:
            eff[key] = user[alias]
    eff["planet_locks"] = True                      # the generator's own repairs, already tried
    eff["armor"] = True
    if eff.get("travel_lock"):
        # 7.0 levels: the three planets the story itself takes you to are open from the start
        start_coords = 3 + (0 if eff["start_coordinates"] == "start_only" else 1)
    else:
        start_coords = 1 if eff["start_coordinates"] == "start_only" else 2
    chosen = len([k for k in str(user.get("start_items", "")).replace(" ", "").split(",") if k in DB["items"]])
    return pool_size(eff) - eff["start_gadgets"] - start_coords - extra_start - chosen < 25


# 3.0: gadgets a campaign visit needs; a campaign seed hands them out at the start even when
# they are excluded, so the order stays finishable
CAMPAIGN_GADGETS = {"hoverboots"}
# 7.0: the planets the story itself takes you to (round 16 log: the parade's rifts end on Nefarious
# City; MIS_NEFCITY_01 completing moves you to Sargasso without the planet menu)
STORY_ARRIVALS = ("corson_v", "nefarious_city", "sargasso")


def verify(seed):
    """Independent check of one seed (a Python dict). Returns a list of problems."""
    probs = []
    s = seed["settings"]
    ex = {k for k in s["exclude"].replace(" ", "").split(",") if k}
    planets = {p["id"]: p for p in DB["planets"]}
    locs = seed["locations"]
    start = seed["start"]["items"]
    # 6.0 the shop: each of the 15 vendor slots sells one weapon of the pool, no weapon twice
    shop = seed.get("shop") or {}
    want_mode = s["shop"] if s["weapons"] else "vanilla"
    if shop.get("mode") != want_mode:
        probs.append(f"shop mode {shop.get('mode')} for setting {s['shop']}")
    slots = shop.get("slots") or {}
    if sorted(slots) != VENDOR:
        probs.append(f"the shop does not name the 15 vendor slots: {sorted(slots)}")
    sold = list(slots.values())
    if len(set(sold)) != len(sold):
        probs.append("a weapon is sold in two slots")
    pool = weapon_pool(s)
    for k, w in slots.items():
        if want_mode != "shuffle" or k in ex:
            if w != k:
                probs.append(f"the slot of {k} must sell {k} (shop {want_mode}, exclude), sells {w}")
        elif w not in pool:
            probs.append(f"the slot of {k} sells {w}, which is not in the weapon pool")
        if REG.get(w, {}).get("acquisition") in ("disabled", "shop_fixed", "start_fixed"):
            probs.append(f"{w} ({REG[w]['acquisition']}) is sold in a shuffled slot")
    if want_mode == "shuffle" and sum(1 for k, w in slots.items() if k == w and k not in ex) > 1:
        probs.append("more than one slot sells its own weapon")
    # 7.0 currency: only the currencies switched on, each amount inside its range, the total
    # inside the budget (unless the minimum alone is above it)
    kinds = {k for k in ("bolts", "raritanium") if s[k]}
    cur_total = {"bolts": 0, "raritanium": 0}
    cur_count = {"bolts": 0, "raritanium": 0}
    for g in ALWAYS_START:
        if g not in start:
            probs.append(f"{g} is not in the start")
    # routes: one per item, no currency
    where = {}
    for k in start:
        where.setdefault(k, []).append("start")
    for lid, l in locs.items():
        it = l.get("item")
        loc = DB["locations"][lid]
        f = filler_of(it) if it else None
        if f:
            if loc["kind"] == "goldbolt":
                probs.append(f"{lid} (a Gold Bolt) holds currency")
            if f[0] not in kinds:
                probs.append(f"{lid} holds {it} with {f[0]} = false")
            elif not s[f[0] + "_min"] <= f[1] <= s[f[0] + "_max"]:
                probs.append(f"{lid} gives {f[1]} {f[0]}, outside {s[f[0] + '_min']}-{s[f[0] + '_max']}")
            else:
                cur_total[f[0]] += f[1]
                cur_count[f[0]] += 1
            continue
        if not it:
            if loc["kind"] != "goldbolt" and kinds:
                probs.append(f"{lid} holds nothing although currency rewards are on")
            continue
        if it not in DB["items"]:
            probs.append(f"{lid} holds {it}, not an item")
        elif DB["items"][it]["category"] == "armor" and not s["armor"]:
            probs.append(f"{lid} holds armor with armor = false")
        if loc.get("holds") == "filler":
            probs.append(f"{lid} only takes filler but holds {it}")
        where.setdefault(it, []).append(lid)
    if not s["armor"] and any(DB["locations"][lid]["kind"] == "armor_source" for lid in locs):
        probs.append("armor sources with armor = false")
    for k in ("bolts", "raritanium"):
        budget = s[k + "_budget"]
        if budget and cur_total[k] > max(budget, cur_count[k] * s[k + "_min"]):
            probs.append(f"{k} rewards total {cur_total[k]} above the budget {budget}")
        if (seed.get("filler") or {}).get("totals", {}).get(k, 0) != cur_total[k]:
            probs.append(f"{k} total in the seed differs from the locations")
    if seed["start"].get("bolts") != s["start_bolts"] or seed["start"].get("raritanium") != s["start_raritanium"]:
        probs.append("start currency differs from the settings")
    # 7.0 prices: each of the 15 slots has a whole, non-negative price, from the rule chosen
    prices = shop.get("prices")
    if s["shop_prices"] == "vanilla":
        if prices:
            probs.append("prices set with shop_prices = vanilla")
    else:
        for k in VENDOR:
            p = (prices or {}).get(k)
            if not isinstance(p, int) or p < 0 or p % 50:
                probs.append(f"slot {k} price {p}")
                continue
            base = REG[k]["price"]
            if s["shop_prices"] == "weapon":
                want = REG.get(slots.get(k), {}).get("price") or base
                if p != want:
                    probs.append(f"slot {k} costs {p}, its weapon {slots.get(k)} costs {want}")
            elif s["shop_prices"] == "percent":
                if abs(p - base * s["shop_price_percent"] / 100) > 25:
                    probs.append(f"slot {k} costs {p}, not {s['shop_price_percent']}% of {base}")
            else:
                lo, hi = base * s["shop_price_percent"] / 100, base * s["shop_price_max_percent"] / 100
                if not lo - 25 <= p <= hi + 25:
                    probs.append(f"slot {k} costs {p}, outside {lo}-{hi}")
    # 7.0 levels: the story's own arrivals (Corson V, Nefarious City, Sargasso) are open from the start
    if s.get("travel_lock"):
        if not s["planet_locks"]:
            probs.append("travel_lock without planet_locks")
        for pid in STORY_ARRIVALS:
            if "access:" + pid not in start:
                probs.append(f"levels: {pid} is not open from the start")
    # start_items: each named item that the seed randomizes starts, unless it is a weapon the shop needs
    for k in [x for x in s.get("start_items", "").replace(" ", "").split(",") if x]:
        if k in start or k not in DB["items"]:
            continue
        cat = DB["items"][k]["category"]
        if cat in ("gadget", "armor") and k in where and k not in ex:
            probs.append(f"start_items names {k} but it is at {where[k]}")
    for k, w in where.items():
        if len(w) > 1:
            probs.append(f"{k} has {len(w)} routes: {w}")
        if k in GAME_GIVEN:
            probs.append(f"{k} is handed out by the game itself but placed at {w}")
        campaign_kit = ((seed.get("campaign") or {}).get("mode", "vanilla") != "vanilla" or s.get("travel_lock")) and k in CAMPAIGN_GADGETS
        if k in ex and not k.startswith("access:") and k not in ALWAYS_START and not (campaign_kit and w == ["start"]):
            probs.append(f"excluded {k} placed at {w}")
    # one item per Gold Bolt
    bolts = [lid for lid, l in DB["locations"].items() if l["kind"] == "goldbolt"]
    if len(bolts) != 25:
        probs.append(f"{len(bolts)} Gold Bolts in the data")
    for lid in bolts:
        it = (locs.get(lid) or {}).get("item")
        if lid not in locs:
            probs.append(f"{lid} is not a location")
        elif not it:
            probs.append(f"{lid} holds nothing")
        elif not grantable(it):
            probs.append(f"{lid} holds {it}, which cannot be handed over")
    # out-of-logic locations may not hold progression items
    gating = gating_gadgets()

    def in_logic(lid):
        loc = DB["locations"][lid]
        if not loc["progression"]:
            return False
        for r in loc.get("requires", []):
            if r in ALWAYS_START:
                continue
            if r.startswith("ability:") or not s["gadgets"] or r in ex:
                return False
        return True
    for lid, l in locs.items():
        it = l.get("item")
        if not it or filler_of(it):
            continue
        cat = DB["items"].get(it, {}).get("category")
        prog = cat == "coordinates" or (cat == "gadget" and it in gating)
        if prog and not in_logic(lid):
            probs.append(f"progression item {it} on out-of-logic location {lid}")
        loc = DB["locations"][lid]
        if it in loc.get("requires", []):
            probs.append(f"{it} behind itself at {lid}")
        if s["planet_locks"] and loc.get("planet") and (loc["kind"] != "goldbolt" or s.get("travel_lock")) and it == "access:" + loc["planet"]:
            probs.append(f"{it} on its own planet")
    # playthrough
    owned = {}
    for k in start:
        owned[k] = owned.get(k, 0) + 1
    got = set()

    def ok(lid):
        loc = DB["locations"][lid]
        if not in_logic(lid):
            return False
        if s["planet_locks"] and loc.get("planet") and not owned.get("access:" + loc["planet"]):
            # with levels (travel_lock) a locked planet's Gold Bolts are out of reach too
            if loc["kind"] != "goldbolt" or s.get("travel_lock"):
                return False
        if any(not owned.get(r) for r in loc.get("requires", []) if r not in ALWAYS_START):
            return False
        if loc.get("planet"):
            wc = sum(1 for k, c in owned.items() if c and k.startswith("weapon:"))
            if wc < weapons_needed(s, planets[loc["planet"]]["story_index"]):
                return False
        return True
    while True:
        new = [lid for lid in sorted(locs) if lid not in got and ok(lid)]
        for lid in new:
            got.add(lid)
            it = locs[lid].get("item")
            if it and not filler_of(it):
                owned[it] = owned.get(it, 0) + 1
        if not new:
            break
    for lid in locs:
        if in_logic(lid) and lid not in got:
            if s["accessibility"] == "full" or DB["locations"][lid]["kind"] == "planet":
                probs.append("unreachable " + lid)
    for k, w in where.items():
        cat = DB["items"].get(k, {}).get("category")
        if (cat == "coordinates" or k in gating) and w != ["start"] and not owned.get(k):
            probs.append("progression item never obtained: " + k)
    # 6.0 every weapon of the pool has exactly one route; nothing outside the pool is placed
    for k, w in REG.items():
        routes = len(where.get(k, [])) + (1 if k in sold else 0)
        if k in pool and s["weapons"] and k not in ex and routes != 1:
            probs.append(f"{k} has {routes} routes")
        if k not in pool and where.get(k):
            probs.append(f"{k} ({w['acquisition']}) is placed at {where[k]}")
    n_rw, n_start = reward_weapons(s)
    got_start = sum(1 for k in start if k in pool)
    chosen = sum(1 for k in start if k in pool and seed["registry"].get(k) == "start (chosen)")
    if got_start - chosen != n_start and not (chosen and got_start - chosen < n_start):
        probs.append(f"{got_start} pool weapons start, expected {n_start}")
    return probs


class DatabaseTests(unittest.TestCase):
    def test_item_ids_come_from_the_dag(self):
        for key, it in DB["items"].items():
            if "id" not in it:
                continue
            if it["config"] == "configs/equipment/wpn_mr_zurkon_item.config":
                self.assertNotIn(it["id"], DAG)            # ARSENAL_RESTORED adds it
                continue
            self.assertEqual(DAG.get(it["id"]), it["config"], key)

    def test_pool_sizes(self):
        cats = {}
        for it in DB["items"].values():
            cats[it["category"]] = cats.get(it["category"], 0) + 1
        self.assertEqual(cats["weapon"], 31 + 9)          # 31 usual (incl. ARSENAL_RESTORED) + 9 hidden
        # 5.0: the 24 armor pieces of the 8 sets you find, in 9 folders (2 of punk / reaver /
        # war machine are Robot Disguise and Wasteland Gear): 27 randomizable pieces
        self.assertEqual(sum(1 for it in DB["items"].values() if it["category"] == "armor" and it["randomizable"]), 21)   # 8.5.2: not Punk, Reaver
        self.assertEqual(sum(1 for it in DB["items"].values() if it["category"] == "armor" and it["owned_from_start"]), 36)   # 8.5.2: + Punk, Reaver
        self.assertEqual(cats["coordinates"], 10)
        self.assertEqual(cats["currency"], 2)
        self.assertEqual(len(VENDOR), 15)
        kinds = {}
        for loc in DB["locations"].values():
            kinds[loc["kind"]] = kinds.get(loc["kind"], 0) + 1
        self.assertEqual(kinds["goldbolt"], 25)
        self.assertEqual(kinds["planet"], 10)
        self.assertEqual(kinds["armor_source"], 27)
        self.assertEqual(sum(1 for l in DB["locations"].values() if l.get("holds") == "filler"), 9)

    def test_weapon_names_come_from_the_games_types(self):
        # round 16: Blackhole Storm sent as wpn_nailgun never arrived. The game's type data
        # (Weapon*Prius) says warprifle spins up and heats (the minigun, Blackhole Storm) and
        # fossilizer slows time when aiming (the sniper, Headhunter); nailgun is an empty type.
        items = DB["items"]
        self.assertEqual(items["weapon:blackhole_storm"]["config"], "configs/equipment/wpn_warprifle_item.config")
        self.assertEqual(items["weapon:headhunter"]["config"], "configs/equipment/wpn_fossilizer_item.config")
        self.assertTrue(items["weapon:nailgun"]["experimental"])
        self.assertTrue(items["weapon:revolver"]["experimental"])
        self.assertNotIn("weapon:executor", items)
        self.assertEqual(items["currency:bolts"]["config"], "configs/pickup/pup_bolt_item.config")

    def test_gadget_type_ids_were_reported_by_the_game(self):
        observed = {565053540, 3505658055, 3984731671, 1705612936, 1700739470, 2861803654, 2983765807, 2681061161, 3741994936}
        for key, it in DB["items"].items():
            if it["category"] == "gadget" and key not in ("glitch", "map_o_matic"):
                self.assertIn(it["type_id"], observed, key)

    def test_verified_flags_match_the_logs(self):
        verified = {k for k, it in DB["items"].items() if it.get("verified_in_game")}
        # wpn_warprifle arrived in round 13 (then named "Headhunter"): it is the Blackhole Storm
        self.assertEqual(verified, {"weapon:predator_launcher", "weapon:blackhole_storm", "weapon:warmonger",
                                    "weapon:schrodinger", "weapon:bombardier", "weapon:glove_of_doom",
                                    "weapon:negatron_collider", "box_breaker", "hoverboots"})


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = pre10_engine()

    def gen(self, seed, user=None, preset="balanced"):
        s, audit = self.eng.generate(seed, user or {}, preset)
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [])
        return py(s)

    def test_reproducible_across_lua_states(self):
        for preset in ("standard", "chaos", "armor", "classic"):
            ea, eb = pre10_engine(), pre10_engine()      # separate Lua states: different string hashing
            a = ea.generate("same-seed", {}, preset)[0]
            b = eb.generate("same-seed", {}, preset)[0]
            self.assertEqual(a.fingerprint, b.fingerprint)
            self.assertEqual(ea.G.serialize(a), eb.G.serialize(b))

    def test_different_seeds_differ(self):
        a = self.gen("seed-a")
        b = self.gen("seed-b")
        same = sum(1 for k in a["locations"] if a["locations"][k].get("item") == b["locations"][k].get("item"))
        self.assertLess(same, len(a["locations"]) * 0.5)
        self.assertNotEqual(a["fingerprint"], b["fingerprint"])

    def test_settings_change_the_fingerprint(self):
        self.assertNotEqual(self.gen("x")["fingerprint"], self.gen("x", {"start_weapons": 3})["fingerprint"])

    def test_share_code_round_trip(self):
        user = {"start_weapons": 1, "weapon_logic": "standard", "raritanium": False, "shop": "vanilla",
                "exclude": "weapon:ryno_8", "bolts_max": 20000, "shop_prices": "percent", "shop_price_percent": 80}
        a = self.gen("share-me", user, "chaos")
        self.assertTrue(a["share_code"].startswith("RA10|share-me|chaos|"))
        self.assertIn("raritanium=false", a["share_code"])
        self.assertIn("bolts_max=20000", a["share_code"])
        seed, preset, u = self.eng.G.parse_share_code(a["share_code"])
        b = self.gen(seed, py(u) or {}, preset)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        bad, why = self.eng.G.parse_share_code("RA6|x|standard|")[:2]
        self.assertIsNone(bad)
        self.assertIn("10.0 seeds differ", why)

    def test_one_item_per_gold_bolt_and_fixed_start(self):
        for i in range(300):
            a = self.gen(f"bolts-{i}")
            self.assertEqual(a["start"]["items"][:2], ["hoverboots", "map_o_matic"])
            self.assertEqual(len(a["gold_bolts"]), 25)
            items = [a["locations"][lid]["item"] for lid in a["gold_bolts"]]
            self.assertTrue(all(items), i)
            self.assertEqual(len(set(items)), 25, i)
            for it in items:
                self.assertTrue(grantable(it), it)
                self.assertNotIn(it, GAME_GIVEN)
            self.assertEqual(a["shop"]["mode"], "shuffle")
            self.assertEqual(sorted(a["shop"]["slots"]), VENDOR)
            self.assertFalse(any(str(l.get("item")).startswith("gold:") for l in a["locations"].values()))
            self.assertEqual(verify(a), [], i)

    def test_starting_inventory_is_random(self):
        starts = set()
        for i in range(60):
            a = self.gen(f"start-{i}")
            rest = tuple(sorted(a["start"]["items"][2:]))
            self.assertEqual(len([k for k in rest if k.startswith("weapon:")]), 2)
            self.assertEqual(len([k for k in rest if DB["items"][k]["category"] == "gadget"]), 1)
            starts.add(rest)
        self.assertGreater(len(starts), 40)

    def test_always_start_items_cannot_be_excluded_or_placed(self):
        a = self.gen("ex", {"exclude": "hoverboots,map_o_matic"})
        self.assertEqual(a["start"]["items"][:2], ["hoverboots", "map_o_matic"])
        self.assertEqual(a["registry"]["hoverboots"], "start (always)")
        for l in a["locations"].values():
            self.assertNotIn(l.get("item"), ALWAYS_START)

    def test_too_few_items_is_refused_or_repaired(self):
        # 5.0: armor fills Gold Bolts too; armor = false with too few items turns it back on.
        # 8.5.2: without Coordinates the start gives up items first; Coordinates stay off
        v = self.gen("vanilla-only", {"include_arsenal_restored": False, "planet_locks": False})
        self.assertFalse(v["settings"]["planet_locks"])
        self.assertTrue(any(w.startswith("start_gadgets lowered") for w in v["warnings"]), v["warnings"])
        a = self.gen("vanilla-only", {"include_arsenal_restored": False, "armor": False, "planet_locks": False})
        self.assertTrue(a["settings"]["armor"])
        self.assertTrue(any("armor turned on" in w for w in a["warnings"]))
        armor = [k for k, it in DB["items"].items() if it["category"] == "armor" and it["randomizable"]]
        s, err = self.eng.generate("nothing", {"weapons": False, "gadgets": False, "exclude": ",".join(armor[:12])}, "balanced")
        self.assertIsNone(s)
        self.assertIn("too few items for one per Gold Bolt", err)

    def test_every_item_has_one_classification(self):
        a = self.gen("routes", {"exclude": "weapon:ryno_8,access:savali", "planet_locks": True})
        allowed = ("start", "location", "excluded", "shop")
        for k, r in a["registry"].items():
            self.assertTrue(r.startswith(allowed), (k, r))
        self.assertEqual(a["registry"]["weapon:ryno_8"], "excluded (setting)")
        self.assertEqual(a["registry"]["access:savali"], "start (excluded from randomization)")
        for k in VENDOR:
            self.assertIn(a["registry"][k], ("shop", "start", "location"))

    def test_armor_items_and_armor_sources(self):
        armor_at = {"goldbolt": 0, "other": 0}
        source_items = 0
        for i in range(40):
            a = self.gen(f"armor-check-{i}")
            sources = [k for k in a["locations"] if DB["locations"][k]["kind"] == "armor_source"]
            self.assertEqual(len(sources), 27)
            for k in sources:
                it = a["locations"][k].get("item") or ""
                self.assertTrue(it, k)                                   # filler at least
                self.assertFalse(it.startswith("access:") or it in gating_gadgets(), "progression on an armor source")
                if DB["locations"][k]["holds"] == "filler":
                    self.assertTrue(filler_of(it), (k, it))
                elif not filler_of(it):
                    source_items += 1
            for lid, l in a["locations"].items():
                if str(l.get("item")).startswith("armor:"):
                    armor_at["goldbolt" if lid in a["gold_bolts"] else "other"] += 1
            # every findable piece is somewhere (start never takes armor)
            placed = {l.get("item") for l in a["locations"].values()}
            for key, it in DB["items"].items():
                if it["category"] == "armor" and it["randomizable"]:
                    self.assertIn(key, placed, (i, key))
        self.assertGreater(armor_at["goldbolt"], 0)
        self.assertGreater(armor_at["other"], 0)
        # without ARSENAL_RESTORED the Gold Bolts and first story missions take every item; with it
        # (9 more weapons) armor pods give real items too
        more = 0
        for i in range(20):
            a = self.gen(f"armor-ar-{i}", {"include_arsenal_restored": True})
            more += sum(1 for k, l in a["locations"].items() if DB["locations"][k]["kind"] == "armor_source"
                        and l.get("item") and not filler_of(l["item"]))
        self.assertGreater(more, 0)
        del source_items
        # without armor pieces the 25 Gold Bolts cannot be filled (the vendor's weapons stay in
        # the shop), so armor = false is turned back on, and says so
        off = self.gen("no-armor", {"armor": False})
        self.assertTrue(off["settings"]["armor"])
        self.assertTrue(any("armor turned on" in w for w in off["warnings"]))

    def test_currency_settings(self):
        """7.0: Bolts / Raritanium on and off, ranges, scaling, budgets"""
        for user, kinds in (({}, {"bolts", "raritanium"}), ({"raritanium": False}, {"bolts"}),
                            ({"bolts": False}, {"raritanium"})):
            a = self.gen("cur-" + "-".join(sorted(kinds)), user)
            got = {filler_of(l["item"]) for l in a["locations"].values() if filler_of(l.get("item"))}
            self.assertEqual({k for k, _ in got}, kinds)
            self.assertEqual(verify(a), [])
        a = self.gen("cur-none", {"bolts": False, "raritanium": False})
        self.assertFalse(any(filler_of(l.get("item")) for l in a["locations"].values()))
        # amounts in range, Bolts round to 250, Raritanium to 5, several different amounts
        a = self.gen("cur-range", {"bolts_min": 2000, "bolts_max": 30000, "raritanium_min": 100,
                                   "raritanium_max": 1500, "bolts_budget": 0, "raritanium_budget": 0})
        amounts = [filler_of(l["item"]) for l in a["locations"].values() if filler_of(l.get("item"))]
        for k, n in amounts:
            lo, hi, step = (2000, 30000, 250) if k == "bolts" else (100, 1500, 5)
            self.assertTrue(lo <= n <= hi and n % step == 0, (k, n))
        self.assertGreater(len({n for k, n in amounts if k == "bolts"}), 10)
        self.assertEqual(verify(a), [])
        # scaling: later planets give more on average
        early, late = [], []
        for i in range(30):
            b = self.gen(f"cur-scale-{i}", {"bolts_budget": 0, "raritanium": False})
            for lid, l in b["locations"].items():
                f = filler_of(l.get("item"))
                p = DB["locations"][lid].get("planet")
                if f and p:
                    idx = next(x["story_index"] for x in DB["planets"] if x["id"] == p)
                    (early if idx <= 3 else late if idx >= 8 else []).append(f[1])
        self.assertLess(sum(early) / len(early) * 1.5, sum(late) / len(late))
        # a budget caps the total and says so; a budget under the minimum gives the minimum everywhere
        c = self.gen("cur-budget", {"bolts_budget": 30000, "bolts_min": 200, "raritanium": False})
        total = sum(f[1] for f in (filler_of(l.get("item")) for l in c["locations"].values()) if f)
        self.assertLessEqual(total, 30000)
        self.assertEqual(c["filler"]["totals"]["bolts"], total)
        self.assertTrue(any("bolts_budget of 30000" in w for w in c["warnings"]))
        d = self.gen("cur-floor", {"bolts_budget": 1000, "bolts_min": 500, "raritanium": False})
        self.assertTrue(all(f[1] == 500 for f in (filler_of(l.get("item")) for l in d["locations"].values()) if f))
        self.assertTrue(any("below" in w for w in d["warnings"]))
        self.assertEqual(verify(d), [])
        # start currency
        e = self.gen("cur-start", {"start_bolts": 5000, "start_raritanium": 40})
        self.assertEqual((e["start"]["bolts"], e["start"]["raritanium"]), (5000, 40))
        # min above max: swapped, and said
        f = self.gen("cur-swap", {"bolts_min": 9000, "bolts_max": 3000})
        self.assertEqual((f["settings"]["bolts_min"], f["settings"]["bolts_max"]), (3000, 9000))
        self.assertTrue(any("swapped" in w for w in f["warnings"]))

    def test_old_filler_settings_are_converted(self):
        a = self.gen("old-filler", {"filler": "bolts", "filler_bolts": 1234})
        self.assertFalse(a["settings"]["raritanium"])
        self.assertEqual((a["settings"]["bolts_min"], a["settings"]["bolts_max"]), (1234, 1234))
        self.assertTrue(all(filler_of(l["item"]) == ("bolts", 1234) for l in a["locations"].values() if filler_of(l.get("item"))))
        self.assertTrue(any("converted" in w for w in a["warnings"]))
        b = self.gen("old-filler-none", {"filler": "none"})
        self.assertFalse(b["settings"]["bolts"] or b["settings"]["raritanium"])

    def test_shop_prices(self):
        """7.0: vanilla (no prices), weapon (the weapon's own price), percent, random"""
        v = self.gen("price-v", {"shop_prices": "vanilla"})
        self.assertFalse(v["shop"].get("prices"))
        w = self.gen("price-w", {"shop_prices": "weapon"})
        for k, sold in w["shop"]["slots"].items():
            want = REG.get(sold, {}).get("price") or REG[k]["price"]
            self.assertEqual(w["shop"]["prices"][k], want, (k, sold))
        p = self.gen("price-p", {"shop_prices": "percent", "shop_price_percent": 50})
        self.assertEqual(p["shop"]["prices"]["weapon:headhunter"], 20000)
        r = self.gen("price-r", {"shop_prices": "random", "shop_price_percent": 10, "shop_price_max_percent": 300})
        self.assertGreater(len(set(r["shop"]["prices"].values())), 8)
        for a in (v, w, p, r):
            self.assertEqual(verify(a), [])
        # prices never move the placements (their own random stream)
        self.assertEqual(w["locations"], self.gen("price-w", {"shop_prices": "weapon"})["locations"])

    def test_start_items(self):
        a = self.gen("chosen", {"start_items": "weapon:headhunter,glitch,armor:pirate_head"})
        for k in ("weapon:headhunter", "glitch", "armor:pirate_head"):
            self.assertIn(k, a["start"]["items"])
            self.assertEqual(a["registry"][k], "start (chosen)")
        self.assertNotIn("weapon:headhunter", a["shop"]["slots"].values())
        self.assertEqual(verify(a), [])
        b = self.gen("chosen-bad", {"start_items": "weapon:shatterbomb,nonsense"})
        self.assertEqual(sum("start_items" in w for w in b["warnings"]), 2)
        self.assertEqual(verify(b), [])

    def test_presets_7(self):
        """the five 7.0 presets: each valid, each different, aliases accepted"""
        fps = set()
        for p in ("balanced", "chaos", "full", "campaign", "everything"):
            a = self.gen("preset-7", {}, p)
            self.assertEqual(verify(a), [])
            fps.add(a["fingerprint"])
        self.assertEqual(len(fps), 5)
        c = self.gen("preset-7", {}, "campaign")
        self.assertTrue(c["settings"]["travel_lock"] and c["settings"]["planet_locks"])
        al = self.gen("alias", {"levels": True, "restored_weapons": True, "mission_order": "vanilla"})
        self.assertTrue(al["settings"]["travel_lock"] and al["settings"]["include_arsenal_restored"])
        self.assertEqual(al["settings"]["campaign_mode"], "vanilla")
        auto = self.gen("alias-auto", {"restored_weapons": "auto"})
        self.assertFalse(auto["settings"]["include_arsenal_restored"])
        self.assertTrue(any("auto" in w for w in auto["warnings"]))

    def test_weapon_pool_split_over_shop_start_and_rewards(self):
        """6.0: 17 pool weapons, 15 vendor slots: every weapon exactly one route, over many seeds"""
        sold_elsewhere = {"pixelizer": 0, "bouncer": 0}
        starts = set()
        for i in range(300):
            a = self.gen(f"pool-{i}")
            self.assertEqual(verify(a), [], i)
            slots = a["shop"]["slots"]
            self.assertEqual(sorted(slots), VENDOR)
            for k in ("pixelizer", "bouncer"):
                if "weapon:" + k in slots.values():
                    sold_elsewhere[k] += 1
            starts.add(tuple(sorted(x for x in a["start"]["items"] if x.startswith("weapon:"))))
            # Shatterbomb and RYNO 8 keep their own routes, cut weapons appear nowhere
            placed = set(slots.values()) | set(a["start"]["items"]) | {l.get("item") for l in a["locations"].values()}
            for k, w in REG.items():
                if w["acquisition"] in ("shop_fixed", "start_fixed", "disabled", "arsenal_restored"):
                    self.assertNotIn(k, placed - {k} if w["acquisition"] == "start_fixed" else placed, (i, k))
        self.assertGreater(sold_elsewhere["pixelizer"], 150)          # the shop sells them in most seeds
        self.assertGreater(sold_elsewhere["bouncer"], 150)
        self.assertGreater(len(starts), 50)                            # random starting weapons
        # vanilla shop: every slot sells its own weapon, Pixelizer and Bouncer start or are rewards
        v = self.gen("pool-vanilla", {"shop": "vanilla"})
        self.assertEqual(verify(v), [])
        self.assertTrue(all(k == w for k, w in v["shop"]["slots"].items()))
        # with ARSENAL_RESTORED (the separate mod) its 9 weapons join the pool
        ar = self.gen("pool-ar", {"include_arsenal_restored": True})
        self.assertEqual(verify(ar), [])
        ar_keys = {k for k, w in REG.items() if w["acquisition"] == "arsenal_restored"}
        everywhere = set(ar["shop"]["slots"].values()) | set(ar["start"]["items"]) | {l.get("item") for l in ar["locations"].values()}
        self.assertEqual(ar_keys - everywhere, set())
        # too many starting weapons: lowered, and said
        many = self.gen("pool-many", {"start_weapons": 4})
        self.assertEqual(sum(1 for x in many["start"]["items"] if x.startswith("weapon:")), 2)
        self.assertTrue(any("start_weapons lowered to 2" in w for w in many["warnings"]))
        # an excluded vendor weapon stays in its own slot
        ex = self.gen("pool-ex", {"exclude": "weapon:negatron_collider"})
        self.assertEqual(ex["shop"]["slots"]["weapon:negatron_collider"], "weapon:negatron_collider")
        self.assertEqual(verify(ex), [])

    def test_no_gadget_behind_itself_and_no_ability_gated_progression(self):
        for i in range(200):
            self.assertEqual(verify(self.gen(f"gadgets-{i}", {"start_coordinates": "start_only", "planet_locks": True})), [])

    def test_bad_settings_fall_back_to_defaults(self):
        a = self.gen("bad", {"shop_slots": 99, "economy": "free", "weapons": "yes", "start_gadgets": 7,
                             "bolts_max": 500000, "shop_prices": "free"})
        self.assertNotIn("shop_slots", a["settings"])
        self.assertEqual(a["settings"]["start_gadgets"], 1)
        self.assertEqual(a["settings"]["bolts_max"], 10000)
        self.assertEqual(a["settings"]["shop_prices"], "weapon")
        # (currency notes: "scaled down", and the user's Raritanium minimum 120 x the rewards above the budget)
        setting_warnings = [w for w in a["warnings"] if "scaled down" not in w and "budget" not in w]
        self.assertEqual(len(setting_warnings), 6, a["warnings"])
        self.assertTrue(any("not used since 4.0" in w for w in a["warnings"]))

    def test_spoiler_lists_every_placement(self):
        s, _ = self.eng.generate("spoil", {}, "balanced")
        text = self.eng.spoiler(s)
        d = py(s)
        for lid, l in d["locations"].items():
            self.assertIn(lid, text)
        self.assertIn("GOLD BOLTS", text)
        self.assertIn("Hoverboots", text)
        self.assertIn("Map-O-Matic", text)
        self.assertIn("SHOP (Ms. Zurkon's 15 weapon slots", text)
        self.assertIn("Shatterbomb and RYNO 8 (after all 10 Spybots) stay in their own slots", text)
        self.assertIn("ARMOR: the armor pieces you can find are rewards", text)
        self.assertIn("CURRENCY:", text)
        self.assertIn("prices: what the weapon sold costs", text)
        lk, _ = self.eng.generate("spoil", {}, "campaign")
        lt = self.eng.spoiler(lk)
        self.assertIn("LEVELS (locked", lt)
        self.assertIn("Open from the start: Corson V (Megalopolis), Nefarious City, Sargasso", lt)
        self.assertIn("PLAYTHROUGH", text)
        self.assertIn(d["share_code"], text)


class BatchTests(unittest.TestCase):
    """Thousands of seeds: generator audit + the independent Python verifier."""
    PRESETS = ("balanced", "chaos", "full", "campaign", "everything", "standard", "coordinates")

    def test_presets(self):
        eng = pre10_engine()
        n = 0
        for preset in self.PRESETS:
            for i in range(300):
                s, audit = eng.generate(f"batch-{preset}-{i}", {}, preset)
                self.assertIsNotNone(s, audit)
                self.assertEqual(audit, [], (preset, i))
                d = py(s)
                self.assertEqual(verify(d), [], (preset, i))
                if d["settings"]["travel_lock"]:
                    from test_campaign import verify_campaign
                    self.assertEqual(verify_campaign(d), [], (preset, i))
                n += 1
        self.assertEqual(n, 2100)

    def test_random_setting_combinations(self):
        eng = pre10_engine()
        rnd = random.Random("unit-batch-7")
        d = eng.defaults()
        n = refused = 0
        for c in range(250):
            preset = rnd.choice(self.PRESETS)
            user = rando.random_settings(rnd, d)
            for k10 in ("hub", "distribution", "shop_weapons", "early_weapons"):
                user.pop(k10, None)        # 10.0 keys: this suite checks the pre-10.0 rules (harness.PRE10_SETTINGS)
            # the vanilla planet order is checked here; campaign combinations by test_campaign.py
            user["campaign_mode"], user["random_start"] = "vanilla", False
            for i in range(4):
                s, audit = eng.generate(f"combo-{c}-{i}", user, preset)
                if s is None:
                    # a refusal must be honest: even with Coordinates these settings leave fewer
                    # grantable items than there are Gold Bolts
                    self.assertTrue(honest_refusal(eng, preset, user, audit), (preset, user, audit))
                    refused += 1
                    continue
                self.assertEqual(audit, [], (preset, user))
                self.assertEqual(verify(py(s)), [], (preset, user, i))
                n += 1
        self.assertGreater(n, 800)


class VerifierMutationTests(unittest.TestCase):
    """The validators must catch broken seeds: each test breaks a valid seed in one way."""

    @classmethod
    def setUpClass(cls):
        cls.eng = pre10_engine()

    def seed(self, preset="campaign", user=None, name="mut"):
        s, audit = self.eng.generate(name, user or {}, preset)
        self.assertEqual(audit, [])
        return s

    def both(self, s):
        """(the generator's own audit, the independent verifiers) for a Lua seed table"""
        from test_campaign import verify_campaign
        d = py(s)
        return list(py(self.eng.G.audit(s)) or []), verify(d) + verify_campaign(d)

    def test_duplicate_item(self):
        s = self.seed()
        d = py(s)
        a, b = d["gold_bolts"][0], d["gold_bolts"][1]
        s.locations[b].item = d["locations"][a]["item"]
        audit, ver = self.both(s)
        self.assertTrue(any("twice" in x for x in audit), audit)
        self.assertTrue(any("routes" in x for x in ver), ver)

    def test_coordinates_on_their_own_planet_soft_lock(self):
        s = self.seed()
        d = py(s)
        # put a locked planet's Coordinates on one of that planet's Gold Bolts
        for lid, l in d["locations"].items():
            it = l.get("item") or ""
            if it.startswith("access:"):
                pid = it[7:]
                own = [g for g in d["gold_bolts"] if DB["locations"][g]["planet"] == pid]
                if own:
                    s.locations[lid].item, s.locations[own[0]].item = d["locations"][own[0]]["item"], it
                    break
        audit, ver = self.both(s)
        self.assertTrue(any("own planet" in x for x in audit), audit)
        self.assertTrue(any("own planet" in x or "stops" in x or "unreachable" in x for x in ver), ver)

    def test_story_planet_not_open(self):
        s = self.seed()
        items = [k for k in py(s.start["items"]) if k != "access:sargasso"]
        s.start["items"] = self.eng.lua.table_from(items)
        audit, ver = self.both(s)
        self.assertTrue(any("sargasso" in x for x in audit), audit)
        self.assertTrue(any("sargasso" in x for x in ver), ver)

    def test_currency_out_of_range_and_over_budget(self):
        s = self.seed("balanced")
        d = py(s)
        lid = next(l for l, x in d["locations"].items() if str(x.get("item")).startswith("filler:bolts:"))
        s.locations[lid].item = "filler:bolts:99999"
        audit, ver = self.both(s)
        self.assertTrue(any("outside" in x for x in audit), audit)
        self.assertTrue(any("outside" in x for x in ver), ver)
        self.assertTrue(any("total" in x for x in ver), ver)

    def test_wrong_price(self):
        s = self.seed("balanced")
        s.shop.prices["weapon:enforcer"] = 7
        audit, ver = self.both(s)
        self.assertTrue(any("price" in x for x in ver), ver)

    def test_missing_progression_item(self):
        s = self.seed()
        d = py(s)
        lid = next(l for l, x in d["locations"].items() if str(x.get("item")).startswith("access:"))
        s.locations[lid].item = "filler:bolts:1000"
        audit, ver = self.both(s)
        self.assertTrue(ver, "a Coordinates item removed: some planet can no longer be reached")


if __name__ == "__main__":
    unittest.main()
