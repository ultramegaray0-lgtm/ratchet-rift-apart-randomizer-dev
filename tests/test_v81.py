"""Randomizer 8.1: the fixes for what your round 17 rivet.log showed.

  * 09_rando_real.lua:672 called a local before its definition (an error on every planet change)
  * Torren IV and Cordelion: "no checkpoint known" (they have no LANDING / SHIP / DEFAULT
    checkpoint): the checkpoint catalog places checkpoints by area and name and scores them
  * a planet-menu landing is remembered as that planet's checkpoint
  (9.0: the hub's trips, its catalog wait and its level bits are gone with the hub)
  * the shop search ran past rivet_hook's 8 ms frame budget every time: it is now sliced
  * mission names your game does not have are gone from the registry
  * ARSENAL_RESTORED's rivet_hook version: rivet.toml lists its folder, an installer puts it there
The game here is the simulator (tests/sim/rivet_sim.lua), NOT your game.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402
from story_helpers import level_game, started  # noqa: E402

MOD = os.path.join(ROOT, "mod", "RiftApartRandomizer")
SCRIPTS = os.path.join(MOD, "scripts")


def forward_local_uses(path):
    """uses of a top-level local (`local function f` / `local f =` at column 0) on lines above its
    definition: inside a function body that is a global lookup, nil at run time"""
    lines = open(path, encoding="utf-8").read().splitlines()
    defs = {}
    for i, line in enumerate(lines):
        m = re.match(r"local function ([A-Za-z_]\w*)", line) or re.match(r"local ([A-Za-z_][\w, ]*)\s*=", line)
        if m:
            for n in re.split(r"\s*,\s*", m.group(1).strip()):
                defs.setdefault(n, i)
    bad = []
    for n, d in defs.items():
        pat = re.compile(r"(?<![\w.:])" + re.escape(n) + r"\b")
        for i in range(d):
            s = re.sub(r"--.*", "", lines[i])
            s = re.sub(r"\"[^\"]*\"|'[^']*'", "", s)
            if pat.search(s) and not re.search(r"\blocal\b[^=]*\b" + re.escape(n) + r"\b", s):
                bad.append("%s:%d %s" % (os.path.basename(path), i + 1, n))
    return bad


class StaticTests(unittest.TestCase):
    # R.status_text has a function-local `total` of its own (checked by hand)
    ALLOWED_NAMES = {("10_rando_runtime.lua", "total")}   # by file and name (its line moves between versions)

    def test_no_top_level_local_is_used_before_its_definition(self):
        bad = []
        for name in sorted(os.listdir(SCRIPTS)):
            if name.endswith(".lua"):
                bad += forward_local_uses(os.path.join(SCRIPTS, name))
        self.assertEqual([b for b in bad if (b.split(":")[0], b.split(" ")[-1]) not in self.ALLOWED_NAMES], [])

    def test_registry_has_no_name_your_game_lacks(self):
        # round 17 research: "not a mission in your game"
        g = Game(settings={"seed": "v81-reg", "preset": "hub"})
        missing = {"MIS_BLIZAR_01", "MIS_CORD_BOSS", "MIS_ZURK_02", "MIS_SARG_02_REVISIT", "MIS_MEGA_01_RIVET"}
        for seg in g.g.RANDO_CAMPAIGN.SEGMENTS.values():
            for m in seg.missions.values():
                self.assertNotIn(m, missing)

    def test_rivet_toml_loads_arsenal_restored(self):
        text = open(os.path.join(MOD, "rivet.toml"), encoding="utf-8").read()
        m = re.search(r"(?ms)^\[assets\].*?^paths\s*=\s*\[([^\]]*)\]", text)
        self.assertTrue(m)
        paths = re.findall(r'"([^"]*)"', m.group(1))
        self.assertIn("mods/default", paths)
        self.assertIn("mods/ARSENAL_RESTORED", paths)
        self.assertIn("mods/ARSENAL_RESTORED.stage", paths)
        for f in ("Install-ArsenalRestored.ps1", "Install-ArsenalRestored.bat"):      # removed in v0.55, back in v0.60
            self.assertTrue(os.path.exists(os.path.join(MOD, "companion", f)), f)
        comp = open(os.path.join(MOD, "companion", "RandoCompanion.ps1"), encoding="utf-8").read()
        self.assertIn("Find-LooseArsenal", comp)

    def test_planet_data_has_area_fragments_for_every_planet(self):
        g = Game(settings={"seed": "v81-areas", "preset": "hub"})
        for p in g.data.planets.values():
            self.assertTrue(len(list(p.checkpoints.areas.values())) >= 1, p.id)


class CatalogTests(unittest.TestCase):
    def catalog(self, g, frames=600):
        T = g.g.RANDO_TRAVEL
        for _ in range(frames // 30):
            g.step(30)
            if T.catalog and T.catalog.done:
                break
        self.assertTrue(T.catalog and T.catalog.done)
        return T

    def test_every_planet_gets_a_checkpoint_and_never_a_tunnel(self):
        g = started(level_game("v81-cat"))
        T = self.catalog(g)
        # 8.4: a planet's story start (CHK_<code>_START / _A_ / _01_) ranks first; Cordelion's and
        # Ardolis' are names your game listed in rounds 19-20
        # (dev 10.11: the simulator also lists CHK_MOL_START, the name your game's catalog chose in
        # rounds 24-26, and it ranks first as it did there)
        want = {"torren_iv": "CHK_MOL_START", "cordelion": "CHK_CORD_A_START", "ardolis": "CHK_ARD_START",
                "sargasso": "CHK_SARG_GELFACTORY_LANDINGPAD", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD"}
        for pid, cp in want.items():
            self.assertEqual(T.best_in_catalog(pid), cp, pid)
        for p in g.data.planets.values():
            best = T.best_in_catalog(p.id)
            self.assertTrue(best, p.id)
            self.assertNotIn("TRANSITION_TO", best)
        self.assertTrue(g.log_has("checkpoint catalog:"))

    def test_cordelion_is_placed_by_its_area(self):
        g = Game(settings={"seed": "v81-area", "preset": "hub"})
        T = g.g.RANDO_TRAVEL
        self.assertEqual(T.planet_of_area("Kedaro_Station"), "cordelion")
        self.assertEqual(T.planet_of_area("Sargasso (open world)"), "sargasso")
        self.assertEqual(T.planet_of_area("Zurkons"), "scarstu")
        self.assertEqual(T.planet_of_area("Megalopolis (open world)"), "corson_v")
        self.assertIsNone(T.planet_of_area("interplanetary_space"))
        self.assertEqual(T.planet_of_checkpoint("CHK_TRANSITION_TO_KEDARO"), "cordelion")
        self.assertEqual(T.planet_of_checkpoint("CHK_TRANSITION_TO_NEFARIOUS_CITY"), "nefarious_city")
        self.assertEqual(T.planet_of_checkpoint("CHK_TRANSITION_TO_MOL"), "torren_iv")

    def test_scores_prefer_landings_and_avoid_bosses_and_cinematics(self):
        g = Game(settings={"seed": "v81-score", "preset": "hub"})
        T = g.g.RANDO_TRAVEL
        s = T.score_checkpoint
        self.assertGreater(s("CHK_SARG_GELFACTORY_LANDINGPAD"), s("CHK_SARG_02_MININGPLATFORM_LANDINGPAD_POSTCINE"))
        self.assertGreater(s("CHK_MOL_01_START"), s("CHK_MOL_02_FIXER_CHASE_CINE"))
        self.assertGreater(s("CHK_STATION_01_START"), s("CHK_STATION_FORGE_BOSS"))
        self.assertLess(s("CHK_TRANSITION_TO_MOL"), 0)

    def test_a_long_listing_is_placed_in_slices(self):
        g = Game(settings={"seed": "v81-slice", "preset": "hub"})
        g.lua.execute("""
            local big = {}
            for i = 1, 600 do big[i] = { name = string.format('CHK_MOL_%03d_START', i), area = 'Molonoth' } end
            rivet.checkpoints = function(f) if f == 'CHK_' then return big end return {} end
        """)
        T = g.g.RANDO_TRAVEL
        T.catalog_reset()
        steps = 0
        while not T.catalog_step():
            steps += 1
            self.assertLess(steps, 200)
        n = len(list(py(T.catalog.planets)["torren_iv"].keys()))
        self.assertEqual(n, 600)
        self.assertGreaterEqual(steps, 600 // int(T.CATALOG_SLICE))

    def test_a_menu_landing_is_remembered(self):
        g = started(level_game("v81-menu"))
        open_pid = "sargasso"                             # open from the start with levels (the story goes there)
        cp = {"nefarious_city": "CHK_NEFCITY_SHIP", "savali": "CHK_SAV_01_LANDING", "blizar_prime": "CHK_BLIZAR_A_LANDINGPAD",
              "sargasso": "CHK_SARG_GELFACTORY_LANDINGPAD", "torren_iv": "CHK_MOL_01_START",
              "cordelion": "CHK_STATION_01_START", "ardolis": "CHK_ARD_01_ARRIVAL", "viceron": "CHK_ZORD_01_START"}[open_pid]
        g.fire("PlanetMenuAcceptEvent", DestinationCheckpointName=cp, InterplanetaryCheckpointName="CHK_TRANSITION_TO_X")
        g.sim.travel_queue[len(g.sim.travel_queue) + 1] = g.lua.table_from({"planet": g.sim.planet_of_cp(cp), "at": g.sim.frame + 2, "cp": cp})
        g.step(900)
        self.assertEqual(py(g.state.travel.landed)[open_pid], cp)
        self.assertTrue(g.log_has("landing on"))


class ShopSliceTests(unittest.TestCase):
    def test_the_vendor_search_spans_frames_with_few_reads_each(self):
        g = Game()
        g.lua.execute("""
            RANDO_V81_READS, RANDO_V81_MAX = 0, 0
            local read = rivet.read
            rivet.read = function(...) RANDO_V81_READS = RANDO_V81_READS + 1; return read(...) end
            local tick = RANDO_SHOP.tick
            RANDO_SHOP.tick = function(...)
              RANDO_V81_READS = 0
              local r = tick(...)
              if RANDO_V81_READS > RANDO_V81_MAX then RANDO_V81_MAX = RANDO_V81_READS end
              return r
            end
        """)
        g.ready(frames=900)
        self.assertTrue(g.log_has("weapon slots, "))
        self.assertTrue(g.log_has("search done after"))
        m = re.search(r"search done after (\d+) frames", "\n".join(g.logs()))
        self.assertGreater(int(m.group(1)), 2)
        # the last slice (the check, the writes and the prices) is the largest; the search itself
        # reads at most H.SLICE_READS chunks a frame
        self.assertLess(g.g.RANDO_V81_MAX, 80)

    def test_a_failing_vendor_stops_after_max_tries(self):
        g = Game()
        g.lua.execute("RANDO_SHOP.discover = function() error('boom') end")
        g.ready(frames=600)
        g.step(120 * 8)
        self.assertLessEqual(g.count_logs("apply:"), int(g.g.RANDO_SHOP.MAX_TRIES))


if __name__ == "__main__":
    unittest.main()


class Round17LogTests(unittest.TestCase):
    """the checkpoints your game listed in round 17 (RANDO-HUB research lines), placed by the
    catalog: every one on the right planet, the planet tunnels on none"""

    def listed(self):
        out = []
        for line in open(os.path.join(ROOT, "tests", "data", "round17_rivet.log"), encoding="utf-8", errors="replace"):
            m = re.search(r"research: checkpoints \S+ \(\d+\): (.*)$", line)
            if m:
                for tok in m.group(1).split(" CHK_"):
                    tok = tok if tok.startswith("CHK_") else "CHK_" + tok
                    if "@" in tok:
                        name, area = tok.split("@", 1)
                        out.append((name.strip(), area.strip()))
        return out

    def test_round17_checkpoints_are_placed_on_their_planets(self):
        listed = self.listed()
        self.assertGreater(len(listed), 50)
        g = Game(settings={"seed": "v81-r17", "preset": "hub"})
        T = g.g.RANDO_TRAVEL
        expect = {"ZURK": "scarstu", "SARG": "sargasso", "BLIZAR": "blizar_prime", "ZORDOOM": "viceron", "MEGA": "corson_v"}
        n = 0
        for name, area in listed:
            got = T.place(name, area)
            if "TRANSITION_TO" in name:
                self.assertIsNone(got, name)
                continue
            for code, pid in expect.items():
                if name.startswith("CHK_" + code) or (code == "MEGA" and "Megalopolis" in area):
                    self.assertEqual(got, pid, (name, area))
                    n += 1
                    break
        self.assertGreater(n, 40)

    def test_round17_best_checkpoints(self):
        g = Game(settings={"seed": "v81-r17b", "preset": "hub"})
        T = g.g.RANDO_TRAVEL
        T.catalog_reset()
        lst = g.lua.table_from([g.lua.table_from({"name": n, "area": a}) for n, a in self.listed()])
        T.catalog_add(lst)
        self.assertEqual(T.best_in_catalog("scarstu"), "CHK_ZURK_LANDING_SHIP")
        self.assertEqual(T.best_in_catalog("blizar_prime"), "CHK_BLIZAR_A_LANDINGPAD")
        self.assertEqual(T.best_in_catalog("sargasso"), "CHK_SARG_GELFACTORY_LANDINGPAD")
        self.assertEqual(T.best_in_catalog("corson_v"), "CHK_MEGA_01_RIVET_START")
        self.assertIsNone(T.best_in_catalog("torren_iv"))      # round 17 listed none of Torren IV's
