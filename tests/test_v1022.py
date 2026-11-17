"""Dev 10.22 (kit 10.0.16): dev(spawnproof).lua v2, after the dev 10.21 log of 2026-11-17 (tests/data/round32_rivet.log:
NefCity, Zurkon arena challenges A1 and A2 replayed, NefCity; "tried 2 battles, 1 normal enemies, 1 boss. Nothing
randomized").

THREE KINDS OF TEST, kept apart:
  * RoundThirtyTwoLogTests: facts read from the real game log (no simulator) - why v1 never armed.
  * RealSpawnerBytesTests: the Spawner component layout v2 reads (+0x48 factory, +0x50 template, +0x58 location,
    +0x9C count, +0xDC slots of 12 bytes) checked against REAL Spawner dumps of the log, cross-checked with what
    rivet.script_node and v1's LastSpawn ties said about the same nodes.
  * SpawnProofTwoSimulatorTests: v2's logic in the SIMULATOR. The memory there is SYNTHETIC, laid out as the real
    bytes and rivet_hook's headers say. These tests show the code does what it says; they prove nothing about the game.
Nothing in this file is in-game verification.
"""
import os
import pathlib
import re
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game, script_files  # noqa: E402
from test_v1021 import crc_hash  # noqa: E402

LOG = ROOT / "tests" / "data" / "round32_rivet.log"


def text():
    return LOG.read_text(encoding="utf-8")


def spawner_bytes(node):
    """the 432 Spawner bytes of a node as the log dumped them (dump lines of 16, or probe lines of dev(spawnprobe))"""
    b = bytearray(432)
    seen = 0
    for l in text().splitlines():
        m = re.search(r"(?:dump %s Spawner component Spawner size 432 at \w+ prius nil|probe \w+ node %s Spawner) \+0x([0-9A-F]{3}): ([0-9a-f ]+)$"
                      % (node, node), l)
        if m:
            off, data = int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", ""))
            b[off:off + len(data)] = data
            seen += len(data)
    assert seen >= 432, (node, seen)
    return bytes(b)


def u32(b, off):
    return struct.unpack_from("<I", b, off)[0]


class RoundThirtyTwoLogTests(unittest.TestCase):
    def test_the_game_path_was_replaced(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text())
        self.assertNotIn("Users\\", text())

    def test_v1_was_loaded_and_never_armed(self):
        t = text()
        self.assertIn("RANDO-SPAWNPROOF\tv1 loaded: one Template-variable replacement on Zurkon (on)", t)
        self.assertIn("SceneManager 7FF7A5857580 (signature matched 1 x)", t)            # the v7 helper worked
        waits = re.findall(r"RANDO-SPAWNPROOF\tnot armed yet: (\d+) regular-enemy template", t)
        self.assertGreaterEqual(len(waits), 6)
        self.assertTrue(all(w == "0" for w in waits))
        self.assertNotIn("ARMED node", t)

    def test_every_template_variable_spawn_was_a_portal_or_prop(self):
        t = text()
        with_tpl = re.findall(r"Template variable \d+ = \d+ uid \w+; spawned (\S+)", t)
        self.assertGreaterEqual(len(with_tpl), 30)
        self.assertTrue(all("anomaly_portal" in s or "wpn_carpetbomber" in s for s in with_tpl), with_tpl)
        enemies = re.findall(r"Template variable none = -; spawned (characters\\enemy\\\S+)", t)
        self.assertIn("characters\\enemy\\enm_pirate_robot_q4b\\actors\\enm_pirate_robot_sh", enemies)

    def test_the_enemy_nodes_hold_a_factories_variable(self):
        self.assertEqual(crc_hash("Factories"), 838143302)
        t = text()
        line = next(l for l in t.splitlines() if "probe index node a2e65561b2d559c4: script_node" in l)
        self.assertIn("vars 838143302:actors={1087138} count 1", line)
        self.assertNotIn("1835115251:", line)                                         # no Template variable
        self.assertIn("SpawnFactory handle 1087133 uid a59e7827e97137af name nil asset nil nil classes SunsetSpawnerFactoryScriptAction,SunsetSpawnerFactory", t)

    def test_v1_jobs_died_on_the_frame_budget(self):
        t = text()
        died = re.findall(r"RANDO-SPAWNPROOF\tRANDO-ERROR\tscripts\\dev\(spawnproof\)\.lua:(\d+): ran past the 8 ms frame budget", t)
        self.assertGreaterEqual(len(died), 10)
        self.assertTrue({"101", "133"} <= set(died))

    def test_the_challenges_ran(self):
        t = text()
        self.assertIn("MissionName=MIS_ZURK_ARENA_CHALLENGE_A1 MissionState=4 PreviousState=2", t)
        self.assertIn("MissionName=MIS_ZURK_ARENA_CHALLENGE_A2 MissionState=4 PreviousState=2", t)


class RealSpawnerBytesTests(unittest.TestCase):
    def test_factory_nodes_cache_the_factory_at_0x48(self):
        b = spawner_bytes("a2e65561b2d559c4")
        self.assertEqual(u32(b, 0x48), 1087138)                                       # = its Factories variable
        self.assertEqual(u32(b, 0x50), 0)
        self.assertEqual(u32(b, 0x58), 0)
        self.assertEqual(u32(b, 0x9C), 3)
        slots = [(u32(b, 0xDC + 12 * i), u32(b, 0xE0 + 12 * i)) for i in range(3)]
        self.assertEqual(slots, [(0x10BDCE, 0x10957D), (0x10BE1C, 0x109577), (0x10BE57, 0x109586)])
        self.assertEqual(u32(b, 0xDC + 36), 0)                                        # nothing past the count

    def test_template_nodes_cache_template_and_location(self):
        t = text()
        line = next(l for l in t.splitlines() if "probe stopped node cd8dc00ee27a07d1: script_node" in l)
        self.assertIn("1835115251:actors={1086816}", line)
        self.assertIn("2761897147:actors={1086815}", line)
        self.assertIn("406637480:actors={1105863}", line)
        b = spawner_bytes("cd8dc00ee27a07d1")
        self.assertEqual(u32(b, 0x48), 0)
        self.assertEqual(u32(b, 0x50), 1086816)                                       # Template
        self.assertEqual(u32(b, 0x58), 1086815)                                       # Location
        self.assertEqual(u32(b, 0x9C), 1)
        self.assertEqual(u32(b, 0xDC), 1105863)                                       # = LastSpawn

    def test_the_slot_list_agrees_with_v1s_lastspawn_tie(self):
        t = text()
        self.assertIn("spawn 1097158 is node 9620735f75f38213's (its LastSpawn); Template variable none", t)
        b = spawner_bytes("9620735f75f38213")
        self.assertEqual(u32(b, 0x48), 1087129)
        self.assertEqual(u32(b, 0x9C), 1)
        self.assertEqual(u32(b, 0xDC), 1097158)

    def test_v2_reads_the_real_bytes_the_same_way(self):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True)
        b = spawner_bytes("a2e65561b2d559c4")
        base = 0x172FE0C6100
        g.lua.execute("for i, v in ipairs({%s}) do SIM.mem[%d + i - 1] = v end" % (",".join(map(str, b)), base))
        res = g.lua.eval("""function()
          local st = RANDO_SPAWNPROOF.spawner_state(%d)
          return st.factory, st.template, st.location, st.count, #st.slots, st.slots[1].spawned, st.slots[3].location
        end""" % base)()
        self.assertEqual(tuple(res), (1087138, 0, 0, 3, 3, 0x10BDCE, 0x109586))


# ---------------------------------------------------------------------------------------------- simulator
SCENE, VARS = 0x5000000000, 0x5100000000
FIX = r"""
local SCENE, VARS = %(scene)d, %(vars)d
SIM.map(SCENE + 0x7500, 0x100)
SIM.put_u64(SCENE + 0x75A0, VARS); SIM.put_u32(SCENE + 0x75BC, 64)
SIM.map(VARS, 64 * 0x40)
SIM.put_u64(SIM.MB + 0x128, SCENE); SIM.put_u32(SIM.MB + 0x130, 1)
PF = { writes = {}, names = {}, classes = {}, nodes = {}, budget = 0, budget_after = 1 }
function PF.var(idx, gen, actors, uid)
  local a = VARS + idx * 0x40
  SIM.put_u64(a, uid or 0); SIM.put_u32(a + 0x10, actors or 0)
  SIM.mem[a + 0x34] = 5; SIM.mem[a + 0x35] = 0; SIM.mem[a + 0x36] = gen; SIM.mem[a + 0x37] = 0
end
function PF.var_actors(idx) return SIM.get_u32(VARS + idx * 0x40 + 0x10) end
-- a node: 0x80 bytes, a plug block with the given variable plugs { {plug, idx}, ... }, a 432-byte Spawner
function PF.node(i, uid, spawner, vars)
  local a, p, s = 0x5200000000 + i * 0x100, 0x5300000000 + i * 0x100, 0x5400000000 + i * 0x200
  SIM.map(a, 0x80); SIM.map(p, 0x80); SIM.map(s, 0x1B0)
  SIM.put_u64(a + 0x48, uid); SIM.put_u64(a + 0x58, p); SIM.put_u32(a + 0x60, spawner)
  SIM.put_u64(p + 8, p + 0x28); SIM.mem[p + 0x1A] = #vars
  for k, v in ipairs(vars) do
    local e = p + 0x28 + (k - 1) * 8
    SIM.put_u32(e, v[1]); SIM.mem[e + 4] = v[2]; SIM.mem[e + 6] = 1
  end
  PF.nodes[#PF.nodes + 1] = { component = 600 + i, actor = 500 + i, uid = string.format("%%016x", uid), class = "SpawnerScriptAction",
                              addr = a, saddr = s, spawner = spawner }
end
-- the Spawner records a spawn: cached factory at +0x48, one slot { spawned, location, time } at +0xDC
function PF.spawner_spawn(i, factory, handle)
  local n = PF.nodes[i + 1]
  SIM.put_u32(n.saddr + 0x48, factory); SIM.put_u32(n.saddr + 0x9C, 1)
  SIM.put_u32(n.saddr + 0xDC, handle); SIM.put_u32(n.saddr + 0xE0, 4000 + i)
end
function PF.cache(i) return SIM.get_u32(PF.nodes[i + 1].saddr + 0x48) end
local ow, oc, ocs, ouid, ord = rivet.write, rivet.component, rivet.components, rivet.uid, rivet.read
rivet.write = function(addr, hex) PF.writes[#PF.writes + 1] = addr; return ow(addr, hex) end
-- rivet_hook's budget: a count hook that raises inside whatever Lua code runs, and clears itself first
local occ = coroutine.create
coroutine.create = function(f)
  local co = occ(f)
  if PF.budget > 0 then
    local n = 0
    debug.sethook(co, function()
      n = n + 1
      if n >= PF.budget_after and PF.budget > 0 then PF.budget = PF.budget - 1; debug.sethook(co); error("ran past the 8 ms frame budget") end
    end, "", 1)
  end
  return co
end
rivet.script_nodes = function() return PF.nodes end
rivet.component = function(actor, class)
  for _, n in ipairs(PF.nodes) do
    if n.actor == actor and class == "SpawnerScriptAction" then return { address = string.format("%%X", n.addr), size = 128, handle = n.component } end
    if n.actor == actor and class == "Spawner" then return { address = string.format("%%X", n.saddr), size = 432, handle = n.spawner } end
  end
  return oc(actor, class)
end
rivet.components = function(h) if PF.classes[h] then return PF.classes[h] end return ocs(h) end
rivet.name = function(h) return PF.names[h] end
rivet.uid = function(h) if PF.names[h] or PF.classes[h] then return string.format("%%016x", h) end return ouid(h) end
"""

FACTORIES, LASTSPAWN, TEMPLATE = 838143302, 406637480, 1835115251
GRUNT = ("characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
FLYER = ("characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])


class SpawnProofTwoSimulatorTests(unittest.TestCase):
    """SYNTHETIC memory: shows the code's logic only."""

    def game(self, lastspawn=True, planet="Zurkon"):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True, dll_version=7)
        self.assertFalse(g.load_errors, g.load_errors)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        L = g.lua.execute
        # factories 8001 / 8002 (SunsetSpawnerFactory nodes) behind nodes A, B, C; Factories variables 1-3 (uid 0,
        # as the real ones), LastSpawn variables 11-13
        for k in (8001, 8002):
            L('PF.classes[%d] = {"SunsetSpawnerFactoryScriptAction", "SunsetSpawnerFactory"}' % k)
        for idx, fac in ((1, 8001), (2, 8002), (3, 8001)):
            L("PF.var(%d, 1, %d, 0)" % (idx, fac))
        for idx in (11, 12, 13):
            L("PF.var(%d, 1, 0, 0)" % idx)
        for i in range(3):
            vars_ = "{%d, %d}" % (FACTORIES, i + 1) + (", {%d, %d}" % (LASTSPAWN, i + 11) if lastspawn else "")
            L("PF.node(%d, 0x%X, %d, {%s})" % (i, 0xA0000000000000 + i, 0x214000 + i, vars_))
        g.travel(planet)
        g.step(150)
        return g

    def spawn(self, g, node, handle, who, factory, lastspawn=True):
        name, classes = who
        L = g.lua.execute
        L('PF.names[%d] = "%s"; PF.classes[%d] = {%s}' % (handle, name.replace("\\", "\\\\"), handle, ",".join('"%s"' % c for c in classes)))
        if lastspawn:
            L("PF.var(%d, 1, %d, 0)" % (node + 11, handle))
        L("PF.spawner_spawn(%d, %d, %d)" % (node, factory, handle))
        g.fire("SpawnerSpawnEvent", SpawnFactory=factory, SpawnIndex=0, SpawnLocation=4000 + node, SpawnedHandle=handle)
        g.step(130)

    def lines(self, g):
        return [l for l in g.logs() if "RANDO-SPAWNPROOF" in l]

    def test_scan_sees_factories_nodes(self):
        g = self.game()
        scan = [l for l in self.lines(g) if "\tscan 1 on scarstu" in l]
        self.assertTrue(scan, self.lines(g))
        self.assertIn("3 node(s) (3 new): 0 Template, 3 Factories, 0 neither; slots holding one actor 3, groups 0, shared 0; 3 with LastSpawn, 3 Spawner(s) read", scan[0])

    def test_a_factory_replacement_is_armed_verified_and_put_back(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)                                          # node A: factory 8001 -> grunt
        self.spawn(g, 1, 7002, FLYER, 8002)                                          # node B: factory 8002 -> flyer
        armed = [l for l in self.lines(g) if "\tARMED " in l]
        self.assertEqual(len(armed), 1, self.lines(g)[-6:])
        self.assertIn("factory, spawned 0 time(s)", armed[0])                       # node C, fresh
        self.assertIn("grunt.actor", armed[0].split("->")[0])
        self.assertIn("flyer.actor", armed[0].split("->")[1])
        self.assertIn("read back OK", armed[0])
        self.assertIn("not activated yet", armed[0])                                 # Spawner +0x48 was 0
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 8002)
        self.assertEqual(g.lua.eval("PF.var_actors(1)"), 8001)                       # node A untouched
        self.spawn(g, 2, 7003, FLYER, 8002)                                          # SYNTHETIC: the game used it
        self.assertTrue(any("VERIFY node" in l and "REPLACEMENT SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])
        g.fire("SpawnerStoppedEvent", SpawnerComponentHandle=0x214002)
        g.step(5)
        self.assertTrue(any("put back (its Spawner stopped)" in l and "variable OK" in l for l in self.lines(g)), self.lines(g)[-3:])
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 8001)

    def test_an_activated_spawner_copy_is_written_and_put_back(self):
        g = self.game()
        g.lua.execute("PF.spawner_spawn(2, 8001, 0); SIM.put_u32(PF.nodes[3].saddr + 0x9C, 0)")  # C activated, no spawn
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        armed = [l for l in self.lines(g) if "\tARMED " in l]
        self.assertEqual(len(armed), 1, self.lines(g)[-6:])
        self.assertIn("Spawner +0x48 8001 -> 8002 OK", armed[0])
        self.assertEqual(g.lua.eval("PF.cache(2)"), 8002)
        g.fire("SpawnerStoppedEvent", SpawnerComponentHandle=0x214002)
        g.step(5)
        self.assertEqual(g.lua.eval("PF.cache(2)"), 8001)
        self.assertTrue(any("Spawner copy put back" in l for l in self.lines(g)))

    def test_spawns_are_tied_by_the_spawner_slots_without_lastspawn(self):
        g = self.game(lastspawn=False)
        self.spawn(g, 0, 7001, GRUNT, 0, lastspawn=False)                            # SpawnFactory 0: only the slot ties it
        g.lua.execute("SIM.put_u32(PF.nodes[1].saddr + 0x48, 8001)")
        self.assertTrue(any("spawn 7001" in l and "via Spawner slot" in l and "slot factory = 8001" in l for l in self.lines(g)), self.lines(g)[-4:])

    def test_the_original_spawning_is_reported(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        self.spawn(g, 2, 7003, GRUNT, 8001)
        self.assertTrue(any("ORIGINAL SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])

    def test_a_budget_error_does_not_end_the_job(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        for after in (5, 40, 200, 600):                                               # the budget runs out at several spots
            g.lua.execute("PF.budget = 1; PF.budget_after = %d" % after)
            self.spawn(g, 1, 7002 + after, FLYER, 8002)
            self.assertEqual(g.lua.eval("PF.budget"), 0)
        self.assertFalse([l for l in self.lines(g) if "RANDO-ERROR" in l], self.lines(g)[-6:])
        self.assertTrue([l for l in self.lines(g) if "\tARMED " in l], self.lines(g)[-6:])

    def test_a_factory_that_spawned_two_kinds_is_never_used(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        g.lua.execute("PF.var(11, 1, 0, 0)")
        self.spawn(g, 0, 7004, FLYER, 8001)                                          # the same factory, another kind
        self.spawn(g, 1, 7002, FLYER, 8002)
        self.assertFalse([l for l in self.lines(g) if "\tARMED " in l], self.lines(g)[-4:])
        g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        g.step(5)
        self.assertTrue(any("level summary" in l and "(MIXED)" in l for l in self.lines(g)))

    def test_nothing_is_written_off_zurkon(self):
        g = self.game(planet="NefCity")
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        self.assertFalse([l for l in self.lines(g) if "ARMED" in l])
        self.assertEqual(len(g.lua.eval("PF.writes")), 0)

    def test_a_reloaded_variable_is_never_written(self):
        g = self.game()
        self.spawn(g, 0, 7001, GRUNT, 8001)
        self.spawn(g, 1, 7002, FLYER, 8002)
        n = len(g.lua.eval("PF.writes"))
        self.assertEqual(n, 2)
        g.lua.execute("PF.var(3, 2, 8001, 0)")                                       # the level reloaded: generation 2
        g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        g.step(5)
        self.assertEqual(len(g.lua.eval("PF.writes")), n)
        self.assertTrue(any("variable skipped" in l for l in self.lines(g)))
        self.assertTrue(any("level summary" in l for l in self.lines(g)))

    def test_it_is_a_developer_file(self):
        self.assertNotIn("dev(spawnproof).lua", [p.name for p in script_files(release=True)])
        self.assertNotIn("dev(spawnproof).lua", [p.name for p in script_files()])


if __name__ == "__main__":
    unittest.main()
