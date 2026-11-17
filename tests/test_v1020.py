"""Dev 10.20 (kit 10.0.15), asked for: "Dev 10.19 still does NOT work in the actual game" (rivet.log of
2026-11-17 with dev 10.19 / kit 10.0.14, kept as tests/data/round30_rivet.log: Zurkon arena, NefCity,
Ardolis, Cordelion; save with Chaos ON).

What that log PROVES (real game, see TheLogTests):
  * kit 10.0.14 / dev 10.19 loaded, 24 of 24 scripts, no Lua error;
  * 18 censuses, every one "0 spawner node(s) read, 0 template(s)": nothing was ever randomized;
  * node +0x60 IS its Spawner component's handle (6 of 6 dumped pairs; same actor at +0x10), and a
    SpawnerStoppedEvent carries that same handle (0x214EBC);
  * neither the node nor its Spawner keeps a Prius (ddlPriusData 0) and the Spawner bytes that reached the
    log hold no pointer but the vtable and the actor;
  * rivet.log keeps 1024 characters of a line: the 432-byte Spawner dumps stopped at 306 bytes;
  * "factory-only spawner (no Templates)" was reported for nodes whose bytes are zero-filled memory.

So 10.19's premise (the Spawner component carries the Templates list) is refuted, and where the list lives at
runtime is still unknown. 10.20 does not guess another offset: it fixes the two diagnostics above and adds
dev(spawnprobe).lua, a READ-ONLY collector for the facts still missing.

Fixtures: the node / Spawner bytes are the real dumped bytes of node b38522d499c03015 (Zurkon). The 126
Spawner bytes the log could not show are zero-filled (REAL bytes unknown). Anything else (a pointer at
+0x198, a template uid behind it, a changed byte) is SYNTHETIC and named so in the test.
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

LOG = ROOT / "tests" / "data" / "round30_rivet.log"
NODE_UID = "b38522d499c03015"
NODE_ADDR = 0x20CE5994180
SPAWNER_ADDR = 0x20CE5A23F00
NODE_HANDLE = 0x214EBB
SPAWNER_HANDLE = 0x214EBC          # = 2182844, the SpawnerStoppedEvent of the log
ACTOR_HANDLE = 1087000             # the node's actor handle (any: the log does not give it)


def log_text():
    return LOG.read_text(encoding="utf-8")


def dumps():
    """{(uid, kind): bytes} of the 10.19 dump lines (kind 'node' or 'spawner')."""
    out = {}
    for line in log_text().splitlines():
        m = re.search(r"RANDO-SPAWNERS\tdump (\w+) (Spawner component Spawner|SpawnerScriptAction) .*?: ([0-9a-f ]+)$", line)
        if m:
            out[(m.group(1), "spawner" if m.group(2).startswith("Spawner component") else "node")] = bytes.fromhex(m.group(3).replace(" ", ""))
    return out


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def u64(b, o):
    return int.from_bytes(b[o:o + 8], "little")


class TheLogTests(unittest.TestCase):
    """Facts read from the real game log (no simulator)."""

    def test_dev_1019_loaded_cleanly_and_read_no_node(self):
        text = log_text()
        self.assertIn("RANDO-NOTIFY\tRandomizer dev 10.19 - seed", text)
        self.assertIn("RANDO-KIT all 12 required scripts are 10.0.14", text)
        self.assertIn("[script] loaded 24 of 24 scripts", text)
        self.assertNotIn("RANDO-ERROR", text)
        census = re.findall(r"census \d+ \([^)]*\): (\d+) spawner node\(s\) read, (\d+) template", text)
        self.assertEqual(len(census), 17)                  # censuses 1-18; number 5 never reached the log
        self.assertTrue(all(n == "0" and t == "0" for n, t in census))
        self.assertIn("0\tspawner slot(s) put back to their original enemies", text)

    def test_node_0x60_is_its_spawner_components_handle(self):
        d = dumps()
        uids = sorted({u for u, _ in d})
        self.assertEqual(len(uids), 6)
        for uid in uids:
            node, sp = d[(uid, "node")], d[(uid, "spawner")]
            self.assertEqual(len(node), 128)
            self.assertEqual(u32(node, 0x60), u32(sp, 0x1C), uid)              # the handle
            self.assertEqual(u64(node, 0x10), u64(sp, 0x10), uid)              # the same actor
            self.assertEqual(u32(node, 0x1C) + 1, u32(sp, 0x1C), uid)          # made right after the node
            self.assertEqual(u64(node, 0x08), 0, uid)                          # no ddlPriusData
            self.assertEqual(u64(sp, 0x08), 0, uid)                            # nor in the Spawner
            self.assertEqual(u64(node, 0x48), int(uid, 16), uid)               # instance uid

    def test_the_stopped_event_names_the_spawner_handle(self):
        self.assertIn("stopped: SpawnerComponentHandle %d, sender" % SPAWNER_HANDLE, log_text())
        self.assertEqual(u32(dumps()[(NODE_UID, "spawner")], 0x1C), SPAWNER_HANDLE)

    def test_the_spawner_holds_no_pointer_in_the_bytes_the_log_kept(self):
        for (uid, kind), b in dumps().items():
            if kind != "spawner":
                continue
            ptrs = [o for o in range(0, len(b) - 7, 8)
                    if 0x10000 < u64(b, o) < 0x7FFFFFFFFFFF and u64(b, o) % 8 == 0 and u64(b, o) & 0xFFFFFFFF and (u64(b, o) >> 40) in (0x2, 0x7F)]
            # +0x00 vtable, +0x10 actor; b38522d4 also holds a module pointer at +0xD0 (not heap: no list)
            self.assertTrue(set(ptrs) <= {0x00, 0x10, 0xD0}, (uid, [hex(o) for o in ptrs]))

    def test_the_spawner_dumps_were_cut_by_the_log_line_limit(self):
        lines = [l for l in log_text().splitlines() if "dump" in l and "Spawner component Spawner size 432" in l]
        self.assertEqual(len(lines), 6)
        for l in lines:
            self.assertEqual(len(dumps()[(l.split("dump ")[1].split(" ")[0], "spawner")]), 306)   # not 432
            self.assertGreater(len(l), 1000)


# ---------------------------------------------------------------------------------------------- the fixture
FIXTURE_LUA = r"""
local node_bytes, sp_bytes = %(node)s, %(sp)s
local function put(addr, t) for i, v in ipairs(t) do SIM.mem[addr + i - 1] = v end end
put(%(naddr)d, node_bytes)
put(%(saddr)d, sp_bytes)
for i = 0, 0xBF do SIM.mem[%(actor_ptr)d + i] = 0 end         -- the node's Actor (its bytes are not in the log)
FIX = { writes = 0, extra = {} }
local orig_write, orig_component, orig_components, orig_nodes, orig_find_uid = rivet.write, rivet.component, rivet.components, rivet.script_nodes, rivet.find_uid
rivet.write = function(...) FIX.writes = FIX.writes + 1; return orig_write(...) end
rivet.script_nodes = function(filter, limit)
  return { { component = %(nh)d, actor = %(ah)d, uid = "%(uid)s", class = "SpawnerScriptAction" } }
end
rivet.component = function(actor, class)
  if actor == %(ah)d and class == "SpawnerScriptAction" then return { address = string.format("%%X", %(naddr)d), size = 128, handle = %(nh)d } end
  if actor == %(ah)d and class == "Spawner" then return { address = string.format("%%X", %(saddr)d), size = 432, handle = FIX.spawner_handle or %(sh)d } end
  local e = FIX.extra[actor]
  if e then return { address = string.format("%%X", e.addr), size = 0x40, handle = actor * 2 } end
  return orig_component(actor, class)
end
rivet.components = function(actor)
  if actor == %(ah)d then return { "SpawnerScriptAction", "Spawner" } end
  local e = FIX.extra[actor]
  if e then return e.classes end
  return orig_components(actor)
end
rivet.find_uid = function(id)
  for h, e in pairs(FIX.extra) do if e.uid and e.uid:upper() == tostring(id):upper() then return h end end
  return nil
end
local orig_uid = rivet.uid
rivet.uid = function(h) local e = FIX.extra[h]; if e then return e.uid end; return orig_uid(h) end
"""


def real_bytes():
    d = dumps()
    node = d[(NODE_UID, "node")]
    sp = d[(NODE_UID, "spawner")] + bytes(432 - 306)       # the unseen tail: zero-filled (REAL bytes unknown)
    return node, sp


def lua_list(b):
    return "{" + ",".join(str(x) for x in b) + "}"


def fixture(g, node=None, sp=None):
    n, s = real_bytes()
    node, sp = node or n, sp or s
    actor_ptr = u64(node, 0x10)
    g.lua.execute(FIXTURE_LUA % {"node": lua_list(node), "sp": lua_list(sp), "naddr": NODE_ADDR, "saddr": SPAWNER_ADDR,
                                  "actor_ptr": actor_ptr, "nh": NODE_HANDLE, "ah": ACTOR_HANDLE, "sh": SPAWNER_HANDLE,
                                  "uid": NODE_UID})


def add_actor(g, handle, uid, classes, addr, actor_ptr, flags=0, asset_id=None, asset_name=None):
    """SYNTHETIC: a loaded actor (a template bot or a spawned bot) with one component at addr."""
    g.lua.execute(r"""
      local h, addr, actor = %d, %d, %d
      for i = 0, 0x3F do SIM.mem[addr + i] = 0 end
      SIM.put_u64(addr + 0x10, actor)
      for i = 0, 0xBF do SIM.mem[actor + i] = 0 end
      SIM.put_u32(actor + 0x10, %d)
      FIX.extra[h] = { uid = "%s", classes = { %s }, addr = addr }
    """ % (handle, addr, actor_ptr, flags, uid, ",".join('"%s"' % c for c in classes)))
    if asset_id is not None:
        asset = actor_ptr + 0x1000
        name = asset + 0x100
        g.lua.execute(r"""
          local actor, asset, name = %d, %d, %d
          for i = 0, 0x2F do SIM.mem[asset + i] = 0 end
          SIM.put_u64(actor + 0x30, asset)
          SIM.put_u64(asset + 8, %d)
          SIM.put_u64(asset + 0x10, name)
          local s = "%s"
          for i = 1, #s do SIM.mem[name + i - 1] = s:byte(i) end
          SIM.mem[name + #s] = 0
        """ % (actor_ptr, asset, name, asset_id, asset_name))


class SpawnerLayerFixTests(unittest.TestCase):
    """16_rando_spawners.lua on the real node / Spawner bytes (the zero-filled tail is the only assumption)."""

    def game(self):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False})
        self.assertFalse(g.load_errors, g.load_errors)
        fixture(g)
        return g

    def read_node(self, g):
        return g.lua.eval('function() local ok, rec, why = pcall(RANDO_SPAWNERS.read_node, '
                          '{ component = %d, actor = %d, uid = "%s", class = "SpawnerScriptAction" }) '
                          'return ok, rec, why end' % (NODE_HANDLE, ACTOR_HANDLE, NODE_UID))()

    def test_zeroed_memory_is_not_a_factory_only_spawner(self):
        # 10.19 called this real node "factory-only spawner (no Templates)": zero bytes passed the layout check
        g = self.game()
        ok, rec, why = self.read_node(g)
        self.assertTrue(ok, why)
        self.assertIsNone(rec)
        self.assertNotIn("factory-only", str(why))
        self.assertIn("Spawner component Spawner", str(why))

    def test_three_empty_lists_are_rejected_but_a_real_factory_only_prius_is_not(self):
        g = self.game()
        f = g.lua.eval("""function(fac_count, loc_count)
          local b = {}
          for i = 1, 0x90 do b[i] = 0 end
          local function arr(off, n) if n > 0 then for k = 0, 7 do b[off + 1 + k] = ({0, 0x10, 0, 0x20, 0, 0, 0, 0})[k + 1] end end b[off + 9] = n end
          arr(8, fac_count); arr(56, loc_count)
          local lay, why, kind = RANDO_SPAWNERS.layout_at(b, 8)
          return tostring(why), tostring(kind)
        end""")
        why, kind = f(0, 0)
        self.assertIn("all three lists empty", why)
        self.assertNotEqual(kind, "empty")
        why, kind = f(1, 0)                                  # a factory and no Templates: still factory-only
        self.assertEqual(kind, "empty")
        why, kind = f(0, 2)                                  # spawn points and no Templates: still empty
        self.assertEqual(kind, "empty")

    def test_dumps_fit_the_log_line_and_keep_every_byte(self):
        g = self.game()
        self.read_node(g)
        lines = [l for l in g.logs() if "RANDO-SPAWNERS\tdump" in l]
        self.assertTrue(lines)
        for l in lines:
            self.assertLess(len("[script] " + l), 1024, l[:80])
        sp = [l for l in lines if "Spawner component Spawner size 432" in l]
        got = bytes.fromhex("".join(l.split(": ", 1)[1].replace(" ", "") for l in sp))
        self.assertEqual(got, real_bytes()[1])                          # all 432 bytes, in order


class SpawnProbeTests(unittest.TestCase):
    """dev(spawnprobe).lua: read-only; real node / Spawner bytes; SYNTHETIC pointers, uids and changes."""

    def game(self, node=None, sp=None):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnprobe=True)
        self.assertFalse(g.load_errors, g.load_errors)
        fixture(g, node, sp)
        g.travel("Zurkon")
        g.step(200)
        return g

    def probe_lines(self, g):
        return [l for l in g.logs() if "RANDO-SPAWNPROBE" in l]

    def test_it_is_a_developer_file_and_never_in_a_release(self):
        self.assertTrue((ROOT / "mod/RiftApartRandomizer/scripts/dev(spawnprobe).lua").exists())
        self.assertNotIn("dev(spawnprobe).lua", [p.name for p in script_files(release=True)])
        self.assertNotIn("dev(spawnprobe).lua", [p.name for p in script_files()])       # only when asked for
        g = Game(spawnprobe=True)
        g.ready()
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.15"))
        self.assertTrue(g.log_has("dev(spawnprobe)"))
        self.assertFalse([l for l in g.logs() if "RANDO-ERROR" in l])

    def test_index_matches_the_spawner_by_the_handle_at_0x60(self):
        g = self.game()
        idx = [l for l in self.probe_lines(g) if "\tindex " in l]
        self.assertTrue(idx, self.probe_lines(g)[:5])
        self.assertIn("Spawner handle == node +0x60 for 1, another handle 0, no Spawner 0", idx[-1])
        self.assertIn("Spawner sizes 432 x1", idx[-1])

    def test_a_spawner_with_another_handle_is_not_used(self):
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnprobe=True)
        fixture(g)
        g.lua.execute("FIX.spawner_handle = %d" % (SPAWNER_HANDLE + 7))
        g.travel("Zurkon")
        g.step(200)
        idx = [l for l in self.probe_lines(g) if "\tindex " in l][-1]
        self.assertIn("for 0, another handle 1", idx)
        self.assertFalse([l for l in self.probe_lines(g) if "\tprobe " in l])

    def test_a_frame_budget_stop_is_retried_not_fatal(self):
        # rivet_hook raises "ran past the frame budget" into a script that runs too long (10.17-10.19 logs)
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnprobe=True)
        fixture(g)
        g.lua.execute("""
          local orig = rivet.component
          FIX.budget = 2
          rivet.component = function(a, c)
            if c == "Spawner" and FIX.budget > 0 then FIX.budget = FIX.budget - 1; error("ran past the 8 ms frame budget", 0) end
            return orig(a, c)
          end""")
        g.travel("Zurkon")
        g.step(200)
        idx = [l for l in self.probe_lines(g) if "\tindex " in l]
        self.assertTrue(idx)
        self.assertIn(": 1 node(s); Spawner handle == node +0x60 for 1, another handle 0, no Spawner 0", idx[-1])
        self.assertFalse([l for l in g.logs() if "RANDO-ERROR" in l])

    def test_the_probe_writes_nothing_and_every_line_fits(self):
        g = self.game()
        g.fire("SpawnerStoppedEvent", SpawnerComponentHandle=SPAWNER_HANDLE)
        g.step(60)
        self.assertEqual(g.lua.eval("FIX.writes"), 0)
        lines = self.probe_lines(g)
        self.assertTrue([l for l in lines if "\tprobe index node %s" % NODE_UID in l])
        for l in lines:
            self.assertLess(len("[script] " + l), 1024, l[:80])
        self.assertFalse([l for l in g.logs() if "RANDO-ERROR" in l])

    def test_the_stopped_event_finds_the_node_through_its_handle(self):
        g = self.game()
        g.fire("SpawnerStoppedEvent", SpawnerComponentHandle=SPAWNER_HANDLE)
        g.step(5)
        self.assertTrue(g.log_has("stopped: SpawnerComponentHandle 214EBC = node %s (its +0x60)" % NODE_UID),
                        self.probe_lines(g)[-6:])

    def test_the_whole_spawner_is_dumped(self):
        g = self.game()
        sp = [l for l in self.probe_lines(g) if "\tprobe index node %s Spawner +0x" % NODE_UID in l]
        got = bytes.fromhex("".join(l.split(": ", 1)[1].replace(" ", "") for l in sp))
        self.assertEqual(got, real_bytes()[1])

    def test_a_template_uid_one_pointer_away_is_found(self):
        # SYNTHETIC: a readable pointer at Spawner +0x198 (the offset 10.19's census found readable in many
        # Spawners) to a block with a template bot's uid at +0x20
        node, sp = real_bytes()
        block = 0x20CE6000000
        sp = bytearray(sp)
        sp[0x198:0x1A0] = block.to_bytes(8, "little")
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False}, spawnprobe=True)
        fixture(g, node, bytes(sp))
        g.lua.execute("for i = 0, 0xFF do SIM.mem[%d + i] = 0 end; SIM.put_u64(%d + 0x20, 0x9ABC0123456789AB)" % (block, block))
        add_actor(g, 777001, "9abc0123456789ab", ["SceneObject", "GameBotShooter"], 0x20CE7000000, 0x20CE7100000,
                  flags=4, asset_id=0x1234, asset_name="bots/goon.actor")
        g.travel("Zurkon")
        g.step(200)
        hit = [l for l in self.probe_lines(g) if "UID HIT" in l]
        self.assertTrue(hit, self.probe_lines(g)[-10:])
        self.assertIn("Spawner+0x198->20CE6000000+0x20 = 9ABC0123456789AB -> handle 777001", hit[0])
        self.assertIn("TEMPLATE", hit[0])
        self.assertIn("GameBotShooter", hit[0])
        self.assertTrue(g.log_has("readable pointers at +0x198 x1"))

    def test_a_spawned_bot_is_described_and_a_changed_spawner_is_reported(self):
        # SYNTHETIC: a spawn, then the Spawner's +0xC8 changes (as an active spawner's runtime state would)
        g = self.game()
        add_actor(g, 888001, "8000000000000abc", ["SceneObject", "GameBotGrunt", "Health"], 0x20CE8000000, 0x20CE8100000,
                  asset_id=0x5678, asset_name="bots/grunt.actor")
        g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=0, SpawnedHandle=888001)
        g.lua.execute("SIM.put_u64(%d + 0xC8, 0x1122334455667788)" % SPAWNER_ADDR)
        g.step(120)
        lines = self.probe_lines(g)
        spawn = [l for l in lines if "\tspawn 1:" in l]
        self.assertTrue(spawn, lines[-8:])
        self.assertIn("handle 888001 uid 8000000000000abc", spawn[0])
        self.assertIn("asset 0000000000005678 bots/grunt.actor", spawn[0])
        self.assertIn("GameBotGrunt", spawn[0])
        sweep = [l for l in lines if "sweep 1: Spawner of node %s changed at 1 place(s): +0x0C8" % NODE_UID in l]
        self.assertTrue(sweep, [l for l in lines if "sweep" in l])
        self.assertEqual(g.lua.eval("FIX.writes"), 0)


if __name__ == "__main__":
    unittest.main()
