# v0.71-DEV8 generator: weapon_xp off = every seed exactly as before; on = valid seeds with weapon XP rewards
import sys, os
from lupa import LuaRuntime
NEW, OLD = sys.argv[1], sys.argv[2]
def runtime(kit):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('rivet = { log = function() end }')
    for f in ('01_rando_data.lua', '02_rando_generator.lua', '03_rando_campaign.lua'):
        lua.execute(open(os.path.join(kit, 'scripts', f), encoding='utf-8').read())
    lua.execute('''
function GEN_ONE(seed, opts)
  local s, err = RANDO_GEN.generate(seed, opts, nil, nil)
  if not s then return { err = tostring(err) } end
  local items = {}
  for _, lid in ipairs(RANDO_GEN.sorted_keys(s.locations)) do items[#items + 1] = lid .. "=" .. tostring(s.locations[lid].item) end
  local probs = RANDO_GEN.audit(s)
  return { fp = s.fingerprint, items = table.concat(items, ";"), problems = table.concat(probs or {}, " | "),
           spoiler = RANDO_GEN.spoiler and RANDO_GEN.spoiler(s) or "" }
end''')
    return lua
new, old = runtime(NEW), runtime(OLD)
fails = 0
def check(c, m):
    global fails
    if not c: fails += 1; print('FAIL', m)
DEV = 'distribution = "goldbolts_first", include_arsenal_restored = true, omega_early = true, start_omega = 1, travel_lock = true'
VARIANTS = ['{ %s }' % DEV, '{ }', '{ distribution = "spread" }', '{ %s, shop_bonus = false }' % DEV]
n_same = n_xp = 0; xp_counts = []
for v in VARIANTS:
    for i in range(40):
        seed = f'dev8-gen-{i}'
        a = new.eval('function(s, o) return GEN_ONE(s, o) end')(seed, new.eval(v))
        b = old.eval('function(s, o) return GEN_ONE(s, o) end')(seed, old.eval(v))
        check(a['err'] is None and b['err'] is None, f'{v} {seed}: generated {a["err"]} {b["err"]}')
        if a['err'] or b['err']: continue
        check(a['fp'] == b['fp'] and a['items'] == b['items'], f'{v} {seed}: weapon_xp off = same seed as DEV7')
        check(a['problems'] == '', f'{v} {seed}: audit {a["problems"]}')
        n_same += 1
        vx = v[:-1] + (', ' if v != '{ }' else '') + 'weapon_xp = true }'
        c = new.eval('function(s, o) return GEN_ONE(s, o) end')(seed, new.eval(vx))
        check(c['err'] is None, f'{vx} {seed}: generated with weapon_xp {c["err"]}')
        if c['err']: continue
        check(c['problems'] == '', f'{vx} {seed}: audit {c["problems"]}')
        k = c['items'].count('filler:xp:')
        xp_counts.append(k)
        # the item placements (not currency) are the same as without weapon_xp
        strip = lambda t: ';'.join(x for x in t.split(';') if 'filler:' not in x)
        check(strip(c['items']) == strip(a['items']), f'{vx} {seed}: items stay where they were')
        check(c['fp'] != a['fp'], f'{vx} {seed}: own fingerprint')
        n_xp += 1
print('seeds compared', n_same, 'weapon_xp seeds', n_xp, 'xp rewards per seed min/avg/max',
      min(xp_counts), sum(xp_counts) / len(xp_counts), max(xp_counts))
print('FAILURES', fails)
sys.exit(1 if fails else 0)
