"""v0.75 (kit 10.0.39): the public release built on v0.71-DEV9, and the LITE package for NexusMods.

  * DefaultsTests: the player's settings - planet shuffle OFF, Enemy Randomizer OFF, Omega weapons ON; the code defaults
    for the enemy compatibility are the safe ones again ("all", movement groups kept apart).
  * HubReturnTests: the trip back to Nefarious City after a finished planet with planet shuffle OFF, ON, and switched ON
    in a run that is past the parade (v0.75 fix: that return used to land as the hub's start and started the campaign
    in the middle of the player's own run - other planets' missions primed, travel locked).
  * LiteTests: the Lite package's own scripts and settings, NO rando_give.dll and NO companion: the start without
    waiting, the fixed seed, the spoiler in rivet.log, rewards that never wait for Coordinates, Bolts / Raritanium
    through the AddToInventoryAction node (with its count), the trip back, and the 0 key.
  * LitePackageTests: tools/build_lite_release.py - no DLL, no .bat / .ps1, no script that needs the DLL.

Everything here runs against the simulator (tests/sim/rivet_sim.lua), NOT the real game.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_v060 import off_game, go, finish, warps, sub_has, HUB_PLANET  # noqa: E402
from test_v100 import hub, hub_game, to_hub, choose, py  # noqa: E402
import build_lite_release as L  # noqa: E402

NODE_ADDR = 0x5000
NODE_ITEM = "98F2996246EB8469"          # the item a Nefarious City AddToInventoryAction node holds (VersaGlove, round 7)


def node(gm):
    """one real AddToInventoryAction node, as Nefarious City keeps them (route 1)"""
    gm.sim.map(NODE_ADDR, 0x80)
    gm.sim.put_hex_id(NODE_ADDR + 0x60, NODE_ITEM)
    gm.sim.put_u32(NODE_ADDR + 0x68, 1)
    gm.lua.execute('SIM.nodes = { { component = 111, actor = 222, uid = "98763a0c6fd24259",'
                   ' class = "AddToInventoryAction", addr = 0x5000, outputs = {} } }')


_LITE = None


def lite_package():
    global _LITE
    if _LITE is None:
        out = pathlib.Path(tempfile.mkdtemp(prefix="rando075-lite-"))
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_lite_release.py"), "--out", str(out)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        z = next(out.glob("*.zip"))
        zipfile.ZipFile(z).extractall(out / "x")
        _LITE = (z, out / "x" / L.NAME)
    return _LITE


def lite_game(extra=None, with_node=True, **kw):
    """the Lite package's scripts with its own settings file, no DLL, no companion"""
    d = pathlib.Path(tempfile.mkdtemp(prefix="rando075-scripts-"))
    for f in (lite_package()[1] / "GAME_FOLDER" / "scripts").glob("*.lua"):
        shutil.copyfile(f, d / f.name)
    if extra:
        p = d / "04_rando_settings.lua"
        p.write_text(p.read_text(encoding="utf-8") + "\n" + "".join(
            f"RANDO_SETTINGS[\"{k}\"] = {('true' if v is True else 'false' if v is False else repr(v).replace(chr(39), chr(34)))}\n"
            for k, v in extra.items()), encoding="utf-8")
    def setup(gm):
        gm.sim.auto_travel = True                    # a warp lands (as hub_game sets it)
        if with_node:
            node(gm)
    g = Game(scripts_dir=str(d), settings_file=True, release=True, dll=False, before_scripts=setup, **kw)
    assert not g.load_errors, g.load_errors
    return g


def lite_start(g, frames=900):
    assert g.wait_seed(), g.logs()[-5:]
    g.travel("NefCity")
    g.step(frames)
    return g


class DefaultsTests(unittest.TestCase):
    def test_the_kit_code_defaults(self):
        g = Game(settings={"seed": "v075-code"})
        self.assertFalse(g.lua.eval("RANDO.config.enemy_randomizer"))
        self.assertEqual(g.lua.eval("RANDO.config.enemy_compat"), "all")
        self.assertFalse(g.lua.eval("RANDO.config.enemy_mix_movement"))
        self.assertFalse(g.lua.eval("RANDO.config.lite"))
        self.assertTrue(g.lua.eval("RANDO.config.bank_rewards"))

    def test_the_developer_settings_file_has_the_enemy_randomizer_off_too(self):
        g = Game(settings_file=True)
        self.assertFalse(g.lua.eval("RANDO_SETTINGS.enemy_randomizer"))
        self.assertTrue(g.log_has("RANDO-ENEMY\tinstalled (OFF until the save says otherwise)"),
                        [l for l in g.logs() if "RANDO-ENEMY" in l][:3])

    def test_the_release_banner(self):
        g = Game(settings={"seed": "v075-banner"}).ready()
        self.assertTrue(g.log_has("RANDO-KIT release v0.75 (kit 10.0.39)"))
        self.assertTrue(g.note_has("Randomizer v0.75 - seed"))


class HubReturnTests(unittest.TestCase):
    def test_planet_shuffle_off(self):
        g = off_game("v075-off")
        self.assertFalse(g.g.RANDO.planet_shuffle_on())
        go(g, "savali")
        before = len(warps(g))
        finish(g, "savali_1")
        self.assertTrue(sub_has(g, "Back to Nefarious City in 12 s"))
        g.step(13 * 60 + 700)
        self.assertGreater(len(warps(g)), before)
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertFalse(hub(g).get("started"))

    def test_planet_shuffle_on(self):
        g = to_hub(hub_game("v075-on", {"hub_return_delay": 12}))
        self.assertTrue(g.g.RANDO.planet_shuffle_on())
        g.R.grant("access:savali")
        g.step(30)
        choose(g, "savali_1", frames=3000)
        before = len(warps(g))
        finish(g, "savali_1")
        self.assertTrue(sub_has(g, "Back to Nefarious City in 12 s"))
        g.step(13 * 60 + 700)
        self.assertGreater(len(warps(g)), before)
        self.assertEqual(g.state.current_planet, HUB_PLANET)

    def test_switched_on_past_the_parade_it_is_a_plain_trip_back(self):
        g = off_game("v075-mid")
        g.step(600)
        g.g.RANDO_HUB.set_shuffle(True, "the 0 key")
        g.step(60)
        self.assertTrue(g.g.RANDO.planet_shuffle_on())
        go(g, "sargasso")
        before = len(warps(g))
        missions_before = dict(py(g.sim.set_state_calls)) if g.sim.set_state_calls else {}
        finish(g, "sargasso_1")
        self.assertTrue(g.log_has("finished (the hub has not started) - back to the hub in"))
        g.step(13 * 60 + 700)
        self.assertEqual(len(warps(g)) - before, 1)
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertTrue(g.log_has("planet shuffle starts with your next New Game"))
        # the hub did NOT start: no campaign start, no other planet's mission primed, nothing written
        self.assertFalse(hub(g).get("started"))
        self.assertFalse(g.log_has("the campaign starts at"))
        self.assertFalse(any("prime\t" in l for l in g.logs()), [l for l in g.logs() if "prime" in l][:3])
        after = dict(py(g.sim.set_state_calls)) if g.sim.set_state_calls else {}
        self.assertEqual(after, missions_before)
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])


class LiteTests(unittest.TestCase):
    def test_starts_without_the_companion_and_without_the_dll(self):
        g = lite_start(lite_game())
        self.assertTrue(g.log_has("RANDO-LITE the Lite package"))
        self.assertTrue(g.log_has("RANDO-SEED generating seed\trift-lite-test"), [l for l in g.logs() if "SEED" in l][:4])
        self.assertTrue(g.log_has("RANDO-SAVE Lite: no companion"))
        self.assertTrue(g.note_has("Randomizer Lite: seed rift-lite-test"))
        self.assertFalse(g.note_has("start the companion"))
        self.assertFalse(g.note_has("companion is not running"))
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.39"), [l for l in g.logs() if "KIT" in l])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])
        # the settings file is taken whole: no option rejected
        self.assertEqual([l for l in g.logs() if "RANDO-SETTINGS" in l and "scaled down" not in l and "below" not in l], [])
        s = g.seed.settings
        self.assertFalse(s.armor)
        self.assertFalse(s.omega_weapons)
        self.assertFalse(s.weapon_xp)
        self.assertFalse(s.shop_bonus)
        self.assertEqual(s.shop_weapons, 0)
        self.assertIsNone(g.g.RANDO_SPAWNERS)
        self.assertIsNone(g.g.RANDO_OMEGA)

    def test_the_start_arrives_through_the_node(self):
        g = lite_start(lite_game(), frames=2400)
        start = list(g.seed.start["items"].values())
        real = [k for k in start if g.data.real_items[k] is not None]
        self.assertTrue(real)
        for k in real:
            self.assertEqual(g.item_status(k), "confirmed", k)
            self.assertTrue(g.owns(k), k)
        self.assertEqual(g.sim.get_hex_id(NODE_ADDR + 0x60), NODE_ITEM)      # put back every time
        self.assertEqual(g.sim.get_u32(NODE_ADDR + 0x68), 1)

    def test_a_random_seed_falls_back_to_the_fixed_one(self):
        g = lite_start(lite_game({"seed": "random"}), frames=300)
        self.assertTrue(g.log_has('RANDO-LITE seed = "random" needs the companion'))
        self.assertEqual(g.seed.seed, "rift-lite-test")

    def test_the_spoiler_goes_into_rivet_log(self):
        g = lite_start(lite_game(), frames=600)
        self.assertTrue(g.log_has("RANDO-SPOILER ---- the spoiler of seed rift-lite-test"))
        self.assertTrue(g.log_has("RANDO-SPOILER ---- end of the spoiler ----"))
        lines = [l for l in g.logs() if "RANDO-SPOILER" in l]
        self.assertGreater(len(lines), 50)
        off = lite_start(lite_game({"spoiler_log": False}), frames=600)
        self.assertFalse(off.log_has("RANDO-SPOILER"))

    def test_bolts_and_raritanium_go_through_the_node_with_their_amount(self):
        g = lite_start(lite_game(), frames=2400)
        bolts = g.data.real_items["currency:bolts"].id
        have = g.sim.currency[bolts] or 0
        lid = g.location_with(lambda l, it: it and str(it).startswith("filler:bolts:"))
        amount = int(str(g.seed.locations[lid].item).split(":")[2])
        self.assertTrue(g.R.collect(lid, "test"))
        g.step(900)
        self.assertEqual((g.sim.currency[bolts] or 0) - have, amount, [l for l in g.logs() if "RANDO-REAL" in l][-5:])
        self.assertTrue(g.log_has(f"sent\t{amount}\tcurrency:bolts"))
        self.assertEqual(len(g.state.currency_queue or {}), 0)
        self.assertEqual(g.sim.get_hex_id(NODE_ADDR + 0x60), NODE_ITEM)
        self.assertEqual(g.sim.get_u32(NODE_ADDR + 0x68), 1)                # the count is put back too
        # never twice
        g.step(1800)
        self.assertEqual((g.sim.currency[bolts] or 0) - have, amount)

    def test_rewards_wait_on_nefarious_city_and_never_for_coordinates(self):
        g = lite_start(lite_game(), frames=2400)
        locked = next(p.id for p in g.data.planets.values() if not g.state.access[p.id] and p.id != "nefarious_city")
        lid = g.location_with(lambda l, it: g.data.locations[l].planet == locked and g.data.locations[l].kind != "goldbolt"
                              and it and str(it).startswith("weapon:"))
        if lid is None:
            lid = g.location_with(lambda l, it: g.data.locations[l].planet == locked and g.data.locations[l].kind != "goldbolt" and it)
        self.assertIsNotNone(lid)
        self.assertTrue(g.R.collect(lid, "test"))
        self.assertTrue(g.state.paid[lid])                                     # paid at once
        self.assertIsNone(g.state.banked[lid])
        self.assertFalse(g.note_has("Banked:"))

    def test_the_trip_back_to_the_hub(self):
        g = lite_start(lite_game({"hub_return_delay": 12}), frames=600)
        go(g, "savali")
        before = len(warps(g))
        finish(g, "savali_1")
        self.assertTrue(sub_has(g, "Back to Nefarious City in 12 s"))
        g.step(13 * 60 + 700)
        self.assertGreater(len(warps(g)), before)
        self.assertEqual(g.state.current_planet, HUB_PLANET)
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])

    def test_the_zero_key_says_planet_shuffle_is_the_full_releases(self):
        g = lite_start(lite_game(), frames=300)
        g.press("0")
        g.step(5)
        self.assertTrue(g.note_has("planet shuffle needs the full release"))
        self.assertFalse(g.g.RANDO.planet_shuffle_on())
        g.g.RANDO.state.planet_shuffle = True                                   # even an old state that had it on
        self.assertFalse(g.g.RANDO.planet_shuffle_on())

    def test_without_a_node_rewards_wait_with_a_lite_hint(self):
        g = lite_game(with_node=False)
        assert g.wait_seed()
        g.travel("Sargasso")
        g.step(1500)
        self.assertTrue(g.note_has("Lite: rewards are handed over there"), g.notes()[-4:])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])


class LitePackageTests(unittest.TestCase):
    def test_no_dll_no_companion_no_dll_only_script(self):
        z, pkg = lite_package()
        files = sorted(str(p.relative_to(pkg)).replace(os.sep, "/") for p in pkg.rglob("*") if p.is_file())
        want = sorted([n for n, _ in L.DOCS] + ["VERSION.txt", "SHA256SUMS.txt", "GAME_FOLDER/rivet.toml"]
                      + ["GAME_FOLDER/scripts/" + s for s in L.SCRIPTS])
        self.assertEqual(files, want)
        self.assertEqual(len(L.SCRIPTS), 13)
        names = zipfile.ZipFile(z).namelist()
        self.assertEqual([n for n in names if re.search(r"\.(dll|exe|bat|ps1)$|rando_companion|boss\.lua|chaos\.lua|enemy\.lua|"
                                                        r"16_rando|17_rando|dev\(", n, re.I)], [])
        toml = (pkg / "GAME_FOLDER" / "rivet.toml").read_text()
        self.assertNotIn("dll_path", toml)
        self.assertRegex(toml, r"\[renderdoc\][^\[]*enabled = false")
        self.assertRegex(toml, r"\[bridge\][^\[]*enabled = false")
        self.assertTrue(z.name.startswith("Ratchet_Rift_Apart_Randomizer_v0.75_Lite_"))

    def test_the_build_refuses_a_dll_or_a_companion(self):
        self.assertEqual(L.check(), [])
        self.assertTrue(L.BINARY.search("GAME_FOLDER/rando_give.dll"))
        self.assertTrue(L.BINARY.search("GAME_FOLDER/rando_companion/Start-Companion.bat"))

    def test_the_same_inputs_give_the_same_zip(self):
        z, _ = lite_package()
        out = pathlib.Path(tempfile.mkdtemp(prefix="rando075-lite-again-"))
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_lite_release.py"), "--out", str(out)], check=True,
                       capture_output=True)
        self.assertEqual((out / z.name).read_bytes(), z.read_bytes())


if __name__ == "__main__":
    unittest.main()
