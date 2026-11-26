#!/usr/bin/env python3
"""test_stage_lua_scale.py - 18_rando_stage_enemies.lua (scale 2.0.0) with a small and a very large manifest (lupa).

16_rando_spawners.lua is stubbed with the few V functions 18 calls (stage_mode, stage_manifest, short, same_name,
handle_uid, presence, encounter, lvl). Checks:
  * <= 20 changes: every STAGE CHANGE line at the start, as stage Lua 1.1.0 did;
  * a big manifest: one STAGE ZONE line per zone at the start, no STAGE CHANGE line until its spawner is listed;
    then exactly one STAGE CHANGE line per listed spawner (never twice, across levels), STAGE VARIABLE per level,
    STAGE VARIABLES counts only for listed spawners, STAGE SPAWN for the patched spawner;
  * the log checker's STAGE CHANGE regex still reads the lines;
  * cost: index + a listing tick of 240 spawners with 600 changes.
usage: python -I test_stage_lua_scale.py SCRIPTS_DIR [MANIFEST_LUA_SMALL]
"""
import os
import re
import sys
import time

from lupa import LuaRuntime

SCRIPTS = sys.argv[1]
SMALL = sys.argv[2] if len(sys.argv) > 2 else None
fails = 0


def check(c, m):
    global fails
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        fails += 1


STUB = r'''
RANDO = { say = function(t, o) py_say(t) end, config = {} }
local V = { STAGE_LUA = "1.1.0" }
RANDO_SPAWNERS = { V = V, frame = 0 }
V.stage_mode = function() return true end
V.stage_manifest = function() return RANDO_STAGE_ENEMIES end
V.short = function(n) n = tostring(n or ""); return (n:gsub("^.*[\\/]", ""):gsub("%.actor$", "")) end
V.same_name = function(a, b) if not (a and b) then return false end a, b = V.short(a), V.short(b)
  local n = math.min(#a, #b, 19) return a:sub(1, n) == b:sub(1, n) end
V.handle_uid = function(h) return HANDLE_UID[h] end
V.presence = function(h) return "present" end
V.encounter = function() return "-" end
HANDLE_UID = {}
'''


def runtime(manifest_src):
    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    LOG = []
    g.py_log = lambda *a: LOG.append("\t".join(str(x) for x in a))
    g.py_say = lambda *a: None
    lua.execute('rivet = setmetatable({ log = function(...) py_log(...) end }, { __index = function() return function() end end })')
    lua.execute(STUB)
    lua.execute(manifest_src)
    lua.execute(open(os.path.join(SCRIPTS, "18_rando_stage_enemies.lua"), encoding="utf-8").read())
    return lua, LOG


def big_manifest(nz=30, per=20):
    L = ["RANDO_STAGE_ENEMIES = { format = 1, tool = \"3.0.0-alpha.2\", kit = \"v3.0-dev\", profile = \"v3\", label = \"test\", stage_lua = \"1.1.0\",",
         "  stage_file = \"mods/RandoEnemies.stage\", stage_sha256 = \"x\", changes = {"]
    n = 0
    for z in range(nz):
        for k in range(per):
            n += 1
            L.append('    { zone = "levels\\\\i29\\\\instance\\\\planet%d\\\\z%d.zone", zone_id = "%016X", planet = "planet%d", '
                     'section = "Zone Script Vars", offset = %d, var_index = %d, original_uid = "%016X", original_index = 1, '
                     'original = "enm_pirate_robot_shooter", original_family = "ground", replacement_uid = "%016X", '
                     'replacement_index = 2, replacement = "enm_pirate_robot_melee", replacement_family = "swarmer", '
                     'original_refs = 3, replacement_refs = 2, tier = "kin/volume", '
                     'pair = "factory|enm_pirate_robot_sh/ground>enm_pirate_robot_me/swarmer", spawner_keys = { "%016X" } },'
                     % (z % 7, z, 0xA000 + z, z % 7, 32 * k, k, 0x1000 + z, 0x2000 + z, 0xF000000 + n))
    L += ["  },", "}"]
    return "\n".join(L), n


IS_CHANGE = re.compile(r"STAGE CHANGE \d+:")
RE_CHANGE = re.compile(r"STAGE CHANGE (\d+): .*?\(([^)]+)\) -> [0-9A-F]{16}(?: #\d+)? \(([^)]+)\) \| .*\| spawners (.*)$")

# ---- small manifest: as before ---------------------------------------------------------------------------------------
if SMALL:
    lua, LOG = runtime(open(SMALL, encoding="utf-8").read())
    n = len(list(lua.globals().RANDO_STAGE_ENEMIES.changes.values()))
    lua.globals().RANDO_SPAWNERS.V.lvl = lua.table_from({"order": lua.table_from({})})
    lua.eval("RANDO_SPAWNERS.V.stage_tick")(1, True, True)
    ch = [l for l in LOG if IS_CHANGE.search(l)]
    check(n <= 20 and len(ch) == n, "small manifest (%d changes): every STAGE CHANGE line at the start (%d)" % (n, len(ch)))
    check(not any("STAGE ZONE" in l for l in LOG), "small manifest: no STAGE ZONE lines")
    check(all(RE_CHANGE.search(l) for l in ch), "small manifest: stage_check_log's regex reads every STAGE CHANGE line")

# ---- big manifest --------------------------------------------------------------------------------------------------
src, N = big_manifest()
lua, LOG = runtime(src)
V = lua.globals().RANDO_SPAWNERS.V
lua.execute("RANDO_SPAWNERS.V.lvl = { order = {}, deaths_seen = 0 }")
t0 = time.time()
V.stage_tick(1, True, True)
check(sum("STAGE ZONE" in l for l in LOG) == 30, "big manifest (%d changes): 30 STAGE ZONE lines at the start" % N)
check(not any(IS_CHANGE.search(l) for l in LOG), "big manifest: no STAGE CHANGE line before a spawner is listed")
check(any("STAGE MODE: %d change(s) in 30 zone(s) on 7 planet(s)" % N in l for l in LOG), "big manifest: STAGE MODE summary line")
check(any("STAGE MODE ON" in l and "%d change(s)" % N in l for l in LOG), "STAGE MODE ON keeps its format (log checker, old tools)")
# a level that lists 240 spawners; 3 of them are changed spawners (zone 4: changes 81, 82, 83)
lua.execute(r'''
local L = { deaths_seen = 0, order = {} }
for i = 1, 237 do L.order[#L.order + 1] = { key = string.format("%016X", 0xB000000 + i), kind = "factory",
  orig = { uid = string.format("%016X", 0x1234 + i), actors = i }, var = { idx = i } } end
for _, n in ipairs({ 81, 82, 83 }) do
  local c = RANDO_STAGE_ENEMIES.changes[n]
  L.order[#L.order + 1] = { key = c.spawner_keys[1], kind = "factory", orig = { uid = c.replacement_uid, actors = 9000 + n }, var = { idx = 500 + n } }
  HANDLE_UID[9000 + n] = c.replacement_uid
end
RANDO_SPAWNERS.V.lvl = L
''')
t1 = time.time()
V.stage_tick(100, True, True)
t_tick = time.time() - t1
ch = [l for l in LOG if IS_CHANGE.search(l)]
check(len(ch) == 3 and all(RE_CHANGE.search(l) for l in ch), "listing: one STAGE CHANGE line per listed changed spawner (3)")
check(sorted(int(RE_CHANGE.search(l).group(1)) for l in ch) == [81, 82, 83], "listing: the right changes (81, 82, 83)")
check(sum("STAGE VARIABLE factory" in l and "IS loaded" in l for l in LOG) == 3, "listing: STAGE VARIABLE ... IS loaded for each")
counts = [l for l in LOG if "STAGE VARIABLES of the listed spawners" in l]
check(len(counts) == 1 and counts[0].count("change ") == 3, "STAGE VARIABLES counts cover only the 3 listed spawners")
V.stage_tick(200, True, True)
check(len([l for l in LOG if IS_CHANGE.search(l)]) == 3, "next look: no STAGE CHANGE line twice")
# a spawn of a listed changed spawner
lua.execute(r'''
local c = RANDO_STAGE_ENEMIES.changes[82]
RANDO_SPAWNERS.V.stage_on_spawn({ h = 777 }, { key = c.spawner_keys[1], kind = "factory", orig = { uid = c.replacement_uid, actors = 9082 } },
  { name = "enm_pirate_robot_melee", family = "swarmer" }, nil, nil)
''')
sp = [l for l in LOG if "STAGE SPAWN 777" in l]
check(len(sp) == 1 and "(the patched spawner)" in sp[0] and "REPLACEMENT SPAWNED" in sp[0], "STAGE SPAWN of the patched spawner")

# A shared node Template variable has multiple owner keys but one stage change.
lua.execute(r'''
local c = RANDO_STAGE_ENEMIES.changes[82]
c.adapter = "node_template"
c.spawner_keys = { "NODE-A", "NODE-B" }
RANDO_STAGE.idx = nil
local idx = RANDO_STAGE.index()
SHARED_OWNER_INDEX_OK = idx.keys["NODE-A"] == c and idx.keys["NODE-B"] == c
RANDO_SPAWNERS.V.stage_on_spawn({ h = 778 },
  { key = "NODE-B", kind = "template", orig = { uid = c.replacement_uid, actors = 9182 } },
  { name = "enm_pirate_robot_melee", family = "swarmer" }, nil, nil)
''')
check(lua.globals().SHARED_OWNER_INDEX_OK, "shared node Template: both owner keys index the same single manifest change")
shared_spawn = [l for l in LOG if "STAGE SPAWN 778" in l]
check(len(shared_spawn) == 1 and "(the patched spawner)" in shared_spawn[0]
      and "REPLACEMENT SPAWNED" in shared_spawn[0], "shared node Template: spawn through second owner is attributed correctly")
# a new level listing the same spawner: STAGE VARIABLE again, STAGE CHANGE not again
lua.execute(r'''
local L = { deaths_seen = 0, order = {} }
local c = RANDO_STAGE_ENEMIES.changes[81]
L.order[1] = { key = c.spawner_keys[1], kind = "factory", orig = { uid = c.replacement_uid, actors = 9081 }, var = { idx = 581 } }
RANDO_SPAWNERS.V.lvl = L
''')
n_var = sum("STAGE VARIABLE factory" in l for l in LOG)
V.stage_tick(400, True, True)
check(sum("STAGE VARIABLE factory" in l for l in LOG) == n_var + 1, "new level: STAGE VARIABLE again for the listed spawner")
check(len([l for l in LOG if IS_CHANGE.search(l)]) == 3, "new level: its STAGE CHANGE line is not repeated")
check(any("STAGE SUMMARY (next level / checkpoint)" in l for l in LOG), "the level before got its STAGE SUMMARY")
# cost
lua.execute("RANDO_STAGE.idx = nil; RANDO_STAGE.m_seen = nil")
c0 = time.time()
lua.eval("RANDO_STAGE.index")()
t_index = time.time() - c0
check(t_index < 0.05 and t_tick < 0.05, "cost: index of %d changes %.1f ms, a 240-spawner listing look %.1f ms (lupa)" % (N, 1000 * t_index, 1000 * t_tick))
print("\n%d failed" % fails)
sys.exit(1 if fails else 0)