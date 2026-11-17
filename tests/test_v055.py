"""v0.55: release cleanup.

* Developer-only scripts are named dev(name).lua; a release has none of them and still works.
* 15_rando_hub.lua (planet shuffle) is optional: without it the game's own story plays and every
  location still pays.
* Planet shuffle is OFF by default; the 0 key is the only key a release answers. Without the
  developer keys no message tells the player about ] [ / ; ' . , or the F keys.
* The release package is built without any dev(name).lua file.
Everything here runs against the simulator (tests/sim/rivet_sim.lua), not the real game.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from harness import DEV_DIR, MOD, ROOT, Game, is_dev, script_files  # noqa: E402
from test_v100 import hub, hub_game, to_hub  # noqa: E402

SCRIPTS = MOD / "scripts"
NOT_PLAYER_KEYS = ["[", "]", ";", "/", "'", ".", ","] + [f"F{i}" for i in range(1, 13)]
# text that would tell a player about a developer key or setting
HINTS = ("Ctrl+]", "Ctrl+[", "] next", "] lists", "] to", "[ to", "press /", "Ctrl+;", "Ctrl+.", "Ctrl+,",
         "test_travel", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "to travel", "hub_runtime")


def py(x):
    from test_v100 import py as _py
    return _py(x)


def default_settings(seed):
    """what the player's 04_rando_settings.lua sets (a hub seed)"""
    return {"seed": seed, "preset": "balanced", "hub": True, "distribution": "goldbolts_first", "planet_locks": True,
            "campaign_mode": "planet_shuffle", "shop_weapons": 8, "shop_close_slots": True}


def release_game(seed="v055", settings=None, **kw):
    st = default_settings(seed)
    st.update(settings or {})
    kw.setdefault("release", True)
    g = hub_game(seed, st, **kw)
    return g


def hint_notes(g):
    return [n for n in g.notes() if any(h in n for h in HINTS)]


def parade(g, release=True):
    """New Game up to the moment the parade hands Ratchet back"""
    g.sim.new_game()
    g.step(60)
    g.sim.parade_control()
    g.step(1500)
    g.sim.parade_wrench()
    g.step(30)
    if release:
        g.sim.parade_release()
    g.step(600)


class ReleaseFilesTests(unittest.TestCase):
    def test_the_release_loads_without_any_developer_file(self):
        files = script_files(release=True)
        self.assertFalse([f.name for f in files if is_dev(f.name)])
        self.assertIn("15_rando_hub.lua", [f.name for f in files])
        g = Game(release=True, settings={"seed": "v055-release"}, dll_version=6)
        self.assertEqual(g.load_errors, [])
        g.ready()
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.18"), [l for l in g.logs() if "KIT" in l])
        self.assertFalse(g.log_has("developer files loaded"))
        self.assertFalse(g.log_has("RANDO-ERROR"))
        for name in ("RANDO_DEV_KEYS", "RANDO_TEST_TRAVEL", "RANDO_TEST_MODE", "RANDO_PROBE", "RANDO_VTABLES"):
            self.assertIsNone(g.g[name], name)

    def test_every_developer_file_follows_the_naming_and_is_listed(self):
        dev = sorted(p.name for p in DEV_DIR.glob("*.lua") if is_dev(p.name))
        self.assertEqual(dev, ["dev(item_ids).lua", "dev(keys).lua", "dev(probe).lua", "dev(spawnprobe).lua", "dev(spawnproof).lua", "dev(testmode).lua",
                               "dev(testtravel).lua", "dev(vtables).lua"])
        for p in list(SCRIPTS.glob("*.lua")) + [DEV_DIR / n for n in dev]:
            text = p.read_text(encoding="utf-8")
            if is_dev(p.name):
                self.assertIn("DEVELOPER TOOL - not part of a release", text.splitlines()[0], p.name)
                self.assertIn(f'RANDO_FILES["{p.name[:-4]}"]', text, p.name)
            else:
                self.assertNotIn("DEVELOPER TOOL", text, p.name)
        g = Game(test_mode=True, dev_tools=True)
        self.assertEqual(g.load_errors, [])
        g.ready()
        self.assertTrue(g.log_has("developer files loaded (not part of a release): dev(item_ids), dev(keys), dev(probe), "
                                  "dev(testmode), dev(testtravel), dev(vtables)"))
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts"))
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_no_release_script_names_a_developer_file_it_needs(self):
        for p in SCRIPTS.glob("*.lua"):
            if is_dev(p.name):
                continue
            text = p.read_text(encoding="utf-8")
            for old in ("16_rando_testtravel", "07_rando_testmode", "08_rando_probe", "06_rando_vtables", "06_rando_item_ids",
                        "extras/", "extras\\"):
                if old == "16_rando_testtravel" and p.name == "10_rando_runtime.lua":
                    continue                       # R.GONE_FILES: reported when an old copy is left behind
                self.assertNotIn(old, text, (p.name, old))

    def test_an_old_test_travel_file_left_behind_is_reported(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix="rando055-"))
        self.addCleanup(shutil.rmtree, d, True)
        for f in script_files(release=True):
            shutil.copy(f, d / f.name)
        old = subprocess.run(["git", "show", "HEAD:mod/RiftApartRandomizer/scripts/16_rando_testtravel.lua"],
                             cwd=ROOT, capture_output=True, text=True)
        if old.returncode != 0:
            self.skipTest("git history with the v0.54 file is needed")
        (d / "16_rando_testtravel.lua").write_text(old.stdout, encoding="utf-8")
        g = Game(scripts_dir=d, release=True)
        g.step(3)
        self.assertTrue(g.log_has("delete from the scripts folder: 16_rando_testtravel.lua"))

    def test_the_probe_finds_its_data_whatever_the_load_order(self):
        g = Game(dev_tools=True)
        self.assertIsNotNone(g.g.RANDO_VTABLES)
        P = g.g.RANDO_PROBE
        P.build_test_items()
        self.assertGreater(len(list(P.test_items.values())), 10)
        # the data loading after the probe (another loader's order) changes nothing
        files = sorted(script_files(dev_tools=True), key=lambda f: (f.name == "dev(item_ids).lua", f.name))
        g2 = Game(files=files)
        self.assertEqual(g2.load_errors, [])
        g2.g.RANDO_PROBE.build_test_items()
        self.assertGreater(len(list(g2.g.RANDO_PROBE.test_items.values())), 10)


class PlayerKeyTests(unittest.TestCase):
    def test_only_zero_answers_and_nothing_hints_at_other_keys(self):
        g = release_game("v055-keys", planet_shuffle=False)
        g.ready(frames=3000)                                  # the start items have all arrived
        before = len(g.notes())
        for key in NOT_PLAYER_KEYS:
            g.press(key)
            g.press(key, ctrl=True)
            g.press(key, ctrl=True)
        g.step(60)
        self.assertEqual(g.notes()[before:], [])
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertFalse(g.log_has("RANDO-KEY\t"), [l for l in g.logs() if "RANDO-KEY\t" in l])
        g.press("0")
        g.step(10)
        self.assertTrue(g.note_has("planet shuffle ON"))
        self.assertTrue(g.R.planet_shuffle_on())
        g.press("0")
        g.step(10)
        self.assertTrue(g.note_has("planet shuffle OFF"))
        self.assertFalse(g.R.planet_shuffle_on())
        self.assertEqual(hint_notes(g), [])

    def test_ctrl_zero_twice_gives_items_back(self):
        g = release_game("v055-restore", planet_shuffle=False)
        g.ready()
        g.press("0", ctrl=True)
        self.assertTrue(g.note_has("press Ctrl+0 again"))
        g.press("0", ctrl=True)
        self.assertTrue(g.note_has("sending"))
        self.assertFalse(g.R.planet_shuffle_on())             # Ctrl+0 is not the shuffle toggle

    def test_the_keys_log_line_names_only_the_player_key(self):
        g = release_game("v055-log", planet_shuffle=False)
        line = next(l for l in g.logs() if "RANDO-KEYS" in l)
        self.assertIn("planet shuffle 0", line)
        for k in ("hub ]", "status ;", "test travel"):
            self.assertNotIn(k, line)

    def test_a_planet_shuffle_run_never_hints_at_developer_keys(self):
        g = to_hub(release_game("v055-hub"))
        self.assertTrue(hub(g)["started"])
        self.assertTrue(g.note_has("Travel with the ship's planet menu"))
        g.sim.complete_mission("MIS_NEFCITY_01")
        g.step(3000)
        # the ship's planet menu takes you to an open planet; its destination starts there
        g.R.grant("access:savali")
        g.step(30)
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_SAV_01_LANDING",
               InterplanetaryCheckpointName="CHK_TRANSITION_TO_SAVALI")
        g.travel("Savali")
        g.step(2400)
        self.assertEqual(hub(g).get("current"), "savali_1")
        g.sim.complete_mission("MIS_SAV_01")
        g.step(3000)
        self.assertIn("savali_1", hub(g)["done"])
        self.assertEqual(hint_notes(g), [])
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_with_the_developer_keys_the_hints_come_back(self):
        g = to_hub(hub_game("v055-devkeys"))
        self.assertTrue(g.note_has("] lists what is open, Ctrl+] goes"))


class PlanetShuffleDefaultTests(unittest.TestCase):
    def test_off_by_default_the_story_is_the_games_own(self):
        g = release_game("v055-off", planet_shuffle=False)
        g.companion_restore()
        parade(g)
        g.step(3000)
        self.assertIsNone(g.state.planet_shuffle)
        self.assertFalse(bool(g.state.hub and g.state.hub.started))
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertFalse(g.g.RANDO_TRAVEL.active())
        self.assertIn("planet shuffle OFF (0 turns it on)", g.R.status_text())
        # the game's own travel: prologue -> Nefarious City
        g.sim.set_mission("MIS_INTRO", 4)
        g.step(30)
        g.travel("NefCity")
        g.step(600)
        self.assertEqual(g.state.current_planet, "nefarious_city")
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertTrue(g.state.collected["planet:corson_v"])

    def test_on_during_the_parade_the_hub_starts_after_it(self):
        g = release_game("v055-early", planet_shuffle=False)
        g.companion_restore()
        g.sim.new_game()
        g.step(60)
        g.press("0")                                          # during the parade
        g.sim.parade_control()
        g.step(1500)
        g.sim.parade_wrench()
        g.step(30)
        g.sim.parade_release()
        for _ in range(60):
            g.step(30)
            if g.state.hub is not None and g.state.hub.started and g.sim.planet == "NefCity":
                break
        self.assertTrue(hub(g)["started"])
        self.assertEqual(g.sim.planet, "NefCity")

    def test_on_after_the_parade_waits_for_the_next_new_game(self):
        g = release_game("v055-late", planet_shuffle=False)
        g.companion_restore()
        parade(g)
        g.sim.set_mission("MIS_INTRO", 4)
        g.travel("NefCity")
        g.step(600)
        g.press("0")
        g.step(3000)
        self.assertTrue(g.log_has("the hub starts with the next New Game"))
        self.assertTrue(g.R.planet_shuffle_on())
        self.assertFalse(bool(g.state.hub and g.state.hub.started))
        self.assertEqual(list(g.sim.warps.values()), [])      # a run past the parade is never moved
        self.assertFalse(g.g.RANDO_TRAVEL.active())           # nor is its travel locked
        # the next New Game keeps the choice and starts the hub after its parade
        g.sim.set_mission("MIS_INTRO", 2, False)
        parade(g)
        for _ in range(60):
            g.step(30)
            if g.state.hub is not None and g.state.hub.started:
                break
        self.assertTrue(g.state.planet_shuffle)
        self.assertTrue(hub(g)["started"])


def play_the_games_order(test, g, menu=True):
    """every story mission in the game's own order, every Gold Bolt of each planet visited;
    returns the locations that never paid"""
    C, DB = g.g.RANDO_CAMPAIGN, g.data
    planets = {p.id: p for p in DB.planets.values()}
    g.companion_restore()
    g.sim.new_game()
    g.step(60)
    current = "corson_v"
    bolts_taken = set()
    for seg in py(C.SEGMENTS):
        pid = seg["planet"]
        if pid != current:
            name = list(planets[pid].event_names.values())[0]
            if menu:
                g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=seg.get("entry") or "CHK_X",
                       InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
            g.travel(name)
            g.step(400)
            current = pid
        for m in seg["missions"]:
            g.fire("MissionStateChangedEvent", MissionName=m, MissionState=4)
            g.step(5)
        if pid not in bolts_taken:
            bolts_taken.add(pid)
            prefix = list(planets[pid].bolt_prefixes.values())[0]
            n = sum(1 for lid in py(g.seed.locations) if g.data.locations[lid].kind == "goldbolt"
                    and g.data.locations[lid].planet == pid)
            for i in range(1, n + 1):
                g.fire("GainGoldBoltEvent", BoltName=f"{prefix.title()} {i}")
        test.assertEqual(g.state.current_planet, pid)
    g.step(600)
    unpaid = []
    for lid in py(g.seed.locations):
        if g.data.locations[lid].kind in ("goldbolt", "planet", "story", "side") and not g.state.paid[lid]:
            unpaid.append(lid)
    return sorted(unpaid)


class HubAbsentTests(unittest.TestCase):
    WITHOUT = ("15_rando_hub.lua",)

    def test_without_the_hub_everything_loads_and_the_story_is_the_games(self):
        g = release_game("v055-nohub", without=self.WITHOUT, planet_shuffle=False)
        self.assertEqual(g.load_errors, [])
        self.assertIsNone(g.g.RANDO_HUB)
        g.companion_restore()
        g.step(3)
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.18 (15_rando_hub not installed)"))
        self.assertTrue(g.seed.hub)                           # the seed is the same seed
        self.assertFalse(g.R.planet_shuffle_on())
        parade(g)
        g.sim.set_mission("MIS_INTRO", 4)
        g.travel("NefCity")
        g.step(600)
        g.sim.set_mission("MIS_NEFCITY_01", 4)
        g.travel("Sargasso")
        g.step(600)
        self.assertEqual(g.state.current_planet, "sargasso")
        self.assertEqual(list(g.sim.warps.values()), [])
        self.assertEqual([c.kind for c in (g.sim.mission_calls or {}).values() if c.kind not in ("query", 1)], [])
        before = len(g.notes())
        g.press("0")                                          # nothing to turn on: no message
        g.step(10)
        self.assertEqual(g.notes()[before:], [])
        g.press("0", ctrl=True)
        self.assertTrue(g.note_has("press Ctrl+0 again"))     # giving items back still works
        self.assertFalse(g.log_has("RANDO-ERROR"))
        self.assertEqual(hint_notes(g), [])

    def test_without_the_hub_every_location_pays_in_the_games_order(self):
        for seed, preset in (("v055-run-1", "balanced"), ("v055-run-2", "chaos"), ("v055-run-3", "everything")):
            with self.subTest(seed=seed):
                g = release_game(seed, {"preset": preset}, without=self.WITHOUT, planet_shuffle=False)
                self.assertEqual(play_the_games_order(self, g), [])
                self.assertEqual(sorted(k for k, v in py(g.state.access).items() if v), sorted(p.id for p in g.data.planets.values()))
                self.assertEqual(list(g.sim.warps.values()), [])
                self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_with_the_hub_and_planet_shuffle_off_the_same_run_pays_the_same(self):
        g = release_game("v055-run-1", planet_shuffle=False)
        self.assertEqual(play_the_games_order(self, g), [])
        self.assertEqual(list(g.sim.warps.values()), [])


class TestTravelAbsentTests(unittest.TestCase):
    def test_locked_travel_works_without_test_travel(self):
        from story_helpers import level_game, started
        g = started(level_game("v055-lock", release=True))
        self.assertIsNone(g.g.RANDO_TEST_TRAVEL)
        locked = next(p.id for p in g.data.planets.values() if not g.state.access[p.id])
        name = list(g.data.planets[[k for k, p in g.data.planets.items() if p.id == locked][0]].event_names.values())[0]
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName="CHK_ANY", InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.travel(name)
        g.step(900)
        self.assertTrue(g.log_has("locked: " + locked) or g.log_has("locked:\t" + locked), [l for l in g.logs() if "locked" in l])
        self.assertFalse(g.log_has("RANDO-ERROR"))

    def test_coordinates_still_open_planets_without_test_travel(self):
        g = release_game("v055-coords", planet_shuffle=False)
        g.ready()
        g.R.grant("access:savali")
        self.assertTrue(g.state.access.savali)
        self.assertTrue(g.note_has("you can fly to Savali now"))


class PackageTests(unittest.TestCase):
    def test_the_package_has_no_developer_file_and_every_required_script(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="rando055-pkg-"))
        self.addCleanup(shutil.rmtree, out, True)
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_public_release.py"), "--out", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        zips = list(out.glob("*.zip"))
        self.assertEqual(len(zips), 1)
        names = zipfile.ZipFile(zips[0]).namelist()
        self.assertEqual([n for n in names if "dev(" in n or "extras" in n or "research" in n or "Install-Arsenal" in n], [])
        scripts = sorted(n.rsplit("/", 1)[1] for n in names if "/GAME_FOLDER/scripts/" in n and n.endswith(".lua"))
        want = sorted(p.name for p in SCRIPTS.glob("*.lua") if not is_dev(p.name) and p.name not in ("chaos.lua", "17_rando_omega.lua"))
        self.assertEqual(scripts, want)
        self.assertEqual(len(scripts), 16)                      # dev 10.12: + 16_rando_spawners, enemy, boss
        self.assertNotIn("chaos.lua", scripts)                  # dev 10.13: held back from player packages
        self.assertNotIn("17_rando_omega.lua", scripts)         # dev 10.15: likewise, until it has run in the game
        # the same inputs give the same bytes
        out2 = pathlib.Path(tempfile.mkdtemp(prefix="rando055-pkg2-"))
        self.addCleanup(shutil.rmtree, out2, True)
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_public_release.py"), "--out", str(out2)], check=True,
                       capture_output=True)
        self.assertEqual(zips[0].read_bytes(), next(out2.glob("*.zip")).read_bytes())


if __name__ == "__main__":
    unittest.main()
