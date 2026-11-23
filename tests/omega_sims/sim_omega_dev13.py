# DEV13 simulator: round53's situation for 17_rando_omega.lua (type-data route, GameWeaponItem instances).
#   python -I tests/sim_omega_dev13.py <kit> [seed] [mode]
#   mode: round53     - Equip set with SelectedCell 118-216 + an Override set of ItemCount-0 copies (bigger)
#         checkpoint  - round53 plus a checkpoint load in the middle of the first census
#         ngplus      - the Omega's weapon was carried over (XP > 0) but never equipped: its send is still queued
#         ngplus_xp0  - the same with XP 0 (never used): nothing may be written
# Prints PASS/FAIL lines at the end; the exit code is the number of FAILs.
import sys, struct, random
import lupa.lua54 as l54
KIT = sys.argv[1]
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
MODE = sys.argv[3] if len(sys.argv) > 3 else "round53"

mem = {}
def region(base, size): mem[base] = bytearray(size); return base
def find(addr):
    for b, buf in mem.items():
        if b <= addr < b + len(buf): return b, buf
    return None, None
def wb(a, data): b, buf = find(a); buf[a-b:a-b+len(data)] = data
def w8(a, v): wb(a, bytes([v]))
def w16(a, v): wb(a, struct.pack('<H', v))
def w32(a, v): wb(a, struct.pack('<I', v & 0xffffffff))
def w64(a, v): wb(a, struct.pack('<Q', v))
def rd(addr_hex, n):
    a = int(addr_hex, 16); b, buf = find(a)
    if b is None or a + n > b + len(buf): return None
    return ' '.join('%02x' % x for x in buf[a-b:a-b+n]) + ' '
writes = []
def wr(addr_hex, text):
    a = int(addr_hex, 16); data = bytes(int(x, 16) for x in text.split())
    writes.append((a, data)); wb(a, data); return len(data)
heap = [0x40000000]
def alloc(size):
    a = heap[0]; heap[0] += ((size + 0xF) & ~0xF) + 0x10; return region(a, size)
def cstr(s): a = alloc(len(s) + 1); wb(a, s.encode() + b'\0'); return a
def typeinfo(tid, size, fields):
    t = alloc(0xC0); w64(t, cstr("T%X" % tid)); w32(t + 8, tid); w32(t + 0x14, size); w16(t + 0x18, len(fields))
    if fields:
        names, types, offs = alloc(8 * len(fields)), alloc(len(fields)), alloc(4 * len(fields))
        for i, (nm, ty, off) in enumerate(fields):
            w64(names + 8 * i, cstr(nm)); w8(types + i, ty); w32(offs + 4 * i, off)
        w64(t + 0x50, names); w64(t + 0x58, types); w64(t + 0x78, offs)
    return t
def compinfo(name, ti, size=0x48):
    c = alloc(0x110); w64(c + 0x60, cstr(name)); w32(c + 0x78, size); w64(c + 0xC8, ti); return c
TI_I = typeinfo(0xF4ADA6B7, 64, [("ItemConfigHash", 20, 48)])
TI_X = typeinfo(0x12345678, 32, [])

INST = 0x600                                  # ComponentInfo size; the id is at instance+1152 (round51-53)
CI_W = compinfo("GameWeaponItem", TI_I, INST)
CI_X = compinfo("Mover", TI_X)
HERO_ACTOR, EQUIP_ACTOR, OVERRIDE_ACTOR, OTHER_ACTOR = (alloc(0x100) for _ in range(4))
def component(actor, size, handle):
    c = alloc(max(0x48, size)); w64(c, 0x7FF600001000); w64(c + 0x10, actor); w32(c + 0x1C, handle); return c

L = l54.LuaRuntime(unpack_returned_tuples=True)
G = L.globals()
inv_mgr = alloc(0x2168); w64(inv_mgr + 0x10, HERO_ACTOR)
logs = []
def log(*a): logs.append(' '.join(str(x) for x in a))
def component_fn(hero, cls):
    if cls == "GameInventoryManager": return L.table_from({"address": "%016x" % inv_mgr, "size": 0x2168})
    raise Exception("this actor has no %s component" % cls)
G.rivet = L.table_from({"log": log, "read": rd, "write": wr, "hero": lambda: 1090771, "component": component_fn,
                        "time": lambda: 100, "components": lambda h: L.table_from({1: "GameInventoryManager"})})
L.execute('RANDO_FILES = {}')
for f in ("01_rando_data.lua", "02_rando_generator.lua"):
    L.execute(open(f"{KIT}/scripts/{f}", encoding="utf-8").read())
ids = dict(L.eval('function() local t = {} for k, it in pairs(RANDO_DATA.items) do if it.category == "omega" then t[it.weapon:sub(8)] = it.id end end return t end')())
weapons = sorted(ids)

SM = region(0x10000000, 0x2000)
entries, equip, override = [], {}, {}
for i in range(5000): entries.append((component(OTHER_ACTOR, 0, 0x100000 + i), CI_X))
def weapon_item(actor, handle, wid, count, cell, xp):
    c = component(actor, INST, handle); d = c + 1152       # d = the weapon id
    w64(d, wid); w32(d + 8, count); w32(d + 16, xp); wb(d + 20, struct.pack('<ff', 30.0, 30.0)); w8(d + 112, cell)
    return c, d
for k, w in enumerate(weapons):                              # Equip: the weapons you own; most cells above 63
    cell = 0 if k % 5 == 0 else random.randint(118, 216)
    xp = 0 if (MODE == "ngplus_xp0" and w == "bouncer") else 10000 + k
    c, d = weapon_item(EQUIP_ACTOR, 0x200000 + k, int(ids[w], 16), 1, cell, xp)
    equip[w] = d; entries.insert(random.randrange(len(entries)), (c, CI_W))
for k, w in enumerate(weapons + weapons[:4]):                # Override: copies, ItemCount 0, a bigger set
    c, d = weapon_item(OVERRIDE_ACTOR, 0x280000 + k, int(ids[w], 16), 0, 0, 10000 + k)
    override.setdefault(w, d); entries.insert(random.randrange(len(entries)), (c, CI_W))
LK = alloc(16 * len(entries))
for i, (c, ci) in enumerate(entries): w64(LK + 16 * i, c); w64(LK + 16 * i + 8, ci)
w64(SM + 0x13C8, LK); w32(SM + 0x13EC, len(entries))
EQ_INV = component(EQUIP_ACTOR, 0x40, 0x2196344); OV_INV = component(OVERRIDE_ACTOR, 0x40, 0x2196345)

L.execute('''
RANDO = { state = { omega = {}, real = {} }, config = { omega_runtime = true }, subs = {} }
function RANDO.subscribe(c, fn) RANDO.subs[c] = fn end
function RANDO.say(t) rivet.log("SAY", t) end
function RANDO.mark_changed() end
function RANDO.item_name(k) return k end
function RANDO.omega_applied(w, why) RANDO.state.omega[w].status = "applied"; rivet.log("APPLIED", w, why) end
RANDO_SEED = {}
RANDO_REAL = { weapon_item = function(n) return nil end, owned = {} }
function RANDO_REAL.set_owned(item, why) RANDO_REAL.owned[item] = why; RANDO.state.real[item] = { status = "owned" } end
RANDO_TRAVEL = { cps = 0 }
function RANDO_TRAVEL.on_checkpoint(hash, loaded) RANDO_TRAVEL.cps = RANDO_TRAVEL.cps + 1 end
''')
L.execute('RANDO_SPAWNERS = { V = { scene = function() return { scene = %d } end } }' % SM)
L.execute(open(f"{KIT}/scripts/17_rando_omega.lua", encoding="utf-8").read())
O = G.RANDO_OMEGA
# the game names both inventories on the hero (InventoryChangedEvent), resolved like the SceneManager lookup does
L.execute('''
local O = RANDO_OMEGA
O.resolve = function(h)
  if h == %d then return { addr = %d, name = "GameEquipInventory" } end
  if h == %d then return { addr = %d, name = "GameOverrideInventory" } end
end
RANDO.subs["InventoryChangedEvent"]({ fields = { Actor = 1090771, Component = %d } })
RANDO.subs["InventoryChangedEvent"]({ fields = { Actor = 1090771, Component = %d } })
''' % (0x2196344, EQ_INV, 0x2196345, OV_INV, 0x2196344, 0x2196345))
target = "bouncer"
real = "queued" if MODE.startswith("ngplus") else "owned"
L.execute('RANDO.state.omega["%s"] = { status = "pending" }; RANDO.state.real["weapon:%s"] = { status = "%s" }' % (target, target, real))
censuses_before_cp = None
for f in range(6000):
    L.execute('RANDO.frame_t0 = os.clock()')
    O.tick(f, True)
    if MODE == "checkpoint" and censuses_before_cp is None and O.progress is not None and O.progress.i > 1500:
        censuses_before_cp = sum('reading the scene' in l for l in logs)
        for w, d in equip.items(): w64(d, 0xDEADBEEF00000000 | random.getrandbits(31))   # the old items are gone
        L.execute('RANDO_TRAVEL.on_checkpoint(781823093, true)')
        for w, d in equip.items(): w64(d, int(ids[w], 16))                               # and rebuilt
    if L.eval('RANDO.state.omega["%s"].status' % target) == "applied": break
for l in logs:
    if 'record ' not in l or 'weapon record' in l: print(l[:260])
fails = 0
def check(name, ok):
    global fails
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails += 1
check("layout trusted", any("layout TRUSTED" in l for l in logs))
if MODE == "ngplus_xp0":
    check("XP 0: the Omega waits", L.eval('RANDO.state.omega["%s"].status' % target) == "pending")
    check("XP 0: nothing written", writes == [])
    check("XP 0: the send is not called off", L.eval('RANDO_REAL.owned["weapon:%s"]' % target) is None)
    print("frames", f, "fails", fails); sys.exit(fails)
if MODE == "ngplus":
    check("the carried-over weapon's send was called off", L.eval('RANDO_REAL.owned["weapon:%s"]' % target) is not None)
check("the Omega was applied", L.eval('RANDO.state.omega["%s"].status' % target) == "applied")
check("written exactly once, at the Equip record's id +0x88",
      [(a, d) for a, d in writes] == [(equip[target] + 0x88, b'\x01')])
check("nothing written into the Override copies", all(not (override[w] <= a < override[w] + 0x100) for a, _ in writes for w in override))
if MODE == "checkpoint":
    check("the checkpoint load dropped the census and a new one ran",
          censuses_before_cp is not None and sum('reading the scene' in l for l in logs) == censuses_before_cp + 1)
    check("the travel module's own checkpoint handler still ran", L.eval('RANDO_TRAVEL.cps') == 1)
print("frames", f, "fails", fails)
sys.exit(fails)
