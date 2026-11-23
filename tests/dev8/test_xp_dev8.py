# v0.71-DEV8 weapon XP at runtime: 17_rando_omega.lua's O.xp_pass on fake weapon records
import sys, os, struct
from lupa import LuaRuntime
KIT = sys.argv[1]
MEM = {}
LOG = []
def put(a, bs):
    for i, b in enumerate(bs): MEM[a + i] = b
def py_read(addr, n):
    a = int(str(addr), 16); out = []
    for i in range(int(n)):
        if a + i not in MEM: break
        out.append('%02X' % MEM[a + i])
    return ' '.join(out) if out else None
def py_write(addr, text):
    a = int(str(addr), 16); put(a, [int(x, 16) for x in str(text).split()]); return True
fails = 0
def check(c, m):
    global fails
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails += 1

def setup(target='smart', recs=None):
    MEM.clear(); LOG.clear()
    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals(); g.py_read, g.py_write = py_read, py_write
    g.py_log = lambda *a: LOG.append('\t'.join(str(x) for x in a))
    lua.execute('''rivet = { log = function(...) py_log(...) end, read = function(a, n) return py_read(a, n) end,
                           write = function(a, t) return py_write(a, t) end }''')
    for f in ('01_rando_data.lua', '02_rando_generator.lua'):
        lua.execute(open(os.path.join(KIT, 'scripts', f), encoding='utf-8').read())
    lua.execute('''
RANDO = { config = { weapon_xp_target = "%s", omega_runtime = true }, state = { xp_pending = {}, xp_done = {}, omega = {} },
          mark_changed = function() end, say = function(t) py_log("SAY", t) end,
          item_name = function(k) return RANDO_GEN.item_name(k) end }
''' % target)
    lua.execute(open(os.path.join(KIT, 'scripts', '17_rando_omega.lua'), encoding='utf-8').read())
    ids = lua.eval('(function() local t = {} for w, id in pairs(RANDO_OMEGA.ID_OF) do t[w] = id end return t end)()')
    base = 0x20000000
    lua.execute('RANDO_OMEGA.inv = { route = "type data", hero_owned = true, records = {} }; RANDO_OMEGA.ddl_layout = { live = true, verified = true, id = 0, omega = 136 }')
    for i, (w, slot, xp, om) in enumerate(recs):
        a = base + i * 0x200
        put(a, [0] * 0x100)
        put(a, list(bytes.fromhex(ids[w]))[::-1])
        put(a + 8, list(struct.pack('<I', 1)))
        put(a + 12, list(struct.pack('<I', slot)))
        put(a + 16, list(struct.pack('<I', xp)))
        put(a + 20, list(struct.pack('<f', 10.0))); put(a + 24, list(struct.pack('<f', 10.0)))
        put(a + 136, [om])
        lua.execute('RANDO_OMEGA.inv.records["%s"] = { id_at = %d }' % (w, a))
    return lua

def xp_of(i): return struct.unpack('<I', bytes(MEM[0x20000000 + i * 0x200 + 16 + k] for k in range(4)))[0]
def run(lua): lua.execute('local co = coroutine.create(RANDO_OMEGA.xp_pass); while coroutine.status(co) ~= "dead" do local ok, e = coroutine.resume(co); assert(ok, e) end')

R = [('enforcer', 1001, 15807, 0), ('ryno_8', 1002, 783588, 1), ('lightning_rod', 1003, 19518, 1), ('negatron_collider', 5015, 0, 0), ('cold_snap', 1004, 1980, 0)]
# smart: the Omega weapon with the least XP (Lightning Rod), not the empty Negatron slot, not the non-Omega Cold Snap
lua = setup('smart', R)
lua.execute('RANDO.state.xp_pending["goldbolt:11"] = 5000')
run(lua)
check(xp_of(2) == 19518 + 5000, 'smart: Omega Lightning Rod (least XP of the Omegas) gets +5000')
check(xp_of(4) == 1980 and xp_of(0) == 15807 and xp_of(3) == 0, 'smart: no other record changed')
check(lua.eval('RANDO.state.xp_pending["goldbolt:11"]') is None and lua.eval('RANDO.state.xp_done["goldbolt:11"].w') == 'lightning_rod', 'smart: pending -> done')
# lowest: Cold Snap (1980), never the empty slot
lua = setup('lowest', R)
lua.execute('RANDO.state.xp_pending["a"] = 1000')
run(lua)
check(xp_of(4) == 2980, 'lowest: Cold Snap (least XP held) gets it; empty Negatron slot skipped')
# smart with no Omega held: least XP held
R2 = [(w, s, x, 0) for (w, s, x, _) in R]
lua = setup('smart', R2)
lua.execute('RANDO.state.xp_pending["b"] = 700')
run(lua)
check(xp_of(4) == 2680, 'smart without Omega: the least XP held')
# a done reward is never given twice; a rollback after a load is given again once
lua = setup('smart', R)
lua.execute('RANDO.state.xp_pending["c"] = 4000'); run(lua)
lua.execute('RANDO.state.xp_pending["c"] = 4000'); run(lua)
check(xp_of(2) == 19518 + 4000, 'a reward already done is not given twice')
put(0x20000000 + 2 * 0x200 + 16, list(struct.pack('<I', 19518)))       # the checkpoint took it back
lua.execute('local co = coroutine.create(RANDO_OMEGA.xp_check_rollback); coroutine.resume(co)')
check(xp_of(2) == 19518 + 4000, 'rollback: given again after the load')
# not trusted: nothing written
lua = setup('smart', R)
lua.execute('RANDO_OMEGA.ddl_layout = nil; RANDO.state.xp_pending["d"] = 4000'); run(lua)
check(xp_of(2) == 19518 and lua.eval('RANDO.state.xp_pending["d"]') == 4000, 'layout not trusted: waits, nothing written')
print('FAILURES', fails); sys.exit(1 if fails else 0)
