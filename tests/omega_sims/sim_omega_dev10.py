# DEV10 simulator: fake game memory for 17_rando_omega.lua's type-data route
import sys, struct, random
import lupa.lua54 as l54
KIT = sys.argv[1]
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
MODE = sys.argv[3] if len(sys.argv) > 3 else "live"     # live | nofields | noscene | dumpdiff

mem = {}   # base -> bytearray
def region(base, size): mem[base] = bytearray(size); return base
def find(addr):
    for b, buf in mem.items():
        if b <= addr < b + len(buf): return b, buf
    return None, None
def w8(a, v): b, buf = find(a); buf[a-b] = v
def wb(a, data):
    b, buf = find(a); buf[a-b:a-b+len(data)] = data
def w32(a, v): wb(a, struct.pack('<I', v & 0xffffffff))
def w64(a, v): wb(a, struct.pack('<Q', v))
def w16(a, v): wb(a, struct.pack('<H', v))
FAIL = {"rate": 0.0}
def rd(addr_hex, n):
    if random.random() < FAIL["rate"]: raise Exception("ran past the 8 ms frame budget")
    a = int(addr_hex, 16); b, buf = find(a)
    if b is None or a + n > b + len(buf): return None
    return ' '.join('%02x' % x for x in buf[a-b:a-b+n]) + ' '
writes = []
def wr(addr_hex, text):
    a = int(addr_hex, 16); data = bytes(int(x, 16) for x in text.split())
    writes.append((a, data)); wb(a, data); return len(data)

heap = [0x40000000]
def alloc(size):
    a = heap[0]; heap[0] += (size + 0xF) & ~0xF; heap[0] += 0x10; return region(a, size)
def cstr(s):
    a = alloc(len(s) + 1); wb(a, s.encode() + b'\0'); return a

# DDL type infos
def typeinfo(tid, parent, size, fields):
    t = alloc(0xC0)
    w64(t, cstr("T%X" % tid)); w32(t + 8, tid); w32(t + 0x10, parent); w32(t + 0x14, size); w16(t + 0x18, len(fields))
    if fields:
        names = alloc(8 * len(fields)); types = alloc(len(fields)); offs = alloc(4 * len(fields))
        for i, (nm, ty, off) in enumerate(fields):
            w64(names + 8 * i, cstr(nm)); w8(types + i, ty); w32(offs + 4 * i, off)
        w64(t + 0x50, names); w64(t + 0x58, types); w64(t + 0x78, offs)
    return t
WFIELDS = [("ItemGuid", 3, 40), ("ItemConfigHash", 20, 48), ("ItemCount", 2, 56), ("ItemId", 1, 60), ("XP", 2, 64),
           ("LoadedAmmo", 8, 72), ("Mods", 3, 88), ("SelectedCell", 0, 160), ("Omega", 15, 184)]
if MODE == "nofields": WFIELDS_USE = []
elif MODE == "dumpdiff": WFIELDS_USE = [(n, t, o + 8 if n == "Omega" else o) for n, t, o in WFIELDS]
else: WFIELDS_USE = WFIELDS
TI_W = typeinfo(0xA89E9C3C, 0x4E5CE3CB, 192 if MODE != "dumpdiff" else 200, WFIELDS_USE)
TI_G = typeinfo(0x388B19BC, 0x4E5CE3CB, 64, [("ItemConfigHash", 20, 48)])
TI_X = typeinfo(0x12345678, 0, 32, [])
def compinfo(name, ti):
    c = alloc(0x110); w64(c + 0x60, cstr(name)); w64(c + 0xC8, ti); return c
CI_W, CI_G, CI_X = compinfo("WeaponItem", TI_W), compinfo("GadgetSwingshotItem", TI_G), compinfo("Mover", TI_X)
CI_N = alloc(0x110)   # a class without prius

HERO_ACTOR = alloc(0x100); OTHER_ACTOR = alloc(0x100)
def component(actor, ti_size, handle, prius_size=None, destroyed=False):
    c = alloc(0x48); w64(c, 0x7FF600001000); w64(c + 0x10, actor); w32(c + 0x1C, handle)
    if destroyed: w8(c + 0x25, 2)
    if prius_size:
        h = alloc(0x18); d = alloc(prius_size); w64(c + 8, h); w32(h + 8, 1); w64(h + 0x10, d)
        return c, d
    return c, None

L = l54.LuaRuntime(unpack_returned_tuples=True)
G = L.globals()
hero_inv_mgr = alloc(0x2168); w64(hero_inv_mgr + 0x10, HERO_ACTOR)
logs = []
def log(*a): logs.append(' '.join(str(x) for x in a))
def component_fn(hero, cls):
    if cls in ("GameInventoryManager",): return L.table_from({"address": "%016x" % hero_inv_mgr, "size": 0x2168})
    raise Exception("this actor has no %s component" % cls)
rivet = L.table_from({"log": log, "read": rd, "write": wr, "hero": lambda: 1090771, "component": component_fn,
                      "time": lambda: 100, "components": lambda h: L.table_from({1: "GameInventoryManager"})})
G.rivet = rivet
L.execute('RANDO_FILES = {}')
for f in ("01_rando_data.lua", "02_rando_generator.lua"):
    L.execute(open(f"{KIT}/scripts/{f}", encoding="utf-8").read())
ids = dict(L.eval('function() local t = {} for k, it in pairs(RANDO_DATA.items) do if it.category == "omega" then t[it.weapon:sub(8)] = it.id end end return t end')())
weapons = sorted(ids)[:22]

# scene: lookups
SM = region(0x10000000, 0x2000)
entries = []
recs = {}
for i in range(6000):
    c, _ = component(OTHER_ACTOR, 0, 0x100000 + i)
    entries.append((c, random.choice([CI_X, CI_X, CI_X, CI_N, CI_G])))
for k, w in enumerate(weapons):
    c, d = component(HERO_ACTOR, 0, 0x200000 + k, 200)
    w64(d + 48, int(ids[w], 16)); recs[w] = d
    entries.insert(random.randrange(len(entries)), (c, CI_W))
# a vendor copy of one weapon on another actor, a destroyed hero copy, an unknown id
c, d = component(OTHER_ACTOR, 0, 0x300000, 200); w64(d + 48, int(ids[weapons[0]], 16)); w8(d + 184, 1); entries.append((c, CI_W))
c, d = component(HERO_ACTOR, 0, 0x300001, 200, destroyed=True); w64(d + 48, int(ids[weapons[1]], 16)); entries.append((c, CI_W))
c, d = component(HERO_ACTOR, 0, 0x300002, 200); w64(d + 48, 0x1122334455667788); entries.append((c, CI_W))
LK = alloc(16 * len(entries))
for i, (c, ci) in enumerate(entries): w64(LK + 16 * i, c); w64(LK + 16 * i + 8, ci)
w64(SM + 0x13C8, LK); w32(SM + 0x13EC, len(entries))

L.execute('''
RANDO = { state = { omega = {}, real = {} }, config = { omega_runtime = true }, subs = {} }
function RANDO.subscribe(c, fn) RANDO.subs[c] = fn end
function RANDO.say(t) rivet.log("SAY", t) end
function RANDO.mark_changed() end
function RANDO.item_name(k) return k end
function RANDO.omega_applied(w, why) RANDO.state.omega[w].status = "applied"; rivet.log("APPLIED", w, why) end
RANDO_SEED = {}
RANDO_REAL = { weapon_item = function(n) return nil end }
''')
if MODE != "noscene":
    L.execute('RANDO_SPAWNERS = { V = { scene = function() return { scene = %d } end } }' % SM)
L.execute(open(f"{KIT}/scripts/17_rando_omega.lua", encoding="utf-8").read())
O = G.RANDO_OMEGA
# the reward: Omega of the first weapon, delivered
start_w = weapons[2]
L.execute('RANDO.state.omega["%s"] = { status = "pending" }; RANDO.state.real["weapon:%s"] = { status = "confirmed" }' % (start_w, start_w))
print("request:", O.request(start_w))
FAIL["rate"] = 0.02
kill_once = {"n": 0}
for f in range(4000):
    L.execute('RANDO.frame_t0 = os.clock()')
    if f % 97 == 5:   # a busy frame: most of the budget gone already
        L.execute('RANDO.frame_t0 = os.clock() - 0.0045')
    O.tick(f, True)
    if f in (20, 45) and O.jobs[1] is not None:   # a budget kill of the running job
        L.execute('local j = RANDO_OMEGA.jobs[1]; if j then RANDO_OMEGA.jobs[1].co = coroutine.create(function() error("ran past the 8 ms frame budget") end) end')
        kill_once["n"] += 1
    if O.inv is not None and f > 2000: break
FAIL["rate"] = 0.0
for f in range(4000, 5200): L.execute('RANDO.frame_t0 = os.clock()'); O.tick(f, True)
for l in logs: print(l[:400])
print("writes:", [(hex(a), d.hex()) for a, d in writes])
print("expected omega byte at", hex(recs[start_w] + 184))
print("state:", L.eval('RANDO.state.omega["%s"].status' % start_w), "frames", f)
known = set(L.eval('function() local t={} for id,w in pairs(RANDO_OMEGA.BY_ID) do t[w]=true end return t end')().keys())
print("weapons in sim:", len(weapons), "known to O.BY_ID:", len([w for w in weapons if w in known]), [w for w in weapons if w not in known])
# keep: the game clears the flag; then a level reload; then an Omega purchase of another weapon
logs.clear(); writes.clear()
wb(recs[start_w] + 184, b'\x00')
for f in range(6000, 7400): L.execute('RANDO.frame_t0 = os.clock()'); O.tick(f, True)
print("keep writes:", [(hex(a), d.hex()) for a, d in writes])
L.execute('RANDO.subs["LevelLoadedEvent"]({ fields = {} })')
for f in range(7400, 8000): L.execute('RANDO.frame_t0 = os.clock()'); O.tick(f, True)
buy = weapons[5]
L.execute('RANDO.subs["VendorPurchaseEvent"]({ fields = { WeaponName = "%s" } })' % buy)
wb(recs[buy] + 184, b'\x01')
for f in range(8000, 8100): L.execute('RANDO.frame_t0 = os.clock()'); O.tick(f, True)
for l in logs:
    if 'record ' not in l: print(l[:300])
