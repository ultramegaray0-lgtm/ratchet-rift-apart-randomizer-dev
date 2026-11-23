# v0.71-DEV9: a shop bonus whose slot sells a weapon you already own is given directly (round 61: Enforcer = Box Breaker
# could never be bought because the save already had the Enforcer).
# Run from the kit folder: python tests/dev9/test_owned_dev9.py .
import sys, os, struct
KIT = sys.argv[1]
sys.argv = [sys.argv[0], os.path.join(KIT, 'scripts')]
sys.path.insert(0, os.path.join(KIT, 'docs'))
import shop_harness as H
from lupa import LuaRuntime

SETTINGS = '{ shop = "shuffle", shop_bonus = true, omega_weapons = true, include_arsenal_restored = true }'
fails = 0
def check(c, m):
    global fails
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails += 1

def pairs(lua):
    return lua.eval('''(function() local t = {}
      for slot, lid in pairs(RANDO_SEED.shop.bonus) do t[#t + 1] = { slot = slot, lid = lid, sells = RANDO_SHOP.shown[slot] or slot } end
      table.sort(t, function(a, b) return a.slot < b.slot end)
      return t end)()''')

def collected(lua): return list(lua.eval('COLLECTED').values())

frame = [1]
def run(n):
    H.run_frames(n, start=frame[0]); frame[0] += n

for seed in ['harness-1', 'harness-2', 'dev8-a', 'dev9-owned']:
    # --- the save already holds the weapon of one bonus slot (09_rando_real.lua says "owned") ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    run(4000)
    P = list(pairs(lua).values())
    check(len(P) >= 1, f'{seed}: the seed has shop bonuses ({len(P)})')
    check(not collected(lua), f'{seed}: nothing paid before anything is owned')
    first = P[0]
    H.lua.execute(f'RANDO.state.real["{first.sells}"] = {{ status = "owned" }}')
    run(200)
    check(not collected(lua), f'{seed}: not paid at the first look (it must still be yours {300} frames later)')
    run(700)
    c = collected(lua)
    check(c == [first.lid], f'{seed}: the bonus of the slot selling the owned {first.sells} is paid, only it ({c})')
    check(any('you already have' in l for l in H.logs('SAY')), f'{seed}: the message says you already have it')
    run(3000)
    check(collected(lua) == [first.lid], f'{seed}: paid once ({collected(lua)})')

    # --- "failed" (only probably owned) never counts; a weapon owned for a moment only does not pay ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    run(4000)
    P = list(pairs(lua).values())
    H.lua.execute(f'RANDO.state.real["{P[0].sells}"] = {{ status = "failed" }}')
    run(1500)
    check(not collected(lua), f'{seed}: status "failed" pays nothing')
    H.lua.execute(f'RANDO.state.real["{P[0].sells}"] = {{ status = "confirmed" }}')
    run(150)
    H.lua.execute(f'RANDO.state.real["{P[0].sells}"] = nil')
    run(1500)
    check(not collected(lua), f'{seed}: owned at one look only: nothing paid')

    # --- the weapon records (17_rando_omega.lua: RANDO_OMEGA.held) ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    run(4000)
    P = list(pairs(lua).values())
    w = P[-1].sells.replace('weapon:', '')
    H.lua.execute('RANDO_OMEGA = { held = { ["%s"] = true } }' % w)
    run(1000)
    check(collected(lua) == [P[-1].lid], f'{seed}: held in the weapon records ({w}) pays its slot bonus ({collected(lua)})')

    # --- a purchase pays first; owning it afterwards pays nothing more ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    run(4000)
    P = list(pairs(lua).values())
    k = P[0].sells
    cfgnum = lua.eval(f'RANDO_SHOP.id_number(RANDO_DATA.items["{k}"].id)')
    H.lua.execute(f'HANDLERS.PurchaseWeaponEvent({{ fields = {{ WeaponName = "WEAPON_X", WeaponConfig = {cfgnum} }} }})')
    H.lua.execute(f'RANDO.state.real["{k}"] = {{ status = "owned" }}')
    run(2000)
    check(collected(lua) == [P[0].lid], f'{seed}: bought -> paid once by the purchase ({collected(lua)})')
    check(not H.logs('OWNED.*pays the bonus'), f'{seed}: the owned check does not pay it again')

    # --- shop_pay_owned = false: DEV8 behaviour ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    H.lua.execute('RANDO.config.shop_pay_owned = false')
    run(4000)
    for p in pairs(lua).values(): H.lua.execute(f'RANDO.state.real["{p.sells}"] = {{ status = "owned" }}')
    run(2000)
    check(not collected(lua), f'{seed}: shop_pay_owned = false pays nothing')

    # --- every weapon owned (round 61: a save with all of them): every bonus paid once ---
    frame[0] = 1
    lua = H.build(SETTINGS, seed_text=seed)
    run(4000)
    P = list(pairs(lua).values())
    for p in P: H.lua.execute(f'RANDO.state.real["{p.sells}"] = {{ status = "owned" }}')
    run(2000)
    c = collected(lua)
    check(sorted(c) == sorted(p.lid for p in P) and len(c) == len(set(c)), f'{seed}: all {len(P)} bonuses paid once each ({len(c)})')

# --- before the vendor was changed in this session nothing is paid (the slot's weapon is not known yet) ---
frame[0] = 1
lua = H.build(SETTINGS, seed_text='harness-1')
H.lua.execute('RANDO_REAL.native_v5 = function() return false end')   # the vendor is never reached
for k in lua.eval('(function() local t = {} for _, w in pairs(RANDO_SEED.shop.slots) do t[#t+1] = w end return t end)()').values():
    H.lua.execute(f'RANDO.state.real["{k}"] = {{ status = "owned" }}')
H.run_frames(3000, start=1)
check(not collected(lua), 'vendor not changed yet: nothing paid')

# --- 17_rando_omega.lua O.held_pass on fake weapon records ---
MEM, LOG = {}, []
def put(a, bs):
    for i, b in enumerate(bs): MEM[a + i] = b
def py_read(addr, n):
    a = int(str(addr), 16); out = []
    for i in range(int(n)):
        if a + i not in MEM: break
        out.append('%02X' % MEM[a + i])
    return ' '.join(out) if out else None
L = LuaRuntime(unpack_returned_tuples=True)
g = L.globals(); g.py_read = py_read
g.py_log = lambda *a: LOG.append('\t'.join(str(x) for x in a))
L.execute('rivet = { log = function(...) py_log(...) end, read = function(a, n) return py_read(a, n) end, write = function() return false end }')
for f in ('01_rando_data.lua', '02_rando_generator.lua'):
    L.execute(open(os.path.join(KIT, 'scripts', f), encoding='utf-8').read())
L.execute('RANDO = { config = {}, state = {}, mark_changed = function() end, say = function() end }')
L.execute(open(os.path.join(KIT, 'scripts', '17_rando_omega.lua'), encoding='utf-8').read())
ids = L.eval('(function() local t = {} for w, id in pairs(RANDO_OMEGA.ID_OF) do t[w] = id end return t end)()')
L.execute('RANDO_OMEGA.inv = { route = "type data", hero_owned = true, records = {} }')
R = [('enforcer', 1001, 15807, 18.0, 1), ('cold_snap', 1004, 0, 4.0, 1), ('negatron_collider', 5015, 0, 0.0, 1),
     ('ricochet', 5003, 0, 0.0, 0), ('bouncer', 5020, 238680, 8.0, 1)]
for i, (w, slot, xp, ammo, count) in enumerate(R):
    a = 0x30000000 + i * 0x200
    put(a, [0] * 0x100)
    put(a, list(bytes.fromhex(ids[w]))[::-1])
    put(a + 8, list(struct.pack('<I', count))); put(a + 12, list(struct.pack('<I', slot)))
    put(a + 16, list(struct.pack('<I', xp))); put(a + 20, list(struct.pack('<f', ammo))); put(a + 24, list(struct.pack('<f', ammo)))
    L.execute('RANDO_OMEGA.inv.records["%s"] = { id_at = %d }' % (w, a))
L.execute('local co = coroutine.create(RANDO_OMEGA.held_pass); while coroutine.status(co) ~= "dead" do local ok, e = coroutine.resume(co); assert(ok, e) end')
held = sorted(L.eval('(function() local t = {} for w in pairs(RANDO_OMEGA.held or {}) do t[#t+1] = w end return t end)()').values())
check(held == ['bouncer', 'cold_snap', 'enforcer'], f'held_pass: held = enforcer, cold_snap (slot < 5000), bouncer (XP); not the empty slots ({held})')
L.execute('RANDO_OMEGA.on_loading()')
check(L.eval('RANDO_OMEGA.held') is None, 'a load drops what was held (read again after it)')
L.execute('RANDO_OMEGA.inv = { route = "type data", hero_owned = false, records = {} }; RANDO_OMEGA.held_pass()')
check(L.eval('RANDO_OMEGA.held') is None, 'records not of the hero: nothing taken as held')

print('FAILURES', fails); sys.exit(1 if fails else 0)
