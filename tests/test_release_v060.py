"""v0.60 public release gates (tools/build_public_release.py, release/).

The PACKAGE is built into a temp folder and its own GAME_FOLDER\\scripts are loaded in the simulator with its own
settings file - what a player installs, not the repo's developer kit.

  * PackageTests: exactly the approved files; Boss / Chaos / developer files absent; v7 DLL; the Arsenal launcher.
  * ExclusionTests: the package's scripts, run: no Boss or Chaos Randomizer, whatever the settings or keys say.
  * PublicDefaultsTests: Enemy Randomizer on, Omega off, Spybots / Lorbs hold nothing, no settings warning.
  * OmegaReleaseTests: Omega rewards in both acquisition orders and New Game+ with the package's scripts
    (omega_weapons = true and the simulator's invented Omega byte - SIMULATOR ONLY).
  * ArsenalLauncherTests: the launcher points at its own script and never overwrites a packaged script;
    with PowerShell 7 (pwsh) the installer is run on a fake game folder.
Nothing here is in-game verification.
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
from test_v1015 import OMEGA_AT, wid, flag, tier, deliver  # noqa: E402
import build_public_release as B  # noqa: E402

_PKG = None


def package():
    """(zip path, extracted package folder), built once per test run"""
    global _PKG
    if _PKG is None:
        out = pathlib.Path(tempfile.mkdtemp(prefix="rando060-"))
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_public_release.py"), "--out", str(out)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        z = next(out.glob("*.zip"))
        ex = out / "x"
        zipfile.ZipFile(z).extractall(ex)
        _PKG = (z, ex / B.NAME)
    return _PKG


def pkg_scripts():
    return package()[1] / "GAME_FOLDER" / "scripts"


def release_game(settings=None, **kw):
    """the package's scripts with the package's own 04_rando_settings.lua (+ extra settings appended)"""
    d = pathlib.Path(tempfile.mkdtemp(prefix="rando060-scripts-"))
    for f in pkg_scripts().glob("*.lua"):
        shutil.copyfile(f, d / f.name)
    # a fixed seed: these tests run without the companion (seed = "random" waits for it)
    settings = dict({"seed": "v060-release", "restored_weapons": False}, **(settings or {}))
    if settings:
        p = d / "04_rando_settings.lua"
        p.write_text(p.read_text(encoding="utf-8") + "\n" + "".join(
            f"RANDO_SETTINGS[{k!r}] = {lua(v)}\n".replace("'", '"') for k, v in settings.items()), encoding="utf-8")
    g = Game(scripts_dir=str(d), settings_file=True, release=True, **kw)
    assert not g.load_errors, g.load_errors
    return g


def lua(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return '"' + v + '"'
    return str(v)


class PackageTests(unittest.TestCase):
    def test_exactly_the_approved_files(self):
        z, pkg = package()
        files = sorted(str(p.relative_to(pkg)).replace(os.sep, "/") for p in pkg.rglob("*") if p.is_file())
        scripts = sorted(B.REQUIRED + B.OPTIONAL)
        want = sorted(B.DOCS + ["VERSION.txt", "SHA256SUMS.txt", "GAME_FOLDER/rivet.toml", "GAME_FOLDER/rando_give.dll"]
                      + ["GAME_FOLDER/scripts/" + s for s in scripts]
                      + ["GAME_FOLDER/rando_companion/" + c for c in B.COMPANION])
        self.assertEqual(files, want)
        self.assertEqual(len(scripts), 16)
        for s in ("16_rando_spawners.lua", "enemy.lua", "17_rando_omega.lua", "15_rando_hub.lua"):
            self.assertIn("GAME_FOLDER/scripts/" + s, files)
        self.assertTrue(z.name.startswith("Ratchet_Rift_Apart_Randomizer_v0.60_"))

    def test_boss_chaos_and_developer_files_are_never_in_it(self):
        names = zipfile.ZipFile(package()[0]).namelist()
        bad = [n for n in names if re.search(r"boss\.lua|chaos\.lua|dev\(|/research/|DEVELOPMENT|TEST_RESULTS|\.py$|spawnpro|testtravel", n, re.I)]
        self.assertEqual(bad, [])
        self.assertEqual(B.EXCLUDED, ["boss.lua", "chaos.lua"])
        # the developer repo keeps both (they are not deleted)
        self.assertTrue((B.KIT and pathlib.Path(B.KIT) / "scripts" / "boss.lua").exists())
        self.assertTrue((pathlib.Path(B.KIT) / "scripts" / "chaos.lua").exists())

    def test_no_player_facing_file_mentions_an_excluded_randomizer(self):
        pkg = package()[1]
        facing = [p for p in pkg.rglob("*") if p.is_file() and (p.suffix in (".md", ".txt", ".bat", ".ps1")
                                                                 or p.name == "04_rando_settings.lua")]
        hits = []
        for p in facing:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if B.EXCLUDED_WORDS.search(line):
                    hits.append(f"{p.name}:{i}: {line.strip()[:80]}")
        self.assertEqual(hits, [])

    def test_the_dll_is_v7_and_the_settings_are_the_players(self):
        import hashlib
        pkg = package()[1]
        self.assertEqual(hashlib.sha256((pkg / "GAME_FOLDER" / "rando_give.dll").read_bytes()).hexdigest(), B.DLL_SHA256)
        self.assertEqual((pkg / "GAME_FOLDER" / "scripts" / "04_rando_settings.lua").read_bytes(),
                         (ROOT / "release" / "04_rando_settings.lua").read_bytes())

    def test_the_same_inputs_give_the_same_zip(self):
        out = pathlib.Path(tempfile.mkdtemp(prefix="rando060-again-"))
        self.addCleanup(shutil.rmtree, out, True)
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_public_release.py"), "--out", str(out)],
                       check=True, capture_output=True)
        self.assertEqual(package()[0].read_bytes(), next(out.glob("*.zip")).read_bytes())


class ExclusionTests(unittest.TestCase):
    def test_no_boss_or_chaos_randomizer_even_when_switched_on(self):
        g = release_game({"boss_randomizer": True, "chaos_randomizer": True})
        g.ready()
        for key in ("=", "BACKSPACE"):
            g.press(key)
            g.press(key, ctrl=True)
        g.travel("Zurkon")
        g.step(600)
        self.assertIsNone(g.g.RANDO_BOSS)
        self.assertIsNone(g.g.RANDO_CHAOS)
        self.assertFalse(g.lua.eval('RANDO_SPAWNERS.V.role_on("boss")'))
        text = "\n".join(g.logs() + g.notes())
        self.assertNotRegex(text, re.compile(r"boss randomizer|chaos randomizer", re.I))
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])


class PublicDefaultsTests(unittest.TestCase):
    def test_a_new_game_with_the_players_settings(self):
        g = release_game()
        g.ready()
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.26"), [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.log_has("RANDO-KIT release v0.62-DEV6 (kit 10.0.26)"))
        # no option the runtime rejects or does not know (the budget note is information, not a complaint)
        complaints = [l for l in g.logs() if "RANDO-SETTINGS" in l and "scaled down to the" not in l]
        self.assertEqual(complaints, [])
        self.assertFalse(g.log_has("RANDO-ERROR"), [l for l in g.logs() if "RANDO-ERROR" in l][:3])
        self.assertFalse(g.log_has("developer files loaded"))
        self.assertTrue(g.lua.eval("RANDO_ENEMY.enabled()"))
        self.assertFalse(g.lua.eval("RANDO.config.enemy_notify"))
        self.assertEqual(g.lua.eval("RANDO.config.enemy_compat"), "all")
        self.assertFalse(g.lua.eval("RANDO.config.enemy_mix_movement"))
        self.assertFalse(g.seed.settings.omega_weapons)
        self.assertFalse(g.seed.settings.collectibles)
        items = {g.seed.locations[lid].item for lid in g.lua.eval("(function() local t = {} for k in pairs(RANDO_SEED.locations) do t[#t + 1] = k end return t end)()").values()}
        self.assertFalse([i for i in items if i and str(i).startswith("omega:")])
        held = [lid for lid in g.lua.eval("(function() local t = {} for k, l in pairs(RANDO_SEED.locations) do if l.item then t[#t + 1] = k end end return t end)()").values()
                if g.data.locations[lid].kind in ("spybot", "lorb", "collectible")]
        self.assertEqual(held, [])
        self.assertTrue(g.lua.eval("RANDO_HUB.returns()"))
        self.assertFalse(g.lua.eval("RANDO.planet_shuffle_on()"))


class OmegaReleaseTests(unittest.TestCase):
    def omega_game(self):
        g = release_game({"omega_weapons": True, "omega_flag_offset": OMEGA_AT})
        g.ready()
        return g

    def test_normal_first_then_omega(self):
        g = self.omega_game()
        g.R.grant("weapon:enforcer")
        deliver(g)
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertEqual(g.give_count("weapon:enforcer"), 1)
        self.assertEqual(flag(g, "enforcer"), 1)
        self.assertEqual(tier(g, "enforcer"), 2)

    def test_omega_first_then_normal(self):
        g = self.omega_game()
        g.R.grant("omega:burst_pistol")
        deliver(g)
        self.assertTrue(g.owns("weapon:burst_pistol"))
        g.R.grant("weapon:burst_pistol")
        deliver(g)
        self.assertEqual(g.give_count("weapon:burst_pistol"), 1)
        self.assertEqual(flag(g, "burst_pistol"), 1)
        self.assertEqual(tier(g, "burst_pistol"), 2)
        g.R.grant("omega:burst_pistol")                                       # the same reward again
        deliver(g)
        self.assertEqual(g.give_count("weapon:burst_pistol"), 1)

    def test_new_game_plus_keeps_the_games_own_omegas(self):
        g = self.omega_game()
        g.sim.give_resets_omega = True
        g.sim.weapons_owned[wid(g, "ricochet")] = True
        g.sim.inv_add(wid(g, "ricochet"))
        g.sim.set_omega(wid(g, "ricochet"), 1)
        g.travel("NefCity")
        deliver(g, 600)
        g.R.grant("weapon:ricochet")
        deliver(g, 1200)
        self.assertEqual(flag(g, "ricochet"), 1)

    def test_every_omega_is_registered_in_the_pool_when_on(self):
        g = release_game({"omega_weapons": True})
        g.ready()
        n = g.lua.eval("#RANDO_GEN.omega_keys(RANDO_SEED.settings)")
        self.assertEqual(n, 20)


class ArsenalLauncherTests(unittest.TestCase):
    def test_the_bat_runs_its_own_script_with_crlf(self):
        comp = package()[1] / "GAME_FOLDER" / "rando_companion"
        raw = (comp / "Install-ArsenalRestored.bat").read_bytes()
        self.assertEqual(raw.replace(b"\r\n", b"").count(b"\n"), 0)
        self.assertIn(b'-File "%~dp0Install-ArsenalRestored.ps1" -Source "%~1"', raw)
        self.assertTrue((comp / "Install-ArsenalRestored.ps1").is_file())
        self.assertTrue(all(b < 128 for b in (comp / "Install-ArsenalRestored.ps1").read_bytes()))

    def test_no_packaged_script_can_be_overwritten_by_the_mods_lua(self):
        ps1 = (package()[1] / "GAME_FOLDER" / "rando_companion" / "Install-ArsenalRestored.ps1").read_text(encoding="ascii")
        ours = re.findall(r'"([a-z_]+\.lua)"', re.search(r"\$ours = @\(([^)]*)\)", ps1).group(1))
        pats = [p.replace("\\\\", "\\") for p in re.findall(r"\$n -match '([^']+)'", ps1)]
        self.assertEqual(len(pats), 2)
        for f in pkg_scripts().glob("*.lua"):
            n = f.name.lower()
            self.assertTrue(n in ours or any(re.search(p, n) for p in pats), n)
        self.assertFalse(any(re.search(p, "arsenal_restored.lua") for p in pats))   # the mod's own scripts still go in

    def test_rivet_toml_already_lists_both_arsenal_paths(self):
        import tomllib
        cfg = tomllib.loads((package()[1] / "GAME_FOLDER" / "rivet.toml").read_text(encoding="utf-8"))
        self.assertIn("mods/ARSENAL_RESTORED", cfg["assets"]["paths"])
        self.assertIn("mods/ARSENAL_RESTORED.stage", cfg["assets"]["paths"])

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 (pwsh) not installed")
    def test_the_installer_on_a_fake_game_folder(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="rando060-arsenal-"))
        self.addCleanup(shutil.rmtree, work, True)
        game = work / "Ratchet & Clank - Rift Apart"
        shutil.copytree(package()[1] / "GAME_FOLDER", game)
        (game / "RiftApart.exe").write_bytes(b"MZ")
        mod = work / "ARSENAL RESTORED 5.7 Beta (RIVET HOOK VERSION).zip"
        with zipfile.ZipFile(mod, "w") as z:
            z.writestr("ARSENAL_RESTORED/info.json", '{"name": "ARSENAL_RESTORED"}')
            z.writestr("ARSENAL_RESTORED/arsenal_restored.lua", "-- the mod")
            z.writestr("ARSENAL_RESTORED/10_rando_runtime.lua", "-- must never replace the randomizer's")
        before = (game / "scripts" / "10_rando_runtime.lua").read_bytes()
        r = subprocess.run(["pwsh", "-NoProfile", "-File", str(game / "rando_companion" / "Install-ArsenalRestored.ps1"),
                            "-Source", str(mod)], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((game / "mods" / "ARSENAL_RESTORED" / "info.json").is_file())
        self.assertTrue((game / "scripts" / "arsenal_restored.lua").is_file())
        self.assertEqual((game / "scripts" / "10_rando_runtime.lua").read_bytes(), before)
        self.assertIn("rivet.toml: already lists mods/ARSENAL_RESTORED", r.stdout)


if __name__ == "__main__":
    unittest.main()
