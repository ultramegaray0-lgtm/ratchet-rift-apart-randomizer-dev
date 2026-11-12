"""Randomizer 8.0: Zurkie's Battleplex hub.

Generator: every hub seed is checked by an independent Python re-implementation of the hub rules
(all orders a player could choose), over many seeds and settings. Runtime: the real scripts
against the simulated game (tests/sim/rivet_sim.lua): New Game -> Zurkie's, the two Coordinates,
travel, the mission ladder (start / force available / replay / explore), finishing destinations,
the return to the hub, the ship's menu, the parade on a load, saving and restoring, and whole
campaigns to the finale. What the simulator assumes about the game for 8.0 (warps and flights
landing, what a state write does) is listed at the top of rivet_sim.lua: it is NOT the game.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402

HUB_PLANET = "scarstu"
FINALE_PLANET = "corson_v"


# ---------------------------------------------------------------------------------------------
# independent verifier of a hub plan (does not use the Lua code)
# ---------------------------------------------------------------------------------------------
def verify_hub(plan, settings):
    errors = []
    dests = plan["destinations"]
    ids = [d["id"] for d in dests if d["kind"] != "finale"]
    by_id = {d["id"]: d for d in dests}
    fin = [d for d in dests if d["kind"] == "finale"]
    if len(fin) != 1 or dests[-1]["kind"] != "finale":
        errors.append("finale missing or not last")
    start = plan["start"]
    if len(start) != settings["hub_start_coordinates"]:
        errors.append("start size %d" % len(start))
    if len(set(start)) != len(start):
        errors.append("start twice")
    for pid in start:
        if pid in (HUB_PLANET, FINALE_PLANET):
            errors.append("start on " + pid)
        firsts = [d for d in dests if d["planet"] == pid and d["visit"] == 1]
        if not firsts or firsts[0]["after"] or firsts[0]["abilities"]:
            errors.append("start planet %s cannot be played first" % pid)
    planets = {d["planet"] for d in dests if d["kind"] == "planet"}
    if set(start) | set(plan["queue"]) != planets or len(plan["queue"]) + len(start) != len(planets):
        errors.append("Coordinates do not cover every planet exactly once")
    k = plan["per_completion"]
    if k != settings["hub_unlocks"]:
        errors.append("per_completion")
    grants = {d["id"]: set(d.get("grants") or []) for d in dests}
    finale_after = plan["finale_after"]
    if settings["hub_finale"] == "all" and finale_after != len(ids):
        errors.append("finale_after %d" % finale_after)

    def available(done):
        n = len(done)
        open_ = set(start) | set(plan["queue"][:min(len(plan["queue"]), n * k)])
        granted = set()
        for x in done:
            granted |= grants[x]
        out = []
        for d in dests:
            if d["id"] in done:
                continue
            if d["kind"] == "finale":
                if n >= finale_after:
                    out.append(d["id"])
                continue
            if d["kind"] != "hub" and d["planet"] not in open_:
                continue
            if any(a not in done for a in d["after"]):
                continue
            if any(a not in granted for a in d["abilities"]):
                continue
            out.append(d["id"])
        return out

    seen = set()
    stack = [frozenset()]
    while stack:
        done = stack.pop()
        if done in seen:
            continue
        seen.add(done)
        av = available(done)
        if not av:
            errors.append("dead end after " + ",".join(sorted(done)))
            break
        if len(done) == len(ids):
            if fin and fin[0]["id"] not in av:
                errors.append("finale closed at the end")
            continue
        for x in av:
            if by_id[x]["kind"] != "finale":
                stack.append(done | {x})
    # the game's own dependencies
    if "viceron_1" in by_id and set(by_id["viceron_1"]["abilities"]) != {"phantom_dash", "hurlshot"}:
        errors.append("viceron abilities")
    return errors, len(seen)


class HubGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import rando
        cls.eng = rando.Engine()

    def gen(self, seed, user=None, preset="hub"):
        s, audit = self.eng.generate(seed, user or {}, preset)
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [], seed)
        return py(s)

    def test_many_seeds_two_start_coordinates(self):
        starts = {}
        for i in range(300):
            s = self.gen(f"hub-many-{i}")
            h = s["hub"]
            self.assertEqual(s["format"], 8)
            self.assertTrue(s["settings"]["hub"])
            self.assertFalse(s["settings"]["planet_locks"])
            self.assertFalse(s["settings"]["travel_lock"])
            self.assertEqual(len(h["start"]), 2)
            self.assertNotEqual(h["start"][0], h["start"][1])
            errors, states = verify_hub(h, s["settings"])
            self.assertEqual(errors, [], f"hub-many-{i}")
            self.assertGreater(states, 100)
            starts[tuple(h["start"])] = starts.get(tuple(h["start"]), 0) + 1
            # 7.0 systems are all still there
            self.assertEqual(s["start"]["items"][:2], ["hoverboots", "map_o_matic"])
            self.assertEqual(len(s["gold_bolts"]), 25)
            self.assertEqual(len(set(s["shop"]["slots"].values())), 15)
        # the starting pair really varies with the seed
        self.assertGreater(len(starts), 12)

    def test_deterministic(self):
        a, b = self.gen("hub-same"), self.gen("hub-same")
        self.assertEqual(a["hub"], b["hub"])
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertEqual(a["locations"], b["locations"])

    def test_settings_variants(self):
        for i, user in enumerate([{"hub_start_coordinates": 3}, {"hub_start_coordinates": 4, "hub_unlocks": 2},
                                  {"hub_unlocks": 3}, {"hub_finale": "half"}, {"hub_revisits": False},
                                  {"hub_revisits": False, "hub_start_coordinates": 3, "hub_finale": "half"}]):
            for j in range(25):
                s = self.gen(f"hub-var-{i}-{j}", user)
                errors, _ = verify_hub(s["hub"], s["settings"])
                self.assertEqual(errors, [], (user, j))
                if user.get("hub_revisits") is False:
                    self.assertFalse(any(d["visit"] == 2 and d["kind"] != "finale" for d in s["hub"]["destinations"]))

    def test_hub_chaos_preset(self):
        for j in range(20):
            s = self.gen(f"hub-chaos-{j}", preset="hub_chaos")
            self.assertEqual(verify_hub(s["hub"], s["settings"])[0], [])
            self.assertEqual(s["settings"]["shop_prices"], "random")

    def test_level_locks_do_not_apply_to_a_hub_seed(self):
        s, audit = self.eng.generate("hub-locks", {"levels": True, "mission_order": "chaos"}, "hub")
        s = py(s)
        self.assertEqual(audit, [])
        self.assertFalse(s["settings"]["planet_locks"])
        self.assertEqual(s["settings"]["campaign_mode"], "vanilla")
        self.assertTrue(any("does not apply to a hub seed" in w for w in s["warnings"]))

    def test_non_hub_seed_has_no_plan_and_ignores_hub_keys(self):
        a = self.gen("seven", preset="balanced")
        b = self.gen("seven", {"hub_unlocks": 3}, "balanced")
        self.assertNotIn("hub", a)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertEqual(a["locations"], b["locations"])

    def test_audit_catches_a_broken_plan(self):
        s, _ = self.eng.generate("hub-mut", {}, "hub")
        lua = self.eng.lua
        audit = lua.eval("function(s) return RANDO_GEN.audit(s) end")
        # the same planet twice at the start
        s.hub.start[2] = s.hub.start[1]
        self.assertTrue(any("twice" in p for p in py(audit(s))))
        s, _ = self.eng.generate("hub-mut", {}, "hub")
        # Viceron (needs two story abilities) as the only start: dead end
        lua.execute("function _break(s) s.hub.start = { 'viceron', s.hub.start[2] } end")
        lua.globals()._break(s)
        problems = py(audit(s))
        self.assertTrue(any("Coordinates" in p or "dead end" in p or "twice" in p for p in problems), problems)
        s, _ = self.eng.generate("hub-mut", {}, "hub")
        lua.execute("function _drop(s) table.remove(s.hub.queue, 1) end")
        lua.globals()._drop(s)
        self.assertTrue(any("no Coordinates ever open" in p for p in py(audit(s))))

    def test_spoiler_has_the_hub(self):
        s, _ = self.eng.generate("hub-spoil", {}, "hub")
        text = self.eng.spoiler(s)
        self.assertIn("ZURKIE'S BATTLEPLEX HUB", text)
        self.assertIn("Starting Coordinates:", text)
        self.assertIn("One way through:", text)
        self.assertIn("leaves something to do until the finale", text)

    def test_share_code(self):
        s = self.gen("hub-share", {"hub_unlocks": 2})
        self.assertTrue(s["share_code"].startswith("RA8|hub-share|hub|"))
        seed, preset, user = self.eng.G.parse_share_code(s["share_code"])
        again = self.gen(seed, py(user), preset)
        self.assertEqual(again["hub"], s["hub"])


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


def hub_game(seed="hub-rt-1", settings=None, dll_version=6, missions=None, travel=True, **kw):
    st = {"seed": seed, "preset": "hub", "hub_return_delay": 2}
    st.update(settings or {})

    def before(game):
        game.sim.auto_travel = travel

    g = Game(settings=st, dll_version=dll_version, before_scripts=before, **kw)
    assert not g.load_errors, g.load_errors
    names = all_missions(g)
    states = {n: 0 for n in names}
    states["MIS_INTRO"] = 2
    for c in ("MIS_ZURK_ARENA_BRONZE_CUP", "MIS_ZURK_ARENA_SILVER_CUP", "MIS_ZURK_ARENA_GOLD_CUP"):
        states[c] = 1
    states.update(missions or {})
    g.sim.install_missions(g.lua.table_from([g.lua.table_from([n, s]) for n, s in states.items() if s is not None]))
    return g


def to_hub(g, wrench=True):
    g.companion_restore()
    g.sim.new_game()
    g.step(60)
    g.sim.parade_control()
    g.step(30)
    if wrench:
        g.sim.parade_wrench()
    for _ in range(40):
        g.step(30)
        h = g.state.hub
        if h is not None and h.started and g.sim.planet == "Zurkon":
            break
    g.step(400)
    return g


def hub(g):
    return py(g.state.hub)


def go(g, dest_id, max_frames=6000):
    """select dest_id with F6 and go with Ctrl+F6"""
    H = g.g.RANDO_HUB
    av = list(py(H.available()))
    assert dest_id in av, (dest_id, av)
    for _ in range(len(av) + 1):
        g.press("F6")
        if av[H.sel - 1] == dest_id:
            break
    g.press("F6", ctrl=True)
    for _ in range(max_frames // 30):
        g.step(30)
        if hub(g).get("current") == dest_id and hub(g).get("attempts", {}).get(dest_id):
            break
    g.step(60)


class HubRuntimeTests(unittest.TestCase):
    def test_new_game_goes_to_zurkies_with_two_coordinates(self):
        g = to_hub(hub_game())
        h = hub(g)
        plan = py(g.seed.hub)
        self.assertTrue(h["started"])
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertEqual(g.sim.warps[1], "CHK_ZURK_00_DEFAULT")
        self.assertEqual(sorted(k for k, v in h["open"].items() if v), sorted(plan["start"]))
        for pid in plan["start"]:
            self.assertTrue(g.state.access[pid])
        self.assertTrue(g.note_has("Zurkie's Battleplex: Coordinates for"))
        # the skipped prologue: its reward paid, MIS_INTRO forced complete through v6
        self.assertTrue(g.state.collected["planet:corson_v"])
        self.assertEqual(g.sim.get_mission("MIS_INTRO"), 4)
        self.assertTrue(h["intro"].startswith("forced 2 -> 4"), h["intro"])
        # the ship's travel on, every level bit set, research logged
        self.assertEqual(g.sim.travel_flag, 1)
        self.assertEqual(g.sim.levels & 0x7FE, 0x7FE)
        self.assertTrue(g.log_has("RANDO-HUB\tresearch: rando_give.dll v6 paths 0x7"))
        self.assertTrue(g.log_has("research: mission\tMIS_SAV_01"))
        self.assertTrue(g.log_has("research: checkpoints LANDING"))
        # the start inventory came too (7.0 systems)
        self.assertTrue(g.state.started)
        self.assertTrue(g.owns("hoverboots"))

    def test_in_game_seed_equals_the_offline_one(self):
        """the game generates the seed in small slices (the hub check yields too): same seed"""
        import rando
        g = hub_game("hub-rt-same")
        g.wait_seed()
        off, audit = rando.Engine().generate("hub-rt-same", {}, "hub")
        self.assertEqual(audit, [])
        self.assertEqual(g.seed.fingerprint, off.fingerprint)
        self.assertEqual(py(g.seed.hub), py(off.hub))
        self.assertEqual(py(g.seed.locations), py(off.locations))

    def test_triggers(self):
        # control: leaves at the first control of the parade, without waiting for the wrench
        g = to_hub(hub_game("hub-rt-control", {"hub_trigger": "control"}), wrench=False)
        self.assertTrue(hub(g)["started"])
        # wrench, but the objective never comes: goes anyway after the timeout
        g = hub_game("hub-rt-timeout")
        g.companion_restore()
        g.sim.new_game()
        g.step(60)
        self.assertFalse(hub(g).get("started"))
        g.step(g.g.RANDO_HUB.TRIGGER_TIMEOUT + 600)
        self.assertTrue(hub(g)["started"])
        self.assertEqual(g.sim.planet, "Zurkon")

    def test_a_save_load_does_not_start_the_hub(self):
        g = hub_game("hub-rt-load")
        g.companion_restore()
        g.sim.load_save("NefCity")
        g.step(g.g.RANDO_HUB.TRIGGER_TIMEOUT + 600)
        self.assertFalse(hub(g).get("started"))
        self.assertEqual(len(list(g.sim.warps.values())), 0)
        # Ctrl+F6 starts it by hand on any save
        g.press("F6", ctrl=True)
        g.step(900)
        self.assertTrue(hub(g)["started"])
        self.assertEqual(g.sim.planet, "Zurkon")

    def test_destination_story_forced_then_finished(self):
        g = to_hub(hub_game())
        plan = py(g.seed.hub)
        g.sim.ship_near = True
        H = g.g.RANDO_HUB
        dest = next(d for d in plan["destinations"] if d["planet"] == plan["start"][0] and d["visit"] == 1)
        go(g, dest["id"])
        h = hub(g)
        self.assertEqual(h["current"], dest["id"])
        self.assertEqual(g.sim.travels[len(g.sim.travels)].how, "fly")        # a ship was near
        first = dest["missions"][0]
        # inactive -> forced available -> started (the game's start call)
        self.assertEqual(h["attempts"][dest["id"]]["what"], "story", h["attempts"])
        self.assertEqual(g.sim.get_mission(first), 2)
        self.assertTrue(any(c.name == first and c.state == 1 for c in g.sim.set_state_calls.values()))
        if dest["hero"] == "rivet":
            self.assertIn("rivet", list(g.sim.heroes.values()))
        # the player finishes the visit's missions
        for m in dest["missions"]:
            if g.sim.get_mission(m) != 2:
                g.step(H.NEXT_MISSION_WAIT + 300)
            g.sim.set_mission(m, 4)
            g.step(30)
        h = hub(g)
        self.assertIn(dest["id"], h["done"])
        self.assertEqual(h["n_done"], 1)
        self.assertTrue(g.state.collected["planet:" + dest["planet"]])
        newly = plan["queue"][0]
        self.assertTrue(h["open"][newly])
        # back to Zurkie's after the delay, new Coordinates announced there
        g.step(60 * 3 + 400)
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertTrue(g.note_has("New Coordinates:"))
        self.assertNotIn("current", hub(g))

    def test_explore_and_finish_by_hand(self):
        # the destination's missions do not exist in this game: explore, then Ctrl+F5 twice
        g = hub_game("hub-rt-explore")
        g.wait_seed()
        plan = py(g.seed.hub)
        target = next(d for d in plan["destinations"] if d["planet"] == plan["start"][0] and d["visit"] == 1)
        g = hub_game("hub-rt-explore", missions={m: None for m in target["missions"]})
        to_hub(g)
        go(g, target["id"])
        self.assertEqual(hub(g)["attempts"][target["id"]]["what"], "explore")
        self.assertTrue(g.note_has("explore"))
        g.press("F5", ctrl=True)
        self.assertNotIn(target["id"], hub(g)["done"])
        g.press("F5", ctrl=True)
        h = hub(g)
        self.assertIn(target["id"], h["done"])
        self.assertTrue(h["by_hand"][target["id"]])
        self.assertTrue(g.state.collected["planet:" + target["planet"]])
        self.assertTrue(g.log_has("[FINISHED BY HAND]"))

    def test_available_mission_started_without_forcing(self):
        g = hub_game("hub-rt-avail")
        g.wait_seed()
        plan = py(g.seed.hub)
        target = next(d for d in plan["destinations"] if d["planet"] == plan["start"][1] and d["visit"] == 1)
        g = hub_game("hub-rt-avail", missions={target["missions"][0]: 1})
        to_hub(g)
        go(g, target["id"])
        self.assertEqual(g.sim.get_mission(target["missions"][0]), 2)
        self.assertFalse(any(c.name == target["missions"][0] for c in g.sim.set_state_calls.values()))

    def test_no_force_no_v6_replay_then_explore(self):
        for settings, version in (({"hub_force_missions": False}, 6), ({}, 5)):
            g = to_hub(hub_game("hub-rt-v5", settings, dll_version=version))
            plan = py(g.seed.hub)
            target = next(d for d in plan["destinations"] if d["planet"] == plan["start"][0] and d["visit"] == 1)
            go(g, target["id"])
            self.assertEqual(hub(g)["attempts"][target["id"]]["what"], "explore", (settings, version))
            self.assertTrue(g.log_has("replay\t" + target["missions"][0]))
            if version == 5:
                # without v6: no intro write, no levels, the hub still runs
                self.assertFalse((hub(g).get("intro") or "").startswith("forced"))
                self.assertEqual(g.sim.levels, 0x6)

    def test_replay_that_works(self):
        g = hub_game("hub-rt-replay", {"hub_force_missions": False})
        g.sim.replay_effect = 2
        to_hub(g)
        plan = py(g.seed.hub)
        target = next(d for d in plan["destinations"] if d["planet"] == plan["start"][0] and d["visit"] == 1)
        go(g, target["id"])
        self.assertEqual(hub(g)["attempts"][target["id"]]["what"], "story")
        self.assertIn("replayed", hub(g)["attempts"][target["id"]]["detail"])

    def test_menu_to_a_locked_planet_goes_back_to_the_hub(self):
        g = to_hub(hub_game("hub-rt-menu"))
        plan = py(g.seed.hub)
        locked = plan["queue"][-1]
        cps = {"nefarious_city": "CHK_NEFCITY_SHIP", "savali": "CHK_SAV_01_LANDING", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD",
               "sargasso": "CHK_SARG_01_LANDING", "torren_iv": "CHK_MOL_01_LANDING", "cordelion": "CHK_CORD_01_LANDING",
               "ardolis": "CHK_ARD_01_LANDING", "viceron": "CHK_ZORD_01_LANDING"}
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cps[locked], InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.sim.warps[len(g.sim.warps) + 1] = cps[locked]
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from({"planet": g.sim.planet_of_cp(cps[locked]), "at": g.sim.frame + 2, "cp": cps[locked]})
        g.step(400)
        g.step(600)
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertTrue(g.note_has("no Coordinates for"))
        self.assertEqual(hub(g)["sent_back"], 1)
        # an open planet through the menu starts its destination
        open_pid = plan["start"][0]
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cps[open_pid], InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from({"planet": g.sim.planet_of_cp(cps[open_pid]), "at": g.sim.frame + 2, "cp": cps[open_pid]})
        g.step(900)
        self.assertEqual(py(g.g.RANDO_HUB.dest(hub(g)["current"]))["planet"], open_pid)

    def test_parade_on_a_load_goes_back_to_the_hub(self):
        g = to_hub(hub_game("hub-rt-keeper"))
        saved = g.companion_export()
        g2 = hub_game("hub-rt-keeper")
        g2.companion_restore(saved)
        g2.sim.load_save("Malinon")
        g2.step(900)
        self.assertEqual(g2.sim.planet, "Zurkon")
        self.assertTrue(g2.log_has("the parade on a load") or g2.log_has("a load into the parade"))

    def test_restore_that_comes_after_the_load(self):
        """the companion often answers after the game has loaded the save: the restored hub then
        acts on the planet this session is on"""
        g = to_hub(hub_game("hub-rt-late"))
        saved = g.companion_export()
        g2 = hub_game("hub-rt-late")
        g2.wait_seed()
        g2.sim.load_save("Malinon")
        g2.step(300)
        self.assertEqual(g2.sim.planet, "Malinon")
        g2.companion_restore(saved)
        g2.step(900)
        self.assertEqual(g2.sim.planet, "Zurkon")
        self.assertTrue(g2.log_has("restored on Corson V without the finale open"))
        # restored at Zurkie's: the hub's world is put back
        g3 = hub_game("hub-rt-late")
        g3.wait_seed()
        g3.sim.load_save("Zurkon")
        g3.step(300)
        g3.companion_restore(saved)
        g3.step(600)
        self.assertEqual(g3.sim.travel_flag, 1)
        self.assertEqual(g3.sim.levels & 0x7FE, 0x7FE)

    def test_saved_progress_survives(self):
        g = to_hub(hub_game("hub-rt-save"))
        plan = py(g.seed.hub)
        target = next(d for d in plan["destinations"] if d["kind"] == "hub" and not d["after"])
        go(g, target["id"])
        g.press("F5", ctrl=True)
        g.press("F5", ctrl=True)
        before = hub(g)
        self.assertIn(target["id"], before["done"])
        saved = g.companion_export()
        g2 = hub_game("hub-rt-save")
        g2.companion_restore(saved)
        g2.sim.load_save("Zurkon")
        g2.step(600)
        after = hub(g2)
        self.assertEqual(after["done"], before["done"])
        self.assertEqual(after["open"], before["open"])
        self.assertTrue(after["started"])
        self.assertEqual(g2.sim.planet, "Zurkon")
        self.assertEqual(len(list(g2.sim.warps.values())), 0)          # a load at Zurkie's moves nothing

    def test_warp_to_zurkies_fails_everywhere(self):
        g = hub_game("hub-rt-nowarp")
        for cp in list(g.sim.checkpoint_list.values()):
            if "ZURK" in cp:
                g.sim.warp_fails[cp] = True
        to_hub(g)
        h = hub(g)
        self.assertTrue(h["started"])
        self.assertEqual(h["phase"], "hub_unreached")
        self.assertTrue(g.note_has("could not reach Zurkie's"))
        self.assertEqual(len([k for k, v in h["open"].items() if v]), 2)

    def test_hub_runtime_off(self):
        g = to_hub(hub_game("hub-rt-off", {"hub_runtime": False}))
        self.assertFalse(hub(g).get("started"))
        self.assertEqual(len(list(g.sim.warps.values())), 0)

    def test_startup_guard_undoes_the_games_own_travel(self):
        g = to_hub(hub_game("hub-rt-guard"))
        g.travel("NefCity")
        g.step(600)
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertTrue(g.log_has("right after the hub started"))

    def test_status_and_keys(self):
        g = to_hub(hub_game("hub-rt-keys"))
        g.press("F9")
        self.assertTrue(g.note_has("hub 0/13 done"))
        g.press("F6")                                   # 8.3: the old key still works (legacy_f_keys)
        self.assertTrue(g.note_has("Ctrl+] to go"))     # and the text names the new one
        g.press("F5")
        self.assertTrue(g.note_has("you are at Zurkie's"))


class HubCampaignTests(unittest.TestCase):
    """Whole campaigns in the simulated game: always the first open destination (and once the
    last one), played by events where the story runs and by hand where it cannot."""

    def play(self, seed, pick_last=False, settings=None, broken=None):
        g = hub_game(seed, settings, missions=broken)
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
            go(g, target)
            att = hub(g).get("attempts", {}).get(target, {})
            if att.get("what") == "story":
                for m in d["missions"]:
                    if g.sim.get_mission(m) in (0, 1):
                        g.step(H.NEXT_MISSION_WAIT + 400)
                    if g.sim.get_mission(m) is not None and g.sim.get_mission(m) != 4:
                        g.sim.set_mission(m, 4)
                    g.step(30)
            if target not in hub(g)["done"]:
                g.press("F5", ctrl=True)
                g.press("F5", ctrl=True)
            self.assertIn(target, hub(g)["done"], (seed, target, att))
            g.step(60 * 3 + 600)
            if d["kind"] == "finale":
                break
            if d["kind"] != "hub":
                self.assertEqual(g.sim.planet, "Zurkon", (seed, target))
        h = hub(g)
        self.assertEqual(h["n_done"], len(plan["destinations"]), (seed, sorted(h["done"])))
        self.assertTrue(g.state.campaign_complete)
        self.assertEqual(h["phase"], "done")
        # every destination's story and side rewards were paid
        for d in plan["destinations"]:
            for lid in py(H.locations_of(H.dest(d["id"]))):
                self.assertTrue(g.state.collected[lid], (seed, lid))
        return g

    def test_campaigns_to_the_finale(self):
        for i in range(4):
            self.play(f"hub-camp-{i}", pick_last=(i % 2 == 1))

    def test_campaign_with_missing_missions(self):
        # some visits' missions do not exist in this game: those are finished by hand
        self.play("hub-camp-broken", broken={"MIS_BLIZAR": None, "MIS_ZORD_01": None, "MIS_MEGA_FINALE": None})


if __name__ == "__main__":
    unittest.main()


class HubRealLogTests(unittest.TestCase):
    """Your game's own event streams (rivet.log rounds 13-16, RANDO-DISCOVER lines) replayed into a
    hub seed: the New Game trigger must fire on the real parade objectives and never on a save load."""

    def replay(self, name):
        from test_runtime import RealLogReplayTests
        g = hub_game("hub-real-" + name)
        g.companion_restore()
        g.travel("NefCity", 5)
        g.step(60)
        started_at = None
        for i, (cls, fields) in enumerate(RealLogReplayTests.events(name)):
            if cls == "PlanetChangedEvent" and fields.get("NewPlanetName"):
                g.travel(fields["NewPlanetName"], 5)
            else:
                g.fire(cls, **fields)
            g.step(2)
            if started_at is None and g.state.hub is not None and g.state.hub.phase != "pre":
                started_at = (i, cls, dict(fields))
        g.step(900)
        return g, started_at

    def test_round14_and_15_new_games_start_the_hub_at_the_wrench(self):
        for name in ("round14_rivet.log", "round15_rivet.log"):
            g, at = self.replay(name)
            self.assertIsNotNone(at, name)
            self.assertEqual(at[2].get("ObjectiveName"), "OBJ_INTRO_PARADE_PICKUP_WRENCH", (name, at))
            self.assertEqual(at[2].get("ObjectiveState"), 2)
            self.assertTrue(hub(g)["started"], name)
            self.assertEqual(g.sim.planet, "Zurkon", name)
            self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_round13_save_loads_never_start_it(self):
        g, at = self.replay("round13_rivet.log")
        self.assertIsNone(at)
        self.assertFalse(hub(g).get("started"))

    def test_round16_new_game_starts_it(self):
        g, at = self.replay("round16_rivet.log")
        self.assertIsNotNone(at)
        self.assertTrue(hub(g)["started"])
        self.assertFalse(g.log_has("RANDO-ERROR"))


class HubLogSummaryTests(unittest.TestCase):
    def test_summary_lists_the_hub(self):
        import summarize_log
        g = to_hub(hub_game("hub-sum"))
        s = summarize_log.summarize([l.replace("[rando]", "[script] [rando]") for l in g.logs()])
        self.assertEqual(s["kit"], "8.5.0")
        self.assertTrue(any(x.startswith("the campaign starts at Zurkie's") for x in s["hub_done"]), s["hub_done"])
        self.assertTrue(any("research: rando_give.dll v6" in x for x in s["hub_research"]))
        self.assertTrue(any("Coordinates opened" in x for x in s["hub"]))
