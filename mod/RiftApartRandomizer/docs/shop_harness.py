import lupa, sys, re, struct
from lupa import LuaRuntime

import os
SCRIPTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')

lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False)
g = lua.globals()
LOG = []
MEM = {}          # address -> byte
def put(addr, data):
    for i, b in enumerate(data): MEM[addr + i] = b
def get(addr, n):
    out = []
    for i in range(n):
        if (addr + i) not in MEM: break
        out.append(MEM[addr + i])
    return out

def hexs(bs): return ' '.join('%02X' % b for b in bs)
def py_log(*a): LOG.append('\t'.join(str(x) for x in a))
def py_read(addr, n):
    n = int(n)
    if n > 512: raise Exception('read limit')
    a = int(str(addr), 16)
    bs = get(a, n)
    if not bs: return None
    return hexs(bs)
WRITES = []
def py_write(addr, text):
    a = int(str(addr), 16)
    bs = [int(x, 16) for x in str(text).split()]
    put(a, bs); WRITES.append((a, bs))
    return True
g.py_log, g.py_read, g.py_write = py_log, py_read, py_write

lua.execute('''
rivet = {}
rivet.log = function(...) py_log(...) end
rivet.read = function(a, n) return py_read(a, n) end
rivet.write = function(a, t) return py_write(a, t) end
rivet.notify = function(t) py_log("NOTIFY", t) end
''')

def load(name):
    src = open(f'{SCRIPTS}/{name}', encoding='utf-8').read()
    return lua.execute(src)

def build(settings_lua, show_items='notify', seed_text='harness-1', ar=True, prices=True):
    """fresh Lua state with a fake vendor in memory; returns helpers"""
    global lua, g
    LOG.clear(); MEM.clear(); WRITES.clear()
    lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False)
    g = lua.globals()
    g.py_log, g.py_read, g.py_write = py_log, py_read, py_write
    lua.execute('''
rivet = {}
rivet.log = function(...) py_log(...) end
rivet.read = function(a, n) return py_read(a, n) end
rivet.write = function(a, t) return py_write(a, t) end
rivet.notify = function(t) py_log("NOTIFY", t) end
''')
    load('01_rando_data.lua'); load('02_rando_generator.lua'); load('03_rando_campaign.lua')
    lua.execute(f'''
local user = {settings_lua}
local seed, err = RANDO_GEN.generate("{seed_text}", user, nil, nil)
assert(seed, tostring(err))
RANDO_SEED = seed
''')
    # fake vendor
    ARR, CFG = 0x275B9DFAEA0, 0x27580000000
    order = ["volcanic_eruptor","thumper","sheepinator","schrodinger","?1","predator_launcher","magnamissile","mr_zurkon","?2","combuster",
             "fusion_grenade","burst_pistol","shatterbomb","enforcer","mr_fungi","negatron_collider","topiary_sprinkler","ricochet","lightning_rod",
             "drillhound","void_repulser","glove_of_doom","buzz_blades","cold_snap","bombardier","warmonger","blackhole_storm","headhunter","ryno_8",
             "pixelizer","bouncer","?3","?4"]
    ids = lua.eval('(function() local t = {} for k, it in pairs(RANDO_DATA.items) do if it.category == "weapon" then t[k] = {id = it.id, price = it.price or 0} end end return t end)()')
    info = {k: (v['id'], v['price']) for k, v in ids.items()}
    unk = {"?1": "A6D296288AEB5801", "?2": "A6D296288AEB5802", "?3": "A6D296288AEB5803", "?4": "A6D296288AEB5804"}
    STRIDE = 0xF8
    put(ARR, [0] * (33 * STRIDE))
    for i, name in enumerate(order):
        base = ARR + i * STRIDE
        put(base, list(struct.pack('<Q', 0x7FF7ACD7ED98)))
        if name.startswith('?'):
            idhex, price = unk[name], 777
        else:
            idhex, price = info['weapon:' + name]
        put(base + 0x14, list(bytes.fromhex(idhex))[::-1])
        put(base + 0x20, list(struct.pack('<I', int(price))))
        put(base + 0x30, list(struct.pack('<I', (i * 7) % 5)))      # a field that varies (MissionShow stand-in)
        put(base + 0x34, list(struct.pack('<I', 0xFFFFFFFF if i % 3 else 2)))
    put(CFG, [0] * 0x200)
    put(CFG + 0x48, list(struct.pack('<Q', ARR)) + list(struct.pack('<ii', 33, 33)))
    g.CFGHEX = '%016X' % CFG
    lua.execute(f'''
VENDOR_ID = "AE5CE1E22662E244"
local marked = 31.0
rivet.configs = function(kind, n) return {{ {{ id = VENDOR_ID, type = "VendorConfig" }} }} end
rivet.config = function(id) return {{ UpgradeCellYOffset = marked, Type = 0 }} end
rivet.config_set = function(id, f, v) marked = v; return true end
COLLECTED = {{}}
HANDLERS = {{}}
SAID = {{}}
RANDO = {{
  config = {{ shop_runtime = true, shop_close_slots = true, shop_show_items = "{show_items}" }},
  state = {{ started = true, collected = {{}}, real = {{}} }},
  loads_seen = 1,
  say = function(t, o) py_log("SAY", t) end,
  mark_changed = function() end,
  grant = function(w) py_log("GRANT", w) end,
  collect = function(lid, why) COLLECTED[#COLLECTED + 1] = lid; RANDO.state.collected[lid] = true; py_log("COLLECT", lid, why) end,
  subscribe = function(name, fn) HANDLERS[name] = fn end,
}}
RANDO_REAL = {{
  lookup_config = function(id, cb) if id == VENDOR_ID then cb(CFGHEX) else cb(nil, "not loaded") end end,
  native_v5 = function() return true end,
  native = {{ addr = 0x1000, version = 7 }},
  qword_from_text = function() return nil end,
  u32_at = function() return 0 end,
  weapon_item = function(name) return nil end,
}}
''')
    load('12_rando_shop.lua')
    return lua

def run_frames(n=4000, start=1):
    lua.execute(f'''
for f = {start}, {start + n - 1} do
  local ok, err = pcall(RANDO_SHOP.tick, f)
  if not ok then py_log("TICK-ERROR", tostring(err)) end
end''')

def logs(pat=None):
    return [l for l in LOG if (pat is None or re.search(pat, l))]
