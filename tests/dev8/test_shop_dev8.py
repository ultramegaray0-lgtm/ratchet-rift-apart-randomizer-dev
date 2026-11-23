# v0.71-DEV8 shop: a try killed half-way by the frame budget must not shuffle the vendor twice.
import sys, os, re
KIT = sys.argv[1]
sys.argv = [sys.argv[0], os.path.join(KIT, 'scripts')]
sys.path.insert(0, os.path.join(KIT, 'docs'))
import shop_harness as H

SETTINGS = '{ shop = "shuffle", shop_bonus = true, omega_weapons = true, include_arsenal_restored = true }'
fails = 0
KILL_LUA = r"""
KILL_AFTER = %d
local n = 0
local w = rivet.write
local WRAP
WRAP = function(a, t)
  local r = w(a, t)
  n = n + 1
  if KILL_AFTER and n == KILL_AFTER then
    KILL_AFTER = nil
    -- rivet_hook's budget error comes from a hook, on whatever line of the script runs next (outside the pcall)
    debug.sethook(function()
      local f = debug.getinfo(2, "f").func
      if f == WRAP or f == w then return end
      debug.sethook()
      error("scripts\\12_rando_shop.lua:573: ran past the 8 ms frame budget", 0)
    end, "l")
  end
  return r
end
rivet.write = WRAP
"""
def check(cond, msg):
    global fails
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails += 1

def final_table(lua):
    # what every slot sells after the run, by the item id in memory
    return lua.eval('''(function()
      local out = {}
      for k, w in pairs(RANDO_SHOP.shown or {}) do out[k] = w end
      return out end)()''')

for seed in ['harness-1', 'harness-2', 'dev8-a', 'dev8-b', 'dev8-c']:
    # 1) clean run: the reference
    lua = H.build(SETTINGS, seed_text=seed)
    H.run_frames(4000)
    ref_mem = dict(H.MEM)
    ref_lines = H.logs(r'weapon slots, \d+ changed')
    ref_shown = dict(final_table(lua))
    check(len(ref_lines) == 1, f'{seed}: clean run applies once ({len(ref_lines)})')
    # 2) the first try is killed by the budget after K writes, as in round 60
    for K in (2, 5, 9, 15, 20, 24):
        lua = H.build(SETTINGS, seed_text=seed)
        state = {'n': 0, 'armed': True}
        orig = H.py_write
        def killing_write(addr, text, K=K, state=state):
            if state['armed']:
                state['n'] += 1
                if state['n'] > K:
                    state['armed'] = False
                    raise Exception('scripts\\12_rando_shop.lua:573: ran past the 8 ms frame budget')
            return orig(addr, text)
        # the budget error must escape pcall(rivet.write) like rivet_hook's hook error does: raise it from Lua
        H.lua.execute(KILL_LUA % K)
        H.run_frames(4000)
        mem = dict(H.MEM)
        # compare the vendor array (item fields) with the clean run
        diff = [a for a in ref_mem if ref_mem[a] != mem.get(a)]
        applied = H.logs(r'weapon slots, \d+ changed')
        budget = H.logs(r'apply:.*frame budget')
        shown = dict(final_table(H.lua))
        check(len(budget) >= 1, f'{seed} K={K}: the first try was killed ({len(budget)})')
        check(len(applied) == 1, f'{seed} K={K}: applied once after the kill ({len(applied)})')
        check(not diff, f'{seed} K={K}: vendor memory equals the clean run ({len(diff)} bytes differ)')
        check(shown == ref_shown, f'{seed} K={K}: every slot sells the same weapon as the clean run')
        given = H.logs(r'given directly')
        check(not given, f'{seed} K={K}: nothing given directly ({len(given)})')


# 3) REROUTE: a vendor without the Mr. Fungi and Drillhound slots (their ids replaced by unknown ones): the seed's weapons
# of those slots are sold in closed slots, not given away, and a bonus riding on them pays when bought there
import struct
for seed in ['harness-1', 'dev8-a', 'dev8-c']:
    lua = H.build(SETTINGS, seed_text=seed)
    ARR, STRIDE = 0x275B9DFAEA0, 0xF8
    for idx, fake in ((14, 'A6D296288AEB5811'), (19, 'A6D296288AEB5812')):
        H.put(ARR + idx * STRIDE + 0x14, list(bytes.fromhex(fake))[::-1])
    H.run_frames(4000)
    slots = dict(H.lua.eval('RANDO_SEED.shop.slots'))
    lost = [k for k in ('weapon:mr_fungi', 'weapon:drillhound') if k in slots and slots[k] != 'weapon:burst_pistol']
    rr = H.logs('REROUTE')
    given = H.logs('given directly')
    check(len(lost) == 0 or len(rr) == 1, f'{seed}: reroute logged for {lost}')
    check(not given, f'{seed}: nothing given directly with spare closed slots ({len(given)})')
    shown = dict(H.lua.eval('RANDO_SHOP.shown'))
    for k in lost:
        check(shown.get(k) == slots[k], f'{seed}: {k} seed weapon {slots[k]} shown as sold ({shown.get(k)})')
    bonus = dict(H.lua.eval('RANDO_SEED.shop.bonus') or {})
    for k in lost:
        if k in bonus:
            w = slots[k]
            H.lua.execute('RANDO_SHOP.on_purchase(%r, nil)' % H.lua.eval('RANDO_DATA.items[%r].name' % w))
            check(bonus[k] in list(H.lua.eval('COLLECTED').values()), f'{seed}: buying {w} pays the rerouted bonus {bonus[k]}')

print('FAILURES', fails)
sys.exit(1 if fails else 0)
