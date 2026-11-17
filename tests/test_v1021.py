"""Dev 10.21 (kit 10.0.16, rando_give.dll v7 as a developer build), asked for: "make the Enemy, Boss and
Chaos randomizers actually work ... prove that the game spawns the randomized enemies" with the rivet.log of
2026-11-17 from the dev 10.20 spawnprobe (tests/data/round31_rivet.log).

THREE KINDS OF TEST, kept apart:
  * RoundThirtyOneLogTests: facts read from the real game log (no simulator).
  * RealPlugBlockTests: rivet_hook's ScriptPlugs layout checked against the REAL plug-block bytes the log
    dumped, cross-checked with what rivet.script_node said about the same node in the same log.
  * SpawnProofSimulatorTests: dev(spawnproof).lua's logic in the SIMULATOR. The memory there (a
    SceneManager, script variables, nodes, spawns) is SYNTHETIC, laid out as rivet_hook's headers say. These
    tests show the code does what it says; they prove nothing about the game.
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
from harness import Game, script_files  # noqa: E402

LOG = ROOT / "tests" / "data" / "round31_rivet.log"


def text():
    return LOG.read_text(encoding="utf-8")


def crc_hash(s):
    """rivet_hook script_signal.cpp hash: reflected CRC-32, start 0xEDB88320, no final xor"""
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        table.append(c)
    c = 0xEDB88320
    for b in s.encode():
        c = (c >> 8) ^ table[(b ^ c) & 0xFF]
    return c


class RoundThirtyOneLogTests(unittest.TestCase):
    def test_the_probe_lost_two_subscriptions_to_the_callback_limit(self):
        t = text()
        self.assertIn("cannot subscribe\tPlanetChangedEvent\ttoo many callbacks registered, the limit is 64", t)
        self.assertIn("cannot subscribe\tCheckpointTriggeredEvent\ttoo many callbacks registered, the limit is 64", t)

    def test_no_arena_node_was_listed_on_zurkon(self):
        t = text()
        zurkon = t.split("NewPlanetName=Zurkon", 1)[1].split("OldPlanetName=Zurkon", 1)[0]
        census = re.findall(r"RANDO-SPAWNERS\tcensus \d+ \([^)]*\): (\d+) spawner node\(s\) read, \d+ template\(s\), (\d+) skipped", zurkon)
        self.assertEqual(len(census), 5)
        self.assertTrue(all(n == "0" and s == "0" for n, s in census))          # nothing listed at all
        self.assertIn("index 1 (level loaded): 2 node(s)", zurkon)                 # only the two hub nodes
        self.assertIn("probe index node a74767e9d45e5361", zurkon)                 # also seen on NefCity
        self.assertIn("dump a74767e9d45e5361 Spawner component", t.split("NewPlanetName=Zurkon")[0])

    def test_neither_component_keeps_prius_data_though_both_classes_have_a_prius_type(self):
        t = text()
        for cls, size, cid in (("SpawnerScriptAction", 128, "31B870E3"), ("Spawner", 432, "FC56D431")):
            line = next(l for l in t.splitlines() if "component %s handle" % cls in l)
            self.assertIn("ddlPriusData 0000000000000000", line)
            self.assertIn("class size %d id %s prius type 7FF7" % (size, cid), line)
            self.assertIn("ReadWrite", line)
        self.assertEqual(crc_hash("Spawner"), 0xFC56D431)                          # the class id is its name hash

    def test_the_spawner_node_takes_its_template_from_a_variable(self):
        t = text()
        line = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361: script_node" in l)
        names = {"Template": 1835115251, "Location": 2761897147, "MaxAlive": 161848772, "NumSpawns": 1830449615,
                 "LastSpawn": 406637480}
        for name, h in names.items():
            self.assertEqual(crc_hash(name), h, name)
            self.assertIn("%d:" % h, line)
        self.assertIn("1835115251:actors", line)                                   # Template: an actors variable
        self.assertIn("406637480:actors", line)                                    # LastSpawn
        self.assertIn("1830449615:float=1.0", line)                                # NumSpawns from a variable
        self.assertEqual(crc_hash("OnSpawned"), 2046202852)                        # its output plug
        self.assertIn("outputs 2046202852->", line)

    def test_spawns_name_what_the_game_created(self):
        t = text()
        self.assertIn("spawned handle 1073501 uid 0001000000002100 name characters\\npc\\npc_civ_robot_06\\npc_nefcity_factory_robot.actor", t)
        self.assertIn("SpawnFactory handle 1067842 uid a7b18a762e717697 name nil asset nil nil classes SunsetSpawnerFactoryScriptAction,SunsetSpawnerFactory", t)


class RealPlugBlockTests(unittest.TestCase):
    """the plug block of node a74767e9d45e5361 as the game had it (one dump line) against rivet_hook's
    ScriptPlugs (outPlugs +0, varPlugs +8, varGroups +0x10, inCount +0x18, outCount +0x19, varCount +0x1A,
    zone +0x1C, owner +0x24) and against rivet.script_node's answer for the same node, same log"""

    def test_layout(self):
        t = text()
        dump = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361 plugs at 2BC95B90DE0 +0x000:" in l)
        b = bytes.fromhex(dump.split(": ", 1)[1].replace(" ", ""))
        self.assertEqual(len(b), 0x28)
        base = 0x2BC95B90DE0
        out_ptr, var_ptr = int.from_bytes(b[0:8], "little"), int.from_bytes(b[8:16], "little")
        in_count, out_count, var_count = b[0x18], b[0x19], b[0x1A]
        self.assertEqual(out_ptr, base + 0x28)                                     # one allocation: header first
        self.assertEqual(var_ptr, out_ptr + 0xC * out_count)                       # then 12-byte out plugs
        node = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361: script_node" in l)
        self.assertIn("connections_in=%d" % in_count, node)
        self.assertEqual(node.count("->"), out_count)
        self.assertEqual(len(re.findall(r"\d+:(?:actors|float)=", node)), var_count)   # 5 variables
        self.assertIn("zone=%016x" % int.from_bytes(b[0x1C:0x24], "little"), node)
        self.assertEqual(int.from_bytes(b[0x24:0x28], "little"), 0x2144C2)         # owner = the node's handle
        comp = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361: component SpawnerScriptAction handle" in l)
        self.assertIn("handle 2144C2", comp)
        node_dump = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361 node +0x000:" in l)
        nb = bytes.fromhex(node_dump.split(": ", 1)[1].replace(" ", ""))
        self.assertEqual(int.from_bytes(nb[0x58:0x60], "little"), base)            # node +0x58 = this block

    def test_the_proof_reads_that_block_the_same_way(self):
        t = text()
        dump = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361 plugs at 2BC95B90DE0 +0x000:" in l)
        node_dump = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361 node +0x000:" in l)
        node_hi = next(l for l in t.splitlines() if "probe index node a74767e9d45e5361 node +0x060:" in l)
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True)
        nb = bytes.fromhex(node_dump.split(": ", 1)[1].replace(" ", "") + node_hi.split(": ", 1)[1].replace(" ", ""))
        pb = bytes.fromhex(dump.split(": ", 1)[1].replace(" ", ""))
        # the 5 variable plug entries themselves were not dumped: SYNTHETIC entries after the real header
        entries = b"".join(int(h).to_bytes(4, "little") + (i + 10).to_bytes(2, "little") + (3).to_bytes(2, "little")
                           for i, h in enumerate((2761897147, 1835115251, 161848772, 406637480, 1830449615)))
        lua = "local function put(a, t) for i, v in ipairs(t) do SIM.mem[a + i - 1] = v end end\n"
        lua += "put(%d, {%s})\n" % (0x2BC9D601F00, ",".join(map(str, nb)))
        lua += "put(%d, {%s})\n" % (0x2BC95B90DE0, ",".join(map(str, pb)))
        lua += "put(%d, {%s})\n" % (0x2BC95B90DE0 + 0x28, ",".join(["0"] * 12))
        lua += "put(%d, {%s})\n" % (0x2BC95B90E14, ",".join(map(str, entries)))
        g.lua.execute(lua)
        res = g.lua.eval("function() local p = RANDO_SPAWNPROOF.plugs_of(0x2BC9D601F00); return p.spawner, p.nvars, p.vars[1835115251].idx, p.vars[406637480].idx, p.uid end")()
        self.assertEqual(res[0], 0x2144C3)                                         # node +0x60: its Spawner
        self.assertEqual(res[1], 5)
        self.assertEqual(res[2], 11)
        self.assertEqual(res[3], 13)
        self.assertEqual(res[4], "A74767E9D45E5361")


# ---------------------------------------------------------------------------------------------- simulator
SCENE, VARS = 0x5000000000, 0x5100000000
FIX = r"""
local SCENE, VARS = %(scene)d, %(vars)d
SIM.map(SCENE + 0x7500, 0x100)
SIM.put_u64(SCENE + 0x75A0, VARS); SIM.put_u32(SCENE + 0x75BC, 64)
SIM.map(VARS, 64 * 0x40)
SIM.put_u64(SIM.MB + 0x128, SCENE); SIM.put_u32(SIM.MB + 0x130, 1)
PF = { writes = {}, names = {}, classes = {}, nodes = {} }
function PF.var(idx, gen, actors, uid)
  local a = VARS + idx * 0x40
  SIM.put_u64(a, uid or 0); SIM.put_u32(a + 0x10, actors or 0)
  SIM.mem[a + 0x34] = 5; SIM.mem[a + 0x35] = 0; SIM.mem[a + 0x36] = gen; SIM.mem[a + 0x37] = 0
end
function PF.var_actors(idx) return SIM.get_u32(VARS + idx * 0x40 + 0x10) end
function PF.var_uid(idx) return SIM.get_u64(VARS + idx * 0x40) end
-- a node: its 0x80 bytes, its plug block { header, var plugs Template / LastSpawn }
function PF.node(i, uid, spawner, tpl_idx, last_idx)
  local a, p = 0x5200000000 + i * 0x100, 0x5300000000 + i * 0x100
  SIM.map(a, 0x80); SIM.map(p, 0x80)
  SIM.put_u64(a + 0x48, uid); SIM.put_u64(a + 0x58, p); SIM.put_u32(a + 0x60, spawner)
  SIM.put_u64(p + 8, p + 0x40); SIM.mem[p + 0x1A] = 2
  SIM.put_u32(p + 0x40, 1835115251); SIM.mem[p + 0x44] = tpl_idx; SIM.mem[p + 0x46] = 1
  SIM.put_u32(p + 0x48, 406637480); SIM.mem[p + 0x4C] = last_idx; SIM.mem[p + 0x4E] = 1
  PF.nodes[#PF.nodes + 1] = { component = 600 + i, actor = 500 + i, uid = string.format("%%016x", uid), class = "SpawnerScriptAction", addr = a }
end
local ow, oc, ocs, ouid = rivet.write, rivet.component, rivet.components, rivet.uid
rivet.write = function(addr, hex) PF.writes[#PF.writes + 1] = addr; return ow(addr, hex) end
rivet.script_nodes = function() return PF.nodes end
rivet.component = function(actor, class)
  for _, n in ipairs(PF.nodes) do if n.actor == actor and class == "SpawnerScriptAction" then return { address = string.format("%%X", n.addr), size = 128, handle = n.component } end end
  return oc(actor, class)
end
rivet.components = function(h) if PF.classes[h] then return PF.classes[h] end return ocs(h) end
rivet.name = function(h) return PF.names[h] end
rivet.uid = function(h) if PF.names[h] then return string.format("%%016x", 0x8000000000000000 | h) end return ouid(h) end
"""


class SpawnProofSimulatorTests(unittest.TestCase):
    """SIMULATED memory: shows the code's logic only."""

    def game(self, dll=7, planet="Zurkon"):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnproof=True, dll_version=dll)
        self.assertFalse(g.load_errors, g.load_errors)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        L = g.lua.execute
        # templates: 9001 a grunt, 9002 a flyer (both regular enemies), 9003 a civilian
        L('PF.names[9001] = "characters\\\\enemy\\\\grunt.actor"; PF.classes[9001] = {"SceneObject", "GameBotShooter"}')
        L('PF.names[9002] = "characters\\\\enemy\\\\flyer.actor"; PF.classes[9002] = {"SceneObject", "GameBotMeleeFlier"}')
        L('PF.names[9003] = "characters\\\\npc\\\\civ.actor"; PF.classes[9003] = {"SceneObject", "NPCBot"}')
        # variables 1-4 Template, 11-14 LastSpawn; nodes A B C D
        for idx, tpl in ((1, 9001), (2, 9002), (3, 9001), (4, 9003)):
            L("PF.var(%d, 1, %d, 0x%X)" % (idx, tpl, 0x8000000000000000 | tpl))
        for idx in (11, 12, 13, 14):
            L("PF.var(%d, 1, 0, 0)" % idx)
        for i, (tpl, last) in enumerate(((1, 11), (2, 12), (3, 13), (4, 14))):
            L("PF.node(%d, 0x%X, %d, %d, %d)" % (i, 0xA0000000000000 + i, 0x214000 + i, tpl, last))
        g.travel(planet)
        g.step(150)
        return g

    def spawn(self, g, last_idx, handle, name, classes):
        g.lua.execute('PF.names[%d] = "%s"; PF.classes[%d] = {%s}; PF.var(%d, 1, %d, 0)'
                      % (handle, name.replace("\\", "\\\\"), handle, ",".join('"%s"' % c for c in classes), last_idx, handle))
        g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=0, SpawnedHandle=handle)
        g.step(130)

    def lines(self, g):
        return [l for l in g.logs() if "RANDO-SPAWNPROOF" in l]

    def test_a_v6_helper_is_refused(self):
        g = self.game(dll=6)
        self.assertTrue(any("rando_give.dll is v6, v7 is needed" in l for l in self.lines(g)), self.lines(g))
        self.assertEqual(len(g.lua.eval("PF.writes")), 0)

    def test_scan_counts_template_variables(self):
        g = self.game()
        scan = [l for l in self.lines(g) if "\tscan 1 on scarstu" in l]
        self.assertTrue(scan, self.lines(g))
        self.assertIn("4 node(s) (4 new); 4 with a Template variable (4 holding one actor, 0 shared), 4 with LastSpawn", scan[0])

    def test_one_replacement_is_armed_verified_and_put_back(self):
        g = self.game()
        self.spawn(g, 11, 7001, "characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])   # node A
        self.spawn(g, 12, 7002, "characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])  # node B
        armed = [l for l in self.lines(g) if "\tARMED node" in l]
        self.assertEqual(len(armed), 1, self.lines(g)[-6:])
        self.assertIn("grunt.actor", armed[0].split("->")[0])
        self.assertIn("flyer.actor", armed[0].split("->")[1])
        self.assertIn("read back OK", armed[0])
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 9002)                     # node C's variable
        self.assertEqual(g.lua.eval("PF.var_actors(4)"), 9003)                     # the civilian node untouched
        self.spawn(g, 13, 7003, "characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])  # SYNTHETIC
        self.assertTrue(any("VERIFY node" in l and "REPLACEMENT SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])
        g.fire("SpawnerStoppedEvent", SpawnerComponentHandle=0x214002)
        g.step(5)
        self.assertTrue(any("put back (its Spawner stopped)" in l and ": OK" in l for l in self.lines(g)))
        self.assertEqual(g.lua.eval("PF.var_actors(3)"), 9001)
        self.assertEqual(g.lua.eval("PF.var_uid(3)") & 0xFFFFFFFFFFFFFFFF, 0x8000000000000000 | 9001)
        self.assertEqual(len(g.lua.eval("PF.writes")), 4)                          # 2 to arm, 2 to put back

    def test_the_original_spawning_is_reported(self):
        g = self.game()
        self.spawn(g, 11, 7001, "characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
        self.spawn(g, 12, 7002, "characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])
        self.spawn(g, 13, 7003, "characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
        self.assertTrue(any("ORIGINAL SPAWNED" in l for l in self.lines(g)), self.lines(g)[-4:])

    def test_nothing_is_written_off_zurkon(self):
        g = self.game(planet="NefCity")
        self.spawn(g, 11, 7001, "characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
        self.spawn(g, 12, 7002, "characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])
        self.assertFalse([l for l in self.lines(g) if "ARMED" in l])
        self.assertEqual(len(g.lua.eval("PF.writes")), 0)

    def test_a_reloaded_variable_is_never_written(self):
        g = self.game()
        self.spawn(g, 11, 7001, "characters\\enemy\\grunt.actor", ["SceneObject", "GameBotShooter"])
        self.spawn(g, 12, 7002, "characters\\enemy\\flyer.actor", ["SceneObject", "GameBotMeleeFlier"])
        self.assertEqual(len(g.lua.eval("PF.writes")), 2)
        g.lua.execute("PF.var(3, 2, 9001, 0x%X)" % (0x8000000000000000 | 9001))      # the level reloaded: generation 2
        g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        g.step(5)
        self.assertEqual(len(g.lua.eval("PF.writes")), 2)
        self.assertTrue(any("put back: skipped" in l for l in self.lines(g)))

    def test_it_is_a_developer_file(self):
        self.assertNotIn("dev(spawnproof).lua", [p.name for p in script_files(release=True)])
        self.assertNotIn("dev(spawnproof).lua", [p.name for p in script_files()])


if __name__ == "__main__":
    unittest.main()
