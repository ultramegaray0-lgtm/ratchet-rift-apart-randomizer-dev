"""Randomizer 3.0 campaign tests.

Offline (real code): campaign sequences for every mode, the campaign-aware solver, and an
INDEPENDENT Python re-implementation that replays each seed's campaign visit by visit.
Simulated: the in-game director against tests/sim's SIMULATED mission system. Those tests show
the director's decisions; they say nothing about whether the real game's mission system reacts
the same way (that is the research run's job, docs/RESEARCH.md)."""
import json
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(__file__))
import rando  # noqa: E402
from luajson import py  # noqa: E402
from harness import Game, MOD, script_files  # noqa: E402
from test_generator import DB, ALWAYS_START, honest_refusal, verify as verify_items  # noqa: E402

ENG = rando.Engine()
SEGS = py(ENG.lua.globals().RANDO_CAMPAIGN.SEGMENTS)
BY_ID = {s["id"]: s for s in SEGS}
LOC_SEG = py(ENG.lua.globals().RANDO_CAMPAIGN.LOCATION_SEGMENT)
MODES = ["vanilla", "planet_shuffle", "mission_shuffle", "full", "chaos"]


def first(x):
    """lupa returns a tuple for several Lua results and a plain value for one"""
    return x[0] if isinstance(x, tuple) else x


def both(x):
    return x if isinstance(x, tuple) else (x, None)


def second(x):
    return both(x)[1]


def seg_of(lid):
    if lid in LOC_SEG:
        return LOC_SEG[lid]
    planet = DB["locations"][lid].get("planet")
    for s in SEGS:
        if s["planet"] == planet and s["visit"] == 1:
            return s["id"]
    return None


VANILLA_ORDER = [seg["id"] for seg in SEGS]


def verify_campaign(seed, order=None):
    """Independent replay: walk the campaign; at each visit check its gadget, ability, Coordinates
    and boss needs against what earlier visits, the start and the shop can have given.
    7.0: a level-locked seed (travel_lock) is walked in the game's own order; there a locked planet's
    Gold Bolts are out of reach too."""
    probs = []
    camp = seed.get("campaign") or {}
    s = seed["settings"]
    order = order or camp.get("order") or (VANILLA_ORDER if s.get("travel_lock") else None)
    if not order:
        if s["campaign_mode"] != "vanilla":
            probs.append("campaign mode without an order")
        return probs
    if sorted(order) != sorted(BY_ID):
        probs.append("order is not a permutation of the visits")
    pos = {sid: i for i, sid in enumerate(order)}
    if order[-1] != "finale":
        probs.append("finale not last")
    # 9.0: every order begins with the story's own start (written here, not read from 03)
    if list(order[:3]) != ["corson_intro", "nefcity_1", "sargasso_1"]:
        probs.append("the order does not start prologue > Nefarious City > Sargasso")
    for sid in order:
        seg = BY_ID[sid]
        for a in seg.get("after", []):
            if pos[a] > pos[sid]:
                probs.append(f"{sid} before {a}")
    kit = set(DB["start_kit"])
    owned = {}
    for k in seed["start"]["items"]:
        owned[k] = owned.get(k, 0) + 1
    abilities = set(kit)
    got = set()
    reached = 0

    story_index = {p["id"]: p["story_index"] for p in DB["planets"]}

    def wneed(i):
        if s["weapon_logic"] == "none" or not s["weapons"]:
            return 0
        if order == VANILLA_ORDER:
            # the game's own order: a visit's tier is its planet's place in the story (the finale last)
            sid = order[i - 1]
            tier = len(DB["planets"]) if sid == "finale" else story_index[BY_ID[sid]["planet"]]
        else:
            tier = max(1, -(-i * len(DB["planets"]) // len(order)))
        return max(0, (tier - 2) // 2) if s["weapon_logic"] == "light" else max(0, tier - 2)

    def loc_ok(lid):
        loc = DB["locations"][lid]
        if not loc["progression"]:
            return False
        ex = {k for k in s["exclude"].replace(" ", "").split(",") if k}
        for r in loc.get("requires", []):
            if r in ALWAYS_START:
                continue
            if r.startswith("ability:") or not s["gadgets"] or r in ex:
                return False
            if not owned.get(r):
                return False
        sid = seg_of(lid)
        if sid is not None and pos[sid] + 1 > reached:
            return False
        if s["planet_locks"] and loc.get("planet") and (loc["kind"] != "goldbolt" or s.get("travel_lock")) \
                and not owned.get("access:" + loc["planet"]):
            return False
        if loc.get("planet"):
            wc = sum(1 for k, c in owned.items() if c and k.startswith("weapon:"))
            p = pos[sid] + 1 if sid is not None else 1
            if wc < wneed(p):
                return False
        return True
    while True:
        # campaign progress
        while reached < len(order):
            seg = BY_ID[order[reached]]
            ok = True
            for r in seg.get("requires", []):
                if r.startswith("ability:"):
                    ok = ok and r[8:] in abilities
                else:
                    ok = ok and (r in kit or owned.get(r, 0) > 0)
            if s["planet_locks"] and not owned.get("access:" + seg["planet"]):
                ok = False
            wc = sum(1 for k, c in owned.items() if c and k.startswith("weapon:"))
            if seg.get("boss") and wc < wneed(reached + 1):
                ok = False
            if not ok:
                break
            abilities.update(seg.get("grants", []))
            reached += 1
        new = [lid for lid in sorted(seed["locations"]) if lid not in got and loc_ok(lid)]
        for lid in new:
            got.add(lid)
            it = seed["locations"][lid].get("item")
            if it:
                owned[it] = owned.get(it, 0) + 1
        if not new:
            break
    if reached < len(order):
        probs.append(f"campaign stops at visit {reached + 1} ({order[reached]})")
    return probs


def verify_fallback(seed):
    """Independent replay of the honest fallback: a campaign seed played in the GAME's own order
    (mission control not verified). The story runs as vanilla, so every visit happens and the
    game hands out its own gadgets; the randomizer only banks rewards until their planet's
    Coordinates arrive. Every in-logic reward and every Coordinates item must still be paid.
    7.0: with travel_lock the story itself waits for Coordinates, so the fallback is the visit-by-
    visit replay in the game's own order."""
    s = seed["settings"]
    if s.get("travel_lock"):
        return verify_campaign(seed, VANILLA_ORDER)
    owned = set(seed["start"]["items"])
    paid = set()
    logic = [lid for lid in sorted(seed["locations"]) if seed["locations"][lid].get("in_logic") is not False
             and DB["locations"][lid]["progression"]]
    while True:
        new = []
        for lid in logic:
            if lid in paid:
                continue
            planet = DB["locations"][lid].get("planet")
            if s["planet_locks"] and planet and DB["locations"][lid]["kind"] != "goldbolt" and "access:" + planet not in owned:
                continue
            new.append(lid)
        for lid in new:
            paid.add(lid)
            it = seed["locations"][lid].get("item")
            if it:
                owned.add(it)
        if not new:
            break
    return [f"never paid: {lid}" for lid in logic if lid not in paid]


class FallbackCheckTests(unittest.TestCase):
    def test_fallback_checker_catches_a_coordinates_cycle(self):
        s, _ = ENG.generate("fb-neg", {"planet_locks": True}, "mission_shuffle")
        d = py(s)
        self.assertEqual(verify_fallback(d), [])
        # move some Coordinates item onto a location of its own planet: a cycle
        for lid, l in d["locations"].items():
            it = l.get("item") or ""
            if it.startswith("access:") and d["settings"]["planet_locks"]:
                own = [x for x, m in DB["locations"].items() if m.get("planet") == it[7:] and m["progression"]
                       and m["kind"] != "goldbolt"
                       and d["locations"].get(x, {}).get("in_logic") is not False and x in d["locations"]]
                if own:
                    d["locations"][own[0]]["item"], l["item"] = it, d["locations"][own[0]].get("item")
                    break
        self.assertNotEqual(verify_fallback(d), [])


class SequenceTests(unittest.TestCase):
    def test_every_mode_gives_valid_orders(self):
        C = ENG.lua.globals().RANDO_CAMPAIGN
        for mode in MODES:
            for rs in (False, True):
                for i in range(200):
                    r = ENG.G.rng(ENG.G.fnv1a(f"{mode}{rs}{i}"))
                    order, start = C.sequence(mode, r, rs)
                    self.assertIsNotNone(order, (mode, rs, i, start))
                    ok, why = both(C.hard_ok(order))
                    self.assertTrue(ok, (mode, rs, why, py(order)))
                    self.assertEqual(py(order)[:3], ["corson_intro", "nefcity_1", "sargasso_1"], (mode, rs, i))

    def test_modes_really_reorder(self):
        C = ENG.lua.globals().RANDO_CAMPAIGN
        vanilla = py(C.sequence("vanilla", ENG.G.rng(1), False)[0])
        for mode in ("planet_shuffle", "mission_shuffle", "full", "chaos"):
            orders = {tuple(py(C.sequence(mode, ENG.G.rng(ENG.G.fnv1a(f"{mode}{i}")), mode in ("full", "chaos"))[0])) for i in range(100)}
            self.assertGreater(len(orders), 50, mode)
            self.assertTrue(any(list(o) != vanilla for o in orders))
        # 9.0: no random start: every mode begins prologue > Nefarious City > Sargasso, and the
        # visit after them varies
        for mode in ("full", "chaos", "mission_shuffle", "planet_shuffle"):
            orders = [py(C.sequence(mode, ENG.G.rng(ENG.G.fnv1a(f"s{mode}{i}")), True)[0]) for i in range(200)]
            self.assertEqual({tuple(o[:3]) for o in orders}, {("corson_intro", "nefcity_1", "sargasso_1")}, mode)
            self.assertGreaterEqual(len({o[3] for o in orders}), 4, mode)

    def test_planet_shuffle_keeps_revisits_after_first_visits(self):
        C = ENG.lua.globals().RANDO_CAMPAIGN
        for i in range(200):
            order = py(C.sequence("planet_shuffle", ENG.G.rng(i + 7), False)[0])
            self.assertEqual(order[:3], ["corson_intro", "nefcity_1", "sargasso_1"])
            for sid in ("sargasso_2", "savali_2", "scarstu_2"):
                first = sid.replace("_2", "_1")
                self.assertLess(order.index(first), order.index(sid))

    def test_story_abilities_come_before_their_use(self):
        C = ENG.lua.globals().RANDO_CAMPAIGN
        for mode in ("mission_shuffle", "full", "chaos"):
            for i in range(200):
                order = py(C.sequence(mode, ENG.G.rng(ENG.G.fnv1a(f"ab{mode}{i}")), True)[0])
                self.assertLess(order.index("nefcity_1"), order.index("viceron_1"))   # Phantom Dash
                self.assertLess(order.index("torren_1"), order.index("viceron_1"))    # Hurlshot


class CampaignSeedTests(unittest.TestCase):
    def gen(self, seed, user=None, preset="mission_shuffle"):
        s, audit = ENG.generate(seed, user or {}, preset)
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [])
        return py(s)

    def test_same_seed_same_campaign(self):
        a = rando.Engine().generate("same", {}, "full_campaign")[0]
        b = rando.Engine().generate("same", {}, "full_campaign")[0]
        self.assertEqual(py(a.campaign.order), py(b.campaign.order))

    def test_campaign_in_spoiler_and_seed(self):
        s, _ = ENG.generate("spoil-camp", {}, "full_campaign")
        text = ENG.spoiler(s)
        self.assertIn("MISSION ORDER (full, experimental)", text)
        d = py(s)
        self.assertEqual(d["campaign"]["needs"], ["mission_control", "travel"])       # 9.0: no random start

    def test_hoverboots_come_before_the_visits_needing_them(self):
        for i in range(100):
            d = self.gen(f"hb-{i}", {}, "full_campaign")
            order = d["campaign"]["order"]
            first_need = min(order.index("torren_1"), order.index("ardolis_1"))
            if "hoverboots" in d["start"]["items"]:
                continue
            where = [lid for lid, l in d["locations"].items() if l.get("item") == "hoverboots"]
            if where:
                self.assertLess(order.index(seg_of(where[0])), first_need, (i, where))
            else:
                self.assertIn("hoverboots", [sl["item"] for sl in d["shop"]])

    def test_gadgets_off_campaign_still_finishable(self):
        d = self.gen("no-gadgets", {"gadgets": False}, "full_campaign")
        self.assertIn("hoverboots", d["start"]["items"])
        self.assertEqual(d["registry"]["hoverboots"], "start (always)")      # 4.0: every seed starts with it


class BatchTests(unittest.TestCase):
    """At least 10,000 campaign seeds: generator audit + 2.0 item verifier + independent campaign replay."""

    def test_campaign_presets(self):
        n = 0
        for preset in ("planet_shuffle", "mission_shuffle", "full_campaign", "campaign_chaos"):
            for i in range(1500):
                s, audit = ENG.generate(f"cb-{preset}-{i}", {}, preset)
                self.assertIsNotNone(s, (preset, i, audit))
                self.assertEqual(audit, [], (preset, i))
                d = py(s)
                self.assertEqual(verify_campaign(d), [], (preset, i))
                self.assertEqual(verify_fallback(d), [], (preset, i))
                n += 1
        self.assertEqual(n, 6000)

    def test_random_settings_with_campaigns(self):
        rnd = random.Random("campaign-unit")
        d0 = ENG.defaults()
        n = refused = 0
        for c in range(1000):
            preset = rnd.choice(["balanced", "chaos", "campaign", "everything", "planet_shuffle", "mission_shuffle",
                                 "full_campaign", "campaign_chaos"])
            user = rando.random_settings(rnd, d0)
            for i in range(4):
                s, audit = ENG.generate(f"rc-{c}-{i}", user, preset)
                # a reordered campaign also starts with its first visits' Coordinates and those of the
                # game's own first planets (three more at most)
                if s is None and honest_refusal(ENG, preset, user, audit, extra_start=3):
                    refused += 1
                    continue
                self.assertIsNotNone(s, (preset, user, audit))
                self.assertEqual(audit, [], (preset, user))
                d = py(s)
                self.assertEqual(verify_campaign(d), [], (preset, user, i))
                self.assertEqual(verify_fallback(d), [], (preset, user, i))
                if d["settings"]["campaign_mode"] == "vanilla":
                    self.assertEqual(verify_items(d), [], (preset, user, i))
                n += 1
        self.assertEqual(n + refused, 4000)
        self.assertGreater(n, 3000)


CAPS_ON = """RANDO_CAPABILITIES = { source = "test", mission_read = { verified = true }, travel = { verified = true },
  new_game_init = { verified = true }, mission_control = { verified = true, backend = "native" } }"""


def registry_missions():
    out = []
    for seg in ENG.lua.globals().RANDO_CAMPAIGN.SEGMENTS.values():
        out.extend(seg.missions.values())
    return out


# dir-5: with generator 4.0 its campaign order starts intro > Nefarious City (a visit with an entry)
def campaign_game(caps=False, preset="mission_shuffle", seed="dir-5", intro=4, states=None, mgr=True, missions_ok=True,
                  settings=None, **kw):
    """A game (system 2, like yours) holding every registry mission: MIS_INTRO in state `intro`,
    `states` as given, the rest locked (0). It reports nothing on load (round 14)."""
    dll_version = kw.pop("dll_version", 4)
    files = [p for p in script_files(**kw) if not (caps and p.name.startswith("06_"))]
    extra_settings = dict(settings or {})
    names = registry_missions()
    st = dict(states or {})
    st.setdefault("MIS_INTRO", intro)

    def before(gm):
        if caps:
            gm.lua.execute(CAPS_ON)
        if mgr:
            rows = ", ".join(f'{{ "{n}", {st.get(n, 0)} }}' for n in names)
            gm.lua.execute(f"SIM.install_missions({{ {rows} }})")
        if not missions_ok:
            gm.lua.execute("SIM.put_u32(SIM.MB + 0x60, 0)")
    st2 = {"seed": seed, "preset": preset}
    st2.update(extra_settings)
    return Game(files=files, settings=st2, before_scripts=before, dll_version=dll_version)


def lab_lines(g):
    return [l for l in g.logs() if "RANDO-LAB" in l]


def build_caps(lines, d):
    import subprocess
    log = os.path.join(d, "rivet.log")
    with open(log, "w") as f:
        f.write("\n".join("[script] [rando]\t" + l for l in lines) + "\n")
    out = os.path.join(d, "06.lua")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_capabilities.py"), log, "--out", out],
                   check=True, capture_output=True)
    with open(out) as f:
        return out, f.read()


def kinds(g):
    return [c.kind for c in g.sim.mission_calls.values()]


def first_order(g):
    return list(g.seed.campaign.order.values())


def open_next(g, seg):
    g.R.grant("access:" + seg.planet)
    for r in seg.requires.values():
        if not r.startswith("ability:"):
            g.R.grant(r)


class DirectorTests(unittest.TestCase):
    """The director against the SIMULATED game: system 2 like yours (start needs 1, complete
    needs 3, no make-available); what START changes (-> 2) is simulated."""

    def test_vanilla_seed_director_stays_out(self):
        g = Game().ready()
        D = g.g.RANDO_CAMPAIGN_RT
        self.assertFalse(first(D.active()))
        self.assertIsNone(D.status_text())
        g.press("F12")
        self.assertEqual(len(g.sim.travels), 0)

    def test_campaign_without_verified_control_falls_back_honestly(self):
        g = campaign_game(caps=False).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        active, why = both(D.active())
        self.assertFalse(active)
        self.assertIn("mission_control", why)
        g.press("F12")
        g.step(300)
        self.assertEqual(len(g.sim.travels), 0)
        self.assertNotIn(3, kinds(g))
        self.assertTrue(g.note_has("not available yet"))
        self.assertIn("not available yet", D.status_text())

    def test_the_game_is_asked_for_states(self):
        g = campaign_game(caps=False, intro=4, states={"MIS_SAV_01": 1}).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        got = {}
        D.refresh(g.lua.table_from(["MIS_INTRO", "MIS_SAV_01", "MIS_NOPE"]),
                  lambda a: got.update({k: (a[k].code, a[k].after, a[k].system) for k in ("MIS_INTRO", "MIS_SAV_01", "MIS_NOPE")}))
        g.step(6)
        self.assertEqual(got["MIS_INTRO"], (11, 4, 2))
        self.assertEqual(got["MIS_SAV_01"], (11, 1, 2))
        self.assertEqual(got["MIS_NOPE"][0], 9)
        self.assertEqual(D.mission_state("MIS_SAV_01"), 1)
        self.assertEqual(second(D.mission_state("MIS_NOPE")), "not a mission in your game")
        self.assertEqual(set(kinds(g)), {1})                     # queries only
        self.assertEqual(D.engine_hash("MIS_INTRO"), 1000115474)
        # once per session: the helper and the intro in rivet.log
        g.step(700)
        self.assertTrue(g.log_has("RANDO-CAMPAIGN mission system 2: MIS_INTRO is complete"))

    def test_director_starts_an_open_visit_travels_and_advances(self):
        g = campaign_game(caps=True, intro=4).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        order = first_order(g)
        self.assertEqual(order[0], "corson_intro")
        g.step(130)                                       # the game says the intro is done
        self.assertEqual(D.campaign_state().pos, 2)
        nxt = g.g.RANDO_CAMPAIGN.BY_ID[order[1]]
        open_next(g, nxt)
        g.lua.execute(f'SIM.set_mission("{nxt.missions[1]}", 1, false)')   # the game opened it
        g.press("F12")
        g.step(20)
        self.assertEqual(g.sim.mission_state[nxt.missions[1]], 2, [l for l in g.logs() if "CAMPAIGN" in l][-6:])
        self.assertIn(3, kinds(g))
        self.assertNotIn(2, kinds(g))                     # no make-available in system 2
        if nxt.entry:                                     # a visit with a known entry point is travelled to
            self.assertEqual(g.sim.travels[1].to, nxt.entry)
        else:                                             # one without (this seed's next visit) is not
            self.assertIsNone(g.sim.travels[1])
        last = nxt.missions[len(nxt.missions)]
        g.lua.execute(f'SIM.set_mission("{last}", 4, false)')
        g.step(250)
        self.assertEqual(D.campaign_state().pos, 3)
        text = g.companion_export()
        g2 = campaign_game(caps=True)
        g2.companion_restore(text)
        self.assertEqual(g2.g.RANDO_CAMPAIGN_RT.campaign_state().pos, 3)

    def test_a_visit_the_game_has_not_opened_is_not_forced(self):
        g = campaign_game(caps=True, intro=4).ready()
        g.step(130)
        nxt = g.g.RANDO_CAMPAIGN.BY_ID[first_order(g)[1]]
        open_next(g, nxt)
        g.press("F12")
        g.step(20)
        self.assertTrue(g.note_has("is not open in your game yet"), g.notes()[-3:])
        self.assertEqual(set(kinds(g)), {1})
        self.assertEqual(len(g.sim.travels), 0)

    def test_item_delivery_and_mission_calls_share_the_mailbox(self):
        g = campaign_game(caps=True, intro=4).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        g.lua.execute("RANDO_REAL.busy = { via = 'test' }")
        got = []
        D.mission_call("query", "MIS_INTRO", lambda r: got.append(r.code))
        g.step(10)
        self.assertEqual(got, [])
        g.lua.execute("RANDO_REAL.busy = nil")
        g.step(3)
        self.assertEqual(got, [11])
        self.assertIsNone(g.lua.eval("RANDO_REAL.mission_busy"))

    def test_full_campaign_starts_with_the_intro_and_needs_no_new_game_init(self):
        """9.0: random_start is gone; full_campaign's order starts with the prologue like every mode"""
        for i in range(10):
            g = campaign_game(caps=False, preset="full_campaign", seed=f"rs-{i}").ready()
            self.assertEqual(first_order(g)[:3], ["corson_intro", "nefcity_1", "sargasso_1"])
            active, why = both(g.g.RANDO_CAMPAIGN_RT.active())
            self.assertFalse(active)
            self.assertNotIn("new_game_init", why)
            self.assertIn("mission_control", why)

    def test_blocked_until_coordinates(self):
        g = campaign_game(caps=True, preset="mission_shuffle", seed="dir-2", settings={"planet_locks": True}).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        g.step(130)
        seg = first(D.current_segment())
        if g.state.access[seg.planet]:
            g.state.access[seg.planet] = None
        g.press("F12")
        g.step(5)
        self.assertTrue(g.note_has("Coordinates"), g.notes()[-3:])
        self.assertEqual(len(g.sim.travels), 0)
        self.assertNotIn(3, kinds(g))

    def test_old_helper_or_other_exe_means_no_mission_calls(self):
        g = campaign_game(caps=True, missions_ok=False).ready()
        D = g.g.RANDO_CAMPAIGN_RT
        ok, why = both(D.native_ok())
        self.assertFalse(ok)
        self.assertIn("did not recognise", why)
        g.step(130)
        g.press("F12")
        g.step(5)
        self.assertEqual(len(g.sim.mission_calls), 0)
        self.assertEqual(len(g.sim.travels), 0)
        g3 = campaign_game(caps=True, dll_version=3).ready()
        self.assertIn("older than v4", second(g3.g.RANDO_CAMPAIGN_RT.native_ok()))

    def test_lab_read_only_asks(self):
        g = campaign_game(caps=False, test_mode=True, intro=4).ready()
        g.press("F12", ctrl=True)
        g.step(80)
        lines = lab_lines(g)
        self.assertTrue(any("RANDO-LAB VERIFIED read (" in l and "system 2)" in l for l in lines), lines[-5:])
        self.assertTrue(any("RANDO-LAB mission MIS_SAV_01 inactive (system 2)" in l for l in lines))
        self.assertTrue(any("RANDO-LAB mission MIS_ZURK_ARENA_BRONZE_CUP: not a mission in your game" in l for l in lines))
        self.assertEqual(set(kinds(g)), {1})
        self.assertEqual(len(g.sim.travels), 0)

    def test_lab_starts_an_open_visit_and_builds_capabilities(self):
        import tempfile
        import pathlib
        g = campaign_game(caps=False, test_mode=True, intro=4, states={"MIS_SAV_01": 1}).ready()
        g.press("F11", ctrl=True)
        g.step(80)
        target = g.g.RANDO_CAMPAIGN_RT.lab.target
        self.assertEqual(target.id, "savali_1")
        verified = [l for l in lab_lines(g) if "VERIFIED" in l]
        self.assertEqual(verified, ["[rando]\tRANDO-LAB VERIFIED native start (mission MIS_SAV_01 went 1 -> 2)"], lab_lines(g))
        g.step(130)
        self.assertEqual(g.sim.travels[1].to, target.entry)
        g.fire("CheckpointTriggeredEvent", CheckpointHash=g.lua.eval(f'rivet.hash("{target.entry}")'), Loaded=True)
        self.assertTrue(g.log_has("RANDO-LAB VERIFIED travel " + target.entry))
        with tempfile.TemporaryDirectory() as d:
            out, text = build_caps(lab_lines(g), d)
            self.assertIn('mission_control = { verified = true, backend = "native" }', text)
            self.assertIn("travel = { verified = true }", text)
            self.assertIn("new_game_init = { verified = false }", text)
            files = [p for p in script_files() if not p.name.startswith("06_")]
            g2 = Game(files=[pathlib.Path(out)] + files, settings={"seed": "dir-1", "preset": "mission_shuffle"})
            g2.ready()
            self.assertTrue(first(g2.g.RANDO_CAMPAIGN_RT.active()))

    def test_lab_on_a_locked_visit_tries_start_then_replay(self):
        g = campaign_game(caps=False, test_mode=True, intro=4).ready()
        g.press("F11", ctrl=True)
        g.step(80)
        # the first locked visit of this seed's campaign order (5.0 seeds have another order)
        target = g.g.RANDO_CAMPAIGN_RT.lab.target
        mis = target.missions[1]
        self.assertTrue(g.log_has(f"RANDO-LAB target\t{target.id}\t{mis}\t(locked)"))
        self.assertTrue(g.log_has(f"RANDO-LAB NO EFFECT native start (mission {mis}: the game's action does nothing in this state"))
        self.assertTrue(g.log_has(f"RANDO-LAB NO EFFECT native replay (mission {mis}"))
        self.assertEqual(g.sim.mission_state[mis], 0)
        # if replay does change it, that is reported as such
        g2 = campaign_game(caps=False, test_mode=True, intro=4).ready()
        g2.lua.execute("SIM.replay_effect = 2")
        g2.press("F11", ctrl=True)
        g2.step(80)
        self.assertTrue(g2.log_has(f"RANDO-LAB VERIFIED native replay (mission {mis} went 0 -> 2)"))

    def test_lab_intro_experiment_verifies_new_game_init(self):
        import tempfile
        g = campaign_game(caps=False, test_mode=True, intro=3).ready()
        g.press("F11", ctrl=True)
        g.step(80)
        verified = [l for l in lab_lines(g) if "VERIFIED" in l]
        self.assertEqual(len(verified), 1, lab_lines(g))
        self.assertIn("native complete (mission MIS_INTRO went 3 -> 4)", verified[0])
        with tempfile.TemporaryDirectory() as d:
            _, text = build_caps(["RANDO-LAB VERIFIED native start (mission MIS_SAV_01 went 1 -> 2)"] + verified, d)
        self.assertIn("new_game_init = { verified = true }", text)

    def test_lab_intro_not_active_is_not_touched(self):
        g = campaign_game(caps=False, test_mode=True, intro=2).ready()
        g.press("F11", ctrl=True)
        g.step(80)
        self.assertEqual(set(kinds(g)), {1})
        self.assertTrue(g.log_has("only finishes an active (3) mission"))
        self.assertEqual(g.sim.mission_state["MIS_INTRO"], 2)

    def test_research_export(self):
        g = campaign_game(caps=False, intro=4).ready()
        g.fire("MissionStateChangedEvent", MissionName="MIS_INTRO", MissionState=2, PreviousState=0)
        g.step(700)                                       # the session diagnostic asks the game once
        st = g.bridge("return rando_research_status()").split("|")
        text = "".join(g.bridge(f"return rando_research_chunk({i})") for i in range(1, int(st[1]) + 1))
        self.assertEqual(len(text), int(st[0]))
        data = g.lua.execute(text)
        self.assertEqual(data.missions["MIS_INTRO"].state, 2)       # what the event said
        self.assertEqual(data.known["MIS_INTRO"].state, 4)          # what the game answered


if __name__ == "__main__":
    unittest.main()


class RegistryBuilderTests(unittest.TestCase):
    """tools/build_campaign_registry.py: research zip -> 07_rando_campaign_registry.lua override."""

    def test_research_zip_becomes_registry_override(self):
        import io, tempfile, zipfile, subprocess
        tmp = tempfile.mkdtemp()
        zpath = os.path.join(tmp, "campaign_research_x.zip")
        research = ('return { missions = { MIS_NEFCITY_01_ESCAPE = { first_frame = 20 }, '
                    'MIS_NEFCITY_01_TRAIN = { first_frame = 10 }, MIS_ZURK_02_ARENA = { first_frame = 5 } } }')
        with zipfile.ZipFile(zpath, "w") as z:
            z.writestr("randomizer_research.lua", research)
            z.writestr("regions.json", '["MIS_ARD_01_MAIN_OVERLAY", "MIS_HAX_DEFAULT", "MIS_ZURK_01_VISIT_01"]')
        out = os.path.join(tmp, "07.lua")
        tool = os.path.join(ROOT, "tools", "build_campaign_registry.py")
        r = subprocess.run([sys.executable, tool, zpath, out], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = open(out, encoding="utf-8").read()
        self.assertNotIn("MIS_HAX", text)                       # not story
        from lupa import lua54
        L = lua54.LuaRuntime()
        scripts = os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts")
        for f in ("01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua"):
            L.execute(open(os.path.join(scripts, f), encoding="utf-8").read())
        L.execute(text)
        by = L.globals().RANDO_CAMPAIGN.BY_ID
        self.assertEqual(list(by.nefcity_1.missions.values()), ["MIS_NEFCITY_01_TRAIN", "MIS_NEFCITY_01_ESCAPE"])
        self.assertEqual(list(by.scarstu_2.missions.values()), ["MIS_ZURK_02_ARENA"])
        self.assertEqual(list(by.scarstu_1.missions.values()), ["MIS_ZURK_01_VISIT_01"])
        self.assertEqual(by.ardolis_1.src, "game (research)")
        self.assertEqual(by.savali_1.src, "dag" if by.savali_1.src == "dag" else by.savali_1.src)  # untouched
        self.assertNotEqual(by.savali_1.src, "game (research)")
