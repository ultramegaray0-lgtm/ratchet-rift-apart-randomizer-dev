# v0.71-DEV8 enemies: enemy_compat = "max" - mixed movement, no evidence filter, pool sharks still flyer-only, watch logs only
import sys, os
from lupa import LuaRuntime
KIT = sys.argv[1]
fails = 0
def check(c, m):
    global fails
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails += 1
def make(mode, mix):
    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals(); LOG = []
    g.py_log = lambda *a: LOG.append('\t'.join(str(x) for x in a))
    lua.execute('rivet = setmetatable({ log = function(...) py_log(...) end }, { __index = function() return function() return nil end end })')
    for f in ('01_rando_data.lua', '02_rando_generator.lua'):
        lua.execute(open(os.path.join(KIT, 'scripts', f), encoding='utf-8').read())
    lua.execute('RANDO = { config = { enemy_compat = "%s", enemy_mix_movement = %s }, state = { enemy_combat = {} }, mark_changed = function() end, say = function() end, subscribe = function() end }' % (mode, mix))
    lua.execute(open(os.path.join(KIT, 'scripts', '16_rando_spawners.lua'), encoding='utf-8').read())
    return lua, LOG
for mode, mix in (('max', 'true'), ('all', 'false')):
    lua, LOG = make(mode, mix)
    V = 'RANDO_SPAWNERS.V'
    lua.execute('''
local V = RANDO_SPAWNERS.V
V.lvl = { tpl = {
  [1] = { name = "enm_pirate_robot_shooter", family = "ground", handle = 1, uid = "A1" },
  [2] = { name = "enm_pirate_bladeball", family = "swarmer", handle = 2, uid = "A2" },
  [3] = { name = "enm_thugs4less_shooterjetpack", family = "flyer", handle = 3, uid = "A3" },
  [4] = { name = "enm_indigenous_poolshark", family = "unclear", class = "GameBotPoolShark", handle = 4, uid = "A4" },
}, arms = {}, combat = {} }
for _, T in pairs(V.lvl.tpl) do T.usable = true end
''')
    # a Zurkon pirate bladeball factory: in "all" the only walker replacement (robot shooter) is banned -> "rejected"
    r = lua.eval('''(function()
      local V = RANDO_SPAWNERS.V
      local r = { kind = "factory", key = "F1", orig = { single = true, actors = 2, uid = "A2" } }
      local rep, why = V.pick(r, V.group_of(V.lvl.tpl[2]), { "enm_pirate_bladeball" }, 0, true)
      return { rep = rep and rep.name or nil, why = why }
    end)()''')
    if mode == 'max':
        check(r['rep'] is not None, f'max: a bladeball spawner gets a replacement ({r["rep"]})')
    else:
        check(r['rep'] is None and 'rejected' in str(r['why']), f'all (DEV7): bladeball spawner rejected ({r["why"]})')
    # a flyer spawner: in max it may take a walker
    r = lua.eval('''(function()
      local V = RANDO_SPAWNERS.V
      local r = { kind = "factory", key = "F2", orig = { single = true, actors = 3, uid = "A3" } }
      local pool = V.pool("flyer", { "enm_thugs4less_shooterjetpack" }, true)
      local n = 0; for _ in ipairs(pool) do n = n + 1 end
      return n end)()''')
    check((r >= 2) if mode == 'max' else (r == 0), f'{mode}: flyer pool without the jetpack has {r} kinds')
    # a pool shark is flyer-only even in max (strict)
    r = lua.eval('''(function()
      local V = RANDO_SPAWNERS.V
      local pool = V.pool("flyer", { "enm_indigenous_poolshark" }, true, true)
      local names = {}; for _, T in ipairs(pool) do names[#names + 1] = T.family end
      return table.concat(names, ",") end)()''')
    check(all(x == 'flyer' for x in r.split(',') if x), f'{mode}: pool shark strict pool is flyers only ({r})')
    # the combat watch: max logs only
    lua.execute('''local V = RANDO_SPAWNERS.V
      V.session = V.session or {}
      local A = { pairs = { "factory|a/ground>b/flyer" }, restored = false }
      V.lvl.arms = { A }
      V.put_back = function(x) x.restored = true end
      V.combat_reject({ "factory|a/ground>b/flyer" }, "alive 45 s", "x")
      PUT = A.restored''')
    put = lua.eval('PUT')
    check((not put) if mode == 'max' else put, f'{mode}: combat watch {"logs only" if mode == "max" else "puts back"}')
print('FAILURES', fails); sys.exit(1 if fails else 0)
