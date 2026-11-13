"""Randomizer 10.0: the Zurkie's hub with mission selection, planet shuffle through Coordinates,
rewards spread over every kind of location, and the shop split from the rewards.

Generator: every hub seed is re-checked by an independent Python verifier written here (it reads
only data from the scripts: the locations, the registry's visits and the seed): the three starting
missions are playable with the start, every destination and every in-logic location is reachable
by collecting what is reachable, every weapon has exactly one route (start, shop or a location),
no ARSENAL_RESTORED weapon is sold, and the start's own reach holds early weapons. Distribution is
measured over many seeds.

Runtime: the real scripts against the simulated game (tests/sim/rivet_sim.lua): New Game -> the
hub at the parade's wrench, the three choices and where each loads (the prologue where the parade
was left, Nefarious City at CHK_NEFCITY_START, the arena at Zurkie's), the mission ladder, the
game's own follow-on travel undone, the planet menu, learned starts, whole campaigns, the shop's
closed slots, and round 23's real event stream. What the simulator assumes about the game is
listed at the top of rivet_sim.lua: it is NOT the game.
"""
import collections
import os
import pathlib
import random
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rando  # noqa: E402
from luajson import py  # noqa: E402
from harness import Game, MOD  # noqa: E402

ENG = rando.Engine()
DB = py(ENG.lua.globals().RANDO_DATA)
CAMP = ENG.lua.globals().RANDO_CAMPAIGN
LOCATION_SEGMENT = py(CAMP.LOCATION_SEGMENT)
SEGMENTS = py(CAMP.SEGMENTS)
START_PLANETS = {"corson_v", "nefarious_city", "scarstu"}     # written down here, not read from 03
START_MISSIONS = ["corson_intro", "scarstu_1", "nefcity_1"]   # the generator's order (03 C.HUB_START)
# v0.51: the hub is Nefarious City; what ] offers right after the start (the prologue ended there)
START_MENU = ["nefcity_1", "scarstu_1", "revisit:corson_v"]
KEEP = {"hub_prologue": "keep"}             # 10.0's prologue as a destination
ALWAYS = {"hoverboots", "map_o_matic"}
DATA = ROOT / "tests" / "data"


def segment_of(lid):
    if lid in LOCATION_SEGMENT:
        return LOCATION_SEGMENT[lid]
    planet = DB["locations"][lid].get("planet")
    for seg in SEGMENTS:
        if seg["planet"] == planet and seg["visit"] == 1:
            return seg["id"]
    return None


def in_logic(lid, s):
    loc = DB["locations"][lid]
    if not loc.get("progression"):
        return False
    for r in loc.get("requires") or []:
        if r.startswith("ability:"):
            return False
        excluded = (s.get("exclude") or "").replace(" ", "").split(",")
        if r not in ALWAYS and (not s["gadgets"] or r in excluded):
            return False
    return True


def walk(d):
    """independent sphere walk of a hub seed: returns (done destinations, collected, spheres)"""
    s = d["settings"]
    kit = set(DB["start_kit"])
    owned = collections.Counter(d["start"]["items"])
    dests = d["hub"]["destinations"]
    ids = [x["id"] for x in dests]
    done, collected, spheres = [], set(), []

    def playable(x, abilities):
        if x["id"] in done:
            return False
        if x["kind"] == "finale" and any(i not in done for i in ids if i != x["id"]):
            return False
        if owned["access:" + x["planet"]] == 0:
            return False
        if any(a not in done for a in x.get("after") or []):
            return False
        for r in x.get("requires") or []:
            if r.startswith("ability:"):
                if r[8:] not in abilities:
                    return False
            elif r not in kit and owned[r] == 0:
                return False
        return True

    while True:
        abilities = set(kit)
        changed = True
        while changed:
            changed = False
            for x in dests:
                for g in [y for y in dests if y["id"] in done]:
                    abilities |= set(g.get("grants") or [])
                if playable(x, abilities):
                    done.append(x["id"])
                    changed = True
        sphere = []
        for lid, l in d["locations"].items():
            if lid in collected or not in_logic(lid, s):
                continue
            seg = segment_of(lid)
            if seg and seg not in done:
                continue
            planet = DB["locations"][lid].get("planet")
            if planet and owned["access:" + planet] == 0:
                continue
            if any(r not in ALWAYS and owned[r] == 0 for r in DB["locations"][lid].get("requires") or []):
                continue
            sphere.append(lid)
        if not sphere:
            break
        spheres.append(sphere)
        for lid in sphere:
            collected.add(lid)
            it = d["locations"][lid].get("item")
            if it and it in DB["items"]:
                owned[it] += 1
    return done, collected, spheres


def verify_hub_seed(d):
    probs = []
    s = d["settings"]
    if d.get("format") != 10:
        probs.append("format %r" % d.get("format"))
    if not (s["hub"] and s["planet_locks"] and s["travel_lock"]):
        probs.append("hub seed without hub/planet_locks/travel_lock")
    opened = {k[7:] for k in d["start"]["items"] if k.startswith("access:")}
    excluded = {k[7:] for k in ((s["exclude"] or "") + "," + (s["start_items"] or "")).replace(" ", "").split(",") if k.startswith("access:")}
    if opened - excluded != START_PLANETS:
        probs.append("open at the start: %s" % sorted(opened))
    h = d.get("hub") or {}
    if list(h.get("start") or []) != START_MISSIONS:
        probs.append("start missions %s" % h.get("start"))
    done, collected, spheres = walk(d)
    ids = [x["id"] for x in h.get("destinations") or []]
    if set(done) != set(ids):
        probs.append("never playable: %s" % sorted(set(ids) - set(done)))
    if done[:3] and set(done[:3]) != set(START_MISSIONS):
        probs.append("the first playable destinations are %s" % done[:3])
    if done and done[-1] != "finale":
        probs.append("the finale is not last")
    for lid in d["locations"]:
        if in_logic(lid, s) and lid not in collected and s["accessibility"] == "full":
            probs.append("not reachable: " + lid)
    # weapons: one route each; the shop sells no ARSENAL_RESTORED weapon and no more than shop_weapons
    routes = collections.Counter()
    for k in d["start"]["items"]:
        routes[k] += 1
    for lid, l in d["locations"].items():
        if l.get("item") in DB["items"]:
            routes[l["item"]] += 1
    vendor = sorted(k for k, it in DB["items"].items() if it["category"] == "weapon" and it.get("vendor"))
    sold = []
    closed = set(d["shop"].get("closed") or [])
    for k in vendor:
        w = (d["shop"].get("slots") or {}).get(k)
        if k in closed:
            if w:
                probs.append("closed slot %s sells %s" % (k, w))
            continue
        if not w:
            probs.append("slot %s sells nothing and is not closed" % k)
            continue
        sold.append(w)
        routes[w] += 1
        if DB["items"][w]["acquisition"] == "arsenal_restored":
            probs.append("ARSENAL_RESTORED weapon %s in the shop" % w)
    moved = len([k for k in vendor if k not in closed and d["shop"]["mode"] == "shuffle"])
    if moved > s["shop_weapons"]:
        probs.append("%d slots sell, shop_weapons %d" % (moved, s["shop_weapons"]))
    if len(sold) != len(set(sold)):
        probs.append("a weapon in two slots")
    for k, it in DB["items"].items():
        if it["category"] != "weapon":
            continue
        pool = it["acquisition"] == "pool" or (it["acquisition"] == "arsenal_restored" and s["include_arsenal_restored"])
        if pool and s["weapons"] and k not in (s["exclude"] or "") and routes[k] != 1:
            probs.append("%s has %d routes" % (k, routes[k]))
        if not pool and k != "weapon:burst_pistol" and routes[k] and k not in sold:
            probs.append("%s (%s) is placed" % (k, it["acquisition"]))
    # early weapons
    if s["distribution"] == "spread" and s["weapon_logic"] == "none" and spheres:
        first = [lid for lid in spheres[0] if DB["locations"][lid].get("holds") != "filler"]
        early = sum(1 for lid in first if DB["items"].get(d["locations"][lid].get("item"), {}).get("category") == "weapon")
        reward_w = sum(1 for l in d["locations"].values() if DB["items"].get(l.get("item"), {}).get("category") == "weapon")
        if early < min(s["early_weapons"], reward_w, len(first)):
            probs.append("early weapons %d" % early)
    return probs


class HubGeneratorTests(unittest.TestCase):
    def gen(self, seed, user=None, preset="balanced"):
        s, audit = ENG.generate(seed, user or {}, preset)
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [], seed)
        return py(s)

    def test_defaults(self):
        d = ENG.defaults()
        self.assertTrue(d["hub"])
        self.assertEqual(d["distribution"], "spread")
        self.assertEqual(d["shop_weapons"], 8)
        self.assertEqual(d["early_weapons"], 2)
        # the user's 8.5.2 values are still the baseline
        for k, v in {"planet_locks": True, "campaign_mode": "planet_shuffle", "shop_prices": "weapon",
                     "raritanium_min": 120, "raritanium_max": 1000}.items():
            self.assertEqual(d[k], v, k)

    def test_many_seeds_every_preset(self):
        n = 0
        for preset in ("balanced", "chaos", "full", "campaign", "everything"):
            for ar in (False, True):
                for i in range(60):
                    d = self.gen(f"v100-{preset}-{ar}-{i}", {"include_arsenal_restored": ar}, preset)
                    self.assertEqual(verify_hub_seed(d), [], (preset, ar, i))
                    n += 1
        self.assertEqual(n, 600)

    def test_random_settings(self):
        rnd = random.Random("v100-random")
        d0 = ENG.defaults()
        n = 0
        for c in range(150):
            user = rando.random_settings(rnd, d0)
            user["hub"] = True
            s, audit = ENG.generate(f"v100-rs-{c}", user, rnd.choice(["balanced", "chaos", "full", "campaign", "everything"]))
            if s is None:
                continue               # too few items for a Gold-Bolts-first fill (honest refusals: test_generator)
            self.assertEqual(audit, [], (c, user))
            self.assertEqual(verify_hub_seed(py(s)), [], (c, user))
            n += 1
        self.assertGreater(n, 120)

    def test_planet_order_really_varies(self):
        firsts, coords_kinds = collections.Counter(), collections.Counter()
        for i in range(200):
            d = self.gen(f"v100-order-{i}")
            route = d["hub"]["route"]
            # the first destination after the three starting missions and Zurkie's second visit
            nxt = [x for x in route if x not in START_MISSIONS and x != "scarstu_2"][0]
            firsts[nxt] += 1
            for lid, l in d["locations"].items():
                if str(l.get("item", "")).startswith("access:"):
                    coords_kinds[DB["locations"][lid]["kind"]] += 1
        self.assertGreaterEqual(len(firsts), 6, firsts)
        # Coordinates are found at Gold Bolts, story missions and side activities alike
        for kind in ("goldbolt", "planet", "story", "side"):
            self.assertGreater(coords_kinds[kind], 50, coords_kinds)

    def test_rewards_are_spread(self):
        items = collections.Counter()
        total = collections.Counter()
        cats = collections.defaultdict(collections.Counter)
        for i in range(200):
            d = self.gen(f"v100-spread-{i}")
            for lid, l in d["locations"].items():
                kind = DB["locations"][lid]["kind"]
                if DB["locations"][lid].get("holds") == "filler":
                    continue
                total[kind] += 1
                it = l.get("item")
                if it in DB["items"]:
                    items[kind] += 1
                    cats[kind][DB["items"][it]["category"]] += 1
        share = {k: items[k] / total[k] for k in total}
        for k, v in share.items():
            self.assertGreater(v, 0.3, (k, share))       # every kind of location holds items
        self.assertLess(share["goldbolt"] - share["armor_source"], 0.3, share)   # Gold Bolts are not favoured
        self.assertGreater(cats["armor_source"]["weapon"], 300, cats["armor_source"])  # armor pods give weapons
        self.assertGreater(cats["goldbolt"]["weapon"] + cats["planet"]["weapon"], 500)

    def test_early_rewards_are_meaningful(self):
        for i in range(200):
            d = self.gen(f"v100-early-{i}")
            _, _, spheres = walk(d)
            first = spheres[0]
            kinds = [DB["items"][d["locations"][lid]["item"]]["category"] for lid in first if d["locations"][lid].get("item") in DB["items"]]
            self.assertGreaterEqual(kinds.count("weapon"), 2, (i, kinds))
            self.assertGreaterEqual(kinds.count("coordinates"), 1, (i, kinds))
            self.assertGreaterEqual(len(kinds), 5, (i, kinds))

    def test_shop_and_rewards_are_separate(self):
        for ar in (False, True):
            for i in range(100):
                d = self.gen(f"v100-shop-{ar}-{i}", {"include_arsenal_restored": ar})
                sold = set((d["shop"]["slots"] or {}).values())
                given = set(d["start"]["items"]) | {l.get("item") for l in d["locations"].values()}
                self.assertFalse(sold & given, (ar, i, sold & given))
                self.assertEqual(len(d["shop"]["closed"]), 15 - 8)
                for w in sold:
                    self.assertEqual(DB["items"][w]["acquisition"], "pool", w)
        d = self.gen("v100-shop-all", {"shop_weapons": 15})
        self.assertFalse(d["shop"]["closed"])
        d = self.gen("v100-shop-none", {"shop_weapons": 0})
        self.assertEqual(len(d["shop"]["closed"]), 15)
        self.assertEqual(verify_hub_seed(d), [])

    def test_gold_bolts_first_is_still_there(self):
        d = self.gen("v100-gbf", {"distribution": "goldbolts_first", "include_arsenal_restored": True})
        for lid in d["gold_bolts"]:
            self.assertIn(d["locations"][lid]["item"], DB["items"], lid)
        self.assertEqual(verify_hub_seed(d), [])

    def test_hub_settings_that_do_not_apply(self):
        d = self.gen("v100-na", {"planet_locks": False, "campaign_mode": "vanilla", "start_coordinates": "random_extra"})
        self.assertTrue(d["settings"]["planet_locks"])
        self.assertEqual(d["settings"]["campaign_mode"], "planet_shuffle")
        self.assertTrue(any("does not apply to a hub seed" in w for w in d["warnings"]))
        self.assertEqual(verify_hub_seed(d), [])

    def test_share_code_and_spoiler(self):
        d = self.gen("v100-share", None, "chaos")
        self.assertTrue(d["share_code"].startswith("RA10|v100-share|chaos|"))
        seed, preset, user = ENG.G.parse_share_code(d["share_code"])
        self.assertEqual(self.gen(seed, py(user) or {}, preset)["fingerprint"], d["fingerprint"])
        bad, why = ENG.G.parse_share_code("RA9|x|balanced|")[:2]
        self.assertIsNone(bad)
        self.assertIn("10.0", why)
        s, _ = ENG.generate("v100-spoiler", {}, "balanced")
        text = ENG.spoiler(s)
        for want in ("HUB AND PLANET SHUFFLE (Nefarious City)", "1. Nefarious City - the hub's story",
                     "2. Battle Arena - Zurkie's Battleplex", "3. Prologue - the parade on Corson V",
                     "the city's story starts there", "CLOSED (shows the Burst Pistol", "No weapon is both sold and given",
                     "each one you pick up is a real Gold Bolt"):
            self.assertIn(want, text)

    def test_audit_catches_mistakes(self):
        lua = ENG.lua
        mutate = lua.eval("""function(seed, what)
          local s = seed
          if what == "sold_and_given" then
            for k, w in pairs(s.shop.slots) do
              for lid, l in pairs(s.locations) do if l.item and RANDO_DATA.items[l.item] and RANDO_DATA.items[l.item].category == "weapon" then l.item = w; return end end
            end
          elseif what == "ar_in_shop" then
            for k, w in pairs(s.shop.slots) do s.shop.slots[k] = "weapon:combuster"; return end
          elseif what == "extra_open" then
            s.start.items[#s.start.items + 1] = "access:viceron"
          elseif what == "route_short" then
            table.remove(s.hub.route, 5)
          elseif what == "closed_sells" then
            s.shop.slots[s.shop.closed[1]] = "weapon:enforcer"
          end
        end""")
        for what, expect in (("sold_and_given", "is sold in the shop and also at"), ("ar_in_shop", "ARSENAL_RESTORED"),
                             ("extra_open", "open from the start"), ("route_short", "never reachable"),
                             ("closed_sells", "is closed and sells")):
            s, _ = ENG.generate("v100-mut", {"include_arsenal_restored": True}, "balanced")
            mutate(s, what)
            probs = list(py(ENG.G.audit(s)) or [])
            self.assertTrue(any(expect in p for p in probs), (what, probs))


# ---------------------------------------------------------------------------------------------
# runtime
# ---------------------------------------------------------------------------------------------
def all_missions(g):
    names = ["MIS_INTRO", "MIS_ZURK_ARENA_BRONZE_CUP", "MIS_ZURK_ARENA_SILVER_CUP", "MIS_ZURK_ARENA_GOLD_CUP"]
    for seg in g.g.RANDO_CAMPAIGN.SEGMENTS.values():
        for m in seg.missions.values():
            if m not in names:
                names.append(m)
    return names


def hub_game(seed="v100-rt", settings=None, missions=None, **kw):
    st = {"seed": seed, "preset": "balanced", "hub": True, "distribution": "spread", "shop_weapons": 8,
          "planet_locks": True, "campaign_mode": "planet_shuffle", "hub_return_delay": 2, "shop_close_slots": True}
    st.update(settings or {})
    g = Game(settings=st, dll_version=6, before_scripts=lambda game: setattr(game.sim, "auto_travel", True), **kw)
    assert not g.load_errors, g.load_errors
    states = {n: 0 for n in all_missions(g)}
    states["MIS_INTRO"] = 2
    for c in ("MIS_ZURK_ARENA_BRONZE_CUP", "MIS_ZURK_ARENA_SILVER_CUP", "MIS_ZURK_ARENA_GOLD_CUP"):
        states[c] = 1
    states.update(missions or {})
    g.sim.install_missions(g.lua.table_from([g.lua.table_from([n, s]) for n, s in states.items() if s is not None]))
    t = g.lua.table_from
    # round 23 / 16 (SIMULATED rule): Nefarious City's first step finishes on a load at CHK_NEFCITY_START
    g.sim.go_to["MIS_NEFCITY_01"] = t({"o": "OBJ_NEFCITY_GO_TO_NEFCITY", "planet": "NefCity", "hero": "ratchet", "at": "CHK_NEFCITY_START"})
    # the game's own next step (round 23)
    g.sim.chain["MIS_INTRO"] = t({"start": "MIS_NEFCITY_01", "travel": "NefCity", "cp": "CHK_NEFCITY_START"})
    g.sim.chain["MIS_NEFCITY_01"] = t({"start": "MIS_SARG_01_FIRST_VISIT", "travel": "Sargasso"})
    return g


PARADE_CP = "CHK_MALINON_PARADE_START"       # a parade checkpoint the simulator lists (SIMULATED name)


def to_hub(g, catalog=True, before=None):
    g.companion_restore()
    if before:
        before(g)
    g.sim.new_game()
    g.step(60)
    g.sim.parade_control()
    if catalog:
        g.step(1500)                           # the checkpoint catalog fills (it starts at frame 600)
    g.sim.checkpoint(PARADE_CP)
    g.sim.parade_wrench()                      # v0.51: also starts OBJ_INTRO_GOING_DOWN (round 23)
    g.step(30)
    g.sim.parade_release()                     # GOING_DOWN done, the parade goes on
    for _ in range(60):
        g.step(30)
        h = g.state.hub
        if h is not None and h.started and g.sim.planet == "NefCity":
            break
    g.step(400)
    return g


def hub(g):
    return py(g.state.hub)


def choose(g, dest_id=None, revisit=None, frames=2400):
    H = g.g.RANDO_HUB
    ents = list(py(H.menu_entries()))
    want = [i for i, e in enumerate(ents) if (dest_id and (e.get("dest") or {}).get("id") == dest_id) or (revisit and e.get("revisit") == revisit)]
    assert want, (dest_id, revisit, ents)
    for _ in range(len(ents) + 1):
        g.press("]")
        if H.sel - 1 == want[0]:
            break
    g.press("]", ctrl=True)
    g.step(frames)


def menu_ids(g):
    return [(e.get("dest") or {}).get("id") or ("revisit:" + e.get("revisit")) for e in py(g.g.RANDO_HUB.menu_entries())]


class HubStartTests(unittest.TestCase):
    def test_new_game_goes_to_the_hub_and_its_story_starts(self):
        g = to_hub(hub_game())
        h = hub(g)
        self.assertTrue(h["started"])
        # v0.51: the hub is Nefarious City, loaded where the game loads its story, with the story on
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values()), ["CHK_NEFCITY_START"])
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 2)
        self.assertTrue(py(g.sim.go_to["MIS_NEFCITY_01"])["done"])     # its first step finished
        self.assertEqual(g.sim.started_as["MIS_NEFCITY_01"], "ratchet")
        self.assertEqual(h["current"], "nefcity_1")
        self.assertTrue(g.note_has("its story starts here"))
        self.assertTrue(g.log_has("start menu:\t1. Nefarious City - the hub's story  |  2. Battle Arena - Zurkie's Battleplex"))
        # the story made active first (as round 17), then the prologue written complete at the hub
        self.assertEqual([(c.name, c.state) for c in g.sim.set_state_calls.values()], [("MIS_NEFCITY_01", 1), ("MIS_INTRO", 4)])
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 4)
        self.assertIn("corson_intro", h["done"])
        self.assertTrue(g.state.collected["planet:corson_v"])
        self.assertEqual(menu_ids(g), START_MENU)
        self.assertIsNone(g.sim.hero_held)                            # the warp came after GOING_DOWN
        self.assertEqual(h["parade_cp"], PARADE_CP)
        # only the three planets are open; the ship's travel on and every level bit set
        self.assertEqual({k for k, v in py(g.state.access).items() if v}, START_PLANETS)
        self.assertEqual(g.sim.travel_flag, 1)
        self.assertEqual(g.sim.levels & 0x7FE, 0x7FE)
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_prologue_resumes_where_the_parade_was_left(self):
        g = to_hub(hub_game(settings=KEEP))
        self.assertEqual(menu_ids(g), ["nefcity_1", "scarstu_1", "corson_intro"])
        choose(g, "corson_intro")
        self.assertEqual(g.sim.planet, "Malinon")
        self.assertEqual(list(g.sim.warps.values())[-1], PARADE_CP)
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 2)
        # nothing written for the prologue: it is still active (only the hub story's start)
        self.assertEqual([(c.name, c.state) for c in g.sim.set_state_calls.values()], [("MIS_NEFCITY_01", 1)])
        self.assertEqual(hub(g)["current"], "corson_intro")
        # the game finishes the prologue and rifts to Nefarious City by itself: that is the hub now,
        # so nothing is undone and there is no second trip
        g.sim.complete_mission("MIS_INTRO")
        g.step(1500)
        self.assertIn("corson_intro", hub(g)["done"])
        self.assertTrue(g.state.collected["planet:corson_v"])
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values())[-1], PARADE_CP)
        self.assertFalse(g.log_has("[ORDER KEPT]"))
        self.assertTrue(g.log_has("already at the hub, no trip back"))

    def test_prologue_without_a_parade_checkpoint_uses_the_intro_default(self):
        g = to_hub(hub_game(settings=KEEP), catalog=False)
        g.state.hub.parade_cp = None
        g.state.hub.parade_hash = None
        choose(g, "corson_intro")
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_MALINON_INTRO_DEFAULT")

    def test_nefarious_city_story_finishes_and_home_is_the_pad(self):
        g = to_hub(hub_game())
        choose(g, "nefcity_1")                                  # the menu entry: it is already running
        self.assertTrue(g.log_has("already active"))
        g.sim.complete_mission("MIS_NEFCITY_01")
        g.sim.checkpoint("CHK_SARG_OPENING_SIMULATED")
        g.step(1500)
        self.assertIn("nefcity_1", hub(g)["done"])
        self.assertEqual(g.sim.planet, "NefCity")             # the game's own trip to Sargasso undone
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_SHIP")   # story done: the pad
        for lid in ("planet:nefarious_city", "story2:nefarious_city"):
            self.assertTrue(g.state.collected[lid], lid)

    def test_the_8x_landing_would_not_have_started_it(self):
        # control: with the story's start and the hub's first checkpoint removed, the hub start
        # lands at CHK_NEFCITY_SHIP (8.x) and the story waits at its first step
        def strip(g):
            g.seed.hub.checkpoints = g.lua.table_from(["CHK_NEFCITY_SHIP"])
            for d in g.seed.hub.destinations.values():
                if d.id == "nefcity_1":
                    d.start_cp = None
        g = to_hub(hub_game(), before=strip)
        self.assertEqual(list(g.sim.warps.values())[0], "CHK_NEFCITY_SHIP")
        self.assertFalse(py(g.sim.go_to["MIS_NEFCITY_01"]).get("done"))

    def test_battle_arena_starts_at_zurkies(self):
        g = to_hub(hub_game())
        choose(g, "scarstu_1")
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertEqual(g.sim.get_mission("MIS_ZURK_01_VISIT_01"), 2)
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_ZURK_00_DEFAULT")
        self.assertEqual(hub(g)["current"], "scarstu_1")
        g.sim.complete_mission("MIS_ZURK_01_VISIT_01")
        g.step(900)
        self.assertIn("scarstu_1", hub(g)["done"])
        # back to the hub: the city's story is not finished, so where it resumes
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_START")
        self.assertTrue(g.state.collected["planet:scarstu"])
        # Zurkie's second visit opens after the first
        self.assertIn("scarstu_2", menu_ids(g))

    def test_a_restarted_prologue_is_no_new_game(self):
        g = to_hub(hub_game(settings=KEEP))
        g.sim.set_mission("MIS_INTRO", 0, False)
        run = g.state.run
        choose(g, "corson_intro", frames=60)
        self.assertEqual([(c.name, c.state) for c in g.sim.set_state_calls.values()][-1], ("MIS_INTRO", 1))
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_INTRO", ObjectiveName="OBJ_INTRO_PARADE_START_CINE", ObjectiveState=1)
        g.step(60)
        self.assertEqual(g.state.run, run)


class PlanetShuffleTests(unittest.TestCase):
    def test_only_open_destinations_are_offered_and_coordinates_open_more(self):
        g = to_hub(hub_game("v100-shuffle"))
        before = set(menu_ids(g))
        self.assertEqual(before, set(START_MENU))
        locked = [p for p in ("savali", "blizar_prime", "torren_iv", "cordelion", "ardolis", "viceron", "sargasso")
                  if not g.state.access[p]]
        self.assertEqual(len(locked), 7)
        g.R.grant("access:savali")
        g.step(30)
        self.assertIn("savali_1", menu_ids(g))
        self.assertNotIn("blizar_1", menu_ids(g))

    def test_menu_to_a_locked_planet_goes_back_to_the_hub(self):
        g = to_hub(hub_game("v100-menu"))
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_BLIZAR_A_LANDINGPAD", InterplanetaryCheckpointName="CHK_TRANSITION_TO_BLIZAR")
        g.travel("Blizar")
        g.step(600)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(g.note_has("no Coordinates for Blizar Prime yet - back to Nefarious City"))

    def test_menu_to_an_open_planet_starts_its_destination(self):
        g = to_hub(hub_game("v100-menu-open"))
        g.R.grant("access:savali")
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING", InterplanetaryCheckpointName="CHK_TRANSITION_TO_SAVALI")
        g.travel("Savali")
        g.step(900)
        self.assertEqual(g.sim.planet, "Savali")
        self.assertEqual(g.sim.get_mission("MIS_SAV_01"), 2)
        self.assertEqual(hub(g)["current"], "savali_1")

    def test_follow_story_option(self):
        # v0.51: the city's story ends with the game's own trip to Sargasso; with Sargasso open and
        # hub_follow_story, that destination is played instead of going home
        g = to_hub(hub_game("v100-follow", {"hub_follow_story": True}))
        g.R.grant("access:sargasso")
        g.step(30)
        g.sim.complete_mission("MIS_NEFCITY_01")
        g.step(1500)
        self.assertEqual(g.sim.planet, "Sargasso")
        self.assertEqual(hub(g)["current"], "sargasso_1")

    def test_a_start_is_learned_and_kept_over_a_new_game(self):
        g = to_hub(hub_game("v100-learn"))
        g.R.grant("access:savali")
        choose(g, "savali_1", frames=300)
        self.assertEqual(g.sim.planet, "Savali")
        g.sim.checkpoint("CHK_SAV_01_START_SIMULATED")       # the game's own first checkpoint there
        g.lua.execute('RANDO_TRAVEL.hash_names[RANDO_TRAVEL.hash("CHK_SAV_01_START_SIMULATED")] = "CHK_SAV_01_START_SIMULATED"')
        g.sim.checkpoint("CHK_SAV_01_START_SIMULATED")
        g.step(30)
        # the first triggered checkpoint (CHK_SAV_01_LANDING after the warp) is the one learned
        self.assertEqual(py(g.state.hub_learned)["savali_1"], "CHK_SAV_01_LANDING")
        g.R.reset_for_new_game("test")
        self.assertEqual(py(g.state.hub_learned)["savali_1"], "CHK_SAV_01_LANDING")

    def test_revisit_entries(self):
        g = to_hub(hub_game("v100-revisit"))
        self.assertIn("revisit:corson_v", menu_ids(g))           # the prologue ended at the hub start
        choose(g, revisit="corson_v", frames=600)
        self.assertEqual(g.sim.planet, "Malinon")
        self.assertIsNone(hub(g).get("current"))


# the game's Gold Bolt names per planet (round 16/23: "Nefarious City 3", "Zurkon's 1", "Sargasso 2")
BOLT_NAME = {}
for _prefix, _pid in DB["bolt_prefixes"].items():
    BOLT_NAME.setdefault(_pid, _prefix)


class CampaignTests(unittest.TestCase):
    """Whole campaigns in the simulated game: each open destination in turn, its missions finished
    by events; missing missions are finished by hand."""

    def play(self, seed, pick_last=False, broken=None):
        g = hub_game(seed, missions=broken)
        g.sim.ship_near = True
        to_hub(g)
        H = g.g.RANDO_HUB
        plan = py(g.seed.hub)
        for _ in range(40):
            av = list(py(H.available()))
            if not av:
                break
            target = av[-1] if pick_last else av[0]
            d = py(H.dest(target))
            choose(g, target)
            att = hub(g).get("attempts", {}).get(target, {})
            if att.get("what") == "story":
                for m in d["missions"]:
                    if g.sim.get_mission(m) is not None and g.sim.get_mission(m) != 4:
                        g.sim.complete_mission(m)
                    g.step(H.NEXT_MISSION_WAIT + 300)
            if target not in hub(g)["done"]:
                g.press("[", ctrl=True)
                g.press("[", ctrl=True)
            self.assertIn(target, hub(g)["done"], (seed, target, att))
            # the planet's Gold Bolts are picked up while there (Coordinates may be on them)
            if d["visit"] == 1 and d["planet"] in BOLT_NAME:
                for k in range(1, 4):
                    g.fire("GainGoldBoltEvent", BoltName="%s %d" % (BOLT_NAME[d["planet"]], k))
                g.step(60)
            g.step(60 * 3 + 900)
            if d["kind"] == "finale":
                break
            self.assertEqual(g.sim.planet, "NefCity", (seed, target))
        h = hub(g)
        self.assertEqual(h["n_done"], len(plan["destinations"]), (seed, sorted(h["done"])))
        self.assertTrue(g.state.campaign_complete)
        for d in plan["destinations"]:
            for lid in py(H.locations_of(H.dest(d["id"]))):
                self.assertTrue(g.state.collected[lid], (seed, lid))
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])
        return g

    def test_campaigns_to_the_finale(self):
        for i in range(3):
            self.play(f"v100-camp-{i}", pick_last=(i % 2 == 1))

    def test_campaign_with_missing_missions(self):
        self.play("v100-camp-broken", broken={"MIS_BLIZAR": None, "MIS_ZORD_01": None, "MIS_MEGA_FINALE": None})


class PrologueEndTests(unittest.TestCase):
    """Round 23's order: MIS_INTRO turns complete on Ardolis, then the game rifts to Nefarious City
    by itself and starts MIS_NEFCITY_01. v0.51: Nefarious City is the hub, so with the prologue kept
    (hub_prologue = "keep") that rift is simply the way home. The game's own trip after the city's
    story (to Sargasso) is undone once that planet has loaded, or after a timeout."""

    def prologue_on_ardolis(self):
        g = to_hub(hub_game(settings=KEEP))
        choose(g, "corson_intro")
        g.travel("Ardolis")                                      # the prologue's own rifts
        g.step(200)
        self.assertEqual(g.sim.planet, "Ardolis")
        self.assertTrue(g.log_has("during\tcorson_intro"))
        g.sim.chain["MIS_INTRO"] = g.lua.table_from({"start": "MIS_NEFCITY_01", "travel": "NefCity"})
        g.sim.complete_mission("MIS_INTRO")
        return g

    def test_the_prologues_rift_to_nefarious_city_is_the_way_home(self):
        g = self.prologue_on_ardolis()
        self.assertEqual(g.sim.get_mission("MIS_NEFCITY_01"), 2)
        g.step(1500)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertIn("corson_intro", hub(g)["done"])
        self.assertFalse(g.log_has("[ORDER KEPT]"))
        self.assertEqual(list(g.sim.warps.values())[-1], PARADE_CP)       # no trip of ours after it
        choose(g, "nefcity_1")
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_START")
        self.assertTrue(g.log_has("already active"))
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def city_story_done(self):
        g = to_hub(hub_game())
        g.sim.complete_mission("MIS_NEFCITY_01")                   # the game then travels to Sargasso
        g.step(200)
        self.assertEqual(g.sim.planet, "Sargasso")
        return g

    def test_home_after_the_new_planet_loads(self):
        g = self.city_story_done()
        g.step(200)
        self.assertEqual(g.sim.planet, "Sargasso")               # nothing before the planet loaded
        g.sim.checkpoint("CHK_SARG_OPENING_SIMULATED")           # a checkpoint no list names
        g.step(600)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_SHIP")
        self.assertTrue(g.log_has("[ORDER KEPT] the game's own travel to sargasso undone"))
        self.assertTrue(g.log_has("the new planet loaded"))

    def test_home_after_a_timeout_without_a_checkpoint(self):
        g = self.city_story_done()
        g.step(400)
        self.assertEqual(g.sim.planet, "Sargasso")
        g.step(900)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(g.log_has("no loaded checkpoint on"))

    def test_a_launch_cancels_the_pending_return(self):
        g = self.city_story_done()
        choose(g, "scarstu_1", frames=60)                        # chosen before the planet loaded
        self.assertIsNone(g.g.RANDO_HUB.order_kept)
        g.step(2400)
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertEqual(hub(g)["current"], "scarstu_1")


class CheckpointNameTests(unittest.TestCase):
    # names your game listed, with the CheckpointHash your logs show for them (rounds 13-23)
    REAL = {"CHK_NEFCITY_START": 2052464476, "CHK_ZURK_00_DEFAULT": 2229284024, "CHK_NEFCITY_SHIP": 263079407,
            "CHK_TRANSITION_TO_SARG": 3358770726, "CHK_ARD_START": 894761074, "CHK_ZURK_LANDING_SHIP": 1736146898,
            "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP": 3250694813, "CHK_ZORDOOM_LANDING_COMBAT": 3337761593}

    def test_the_engine_hash_names_checkpoints(self):
        g = Game()
        for name, h in self.REAL.items():
            self.assertEqual(g.g.RANDO_TRAVEL.hash(name), h, name)
            self.assertEqual(g.g.rivet.hash(name), h, name)

    def test_round23_hashes_are_found_in_the_log(self):
        text = (DATA / "round23_rivet.log").read_text(encoding="utf-8", errors="replace")
        for name in ("CHK_NEFCITY_START", "CHK_TRANSITION_TO_SARG", "CHK_MEGA_L27_PSHIFT_SLIDE"):
            h = Game().g.RANDO_TRAVEL.hash(name)
            self.assertIn("CheckpointHash=%d " % h, text, name)

    def test_triggered_checkpoints_are_logged_by_name(self):
        g = Game()
        g.ready()
        g.fire("CheckpointTriggeredEvent", CheckpointHash=2052464476, Loaded=True)
        self.assertTrue(g.log_has("RANDO-CHECKPOINT\tCHK_NEFCITY_START"))


class ShopTests(unittest.TestCase):
    def shop_game(self, seed="v100-shop", settings=None, extra_slots=()):
        st = {"seed": seed, "preset": "balanced", "hub": True, "distribution": "spread", "shop_weapons": 8,
              "planet_locks": True, "campaign_mode": "planet_shuffle", "shop_close_slots": True}
        st.update(settings or {})
        g = Game(settings=st)
        data = g.g.RANDO_DATA
        ids = [Game.AMMO_ID]
        for key in sorted(data["items"].keys()):
            it = data["items"][key]
            if it["category"] == "weapon" and it["vendor"]:
                ids.append(it["id"])
        for k in ("weapon:burst_pistol", "weapon:shatterbomb", "weapon:ryno_8") + tuple(extra_slots):
            ids.append(data["items"][k]["id"])
        g.install_vendor(ids)
        return g, ids

    def slots_after(self, g, ids):
        g.ready(frames=2400)
        return [g.sim.vendor_slot_item(Game.VENDOR_ID, i) for i in range(1, len(ids) + 1)]

    def test_closed_slots_and_no_duplicates(self):
        g, ids = self.shop_game(settings={"include_arsenal_restored": True},
                                extra_slots=("weapon:combuster", "weapon:fusion_grenade", "weapon:bouncer"))
        after = self.slots_after(g, ids)
        data = g.g.RANDO_DATA
        by_id = {data["items"][k]["id"].upper(): k for k in data["items"].keys() if data["items"][k]["category"] == "weapon"}
        seed = py(g.seed)
        burst = data["items"]["weapon:burst_pistol"]["id"].upper()
        sold = [by_id.get(x.upper()) for x in after]
        given = set(seed["start"]["items"]) | {l.get("item") for l in seed["locations"].values()}
        for w in sold:
            if w and w != "weapon:burst_pistol":
                self.assertNotIn(w, given, w)           # nothing sold is also given
        # the closed normal slots and the ARSENAL_RESTORED / Bouncer slots show the Burst Pistol
        self.assertGreaterEqual(sum(1 for x in after if x.upper() == burst), 7 + 3 + 1)
        self.assertTrue(g.log_has("->CLOSED"))
        self.assertIn("slots closed", g.R.status_text())

    def test_close_slots_off_keeps_them(self):
        g, ids = self.shop_game(settings={"shop_close_slots": False})
        after = self.slots_after(g, ids)
        burst = g.g.RANDO_DATA["items"]["weapon:burst_pistol"]["id"].upper()
        self.assertEqual(sum(1 for x in after if x.upper() == burst), 1)   # only its own slot
        self.assertTrue(g.log_has("kept (shop_close_slots = false)"))

    def test_bytes_are_parsed_fast_and_right(self):
        g = Game()
        rnd = random.Random(5)
        raw = bytes(rnd.randrange(256) for _ in range(512))
        text = " ".join("%02X" % b for b in raw)
        got = g.g.RANDO_SHOP.bytes_of(text)
        self.assertEqual(bytes(got[i] for i in range(1, len(raw) + 1)), raw)
        self.assertEqual(list(g.g.RANDO_SHOP.bytes_of("aB c").values()), [0xAB])
        t0 = time.perf_counter()
        for _ in range(200):
            g.g.RANDO_SHOP.bytes_of(text)
        per = (time.perf_counter() - t0) / 200
        self.assertLess(per, 0.002, per)       # well under the frame budget (lupa, this machine)

    def test_a_budget_error_halves_the_reads(self):
        g = Game()
        S = g.g.RANDO_SHOP
        chunk = S.CHUNK
        g.lua.execute("""
          local v = {}
          RANDO_SHOP.jobs = { { id = "X", obj = 0, v = v, co = coroutine.create(function() error("scripts\\\\12_rando_shop.lua:98: ran past the 8 ms frame budget") end), started = 0 } }
          RANDO_SHOP.run_job()
          TEST_V = v""")
        self.assertEqual(S.CHUNK, chunk // 2)
        self.assertIsNone(g.g.TEST_V.tries)
        self.assertTrue(g.log_has("not counted as a try"))


class RealLogTests(unittest.TestCase):
    def replay(self, name):
        from test_runtime import RealLogReplayTests
        g = hub_game("v100-real-" + name)
        g.companion_restore()
        g.travel("NefCity", 5)
        g.step(60)
        started_at = None
        for i, (cls, fields) in enumerate(RealLogReplayTests.events(name)):
            if cls == "PlanetChangedEvent" and fields.get("NewPlanetName"):
                g.travel(fields["NewPlanetName"], 5)
            elif any(isinstance(v, int) and not -2**63 <= v < 2**63 for v in fields.values()):
                continue                       # a 64-bit handle the Lua bridge cannot carry (unused here)
            else:
                g.fire(cls, **fields)
            g.step(2)
            if started_at is None and g.state.hub is not None and g.state.hub.phase != "pre":
                started_at = (i, cls, dict(fields))
            if started_at:
                break
        g.step(900)
        return g, started_at

    def test_round23_new_game_starts_the_hub_after_the_parade_hands_ratchet_back(self):
        g, at = self.replay("round23_rivet.log")
        self.assertIsNotNone(at)
        # v0.51: not at the wrench (round 23 line 475) but after OBJ_INTRO_GOING_DOWN finished (510)
        events = [e for e in __import__("test_runtime").RealLogReplayTests.events("round23_rivet.log")]
        idx = {(c, f.get("ObjectiveName"), f.get("ObjectiveState")): i for i, (c, f) in reversed(list(enumerate(events)))}
        going_down_done = idx[("ObjectiveStateChangedEvent", "OBJ_INTRO_GOING_DOWN", 2)]
        self.assertGreater(at[0], going_down_done)
        # ... and still during the parade: before the log's first trip off Corson V
        first_trip = min(i for i, (c, f) in enumerate(events) if c == "PlanetChangedEvent" and f.get("NewPlanetName")
                         and i > going_down_done)
        self.assertLess(at[0], first_trip)
        self.assertTrue(hub(g)["started"])
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertEqual(list(g.sim.warps.values())[0], "CHK_NEFCITY_START")
        # the parade checkpoint reached by then is kept (for hub_prologue = "keep")
        self.assertIsNotNone(hub(g).get("parade_hash"))

    def test_round13_save_loads_never_start_it(self):
        g, at = self.replay("round13_rivet.log")
        self.assertIsNone(at)
        self.assertFalse(hub(g).get("started"))


class SettingsFileTests(unittest.TestCase):
    def test_your_settings_file_makes_a_hub_seed(self):
        g = Game(settings_file=True, dll_version=6)
        self.assertEqual(g.load_errors, [])
        self.assertEqual(g.bridge("return rando_seed_mode()"), "random")
        g.bridge('return rando_use_seed("v100-your-04")')
        g.bridge("return rando_set_arsenal(true)")
        self.assertTrue(g.wait_seed())
        s = py(g.seed)
        self.assertTrue(s["settings"]["hub"])
        self.assertEqual(s["settings"]["campaign_mode"], "planet_shuffle")
        self.assertEqual((s["settings"]["raritanium_min"], s["settings"]["raritanium_max"]), (120, 1000))
        self.assertEqual(verify_hub_seed(s), [])
        self.assertTrue(g.log_has("RANDO-KIT all 14 scripts are 10.0.2"))
        self.assertFalse(g.log_has("is from an older kit"))
        c = g.R.config
        self.assertEqual((c.key_hub, c.key_hub_return, c.key_story), ("]", "[", "/"))


if __name__ == "__main__":
    unittest.main()
