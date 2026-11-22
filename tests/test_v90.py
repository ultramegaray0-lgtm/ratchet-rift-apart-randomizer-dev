"""Randomizer 9.0's story start, kept in 10.0 as hub = false: a new game plays the prologue, then
Nefarious City, then Sargasso, as in the game. (10.0 brings the hub back as the default; its tests
are tests/test_v100.py. Every seed here sets hub = false.)

Generator: the hub presets and settings are retired (and say so), and every campaign order of every
mode begins with the story's start (checked by verify_story_start, written here independently of
03_rando_campaign.lua). Runtime: the real scripts against the simulated game (tests/sim): the kit
loads without 15_rando_hub.lua, the user's own 04_rando_settings.lua (9.0 and the 8.5.2 one) loads,
and a new game is never moved: no warp, no flight, no mission state written, no hero swap, while
the prologue, Nefarious City and Sargasso play out. A leftover 15_rando_hub.lua from an older kit is
reported, and does nothing to a 9.0 seed. What the simulator assumes about the game is listed at the
top of tests/sim/rivet_sim.lua: it is NOT the game.
"""
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lupa import lua54  # noqa: E402
from luajson import py  # noqa: E402
from harness import Game, MOD  # noqa: E402

DATA = ROOT / "tests" / "data"
SCRIPTS = MOD / "scripts"

# the game's own start (the parade's rifts end on Nefarious City; finishing MIS_NEFCITY_01 takes
# you to Sargasso, round 16 lines 338-344) - written down here, not read from 03
STORY_START = ["corson_intro", "nefcity_1", "sargasso_1"]
HUB_KEYS = {"hub_start_coordinates", "hub_unlocks", "hub_finale", "hub_revisits", "random_start"}
NO_HUB = {"hub": False}


def verify_story_start(d):
    """problems of one packaged seed (a Python dict) with the 9.0 rules"""
    probs = []
    if d.get("hub") is not None:
        probs.append("the seed has a hub plan")
    s = d.get("settings") or {}
    for k in HUB_KEYS:
        if k in s:
            probs.append("the seed's settings still hold " + k)
    if s.get("hub"):
        probs.append("hub = true")
    if d.get("format") != 10:
        probs.append("format %r, not 10" % d.get("format"))
    order = (d.get("campaign") or {}).get("order")
    if order:
        if list(order[:3]) != STORY_START:
            probs.append("the campaign starts %s, not %s" % (order[:3], STORY_START))
        if len(set(order)) != len(order):
            probs.append("a visit twice in the campaign")
        if order[-1] != "finale":
            probs.append("the finale is not last")
    return probs


def USER_SETTINGS(path=None):
    """(preset, generator options) of a 04_rando_settings.lua file (default: the kit's)"""
    import rando
    eng = rando.Engine()
    known = set(eng.defaults()) | {"restored_weapons", "mission_order", "levels", "filler", "filler_bolts",
                                   "filler_raritanium"} | HUB_KEYS
    L = lua54.LuaRuntime(unpack_returned_tuples=True)
    L.execute(pathlib.Path(path or SCRIPTS / "04_rando_settings.lua").read_text(encoding="utf-8"))
    st = py(L.globals().RANDO_SETTINGS)
    preset = st.get("preset", "balanced")
    return preset, {k: v for k, v in st.items() if k in known}


def all_missions(g):
    names = set()
    C = g.g.RANDO_CAMPAIGN
    for seg in C.SEGMENTS.values():
        for m in seg.missions.values():
            names.add(m)
    return sorted(names)


def story_game(settings=None, scripts_dir=None, settings_file=False, **kw):
    """a game whose missions and checkpoints exist (auto_travel: a warp or flight would land)"""

    def before(game):
        game.sim.auto_travel = True
        game.sim.ship_near = True

    st = {"seed": "v90-story", "hub": False}
    st.update(settings or {})
    g = Game(settings=None if settings_file else st, scripts_dir=scripts_dir, settings_file=settings_file,
             dll_version=6, before_scripts=before, **kw)
    assert not g.load_errors, g.load_errors
    states = {n: 0 for n in all_missions(g)}
    states["MIS_INTRO"] = 2
    g.sim.install_missions(g.lua.table_from([g.lua.table_from([n, s]) for n, s in states.items()]))
    return g


def changes(g):
    """everything the randomizer did to the game's story or position"""
    calls = [c.kind for c in g.sim.mission_calls.values()] if g.sim.mission_calls is not None else []
    return {"warps": list(g.sim.warps.values()), "travels": [t.how for t in g.sim.travels.values()],
            "mission_writes": [k for k in calls if k not in ("query", 1)], "set_state": len(g.sim.set_state_calls or {}),
            "heroes": list(g.sim.heroes.values())}


def play_the_story_start(test, g):
    """New Game, the parade, then the game's own travel to Nefarious City and Sargasso"""
    g.companion_restore()
    g.sim.new_game()                     # the prologue: Corson V (Malinon)
    g.step(60)
    g.sim.parade_control()
    g.step(30)
    g.sim.parade_wrench()                # 8.0-8.5's hub left the parade here
    g.step(2400)
    test.assertEqual(g.sim.planet, "Malinon")
    test.assertEqual(g.state.current_planet, "corson_v")
    test.assertTrue(g.log_has("NEW GAME: run"))
    g.sim.set_mission("MIS_INTRO", 4)
    g.step(30)
    g.travel("NefCity")                  # the parade's rifts end on Nefarious City (no planet menu)
    g.step(600)
    test.assertEqual(g.state.current_planet, "nefarious_city")
    g.sim.set_mission("MIS_NEFCITY_01", 4)
    g.step(30)
    g.travel("Sargasso")                 # the game takes you on by itself
    g.step(600)
    test.assertEqual(g.state.current_planet, "sargasso")
    test.assertEqual(changes(g), {"warps": [], "travels": [], "mission_writes": [], "set_state": 0, "heroes": []})
    for lid in ("planet:corson_v", "planet:nefarious_city"):
        test.assertTrue(g.state.collected[lid], lid)


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import rando
        cls.eng = rando.Engine()

    def gen(self, seed, user=None, preset="balanced"):
        st = dict(NO_HUB)
        st.update(user or {})
        s, audit = self.eng.generate(seed, st, preset)
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [], seed)
        return py(s)

    def test_no_hub_plan_with_hub_false(self):
        G = self.eng.G
        d = py(G.DEFAULTS)
        self.assertFalse(HUB_KEYS & set(d), HUB_KEYS & set(d))
        self.assertTrue(d["hub"])                       # 10.0: the hub is the default
        self.assertIsNone(G.PRESETS["hub"])
        self.assertIsNone(G.PRESETS["hub_chaos"])
        self.assertIsNone(self.eng.lua.globals().RANDO_CAMPAIGN.hub_plan)   # the 8.x plan builder is gone
        self.assertEqual(G.VERSION, "10.11.0")
        s = self.gen("v90-nohub")
        self.assertIsNone(s.get("hub"))
        self.assertEqual(s["campaign"]["order"][:3], STORY_START)

    def test_your_defaults_are_kept(self):
        d = py(self.eng.G.DEFAULTS)
        for k, v in {"planet_locks": True, "campaign_mode": "planet_shuffle", "shop_prices": "weapon",
                     "raritanium_min": 120, "raritanium_max": 1000}.items():
            self.assertEqual(d[k], v, k)

    def test_retired_presets_give_the_same_seed_as_their_replacement(self):
        for old, new in (("hub", "balanced"), ("hub_chaos", "chaos")):
            a = self.gen("v90-retired", None, old)
            b = self.gen("v90-retired", None, new)
            self.assertTrue(any(("preset %s is gone" % old) in w for w in a["warnings"]), a["warnings"])
            self.assertEqual(a["fingerprint"], b["fingerprint"])
            self.assertEqual(a["locations"], b["locations"])
            self.assertEqual(verify_story_start(a), [])

    def test_retired_settings_are_named_and_ignored(self):
        a = self.gen("v90-settings", {"hub_unlocks": 2, "hub_start_coordinates": 4, "hub_finale": "half",
                                      "hub_revisits": False, "random_start": True})
        b = self.gen("v90-settings")
        gone = [w for w in a["warnings"] if "is gone in 9.0" in w or "is not used in 10.0" in w]
        self.assertEqual(len(gone), 5, a["warnings"])
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertEqual(verify_story_start(a), [])

    def test_every_mode_starts_with_the_prologue_then_nefarious_city(self):
        n = 0
        for preset in ("balanced", "campaign", "chaos", "full", "everything", "planet_shuffle", "mission_shuffle",
                       "full_campaign", "campaign_chaos"):
            for i in range(40):
                d = self.gen(f"v90-start-{preset}-{i}", None, preset)
                self.assertEqual(verify_story_start(d), [], (preset, i))
                n += 1
        for mode in ("planet_shuffle", "mission_shuffle", "full", "chaos"):
            for levels in (False, True):
                for i in range(25):
                    d = self.gen(f"v90-mode-{mode}-{levels}-{i}", {"campaign_mode": mode, "levels": levels})
                    self.assertEqual(verify_story_start(d), [], (mode, levels, i))
                    self.assertEqual(d["campaign"]["order"][:3], STORY_START)
                    n += 1
        self.assertEqual(n, 560)

    def test_the_rest_is_still_reordered(self):
        fourth = set()
        for i in range(60):
            d = self.gen(f"v90-reorder-{i}", {"campaign_mode": "mission_shuffle"})
            fourth.add(d["campaign"]["order"][3])
        self.assertGreaterEqual(len(fourth), 5, fourth)

    def test_story_planets_are_open_with_levels(self):
        for preset in ("campaign", "everything", "chaos"):
            d = self.gen(f"v90-open-{preset}", None, preset)
            start = d["start"]["items"]
            for pid in ("corson_v", "nefarious_city", "sargasso"):
                self.assertIn("access:" + pid, start, (preset, pid))

    def test_share_code_and_format(self):
        d = self.gen("share-v90", None, "chaos")
        self.assertTrue(d["share_code"].startswith("RA10|share-v90|chaos|"), d["share_code"])
        self.assertEqual(d["format"], 10)
        G = self.eng.G
        seed, preset, user = G.parse_share_code(d["share_code"])
        self.assertEqual((seed, preset), ("share-v90", "chaos"))
        old, why = G.parse_share_code("RA8|x|hub|")
        self.assertIsNone(old)
        self.assertIn("10.0", why)

    def test_spoiler_says_how_the_story_starts(self):
        s, _ = self.eng.generate("v90-spoiler", dict(NO_HUB), "balanced")
        text = self.eng.spoiler(s)
        self.assertIn("STORY START", text)
        self.assertIn("prologue (Corson V), then Nefarious City, then Sargasso", text)
        self.assertNotIn("HUB", text)
        self.assertNotIn("Random start", text)

    def test_your_04_settings_generate(self):
        # your 10.0 file with hub = false (its hub = true default is tests/test_v100.py's)
        preset, opts = USER_SETTINGS()
        self.assertEqual(preset, "balanced")
        self.assertFalse(HUB_KEYS & set(opts))
        for ar in (False, True):
            for i in range(60):
                d = self.gen(f"v90-04-{ar}-{i}", dict(opts, restored_weapons=ar), preset)
                self.assertEqual(verify_story_start(d), [])
                s = d["settings"]
                self.assertTrue(s["planet_locks"])
                self.assertEqual(s["campaign_mode"], "planet_shuffle")
                self.assertEqual((s["raritanium_min"], s["raritanium_max"]), (120, 1000))
                self.assertEqual(s["include_arsenal_restored"], ar)

    def test_your_old_8_5_2_settings_still_generate(self):
        preset, opts = USER_SETTINGS(DATA / "user_04_rando_settings_8.5.2.lua")
        self.assertEqual(preset, "hub")
        d = self.gen("v90-old-04", dict(opts, restored_weapons=False), preset)
        self.assertTrue(any("preset hub is gone" in w for w in d["warnings"]), d["warnings"])
        self.assertEqual(verify_story_start(d), [])


class KitTests(unittest.TestCase):
    def test_the_kit_is_one_version(self):
        names = sorted(p.name for p in SCRIPTS.glob("*.lua") if not p.name.startswith("dev("))
        self.assertIn("15_rando_hub.lua", names)           # optional, but part of the release
        from harness import INSTALLED
        # dev 10.12: + 16_rando_spawners, enemy, boss; 10.13: chaos; 10.15: 17_rando_omega (v0.60 player install: 16)
        self.assertEqual(len(names), 16 if INSTALLED else 18, names)
        for p in SCRIPTS.glob("*.lua"):
            self.assertIn('"] = "10.0.27"', p.read_text(encoding="utf-8"), p.name)   # every RANDO_FILES tag, dev files too

    def test_kit_check_passes(self):
        g = Game()
        self.assertEqual(g.load_errors, [])
        g.step(2)
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.27"), [l for l in g.logs() if "KIT" in l])

    def test_hub_keys_do_nothing_without_a_hub(self):
        g = Game()
        g.ready()
        for key in ("]", "[", "/"):
            g.press(key)
            g.press(key, ctrl=True)
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertEqual(list(g.sim.travels.values()), [])
        self.assertIsNone(g.state.hub)


class SettingsFileTests(unittest.TestCase):
    def scripts_with(self, settings_file=None, extra=None):
        d = pathlib.Path(tempfile.mkdtemp(prefix="rando90-"))
        self.addCleanup(shutil.rmtree, d, True)
        for p in SCRIPTS.glob("*.lua"):
            shutil.copy(p, d / p.name)
        if settings_file:
            shutil.copy(settings_file, d / "04_rando_settings.lua")
        for name, src in (extra or {}).items():
            shutil.copy(src, d / name)
        return d

    def start(self, g, seed):
        # seed = "random" and restored_weapons = "auto": what the companion answers
        self.assertEqual(g.bridge("return rando_seed_mode()"), "random")
        g.bridge(f'return rando_use_seed("{seed}")')
        g.bridge("return rando_set_arsenal(false)")
        self.assertTrue(g.wait_seed(), g.logs()[-5:])

    def test_your_settings_file_with_hub_false(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix="rando90-"))
        self.addCleanup(shutil.rmtree, d, True)
        for p in SCRIPTS.glob("*.lua"):
            shutil.copy(p, d / p.name)
        text = (SCRIPTS / "04_rando_settings.lua").read_text(encoding="utf-8")
        (d / "04_rando_settings.lua").write_text(text.replace('  seed = "random",', '  seed = "random", hub = false,', 1), encoding="utf-8")
        g = story_game(settings_file=True, scripts_dir=d)
        self.start(g, "v90-your-04")
        self.assertEqual(g.seed.preset, "balanced")
        self.assertFalse(any("is gone in 9.0" in l for l in g.logs()), [l for l in g.logs() if "gone" in l])
        self.assertTrue(g.seed.planet_locks)
        self.assertFalse(g.seed.travel_lock)
        self.assertIsNone(g.seed.hub)
        play_the_story_start(self, g)

    def test_your_8_5_2_settings_file_still_loads(self):
        # 10.0: its hub options mean something again; preset "hub" is balanced (which has the hub)
        g = story_game(settings_file=True, scripts_dir=self.scripts_with(DATA / "user_04_rando_settings_8.5.2.lua"))
        self.start(g, "v90-old-04")
        self.assertTrue(g.log_has("preset hub is gone"))
        self.assertTrue(g.log_has("story_on_arrival\tis not used since 10.0"))
        self.assertFalse(g.log_has("key_hub\tis gone"))
        self.assertEqual(g.seed.settings.campaign_mode, "planet_shuffle")
        self.assertTrue(g.seed.settings.hub)
        self.assertIsNotNone(g.seed.hub)

    def test_an_8_5_hub_script_is_reported_as_another_version(self):
        d = self.scripts_with(extra={"15_rando_hub.lua": DATA / "old_15_rando_hub_8.5.lua"})
        g = story_game(scripts_dir=d)
        g.step(2)
        self.assertTrue(g.log_has("other versions: 15_rando_hub 8.5.0"), [l for l in g.logs() if "KIT" in l])


class StoryStartTests(unittest.TestCase):
    def test_new_game_plays_the_prologue_then_nefarious_city(self):
        for preset in ("balanced", "campaign", "everything", "planet_shuffle", "campaign_chaos"):
            with self.subTest(preset=preset):
                g = story_game({"preset": preset, "seed": "v90-" + preset})
                play_the_story_start(self, g)
                if g.seed.travel_lock:
                    for pid in ("corson_v", "nefarious_city", "sargasso"):
                        self.assertTrue(g.state.access[pid], pid)

    def test_the_planet_menu_still_locks_planets_with_levels(self):
        g = story_game({"preset": "campaign", "seed": "v90-menu"})
        play_the_story_start(self, g)
        locked = [p.id for p in g.data.planets.values() if not g.state.access[p.id]]
        self.assertTrue(locked)
        names = {"blizar_prime": ("Blizar", "CHK_BLIZAR_A_LANDINGPAD"), "savali": ("Savali", "CHK_SAV_01_LANDING"),
                 "scarstu": ("Zurkon", "CHK_ZURK_LANDING_SHIP"), "torren_iv": ("Torren", "CHK_MOL_01_START"),
                 "cordelion": ("Cordelion", "CHK_CORD_A_START"), "ardolis": ("Ardolis", "CHK_ARD_START"),
                 "viceron": ("Viceron", "CHK_ZORDOOM_START")}
        pid = [p for p in locked if p in names][0]
        event, cp = names[pid]
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cp)
        g.travel(event)
        g.step(400)
        self.assertEqual(len(g.sim.warps), 1, (pid, changes(g)))
        self.assertTrue(g.log_has("locked:\t" + pid))

    def test_campaign_key_says_nothing(self):
        g = story_game({"preset": "balanced"})
        g.companion_restore()
        g.step(60)
        g.press("'")
        g.step(30)
        self.assertEqual(changes(g)["travels"], [])


if __name__ == "__main__":
    unittest.main()
