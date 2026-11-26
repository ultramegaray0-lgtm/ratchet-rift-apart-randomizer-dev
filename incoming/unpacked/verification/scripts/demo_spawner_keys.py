"""demo_spawner_keys.py - what 18_rando_stage_enemies.lua reports in the game with a 1.0.0 manifest (every same-kind
spawner in spawner_keys, each twice) vs a 1.0.1 manifest (only the spawner seen holding the original uid).

The situation of the Ardolis POC, in the kit's own Lua test harness (tests/v076dev4/test_stage_dev4.py's fake scene):
  F1 = the patched spawner (its variable held the original uid B2; the loaded .stage makes it hold B3)
  F2 = another spawner of the SAME kind whose variable holds a DIFFERENT template actor of that kind (B4) - untouched
usage: python -I demo_spawner_keys.py <kit folder>
"""
import os
import sys

from lupa import LuaRuntime

KIT = sys.argv[1]
sys.path.insert(0, os.path.join(KIT, "tools", "stage_enemies"))
import stage_enemies as SE  # noqa: E402

MEM = {}
BASE, VS = 0x10000000, 0x40


def put(a, bs):
    for i, b in enumerate(bs):
        MEM[a + i] = b


def py_read(addr, n):
    a = int(str(addr), 16)
    out = []
    for i in range(int(n)):
        if a + i not in MEM:
            break
        out.append("%02X" % MEM[a + i])
    return " ".join(out) if out else None


def set_var(idx, uid_hex, actors, gen=1, typ=5):
    a = BASE + idx * VS
    put(a, [0] * VS)
    put(a, list(bytes.fromhex(uid_hex))[::-1])
    put(a + 0x10, list(actors.to_bytes(4, "little")))
    put(a + 0x34, list(typ.to_bytes(2, "little")))
    put(a + 0x36, list(gen.to_bytes(2, "little")))


KINDS = [("enm_neo_nefarious_shooter", "ground", 11, "00000000000000B1"),
         ("enm_neo_nefarious_melee", "swarmer", 12, "00000000000000B2"),     # original template actor (patched ref)
         ("enm_neo_nefarious_swarmer", "swarmer", 13, "00000000000000B3"),   # replacement
         ("enm_neo_nefarious_melee", "swarmer", 14, "00000000000000B4")]     # a second melee template actor


def run(spawner_keys):
    MEM.clear()
    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    LOG = []
    g.py_log = lambda *a: LOG.append("\t".join(str(x) for x in a))
    g.py_read = py_read
    lua.execute('rivet = setmetatable({ log = function(...) py_log(...) end, read = function(a, n) return py_read(a, n) end, '
                'write = function() return false end }, { __index = function() return function() return nil end end })')
    for f in ("01_rando_data.lua", "02_rando_generator.lua"):
        lua.execute(open(os.path.join(KIT, "scripts", f), encoding="utf-8").read())
    lua.execute('RANDO = { config = { enemy_compat = "killable", enemy_randomizer = true }, state = { enemy_combat = {} }, '
                'mark_changed = function() end, say = function() end, subscribe = function() end }')
    lua.execute(open(os.path.join(KIT, "scripts", "16_rando_spawners.lua"), encoding="utf-8").read())
    lua.execute(open(os.path.join(KIT, "scripts", "18_rando_stage_enemies.lua"), encoding="utf-8").read())
    lua.execute('local V = RANDO_SPAWNERS.V; SC = { base = %d, max = 64 }; V.scene = function() return SC end; '
                'V.enabled = function() return true end; V.role_on = function() return true end; RANDO_SPAWNERS.frame = 100' % BASE)
    set_var(1, KINDS[2][3], 13)     # F1: the .stage loaded - holds the replacement
    set_var(2, KINDS[3][3], 14)     # F2: same kind, other template actor, not changed
    set_var(3, KINDS[0][3], 11)
    m = {"label": "demo", "stage_sha256": "00", "changes": [{
        "zone": "levels/test/z.zone", "zone_id": "8000000000000001", "section": "Zone Script Vars", "rel": 64,
        "original_uid": KINDS[1][3], "original": KINDS[1][0], "original_family": KINDS[1][1],
        "replacement_uid": KINDS[2][3], "replacement": KINDS[2][0], "replacement_family": KINDS[2][1],
        "original_refs_in_script_vars": 1, "replacement_refs_in_script_vars": 1,
        "pair": "factory|enm_neo_nefarious_m/swarmer>enm_neo_nefarious_s/swarmer", "spawner_keys": spawner_keys}]}
    lua.execute(SE.manifest_lua(m))
    lua.execute('''local V = RANDO_SPAWNERS.V
V.new_level("planet test"); V.lvl.scans = 1
for i = 1, 3 do V.add_rec({ kind = "factory", actor = 900 + i, key = "F" .. i, var = { idx = i, gen = 1 } }) end
for _, r in ipairs(V.lvl.order) do V.read_one_orig(SC, r) end''')
    for n, fam, h, uid in KINDS:
        lua.execute('local V = RANDO_SPAWNERS.V; local T = V.tpl_of(%d, "%s"); T.name, T.family, T.class = "%s", "%s", "x"; '
                    'T.role = V.role_of(T)' % (h, uid, n, fam))
    lua.execute("RANDO_SPAWNERS.V.stage_tick(100, true, true)")
    lua.execute('''local V = RANDO_SPAWNERS.V
V.ledger_add({ h = 5001 }, V.lvl.order[1], { name = "enm_neo_nefarious_swarmer", family = "swarmer" }, nil, "NOT CHANGED", V.STAGE_WHY)
V.ledger_add({ h = 5002 }, V.lvl.order[2], { name = "enm_neo_nefarious_melee", family = "swarmer" }, nil, "NOT CHANGED", V.STAGE_WHY)
V.ledger_add({ h = 5003 }, V.lvl.order[2], { name = "enm_neo_nefarious_melee", family = "swarmer" }, nil, "NOT CHANGED", V.STAGE_WHY)
V.new_level("leaving"); RANDO_STAGE.level()''')
    return [l.split("RANDO-STAGE\t", 1)[-1] for l in LOG if "RANDO-STAGE" in l and ("STAGE VARIABLE" in l or "STAGE SUMMARY" in l or "STAGE SPAWNER" in l)]


for label, keys in (("tool 1.0.0 manifest: spawner_keys = every same-kind spawner, twice", ["F1", "F1", "F2", "F2"]),
                    ("tool 1.0.1 manifest: spawner_keys = the spawner seen holding the original uid", ["F1"])):
    print("== " + label)
    for line in run(keys):
        print("   " + line)
