# v0.71-DEV8 armor: 3+ pieces "owned" in one poll are phantoms (round 60), a single new piece pays
import sys, os
from lupa import LuaRuntime
KIT = sys.argv[1]
fails = 0
def check(c, m):
    global fails
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails += 1
lua = LuaRuntime(unpack_returned_tuples=True)
g = lua.globals()
OWN = {}
LOG = []
g.py_own = lambda i: OWN.get(str(i).upper(), False)
g.py_log = lambda *a: LOG.append('\t'.join(str(x) for x in a))
lua.execute('rivet = { log = function(...) py_log(...) end, vanity_owns = function(id) return py_own(id) end }')
for f in ('01_rando_data.lua', '02_rando_generator.lua', '03_rando_campaign.lua'):
    lua.execute(open(os.path.join(KIT, 'scripts', f), encoding='utf-8').read())
lua.execute('''
RANDO_SEED = RANDO_GEN.generate("armor-dev8", {}, nil, nil)
COLLECTED = {}
RANDO = { loading = false, state = { started = true, collected = {}, inventory = {}, armor_found = {}, armor_sources = {} },
          mark_changed = function() end,
          collect = function(lid) COLLECTED[#COLLECTED + 1] = lid; RANDO.state.collected[lid] = true; return true end }
''')
lua.execute(open(os.path.join(KIT, 'scripts', '13_rando_armor.lua'), encoding='utf-8').read())
pieces = list(lua.eval('RANDO_ARMOR.PIECES').values())
idof = {p: lua.eval('RANDO_DATA.items[%r].id' % p).upper() for p in pieces}
frame = [0]
def poll(n=2000):
    lua.execute('for f = %d, %d do RANDO_ARMOR.tick(f) end' % (frame[0] + 1, frame[0] + n)); frame[0] += n
def ncol(): return len(lua.eval('COLLECTED'))
poll()                                                         # baseline: nothing owned
check(any('baseline' in l for l in LOG), 'baseline taken')
OWN[idof[pieces[0]]] = True; poll()
check(ncol() == 1, 'one real pickup pays (%d)' % ncol())
for p in pieces[1:17]: OWN[idof[p]] = True
poll()
check(ncol() == 1, '16 pieces at once are phantoms: nothing paid (%d)' % ncol())
check(any('PHANTOM 16' in l for l in LOG), 'PHANTOM line logged')
for p in pieces[1:17]: OWN[idof[p]] = False
poll()
check(any('phantom piece cleared' in l for l in LOG), 'phantoms clear when they read not owned')
OWN[idof[pieces[5]]] = True; poll()
check(ncol() == 2, 'a later real pickup of a former phantom pays (%d)' % ncol())
lua.execute('RANDO.loading = true'); OWN[idof[pieces[6]]] = True; poll(10)
lua.execute('RANDO.loading = false'); poll(200)
check(ncol() == 2, 'nothing polled in the settle time after a load')
poll(1000)
check(ncol() == 3, 'after it, the new piece pays (%d)' % ncol())
print('FAILURES', fails); sys.exit(1 if fails else 0)
