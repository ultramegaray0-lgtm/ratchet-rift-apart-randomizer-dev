"""Dev 10.11 (kit 10.0.7, generator 10.11.0), asked for: "make sure planet shuffle actually works:
when the player gets new Coordinates and goes to a new planet, take them to the new planet's intro
so the player starts the first mission on that planet. Also make sure players get to Coordinates or
first visits first, not revisits."

Generator (re-checked here by an independent Python reading of the registry, not 03's functions):
  * no Coordinates and no gadget a location needs on a revisit (a planet's second visit) or the finale;
  * a planet's Coordinates only where its first visit can be played the moment they are found
    (every visit it waits for is done there: Viceron's are a reward of Torren IV's story);
  * the audit catches a seed that breaks either rule; coords_first_visit = false is 10.1's freedom.
Runtime (the real scripts against tests/sim/rivet_sim.lua, which is NOT the game):
  * between stories the next visit of every open planet is made active (no travel, no hero swap),
    never one on the planet you are on and never while a story runs;
  * a planet-menu landing whose story was active before the flight is left to the game's own arrival
    (nothing loaded); one started on landing loads the visit's intro (Blizar: the destroyed pad);
  * a planet whose first visit waits for another visit (Viceron) sends you back with the reason and is
    never a revisit; ] lists first visits before revisits;
  * the game's own story travel to a planet whose first visit is open is played there.
"""
import collections
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rando  # noqa: E402
from luajson import py  # noqa: E402
from test_v100 import hub_game, to_hub, hub, choose, menu_ids  # noqa: E402

ENG = rando.Engine()
DB = py(ENG.lua.globals().RANDO_DATA)
CAMP = ENG.lua.globals().RANDO_CAMPAIGN
LOCATION_SEGMENT = py(CAMP.LOCATION_SEGMENT)
SEGMENTS = {s["id"]: s for s in py(CAMP.SEGMENTS)}
# written down here from the registry's meaning, not read from 03's new functions
REVISITS = {"scarstu_2", "sargasso_2", "savali_2", "finale"}
PAYS_ON_FINISH = {"planet", "story", "side"}
ALWAYS = {"hoverboots", "map_o_matic"}
USER_04 = {"distribution": "goldbolts_first", "include_arsenal_restored": False}


def segment_of(lid):
    if lid in LOCATION_SEGMENT:
        return LOCATION_SEGMENT[lid]
    planet = DB["locations"][lid].get("planet")
    for seg in SEGMENTS.values():
        if seg["planet"] == planet and seg["visit"] == 1:
            return seg["id"]
    return None


def must_be_done(seg_id):
    """every visit that has to be finished before seg_id can be played (independent closure)"""
    out, todo = set(), [seg_id]
    while todo:
        seg = SEGMENTS[todo.pop()]
        direct = list(seg.get("after") or [])
        for r in seg.get("requires") or []:
            if r.startswith("ability:"):
                ab = r[len("ability:"):]
                direct += [x["id"] for x in SEGMENTS.values() if ab in (x.get("grants") or [])]
        if seg.get("kind") == "finale":
            direct += [x for x in SEGMENTS if x != seg["id"]]
        for x in direct:
            if x not in out:
                out.add(x)
                todo.append(x)
    return out


def done_when_found(lid):
    seg = segment_of(lid)
    done = must_be_done(seg)
    if DB["locations"][lid]["kind"] in PAYS_ON_FINISH:
        done.add(seg)
    if seg not in ("nefcity_1", "corson_intro"):
        done.add("nefcity_1")          # the hub's own story is played first (the ship is off meanwhile)
    return done


def first_visit(planet):
    return min((s for s in SEGMENTS.values() if s["planet"] == planet), key=lambda s: s["visit"])


def gating_gadgets():
    g = set()
    for loc in DB["locations"].values():
        for r in loc.get("requires") or []:
            if r in DB["items"] and DB["items"][r].get("category") == "gadget" and r not in ALWAYS:
                g.add(r)
    return g


def check_seed(d):
    """the two rules, independently; returns a list of problems"""
    bad = []
    gating = gating_gadgets()
    exc = set((d["hub"] or {}).get("coords_exceptions") or [])
    for lid, l in d["locations"].items():
        key = l.get("item")
        it = DB["items"].get(key) if key else None
        if not it or key in exc:
            continue
        seg = segment_of(lid)
        if it["category"] == "coordinates" or key in gating:
            if seg in REVISITS:
                bad.append(f"{key} on the revisit {seg} ({lid})")
        if it["category"] == "coordinates":
            first = first_visit(it["planet"])
            missing = must_be_done(first["id"]) - done_when_found(lid)
            if missing:
                bad.append(f"{key} at {lid}: {first['id']} still waits for {sorted(missing)}")
    return bad


class GeneratorRuleTests(unittest.TestCase):
    def seeds(self, prefix, n, settings=None):
        for i in range(n):
            s, audit = ENG.generate(f"{prefix}-{i}", settings or {})
            self.assertIsNotNone(s, audit)
            self.assertEqual(audit, [], (prefix, i))
            yield py(s)

    def test_coordinates_open_a_first_visit_spread(self):
        where = collections.Counter()
        for d in self.seeds("v1011-spread", 120):
            self.assertEqual(check_seed(d), [])
            self.assertFalse(d["hub"]["coords_exceptions"])
            self.assertTrue(d["hub"]["coords_first_visit"])
            for lid, l in d["locations"].items():
                if l.get("item") == "access:viceron":
                    where[segment_of(lid)] += 1
        self.assertEqual(set(where), {"torren_1"}, where)       # Viceron after Torren IV's story

    def test_coordinates_open_a_first_visit_with_your_settings(self):
        for d in self.seeds("v1011-user", 120, USER_04):
            self.assertEqual(check_seed(d), [])

    def test_fewer_locations_still_keep_the_rule(self):
        for st in ({"story_milestones": False, "side_locations": False},
                   {"story_milestones": False, "side_locations": False, "distribution": "goldbolts_first"},
                   {"exclude": "access:torren_iv"}, {"weapon_logic": "standard"}, {"collectibles": False}):
            for d in self.seeds("v1011-few-%d" % len(st), 40, st):
                self.assertEqual(check_seed(d), [], st)
                self.assertFalse(d["hub"]["coords_exceptions"], st)

    def test_revisits_hold_no_progression_but_still_rewards(self):
        kinds = collections.Counter()
        for d in self.seeds("v1011-rev", 60):
            for lid, l in d["locations"].items():
                if segment_of(lid) in ("scarstu_2", "sargasso_2", "savali_2") and l.get("item") in DB["items"]:
                    kinds[DB["items"][l["item"]]["category"]] += 1
        self.assertNotIn("coordinates", kinds)
        self.assertGreater(sum(kinds.values()), 0, kinds)          # weapons, armor... still go there

    def test_audit_catches_both_rules(self):
        s, audit = ENG.generate("v1011-audit", {})
        self.assertEqual(audit, [])
        vic = [lid for lid, l in py(s.locations).items() if l.get("item") == "access:viceron"][0]
        # a Gold Bolt on Savali: found while Savali's visit is played, Torren IV maybe never done
        other = [lid for lid in py(s.locations) if lid.startswith("goldbolt:") and DB["locations"][lid]["planet"] == "savali"][0]
        a, b = s.locations[vic].item, s.locations[other].item
        s.locations[vic].item, s.locations[other].item = b, a
        problems = list(py(ENG.G.audit(s)) or [])
        self.assertTrue(any("access:viceron" in p and "torren_1" in p for p in problems), problems)
        # Coordinates on a revisit
        s2, _ = ENG.generate("v1011-audit-2", {})
        rev = "story2:savali"
        coords = [lid for lid, l in py(s2.locations).items() if (l.get("item") or "").startswith("access:") and l.get("item") != "access:viceron"][0]
        a, b = s2.locations[coords].item, s2.locations[rev].item
        s2.locations[coords].item, s2.locations[rev].item = b, a
        problems = list(py(ENG.G.audit(s2)) or [])
        self.assertTrue(any("savali_2 is a revisit" in p for p in problems), problems)

    def test_the_rule_can_be_switched_off(self):
        segs = collections.Counter()
        for d in self.seeds("v1011-off", 60, {"coords_first_visit": False}):
            self.assertFalse(d["hub"]["coords_first_visit"])
            for lid, l in d["locations"].items():
                if l.get("item") == "access:viceron":
                    segs[segment_of(lid)] += 1
        self.assertGreater(len(segs), 1, segs)                      # 10.1's freedom

    def test_spoiler_says_so(self):
        s, _ = ENG.generate("v1011-spoiler", {})
        text = ENG.spoiler(s)
        self.assertIn("Coordinates always open a first visit", text)
        self.assertIn("starts its first", text)

    def test_registry_intros(self):
        self.assertEqual(SEGMENTS["blizar_1"]["intros"][0], "CHK_BLIZAR_B_LANDINGPAD_DESTROYED")   # round 17 menu
        self.assertEqual(SEGMENTS["savali_1"]["intros"][0], "CHK_SAV_01_LANDING")                 # round 17 menu
        self.assertEqual(SEGMENTS["scarstu_1"]["intros"][0], "CHK_ZURK_00_DEFAULT")               # rounds 14/16/23
        self.assertEqual(py(CAMP.OPENINGS)["sargasso_1"]["hash"], 2498464355)                     # rounds 16/23
        s, _ = ENG.generate("v1011-plan", {})
        plan = {d["id"]: d for d in py(s.hub.destinations)}
        self.assertEqual(plan["torren_1"]["intros"], ["CHK_MOL_START"])


def city_done(seed, settings=None, grant=()):
    """at the hub with the city's story finished and the game's own trip to Sargasso undone"""
    st = {"hub_follow_new": False}
    st.update(settings or {})
    g = to_hub(hub_game(seed, st))
    g.sim.complete_mission("MIS_NEFCITY_01")
    g.step(3000)
    assert "nefcity_1" in hub(g)["done"], hub(g)
    assert g.sim.planet == "NefCity", g.sim.planet
    for k in grant:
        g.R.grant(k)
    g.step(600)
    return g


class PrimeTests(unittest.TestCase):
    def test_coordinates_make_the_next_visit_active_without_travel(self):
        g = city_done("v1011-prime")
        warps = len(py(g.sim.warps))
        heroes = len(py(g.sim.heroes))
        g.R.grant("access:savali")
        g.step(30)
        self.assertNotEqual(g.sim.get_mission("MIS_SAV_01"), 2)    # not at once: after the scene settles
        g.step(600)
        self.assertEqual(g.sim.get_mission("MIS_SAV_01"), 2)
        self.assertEqual(len(py(g.sim.warps)), warps)
        self.assertEqual(len(py(g.sim.heroes)), heroes)
        self.assertTrue(g.log_has("prime\tsavali_1: start\tMIS_SAV_01"))
        self.assertTrue(g.note_has("Savali is open"))
        self.assertIsNone(hub(g).get("current"))

    def test_nothing_is_made_active_while_a_story_runs(self):
        g = to_hub(hub_game("v1011-running"))              # the city's story runs
        g.R.grant("access:savali")
        g.step(1200)
        self.assertNotEqual(g.sim.get_mission("MIS_SAV_01"), 2)
        self.assertFalse(g.log_has("prime\tsavali_1"))

    def test_never_a_visit_of_the_planet_you_are_on(self):
        g = city_done("v1011-here", grant=("access:savali",))
        H = g.g.RANDO_HUB
        g.lua.execute('RANDO.state.current_planet = "savali"')
        ids = [py(d)["id"] for d in py(H.prime_candidates())]
        self.assertNotIn("savali_1", ids)

    def test_switch_off(self):
        g = city_done("v1011-off", {"hub_prime_open": False}, grant=("access:savali",))
        self.assertNotEqual(g.sim.get_mission("MIS_SAV_01"), 2)


class ArrivalTests(unittest.TestCase):
    def test_a_primed_visit_plays_the_games_own_arrival(self):
        g = city_done("v1011-arrive", grant=("access:savali",))
        self.assertEqual(g.sim.get_mission("MIS_SAV_01"), 2)
        warps = len(py(g.sim.warps))
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING", InterplanetaryCheckpointName="CHK_TRANSITION_TO_SAVALI")
        g.travel("Savali")
        g.step(900)
        self.assertEqual(g.sim.planet, "Savali")
        self.assertEqual(hub(g)["current"], "savali_1")
        self.assertEqual(len(py(g.sim.warps)), warps)             # nothing loaded again
        self.assertTrue(g.log_has("was active before the landing"))

    def test_a_visit_started_on_landing_loads_its_intro(self):
        g = city_done("v1011-intro", {"hub_prime_open": False}, grant=("access:blizar_prime",))
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_BLIZAR_A_LANDINGPAD", InterplanetaryCheckpointName="CHK_TRANSITION_TO_BLIZAR")
        g.travel("Blizar")
        g.step(1500)
        self.assertEqual(g.sim.get_mission("MIS_BLIZAR"), 2)
        self.assertEqual(py(g.sim.warps)[-1], "CHK_BLIZAR_B_LANDINGPAD_DESTROYED")   # the first visit's intro
        self.assertEqual(hub(g)["current"], "blizar_1")

    def test_hub_launch_goes_to_the_intro(self):
        g = city_done("v1011-launch", grant=("access:savali",))
        choose(g, "savali_1", frames=900)
        self.assertEqual(g.sim.planet, "Savali")
        self.assertEqual(py(g.sim.warps)[-1], "CHK_SAV_01_LANDING")
        self.assertTrue(g.log_has("(its intro)"))

    def test_a_stuck_first_step_is_loaded_at_the_intro(self):
        g = city_done("v1011-stuck", grant=("access:savali",))
        t = g.lua.table_from
        g.sim.go_to["MIS_SAV_01"] = t({"o": "OBJ_SAV_GO_TO_SAVALI", "planet": "Savali", "hero": "rivet"})  # never finishes
        g.fire("ObjectiveStateChangedEvent", MissionName="MIS_SAV_01", ObjectiveName="OBJ_SAV_GO_TO_SAVALI", ObjectiveState=1)
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING", InterplanetaryCheckpointName="CHK_TRANSITION_TO_SAVALI")
        g.travel("Savali")
        g.step(g.g.RANDO_HUB.INTRO_STUCK_WAIT + 600)
        self.assertIn("CHK_SAV_01_LANDING", py(g.sim.warps)[-2:])
        self.assertTrue(g.log_has("loading\tCHK_SAV_01_LANDING\tonce more"))

    def test_viceron_before_torren_sends_you_back_with_the_reason(self):
        g = city_done("v1011-viceron", grant=("access:viceron",))
        self.assertNotIn("revisit:viceron", menu_ids(g))
        self.assertNotIn("viceron_1", menu_ids(g))
        self.assertTrue(g.note_has("its first visit needs the Hurlshot from the story on Torren IV"), g.notes()[-3:])
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_ZORDOOM_START", InterplanetaryCheckpointName="CHK_TRANSITION_TO_ZORDOOM")
        g.travel("Viceron")
        g.step(900)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(any("first visit needs the Hurlshot from the story on Torren IV" in n and "back to Nefarious City" in n
                            for n in g.notes()), g.notes()[-3:])
        self.assertNotEqual(g.sim.get_mission("MIS_ZORD_01"), 2)

    def test_first_visits_are_listed_before_revisits(self):
        g = city_done("v1011-order")
        g.lua.execute('RANDO.state.hub.done.scarstu_1 = 9')
        g.R.grant("access:savali")
        g.step(30)
        ids = menu_ids(g)
        self.assertLess(ids.index("savali_1"), ids.index("scarstu_2"), ids)

    def test_the_games_own_trip_to_an_open_first_visit_is_played(self):
        g = to_hub(hub_game("v1011-follow"))
        g.R.grant("access:sargasso")
        g.step(30)
        g.sim.complete_mission("MIS_NEFCITY_01")                    # the game starts Sargasso's story and goes there
        g.step(1500)
        self.assertEqual(g.sim.planet, "Sargasso")
        self.assertEqual(hub(g)["current"], "sargasso_1")
        self.assertFalse(g.log_has("ORDER KEPT"))
        self.assertTrue(g.log_has("was active before the landing"))

    def test_the_games_own_trip_to_a_closed_planet_is_still_undone(self):
        g = to_hub(hub_game("v1011-closed"))
        g.lua.execute('RANDO.state.access.sargasso = nil')
        g.sim.complete_mission("MIS_NEFCITY_01")
        g.step(3000)
        self.assertEqual(g.sim.planet, "NefCity")
        self.assertTrue(g.log_has("[ORDER KEPT] the game's own travel to sargasso undone"))


if __name__ == "__main__":
    unittest.main()
