"""Randomizer 8.4: the stabilization pass after round 20 (rivet.log of 2026-11-12, kit 8.3).

What round 20 showed, and what each test here pins down:
  * Stories that did not start (Torren IV) and Viceron played as Ratchet: the save's remembered
    hero ("rivet") was trusted while the game had Ratchet, so every swap was skipped or refused with
    "already playing as that hero". A story's first step ("go to <planet>") finished at once with
    the visit's own hero (Ardolis, Savali) and never with the other one (Torren IV, Viceron, and
    Nefarious City as Rivet in round 17). 8.4 checks the hero with the game before a start, fixes
    four wrong heroes in the registry, starts the story before the trip, and reloads a story that
    still waits.
  * "weapon type 1002 ... 1012 is weapon:burst_pistol": a load's replay was taken for a purchase.
  * Ms. Zurkon: "only 0 vendor weapon(s) in the array at +0x48" in rounds 18-20: ItemDatas holds
    pointers to slot objects.
  * ARSENAL_RESTORED was loaded but the seed was made without it (the companion answered late).
  * A hub trip went to a mid-mission checkpoint a test trip had left as "where you last landed".
The game here is the simulator (tests/sim/rivet_sim.lua), NOT your game. Its 8.4 additions (the
hero swap and the "go to" step) are modelled on the round 17/20 logs and marked SIMULATED there.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402
from test_hub import hub_game, to_hub, hub, go  # noqa: E402

SCRIPTS = os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts")


def game(seed="v84-1", settings=None, missions=None, test_travel=True, **kw):
    st = {"test_travel": test_travel}
    st.update(settings or {})
    g = to_hub(hub_game(seed, st, missions=missions, **kw))
    g.step(1200)                     # the checkpoint catalog
    return g


def settle(g, frames=900):
    for _ in range(frames // 30):
        g.step(30)


def select(g, pid):
    TT = g.g.RANDO_TEST_TRAVEL
    for _ in range(12):
        g.press(".")
        if TT.selected() == pid:
            return
    raise AssertionError("never selected " + pid)


def warp(g, pid, frames=900):
    select(g, pid)
    g.press(".", ctrl=True)
    settle(g, frames)


def go_to(g, mission, objective, planet, hero, on_start=True):
    g.sim.go_to[mission] = g.lua.table_from({"o": objective, "planet": planet, "hero": hero})
    g.sim.goto_on_start = on_start


def obj(g, mission):
    o = hub(g).get("obj", {}).get(mission)
    return (o or {}).get("o"), (o or {}).get("s")


class RegistryTests(unittest.TestCase):
    """the heroes of the visits, from the walkthroughs (Ratchet & Clank wiki plot, gamepressure,
    thegamer) and from your logs (round 20: Ardolis' story ran as Ratchet)"""

    def test_heroes(self):
        g = Game()
        C = g.g.RANDO_CAMPAIGN
        want = {"nefcity_1": "ratchet", "sargasso_1": "rivet", "scarstu_1": "ratchet", "savali_1": "ratchet",
                "blizar_1": "rivet", "torren_1": "rivet", "cordelion_1": "ratchet", "scarstu_2": "rivet",
                "ardolis_1": "ratchet", "sargasso_2": "rivet", "savali_2": "ratchet", "viceron_1": "rivet",
                "finale": "ratchet"}
        for sid, hero in want.items():
            self.assertEqual(C.BY_ID[sid].hero, hero, sid)

    def test_entries_are_names_your_game_listed(self):
        g = Game()
        C = g.g.RANDO_CAMPAIGN
        self.assertEqual(C.BY_ID["viceron_1"].entry, "CHK_ZORDOOM_START")
        self.assertEqual(C.BY_ID["cordelion_1"].entry, "CHK_CORD_A_START")
        self.assertEqual(C.BY_ID["ardolis_1"].entry, "CHK_ARD_START")
        logs = "".join(open(os.path.join(ROOT, "tests", "data", n), encoding="utf-8", errors="replace").read()
                       for n in ("round19_rivet.log", "round20_rivet.log"))
        for seg in ("viceron_1", "cordelion_1", "ardolis_1"):
            self.assertIn(C.BY_ID[seg].entry, logs)

    def test_heroes_do_not_change_the_seed(self):
        a = hub_game("v84-fp")
        a.companion_restore()
        a.wait_seed()
        self.assertEqual(a.seed.fingerprint, a.g.RANDO_GEN.fingerprint("v84-fp", a.seed.settings))
        self.assertEqual(a.g.RANDO_GEN.VERSION, "8.0.0")          # generator unchanged: saves carry over


class HeroTests(unittest.TestCase):
    def test_a_stale_saved_hero_is_never_trusted(self):
        """round 20: the save said rivet, the game had Ratchet; Viceron was played as Ratchet"""
        g = game("v84-stale")
        g.g.RANDO_HUB.state().hero = "rivet"
        self.assertEqual(g.sim.playing, "ratchet")
        warp(g, "viceron")
        self.assertEqual(g.sim.playing, "rivet")
        self.assertEqual(g.sim.started_as["MIS_ZORD_01"], "rivet")
        self.assertFalse(g.log_has("failed: already playing"))

    def test_already_playing_counts_as_confirmed(self):
        g = game("v84-already")
        H = g.g.RANDO_HUB
        got = []
        H.ensure_hero("ratchet", lambda ok, how: got.append((ok, how)))
        self.assertEqual(got, [(True, "already")])
        self.assertEqual(len(py(g.sim.heroes)), 0)

    def test_the_story_waits_for_a_slow_swap(self):
        g = game("v84-slow")
        g.sim.swap_frames = 150
        warp(g, "torren_iv", 1500)
        self.assertEqual(g.sim.started_as["MIS_MOL_01_FIRST_VISIT"], "rivet")
        self.assertTrue(g.log_has("confirmed after the swap"))

    def test_a_refused_swap_is_said_and_the_story_still_starts(self):
        g = game("v84-refused")
        g.sim.swap_refuse = "the hero has no HeroTransformationManager"
        warp(g, "torren_iv", 1800)
        self.assertTrue(g.note_has("could not switch to rivet"))
        self.assertEqual(g.sim.get_mission("MIS_MOL_01_FIRST_VISIT"), 2)

    def test_zurkies_own_visit_keeps_its_hero_through_a_load(self):
        g = game("v84-hubhero", missions={"MIS_ZURK_01_VISIT_01": 4})
        H = g.g.RANDO_HUB
        h = H.state()
        h.done["scarstu_1"] = 1
        h.n_done = 1
        g.press("/")                                       # scarstu_2 (Rivet) at Zurkie's
        settle(g, 600)
        self.assertEqual(hub(g)["current"], "scarstu_2")
        self.assertEqual(g.sim.playing, "rivet")
        g.travel("Zurkon")                                 # a load at Zurkie's
        settle(g, 600)
        self.assertEqual(g.sim.playing, "rivet")

    def test_back_at_zurkies_is_ratchet(self):
        g = game("v84-back")
        warp(g, "torren_iv")
        self.assertEqual(g.sim.playing, "rivet")
        g.press("[")
        g.press("[")
        settle(g, 900)
        self.assertEqual(g.sim.planet, "Zurkon")
        self.assertEqual(g.sim.playing, "ratchet")


class StoryStartTests(unittest.TestCase):
    def test_hub_trip_primes_the_story_and_its_first_step_finishes_on_landing(self):
        """the planet loads with the story active and its hero there (round 20: Savali)"""
        g = hub_game("v84-prime")
        g.sim.ship_near = True
        to_hub(g)
        plan = py(g.seed.hub)
        target = next(d for d in plan["destinations"] if d["planet"] in plan["start"] and d["visit"] == 1)
        planet = {"savali": "Savali", "blizar_prime": "Blizar", "torren_iv": "Torren", "cordelion": "Cordelion",
                  "nefarious_city": "NefCity", "sargasso": "Sargasso", "ardolis": "Ardolis"}[target["planet"]]
        m = target["missions"][0]
        go_to(g, m, "OBJ_TEST_GO_TO_PLANET", planet, target["hero"], on_start=False)
        go(g, target["id"])
        settle(g, 600)
        self.assertEqual(g.sim.started_as[m], target["hero"])
        self.assertTrue(g.log_has("prime\t" + target["id"] + ":"))
        self.assertEqual(obj(g, m), ("OBJ_TEST_GO_TO_PLANET", 2))
        self.assertFalse(any("[STORY RELOAD]" in x for x in py(g.state.history)))

    def test_on_planet_start_that_waits_is_reloaded_and_then_moves(self):
        """the ship's menu lands first and starts the story there; when "go to" waits (it does
        not finish on a start there), the planet is reloaded once (round 20: Viceron moved on
        after its reload)"""
        g = game("v84-reload", test_travel=False)
        go_to(g, "MIS_ZORD_01", "OBJ_ZORD_01_GO_TO_ZORDOOM", "Viceron", "rivet", on_start=False)
        H = g.g.RANDO_HUB
        g.state.access["viceron"] = True
        H.state().open["viceron"] = True
        cp = "CHK_ZORDOOM_START"
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cp, InterplanetaryCheckpointName="CHK_TRANSITION_TO_ZORDOOM")
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from({"planet": "Viceron", "at": g.sim.frame + 2, "cp": cp})
        settle(g, 900)
        self.assertEqual(obj(g, "MIS_ZORD_01"), ("OBJ_ZORD_01_GO_TO_ZORDOOM", 1))
        settle(g, 2400)
        self.assertTrue(any("[STORY RELOAD] viceron_1" in x for x in py(g.state.history)))
        self.assertEqual(g.sim.planet, "Viceron")
        self.assertEqual(obj(g, "MIS_ZORD_01"), ("OBJ_ZORD_01_GO_TO_ZORDOOM", 2))
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_menu_landings_are_remembered_test_trips_are_not(self):
        g = game("v84-landed")
        warp(g, "torren_iv")
        tr = g.state.travel
        self.assertIsNone(tr.landed["torren_iv"])
        self.assertTrue(tr.test_landed["torren_iv"])

    def test_old_saves_move_their_landings_to_test_landings(self):
        g = game("v84-migrate")
        T = g.g.RANDO_TRAVEL
        tr = T.state()
        tr.landed_v = None
        tr.landed["torren_iv"] = "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP"
        T.state()
        self.assertIsNone(g.state.travel.landed["torren_iv"])
        self.assertEqual(g.state.travel.test_landed["torren_iv"], "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP")
        cp, how = T.checkpoint_for("torren_iv")
        self.assertNotEqual(cp, "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP")

    def test_story_starts_rank_first_and_command_ship_is_not_a_landing(self):
        g = Game()
        T = g.g.RANDO_TRAVEL
        sc = T.score_checkpoint
        self.assertEqual(sc("CHK_ARD_START"), 95)
        self.assertEqual(sc("CHK_CORD_A_START"), 95)
        self.assertEqual(sc("CHK_ZORDOOM_START"), 95)
        self.assertLess(sc("CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP"), sc("CHK_ZORDOOM_START"))
        self.assertLess(sc("CHK_ZORDOOM_DOME_START"), 95)
        self.assertEqual(sc("CHK_NEFCITY_SHIP"), 80)


class WeaponTypeTests(unittest.TestCase):
    def test_a_load_after_an_equip_teaches_nothing(self):
        """round 20: Cordelion's replay (1002-1012) right after the Burst Pistol was equipped"""
        g = Game().ready(frames=300)
        for k in ("weapon:enforcer", "weapon:buzz_blades", "weapon:headhunter", "weapon:lightning_rod"):
            g.sim.weapons_owned[g.data.real_items[k].id] = True
        g.fire("UserEquippedWeaponEvent", WeaponName="WEAPON_BURST_PISTOL")
        g.travel("Cordelion")
        g.step(700)
        wt = py(g.state.weapon_types) or {}
        self.assertNotIn("weapon:burst_pistol", list(wt.values()))
        self.assertFalse(g.log_has("is\tweapon:burst_pistol"))

    def test_the_wrong_lessons_of_a_save_are_dropped(self):
        g = Game().ready(frames=60)
        wt = g.state.weapon_types or g.lua.table_from({})
        for t in range(1002, 1013):
            wt[t] = "weapon:burst_pistol"
        wt[1010] = "weapon:lightning_rod"
        g.state.weapon_types = wt
        g.real.sync()
        left = py(g.state.weapon_types)
        self.assertNotIn("weapon:burst_pistol", list(left.values()))
        self.assertEqual(left.get("1010"), "weapon:lightning_rod")

    def test_a_purchase_teaches_its_type_in_either_order(self):
        g = Game().ready(frames=300)
        g.travel("Zurkon"); g.step(700)
        g.fire("WeaponAddedEvent", WeaponType=1013)               # round 20: the type came first
        g.fire("PurchaseWeaponEvent", WeaponName="WEAPON_SHEEPINATOR", WeaponConfig=1)
        cfg = g.data.real_items["weapon:headhunter"].config         # WEAPON_<config name> as the game says it
        wname = "WEAPON_" + cfg.split("/wpn_")[1].replace("_item.config", "").upper()
        g.fire("PurchaseWeaponEvent", WeaponName=wname, WeaponConfig=1)
        g.fire("WeaponAddedEvent", WeaponType=1014)               # the name first
        wt = py(g.state.weapon_types)
        self.assertEqual(wt.get("1013"), "weapon:sheepinator")
        self.assertEqual(wt.get("1014"), "weapon:headhunter")

    def test_a_purchase_is_never_a_late_answer(self):
        g = Game().ready(frames=300)
        g.travel("Zurkon"); g.step(700)
        ex = g.data.real_items["weapon:revolver"].id
        g.sim.ignore_items[ex] = True
        g.R.grant("weapon:revolver")
        g.step(400)
        g.fire("WeaponAddedEvent", WeaponType=1013)
        g.fire("PurchaseWeaponEvent", WeaponName="WEAPON_SHEEPINATOR", WeaponConfig=1)
        g.step(200)
        self.assertNotEqual(g.item_status("weapon:revolver"), "owned")
        self.assertEqual(py(g.state.weapon_types).get("1013"), "weapon:sheepinator")


class ShopTests(unittest.TestCase):
    def test_slot_objects_by_pointer_are_found_and_changed(self):
        """rounds 18-20: "only 0 vendor weapon(s) in the array at +0x48" - ItemDatas holds pointers"""
        def before(gm):
            gm.sim.vendor_pointers = True
        g = Game(before_scripts=before).ready(frames=900)
        self.assertTrue(g.log_has("slot objects by pointer, Item at +0x10"))
        by_id = {g.data["items"][k].id: k for k in g.data["items"].keys() if k.startswith("weapon:")}
        slots = {k: g.seed.shop.slots[k] for k in g.seed.shop.slots.keys()}
        authored = [by_id.get(v, v) for v in g.sim.vendor_mem[Game.VENDOR_ID].authored.values()]
        for i, a in enumerate(authored, start=1):
            now = by_id.get(g.sim.vendor_slot_item(Game.VENDOR_ID, i), g.sim.vendor_slot_item(Game.VENDOR_ID, i))
            self.assertEqual(now, slots.get(a, a))
        self.assertFalse(g.log_has("only 0 vendor weapon"))
        self.assertTrue(g.log_has("Price at +0x18"))

    def test_inline_layout_still_works(self):
        g = Game().ready(frames=900)
        self.assertTrue(g.log_has("(element 0x58 bytes, Item at +0x10"))


class ArsenalTests(unittest.TestCase):
    def test_the_game_itself_says_the_mod_is_installed(self):
        marker = None

        def before(gm):
            gm.sim.configs["B9CBAD67F39CCC3F"] = gm.lua.table_from({"type": "WeaponItemConfig", "fields": gm.lua.table_from({})})
        g = Game(settings={"seed": "v84-ar", "preset": "hub", "restored_weapons": "auto"}, before_scripts=before)
        g.step(200)
        self.assertTrue(g.log_has("ARSENAL_RESTORED is installed"))
        self.assertTrue(g.log_has("Mr. Zurkon item config loaded"))
        g.wait_seed()
        self.assertTrue(g.seed.settings.include_arsenal_restored)
        del marker

    def test_a_random_seed_waits_for_the_companion_not_a_timer(self):
        g = Game(settings={"seed": "random", "preset": "hub", "restored_weapons": "auto"})
        g.step(4000)
        self.assertFalse(g.log_has("did not answer"))
        self.assertEqual(g.lua.eval("rando_arsenal_mode()"), "auto")

    def test_a_fixed_seed_still_times_out(self):
        g = Game(settings={"seed": "v84-fixed", "preset": "hub", "restored_weapons": "auto"})
        g.step(3700)
        self.assertTrue(g.log_has("the companion did not answer: treated as not installed"))


class KeyTests(unittest.TestCase):
    def test_campaign_key_says_nothing_in_a_hub_seed(self):
        g = game("v84-f12")
        n = len(py(g.sim.notes))
        g.press("F12")
        self.assertEqual(len(py(g.sim.notes)), n)
        self.assertTrue(g.log_has("no campaign order in this seed (hub seed)"))


class Round20LogTests(unittest.TestCase):
    def test_round20_events_replay_without_errors(self):
        from test_runtime import RealLogReplayTests
        g = hub_game("v84-r20")
        g.companion_restore()
        g.travel("NefCity", 5)
        g.step(60)
        for cls, fields in RealLogReplayTests.events("round20_rivet.log"):
            fields = {k: (float(v) if isinstance(v, int) and abs(v) >= 2 ** 63 else v) for k, v in fields.items()}
            if cls == "PlanetChangedEvent" and fields.get("NewPlanetName"):
                g.travel(fields["NewPlanetName"], 5)
            else:
                g.fire(cls, **fields)
            g.step(2)
        g.step(900)
        self.assertFalse(g.log_has("RANDO-ERROR"))
        wt = py(g.state.weapon_types) or {}
        self.assertLessEqual(len(set(wt.values())), len(wt))
        self.assertNotIn("weapon:burst_pistol", list(wt.values()))


class VersionTests(unittest.TestCase):
    def test_versions(self):
        for name, want in (("10_rando_runtime.lua", 'R.KIT_VERSION = "8.4.0"'), ("15_rando_hub.lua", 'H.VERSION = "8.4.0"'),
                           ("16_rando_testtravel.lua", 'TT.VERSION = "8.4.0"')):
            with open(os.path.join(SCRIPTS, name), encoding="utf-8") as f:
                self.assertIn(want, f.read(), name)


if __name__ == "__main__":
    unittest.main()


class KitCheckTests(unittest.TestCase):
    def test_a_complete_kit_says_so(self):
        g = Game(settings_file=True)
        g.step(3)
        self.assertTrue(g.log_has("RANDO-KIT all 14 scripts are 8.4.0"))
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_a_missing_or_older_script_is_reported(self):
        from harness import script_files
        files = [f for f in script_files() if not f.name.startswith("16_")]
        g = Game(files=files)
        g.lua.execute('RANDO_FILES["13_rando_armor"] = "8.3.0"')      # a file left from the 8.3 kit
        g.step(3)
        self.assertTrue(g.log_has("missing 16_rando_testtravel"))
        self.assertTrue(g.log_has("other versions: 13_rando_armor 8.3.0"))
        self.assertTrue(g.note_has("mixes kits"))


class InstallTests(unittest.TestCase):
    """INSTALL.txt names exactly the files the kit holds"""
    KIT = os.path.join(ROOT, "mod", "RiftApartRandomizer")

    def install_text(self):
        with open(os.path.join(self.KIT, "INSTALL.txt"), encoding="utf-8") as f:
            return f.read()

    def test_scripts(self):
        import re
        text = self.install_text()
        listed = set(re.findall(r"\b(\d\d_rando_[a-z]+)\b", text.split("Copy the 14 files")[1].split("Use this kit")[0]))
        shipped = {f[:-4] for f in os.listdir(os.path.join(self.KIT, "scripts")) if f.endswith(".lua")}
        self.assertEqual(listed, shipped)
        self.assertEqual(len(shipped), 14)
        g = Game()
        self.assertEqual(set(g.R.KIT_FILES.values()), shipped)

    def test_docs(self):
        import re
        text = self.install_text()
        block = text.split("docs\\")[-1]
        listed = set(re.findall(r"([A-Z_0-9.]+\.(?:md|txt))", block))
        shipped = {f for f in os.listdir(os.path.join(self.KIT, "docs")) if f.endswith((".md", ".txt"))}
        self.assertEqual(listed, shipped)

    def test_top_level(self):
        shipped = set(os.listdir(self.KIT))
        self.assertEqual(shipped, {"INSTALL.txt", "rivet.toml", "rando_give.dll", "rando_give_source", "scripts",
                                   "companion", "extras", "docs"})
