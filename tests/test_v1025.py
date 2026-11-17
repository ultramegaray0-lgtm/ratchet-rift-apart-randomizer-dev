"""Dev 10.25 (kit 10.0.17): after the dev 10.24 log of 2026-11-18 (tests/data/round35_rivet.log: v7 helper in the game,
spawnproof v3 scripts, NefCity, Zurkon arena challenge A1 replayed and completed; "still nothing").

  * RoundThirtyFiveLogTests: facts from the real game log - the experiment ran this time (SceneManager found, 197 nodes,
    970 spawns tied) but never armed; and the arena's SunsetSpawnerFactory nodes carry a "Templates" variable whose
    value decides the enemy (3 values, 11 factories, every factory always the same kind).
  * FactoryTemplatesSimulatorTests: dev(spawnproof).lua v5's factory Templates route in the SIMULATOR (SYNTHETIC memory,
    laid out as rivet_hook's headers and the real plug blocks say). Shows the code's logic only.
Nothing in this file is in-game verification.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_v1021 import crc_hash  # noqa: E402

LOG = ROOT / "tests" / "data" / "round35_rivet.log"
TEMPLATES, LOCATIONS, INITIALCOUNT = 3990217346, 2501629366, 2429945776


def text():
    return LOG.read_text(encoding="utf-8")


def factory_map():
    """{factory: (Templates value, Locations value)} and {factory: set of spawned names} from the real log"""
    t = text()
    fac = {}
    for m in re.finditer(r"factory (\d+): classes SunsetSpawnerFactoryScriptAction,SunsetSpawnerFactory; node variables ([^\n]+)", t):
        vars_ = dict(re.findall(r"(\d+):actors=\{(\d+)\}", m.group(2)))
        if str(TEMPLATES) in vars_:
            fac[int(m.group(1))] = (int(vars_[str(TEMPLATES)]), int(vars_.get(str(LOCATIONS), 0)))
    spawned = {}
    for m in re.finditer(r"spawn \d+ \(SpawnFactory (\d+), location (\d+)\): [^\n]*?spawned (\S+) \(handle", t):
        f = int(m.group(1))
        if f in fac and m.group(3) != "nil":
            spawned.setdefault(f, set()).add(m.group(3))
    return fac, spawned


class RoundThirtyFiveLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_the_experiment_ran_with_the_v7_helper(self):
        t = text()
        self.assertIn("RANDO-SPAWNPROOF\tSceneManager 7FF7A5857580 (signature matched 1 x)", t)
        self.assertIn("scan 1 on scarstu: 197 node(s) (197 new): 106 Template, 91 Factories, 0 neither", t)
        self.assertIn("970 spawn(s) tied", t)
        self.assertNotIn("ARMED", t)
        self.assertIn("RANDO-SPAWNPROOF\tv3 loaded:", t)          # the 10.24 dev file was not copied (v4 only added BLOCKED)

    def test_the_factory_variable_names(self):
        self.assertEqual(crc_hash("Templates"), TEMPLATES)
        self.assertEqual(crc_hash("Locations"), LOCATIONS)
        self.assertEqual(crc_hash("InitialCount"), INITIALCOUNT)

    def test_a_factory_templates_value_decides_the_enemy(self):
        fac, spawned = factory_map()
        arena = {f: v for f, v in fac.items() if 1097940 <= f <= 1097960}
        self.assertEqual(len(arena), 10)                                        # 1097946 was spawned, not described
        by_template = {}
        for f, (tpl, _) in arena.items():
            names = spawned.get(f, set())
            self.assertLessEqual(len(names), 1, (f, names))                 # one factory, one kind
            for n in names:
                by_template.setdefault(tpl, set()).add(n)
        self.assertEqual(len(by_template), 3)
        for tpl, names in by_template.items():
            self.assertEqual(len(names), 1, (tpl, names))                   # one Templates value, one kind
        self.assertIn("pirate_robot_sh", next(iter(by_template[1097446])))
        self.assertIn("pirate_robot_me", next(iter(by_template[1097451])))
        self.assertIn("bladeball", next(iter(by_template[1097452])))

    def test_the_spawn_location_is_the_factorys_locations_value(self):
        self.assertIn("spawn 1099133 (SpawnFactory 1097957, location 1097478)", text())
        fac, _ = factory_map()
        self.assertEqual(fac[1097957][1], 1097478)

    def test_why_v3_never_armed(self):
        t = text()
        # the factories the events name are not tied to any node: the node route had nothing to swap
        no_node = len(re.findall(r"spawn \d+ \(SpawnFactory 10979\d\d, [^)]*\): no node", t))
        tied = len(re.findall(r"spawn \d+ \(SpawnFactory 10979\d\d, [^)]*\): node ", t))
        self.assertGreater(no_node, 30)
        self.assertLess(tied, 5)


# ---------------------------------------------------------------------------------------------- simulator
SCENE, VARS = 0x5000000000, 0x5100000000
FIX = r"""
local SCENE, VARS = %(scene)d, %(vars)d
SIM.map(SCENE + 0x7500, 0x100)
SIM.put_u64(SCENE + 0x75A0, VARS); SIM.put_u32(SCENE + 0x75BC, 64)
SIM.map(VARS, 64 * 0x40)
SIM.put_u64(SIM.MB + 0x128, SCENE); SIM.put_u32(SIM.MB + 0x130, 1)
PF = { writes = {}, names = {}, classes = {}, factories = {} }
function PF.var(idx, gen, actors, uid)
  local a = VARS + idx * 0x40
  SIM.put_u64(a, uid or 0); SIM.put_u32(a + 0x10, actors or 0)
  SIM.mem[a + 0x34] = 5; SIM.mem[a + 0x35] = 0; SIM.mem[a + 0x36] = gen; SIM.mem[a + 0x37] = 0
end
function PF.var_actors(idx) return SIM.get_u32(VARS + idx * 0x40 + 0x10) end
-- a SunsetSpawnerFactoryScriptAction node on actor `fac`: plug block with Templates (var tidx) and Locations
function PF.factory(i, fac, tidx, lidx)
  local a, p = 0x5600000000 + i * 0x100, 0x5700000000 + i * 0x100
  SIM.map(a, 0x80); SIM.map(p, 0x80)
  SIM.put_u64(a + 0x48, 0xF000 + i); SIM.put_u64(a + 0x58, p)
  SIM.put_u64(p + 8, p + 0x28); SIM.mem[p + 0x1A] = 2
  SIM.put_u32(p + 0x28, 3990217346); SIM.mem[p + 0x2C] = tidx; SIM.mem[p + 0x2E] = 1
  SIM.put_u32(p + 0x30, 2501629366); SIM.mem[p + 0x34] = lidx; SIM.mem[p + 0x36] = 1
  PF.factories[#PF.factories + 1] = { component = 900 + i, actor = fac, uid = string.format("%%016x", 0xF000 + i),
                                      class = "SunsetSpawnerFactoryScriptAction", addr = a }
  PF.classes[fac] = { "SunsetSpawnerFactoryScriptAction", "SunsetSpawnerFactory" }
end
local ow, oc, ocs, ouid = rivet.write, rivet.component, rivet.components, rivet.uid
rivet.write = function(addr, hex) PF.writes[#PF.writes + 1] = addr; return ow(addr, hex) end
rivet.script_nodes = function(filter)
  if filter == "SunsetSpawnerFactoryScriptAction" then return PF.factories end
  return {}
end
rivet.component = function(actor, class)
  for _, n in ipairs(PF.factories) do
    if n.actor == actor and class == "SunsetSpawnerFactoryScriptAction" then return { address = string.format("%%X", n.addr), size = 160, handle = n.component } end
  end
  return oc(actor, class)
end
rivet.components = function(h) if PF.classes[h] then return PF.classes[h] end return ocs(h) end
rivet.name = function(h) return PF.names[h] end
rivet.uid = function(h) if PF.names[h] or PF.classes[h] then return string.format("%%016x", h) end return ouid(h) end
"""
GRUNT = ("characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
FLYER = ("characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])


class FactoryTemplatesSimulatorTests(unittest.TestCase):
    """SYNTHETIC memory: shows the code's logic only."""

    def game(self, shared=False):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True, dll_version=7)
        self.assertFalse(g.load_errors, g.load_errors)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        L = g.lua.execute
        # Templates values 9001 (grunt template) and 9002 (flyer template), as the real ones: uid with bit 63
        # factories A 8001 (var 1 = 9001), B 8002 (var 2 = 9002), C 8003 (var 3 = 9001, not spawned yet);
        # shared: D 8004 uses A's variable 1
        for idx, tpl in ((1, 9001), (2, 9002), (3, 9001)):
            L("PF.var(%d, 1, %d, 0x%X)" % (idx, tpl, 0x8000000000000000 | tpl))
        for idx in (11, 12, 13):
            L("PF.var(%d, 1, %d, 0)" % (idx, 4000 + idx))
        L("PF.factory(0, 8001, 1, 11); PF.factory(1, 8002, 2, 12); PF.factory(2, 8003, 3, 13)")
        if shared:
            L("PF.factory(3, 8004, 1, 11)")
        g.travel("Zurkon")
        g.step(150)
        return g

    def spawn(self, g, fac, handle, who):
        name, classes = who
        g.lua.execute('PF.names[%d] = "%s"; PF.classes[%d] = {%s}' % (handle, name.replace("\\", "\\\\"), handle,
                                                                     ",".join('"%s"' % c for c in classes)))
        g.fire("SpawnerSpawnEvent", SpawnFactory=fac, SpawnIndex=0, SpawnLocation=4011, SpawnedHandle=handle)
        g.step(130)

    def lines(self, g):
        return [l for l in g.logs() if "RANDO-SPAWNPROOF" in l]

    def test_factories_are_listed_with_their_templates(self):
        g = self.game()
        line = [l for l in self.lines(g) if "factories on scarstu" in l]
        self.assertTrue(line, self.lines(g))
        self.assertIn("3 with a Templates variable (3 new); 2 Templates value(s): 9001 x2, 9002 x1", line[0])

    def test_a_factory_templates_replacement_is_armed_verified_and_put_back(self):
        g = self.game()
        self.spawn(g, 8001, 7001, GRUNT)
        self.spawn(g, 8002, 7002, FLYER)
        chosen = [l for l in self.lines(g) if "factory 8001 chosen" in l]
        self.assertTrue(chosen, self.lines(g)[-5:])                            # it already spawned: first choice
        armed = [l for l in self.lines(g) if "\tARMED " in l]
        self.assertEqual(len(armed), 1)
        self.assertIn("ftemplate", armed[0])
        self.assertIn("Templates variable 1", armed[0])
        self.assertIn("read back OK", armed[0])
        self.assertEqual(g.lua.eval("PF.var_actors(1)"), 9002)
        self.assertTrue(g.note_has("SPAWNPROOF ARMED: next grunt here should be flyer"), g.notes()[-3:])
        self.spawn(g, 8001, 7003, FLYER)                                         # SYNTHETIC: the game used it
        self.assertTrue(any("VERIFY node factory 8001" in l and "REPLACEMENT SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])
        self.assertTrue(any("spawn 7003 " in l and "[ARMED factory variable, spawn 1 since]" in l for l in self.lines(g)))
        g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        g.step(5)
        self.assertTrue(any("put back" in l and "factory 8001" in l and "variable OK" in l for l in self.lines(g)), self.lines(g)[-4:])
        self.assertEqual(g.lua.eval("PF.var_actors(1)"), 9001)
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 9001)                   # factory C untouched

    def test_a_shared_variable_is_verified_on_any_of_its_factories(self):
        g = self.game(shared=True)
        self.spawn(g, 8001, 7001, GRUNT)
        self.spawn(g, 8002, 7002, FLYER)
        self.assertTrue(any("is used by 2 factory node(s)" in l for l in self.lines(g)), self.lines(g)[-4:])
        self.spawn(g, 8004, 7004, FLYER)                                         # SYNTHETIC
        self.assertTrue(any("VERIFY" in l and "SpawnFactory 8004" in l and "REPLACEMENT SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])

    def test_after_an_original_verdict_a_fresh_factory_is_next(self):
        g = self.game()
        self.spawn(g, 8001, 7001, GRUNT)
        self.spawn(g, 8002, 7002, FLYER)
        self.spawn(g, 8001, 7003, GRUNT)                                         # SYNTHETIC: no effect
        self.assertTrue(any("ORIGINAL SPAWNED" in l for l in self.lines(g)))
        self.assertTrue(any("put back (not replaced: trying another factory)" in l and "variable OK" in l for l in self.lines(g)))
        self.assertEqual(g.lua.eval("PF.var_actors(1)"), 9001)
        chosen = [l for l in self.lines(g) if " chosen (" in l]
        self.assertEqual(len(chosen), 2, chosen)                                  # in the same fight
        self.assertIn("factory 8003 chosen (a fresh factory first, after an ORIGINAL verdict", chosen[1])
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 9002)

    def test_one_factory_experiment_at_a_time(self):
        g = self.game()
        self.spawn(g, 8001, 7001, GRUNT)
        self.spawn(g, 8002, 7002, FLYER)
        self.spawn(g, 8002, 7005, FLYER)
        self.assertEqual(len([l for l in self.lines(g) if "\tARMED " in l]), 1)

    def test_nothing_is_written_off_zurkon(self):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True, dll_version=7)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        g.lua.execute("PF.var(1, 1, 9001, 1); PF.var(2, 1, 9002, 2); PF.var(11, 1, 4011, 0); PF.var(12, 1, 4012, 0)")
        g.lua.execute("PF.factory(0, 8001, 1, 11); PF.factory(1, 8002, 2, 12)")
        g.travel("NefCity")
        g.step(150)
        self.spawn(g, 8001, 7001, GRUNT)
        self.spawn(g, 8002, 7002, FLYER)
        self.assertEqual(len(g.lua.eval("PF.writes")), 0)


if __name__ == "__main__":
    unittest.main()
