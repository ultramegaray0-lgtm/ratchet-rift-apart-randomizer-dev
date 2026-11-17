"""Dev 10.27 (kit 10.0.18): the Enemy Randomizer (enemy.lua, the - key) on the variable route - the method round37
proved in the real game (tests/data/round37_rivet.log: a SunsetSpawnerFactory's "Templates" variable written before
it spawned -> 6/6 factories, 20/20 spawns of the replacement).

Every test here runs the PRODUCTION code (16_rando_spawners.lua section SP.V + enemy.lua) - not a copy.
  * UnitTests: rules (names, roles, movement groups, picks).
  * SimulatorTests: the simulator with SYNTHETIC memory laid out as the real plug blocks and SceneManager variables.
    Its "game" spawns what a spawner's variable holds at spawn time: the behaviour round37 proved for factories. For
    node Template and group variables that behaviour is ASSUMED (not seen in the game yet).
  * Round37ReplayTests: the real factory handles, Templates values and enemy names of round37's first A1 run, replayed
    through the production engine in the simulator.
Nothing in this file is in-game verification.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_v1021 import crc_hash  # noqa: E402

SCRIPTS = ROOT / "mod" / "RiftApartRandomizer" / "scripts"
LOG37 = ROOT / "tests" / "data" / "round37_rivet.log"
SCENE, VARS = 0x5000000000, 0x5100000000
GROUP = 0x80C006D9

FIX = r"""
local SCENE, VARS = %(scene)d, %(vars)d
SIM.map(SCENE + 0x7500, 0x100)
SIM.put_u64(SCENE + 0x75A0, VARS); SIM.put_u32(SCENE + 0x75BC, 250)
SIM.map(VARS, 250 * 0x40)
SIM.put_u64(SIM.MB + 0x128, SCENE); SIM.put_u32(SIM.MB + 0x130, 1)
PF = { writes = {}, names = {}, classes = {}, factories = {}, nodes = {}, tdef = {}, fvar = {}, nvar = {}, nlast = {},
       loaded = {}, probe = false, spawned_names = {} }
function PF.var(idx, gen, actors, uid)
  local a = VARS + idx * 0x40
  SIM.put_u64(a, uid or 0); SIM.put_u32(a + 0x10, actors or 0)
  SIM.mem[a + 0x34] = 5; SIM.mem[a + 0x35] = 0; SIM.mem[a + 0x36] = gen; SIM.mem[a + 0x37] = 0
end
function PF.var_actors(idx) return SIM.get_u32(VARS + idx * 0x40 + 0x10) end
function PF.var_uid(idx) return string.format("%%016X", SIM.get_u64(VARS + idx * 0x40)) end
function PF.set_gen(idx, gen) SIM.mem[VARS + idx * 0x40 + 0x36] = gen end
-- a template actor: what it spawns; its uid as the real ones (bit 63 set); loaded = rivet.find_uid finds it
function PF.tpl(h, name, cls, idx)
  PF.tdef[h] = { name = name, cls = cls }
  PF.loaded[string.format("%%016X", 0x8000000000000000 | h)] = h
  if idx then PF.var(idx, 1, h, 0x8000000000000000 | h) end
end
function PF.factory(i, fac, tidx, lidx)
  local a, p = 0x5600000000 + i * 0x100, 0x5700000000 + i * 0x100
  SIM.map(a, 0x80); SIM.map(p, 0x80)
  SIM.put_u64(a + 0x48, 0xF000 + i); SIM.put_u64(a + 0x58, p)
  SIM.put_u64(p + 8, p + 0x28); SIM.mem[p + 0x1A] = 2
  SIM.put_u32(p + 0x28, 3990217346); SIM.mem[p + 0x2C] = tidx; SIM.mem[p + 0x2E] = 1
  SIM.put_u32(p + 0x30, 2501629366); SIM.mem[p + 0x34] = lidx; SIM.mem[p + 0x36] = 1
  PF.factories[#PF.factories + 1] = { component = 900 + i, actor = fac, uid = string.format("%%016x", 0xF000 + i),
                                      class = "SunsetSpawnerFactoryScriptAction", addr = a }
  PF.classes[fac] = { "SunsetSpawnerFactoryScriptAction", "SunsetSpawnerFactory" }
  PF.fvar[fac] = tidx
end
-- a SpawnerScriptAction node: Template (var tidx) and LastSpawn (var lastidx); its Spawner component handle 6000+i
function PF.node(i, actor, tidx, lastidx)
  local a, p = 0x5800000000 + i * 0x100, 0x5900000000 + i * 0x100
  SIM.map(a, 0x80); SIM.map(p, 0x80)
  SIM.put_u64(a + 0x48, 0xE000 + i); SIM.put_u64(a + 0x58, p); SIM.put_u32(a + 0x60, 6000 + i)
  SIM.put_u64(p + 8, p + 0x28); SIM.mem[p + 0x1A] = 2
  SIM.put_u32(p + 0x28, 1835115251); SIM.mem[p + 0x2C] = tidx; SIM.mem[p + 0x2E] = 1
  SIM.put_u32(p + 0x30, 406637480); SIM.mem[p + 0x34] = lastidx; SIM.mem[p + 0x36] = 1
  PF.var(lastidx, 1, 0, 0)
  PF.nodes[#PF.nodes + 1] = { component = 700 + i, actor = actor, uid = string.format("%%016x", 0xE000 + i),
                              class = "SpawnerScriptAction", addr = a }
  PF.nvar[actor] = tidx; PF.nlast[actor] = lastidx
end
local ow, oc, ocs = rivet.write, rivet.component, rivet.components
rivet.write = function(addr, hex) PF.writes[#PF.writes + 1] = addr; return ow(addr, hex) end
rivet.script_nodes = function(filter)
  if PF.nodes_error then error(PF.nodes_error, 0) end
  if filter == "SunsetSpawnerFactoryScriptAction" then return PF.factories end
  if filter == "SpawnerScriptAction" then return PF.nodes end
  return {}
end
rivet.component = function(actor, class)
  for _, n in ipairs(PF.factories) do
    if n.actor == actor and class == "SunsetSpawnerFactoryScriptAction" then return { address = string.format("%%X", n.addr), size = 160, handle = n.component } end
  end
  for _, n in ipairs(PF.nodes) do
    if n.actor == actor and class == "SpawnerScriptAction" then return { address = string.format("%%X", n.addr), size = 160, handle = n.component } end
  end
  return oc(actor, class)
end
rivet.components = function(h)
  if PF.classes[h] then return PF.classes[h] end
  if PF.probe and PF.tdef[h] then return { "SceneObject", PF.tdef[h].cls } end
  return ocs(h)
end
rivet.name = function(h)
  if PF.names[h] then return PF.names[h] end
  if PF.probe and PF.tdef[h] then return PF.tdef[h].name end
  return nil
end
rivet.find_uid = function(uid) return PF.loaded[tostring(uid):upper()] end
-- THE GAME'S SPAWN (simulated): a spawner spawns the template its variable holds NOW (what round37 proved for factories)
function PF.made(h, d)
  PF.names[h] = d.name; PF.classes[h] = { "SceneObject", d.cls }
  PF.spawned_names[#PF.spawned_names + 1] = d.name
  return d.name
end
function PF.spawn_factory(fac, h)
  local d = PF.tdef[PF.var_actors(PF.fvar[fac])]
  local n = PF.made(h, d)
  SIM.emit("SpawnerSpawnEvent", { SpawnFactory = fac, SpawnIndex = 0, SpawnLocation = 4011, SpawnedHandle = h })
  return n
end
function PF.spawn_node(actor, h, member)
  local t = PF.var_actors(PF.nvar[actor])
  local d = ((t & 0x80000000) ~= 0) and PF.tdef[member] or PF.tdef[t]
  local n = PF.made(h, d)
  SIM.put_u32(VARS + PF.nlast[actor] * 0x40 + 0x10, h)
  SIM.emit("SpawnerSpawnEvent", { SpawnFactory = 0, SpawnIndex = 0, SpawnLocation = 4012, SpawnedHandle = h })
  return n
end
"""

# template actors (handle, name, bot class); var index = handle - 9000 for the factory templates
GRUNT = (9001, "characters\\\\enemy\\\\enm_grunt\\\\actors\\\\enm_grunt", "GameBotShooter")
MELEE = (9002, "characters\\\\enemy\\\\enm_melee\\\\actors\\\\enm_melee", "GameBotMeleeSwarmer")
BLADE = (9003, "characters\\\\enemy\\\\enm_blade\\\\actors\\\\enm_bladeball.a", "GameBotMeleeSwarmer")
FLYER = (9004, "characters\\\\enemy\\\\enm_flyer\\\\actors\\\\enm_flyer", "GameBotMeleeFlier")
JET = (9005, "characters\\\\enemy\\\\enm_jet\\\\actors\\\\enm_jet", "GameBotShooterJetPack")
TANK = (9006, "characters\\\\enemy\\\\enm_tank\\\\actors\\\\enm_tank", "GameBotTankBase")
NPC = (9007, "characters\\\\npc\\\\npc_civ_average_bot.actor", "NPCBot")
TURRET = (9008, "characters\\\\enemy\\\\enm_turret\\\\actors\\\\enm_turret", "GameBotShooterTurret")
MUTT = (9101, "characters\\\\enemy\\\\enm_robomutt_ps4\\\\actors\\\\enm_thugs4less_robomutt", "GameBotMeleeSwarmer")
THUG = (9102, "characters\\\\enemy\\\\enm_thug_brawler_rcn\\\\actors\\\\enm_thugs4less_mele", "GameBotMeleeSwarmer")
ALL = (GRUNT, MELEE, BLADE, FLYER, JET, TANK, NPC, TURRET)


def short(name):
    return name.replace("\\\\", "\\").split("\\")[-1].replace(".actor", "").replace(".a", "")


class Sim:
    """one simulated level; factories f(i) = 8001+i; the production engine"""

    def __init__(self, test, factories, nodes=(), dll=7, probe=False, enemy=True, planet="Zurkon", extra=None, settings=None):
        st = {"enemy_randomizer": enemy, "boss_randomizer": False}
        st.update(settings or {})
        self.g = g = Game(settings=st, dll_version=dll)
        test.assertFalse(g.load_errors, g.load_errors)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        L = g.lua.execute
        for h, name, cls in ALL:
            L('PF.tpl(%d, "%s", "%s", %d)' % (h, name, cls, h - 9000))
        for h, name, cls in (MUTT, THUG):
            L('PF.tpl(%d, "%s", "%s")' % (h, name, cls))           # group members only: no variable holds them
        if probe:
            L("PF.probe = true")
        # factories: (actor, template handle) -> Templates var 20+i, Locations var 120+i
        for i, (fac, tpl) in enumerate(factories):
            L("PF.var(%d, 1, %d, 0x%X)" % (20 + i, tpl, 0x8000000000000000 | tpl))
            L("PF.var(%d, 1, %d, 0)" % (120 + i, 4000 + i))
            L("PF.factory(%d, %d, %d, %d)" % (i, fac, 20 + i, 120 + i))
        # nodes: (actor, template handle or GROUP) -> Template var 60+i, LastSpawn var 160+i
        for i, (actor, tpl) in enumerate(nodes):
            uid = 0 if tpl == GROUP else (0x8000000000000000 | tpl)
            L("PF.var(%d, 1, %d, 0x%X)" % (60 + i, tpl, uid))
            L("PF.node(%d, %d, %d, %d)" % (i, actor, 60 + i, 160 + i))
        if extra:
            L(extra)
        g.travel(planet)
        g.step(60)
        self.next_h = 70000

    def ev(self):
        return [l for l in self.g.logs() if "RANDO-ENEMIES" in l]

    def has(self, text):
        return any(text in l for l in self.ev())

    def spawn(self, fac, steps=12):
        self.next_h += 1
        n = self.g.lua.eval("PF.spawn_factory(%d, %d)" % (fac, self.next_h))
        self.g.step(steps)
        return short(n)

    def spawn_node(self, actor, member=None, steps=12):
        self.next_h += 1
        n = self.g.lua.eval("PF.spawn_node(%d, %d, %s)" % (actor, self.next_h, member if member else "nil"))
        self.g.step(steps)
        return short(n)

    def var(self, idx):
        return self.g.lua.eval("PF.var_actors(%d)" % idx)

    def writes(self):
        return len(self.g.lua.eval("PF.writes"))

    def checkpoint(self, steps=60):
        self.g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        self.g.step(steps)

    def status(self):
        return self.g.lua.eval("RANDO_SPAWNERS.V.status()")


def lua_engine():
    """the production module alone, for rule tests"""
    g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False})
    return g, g.lua.eval("RANDO_SPAWNERS.V")


# ---------------------------------------------------------------------------------------------- rules
class UnitTests(unittest.TestCase):
    def test_plug_names_are_the_engines_hashes(self):
        g, V = lua_engine()
        self.assertEqual(V.PLUG_TEMPLATES, crc_hash("Templates"))
        self.assertEqual(V.PLUG_TEMPLATES, 3990217346)                         # round35-37: the factories' variable
        self.assertEqual(V.PLUG_TEMPLATE, crc_hash("Template"))
        self.assertEqual(V.PLUG_LASTSPAWN, 406637480)

    def test_names_cut_at_64_characters_still_match(self):
        g, V = lua_engine()
        self.assertEqual(V.short("characters\\enemy\\enm_pirate_robot_q4b\\actors\\enm_pirate_robot_me"), "enm_pirate_robot_me")
        self.assertEqual(V.short("characters\\enemy\\x\\actors\\enm_pirate_bladeball.a"), "enm_pirate_bladeball")
        self.assertTrue(V.same_name("a\\enm_thugs4less_shoo", "enm_thugs4less_shooter"))   # round35: names cut by rivet.name
        self.assertFalse(V.same_name("enm_pirate_robot_me", "enm_pirate_robot_sh"))
        self.assertFalse(V.same_name("enm_a", "enm_b"))

    def test_roles(self):
        g, _ = lua_engine()
        role = lambda fam, name, hb=False: g.lua.eval('RANDO_SPAWNERS.V.role_of({ family = "%s", name = "%s", hb = %s })'
                                                      % (fam, name, "true" if hb else "false"))
        self.assertEqual(role("ground", "enm_pirate_robot_sh"), "enemy")
        self.assertEqual(role("swarmer", "enm_thugs4less_robomutt"), "enemy")
        self.assertEqual(role("large", "enm_grunthor"), "boss")                   # boss tier: never the Enemy Randomizer's
        self.assertEqual(role("ground", "enm_pirate_robot_sh", True), "boss")     # a health bar makes it boss tier
        self.assertEqual(role("story_boss", "nefarious_finale"), "story_boss")
        self.assertEqual(role("ground", "enm_boss_guard"), "never")               # "boss" in a name: never touched
        self.assertEqual(role("friendly", "npc_civ_average_bot"), "never")            # friendly and an NPC name: never
        self.assertEqual(role("ground", "npc_pirate_robot_bo"), "never")          # an NPC name with a bot class
        self.assertEqual(role("swarmer", "test_npc_zurkon_j"), "never")

    def test_movement_groups(self):
        g, V = lua_engine()
        groups = {k: V.FAMILY_GROUP[k] for k in ("ground", "swarmer", "flyer", "turret")}
        self.assertEqual(groups, {"ground": "walker", "swarmer": "walker", "flyer": "flyer", "turret": "turret"})
        self.assertIsNone(V.FAMILY_GROUP["large"])

    def test_the_enemy_client_uses_the_variable_route(self):
        g, V = lua_engine()
        self.assertEqual(g.lua.eval("RANDO_ENEMY.client.route"), "vars")
        self.assertEqual(g.lua.eval("RANDO_BOSS and RANDO_BOSS.client.route"), None)       # Boss: still the old route
        self.assertTrue(g.lua.eval("RANDO_SPAWNERS.legacy(RANDO_SPAWNERS.clients.boss)"))


# ---------------------------------------------------------------------------------------------- simulator
A1 = [(8001, 9001), (8002, 9002), (8003, 9001), (8004, 9003), (8005, 9001), (8006, 9002)]


class SimulatorTests(unittest.TestCase):
    """SYNTHETIC memory; the production engine."""

    def test_factories_are_listed_and_nothing_unknown_is_changed(self):
        s = Sim(self, A1)
        self.assertTrue(s.has("scan 1 on scarstu: 6 spawner variable(s) (6 new): 6 factory Templates, 0 node Template, 0 node Template group"), s.ev())
        self.assertEqual(s.writes(), 0)                                           # nothing learned yet: nothing written

    def test_after_the_first_spawns_the_fresh_factories_change_and_spawn_the_replacement(self):
        s = Sim(self, A1)
        self.assertEqual(s.spawn(8001), "enm_grunt")                              # wave 1: originals, learned
        self.assertEqual(s.spawn(8002), "enm_melee")
        changed = [l for l in s.ev() if "\tCHANGED factory Templates" in l]
        # 8003 / 8005 (grunt) -> the only other walker known (melee); 8006 (melee) -> grunt; 8004 (bladeball) unknown
        self.assertEqual(len(changed), 3, changed)
        self.assertEqual(s.var(22), 9002)                                         # 8003: grunt -> melee
        self.assertEqual(s.var(24), 9002)
        self.assertEqual(s.var(25), 9001)                                         # 8006: melee -> grunt
        self.assertEqual(s.var(23), 9003)                                         # 8004: unknown kind, unchanged
        self.assertEqual(s.var(20), 9001)                                         # 8001: spent, unchanged
        self.assertEqual(s.spawn(8003), "enm_melee")                              # SIMULATED game: the variable decides
        self.assertTrue(s.has("VERIFY factory Templates 000000000000F002: requested enm_melee, spawned enm_melee: REPLACEMENT SPAWNED"), s.ev()[-3:])
        self.assertTrue(s.g.note_has("Enemy Randomizer: working"), s.g.notes()[-3:])
        self.assertEqual(s.spawn(8003), "enm_melee")                              # the same factory again: still changed
        self.assertEqual(s.spawn(8006), "enm_grunt")

    def test_a_new_kind_learned_mid_fight_widens_the_pool(self):
        s = Sim(self, A1 + [(8007, 9003)])
        s.spawn(8001); s.spawn(8002)
        s.spawn(8004)                                                             # bladeball learned
        self.assertNotEqual(s.var(26), 9003)                                      # 8007 (bladeball) changed now
        self.assertIn(s.var(26), (9001, 9002))

    def test_later_waves_factories_found_by_a_later_scan(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002)
        s.g.lua.execute("PF.var(40, 1, 9001, 0x%X); PF.var(140, 1, 4140, 0); PF.factory(20, 8021, 40, 140)" % (0x8000000000000000 | 9001))
        s.g.step(130)                                                             # the next listing
        self.assertEqual(s.var(40), 9002, s.ev()[-4:])
        self.assertEqual(s.spawn(8021), "enm_melee")

    def test_template_actors_answering_before_a_spawn_change_the_first_wave(self):
        s = Sim(self, A1, probe=True)
        self.assertTrue(s.has("template actors asked before a spawn: 3, answered 3"), s.ev())
        changed = [l for l in s.ev() if "\tCHANGED " in l]
        self.assertEqual(len(changed), 6, changed)                                # every factory, before any spawn
        self.assertNotEqual(s.spawn(8001), "enm_grunt")

    def test_flyers_only_for_flyers_turrets_for_turrets_never_boss_or_npc(self):
        facs = [(8001, 9001), (8002, 9002), (8003, 9004), (8004, 9005), (8005, 9006), (8006, 9007), (8007, 9008),
                (8008, 9004), (8009, 9006), (8010, 9007), (8011, 9001)]
        s = Sim(self, facs, probe=True)
        self.assertEqual(s.var(27), 9005)                                         # flyer -> the other flyer (jet)
        self.assertEqual(s.var(23), 9004)                                         # jet -> flyer
        self.assertEqual(s.var(24), 9006)                                         # tank (boss tier): untouched
        self.assertEqual(s.var(28), 9006)
        self.assertEqual(s.var(25), 9007)                                         # NPC: untouched
        self.assertEqual(s.var(29), 9007)
        self.assertEqual(s.var(26), 9008)                                         # the only turret: nothing to swap with
        for idx in (20, 21, 30):
            self.assertIn(s.var(idx), (9001, 9002))                               # walkers stay walkers
        self.assertTrue(all(s.var(i) not in (9006, 9007) or i in (24, 25, 28, 29) for i in range(20, 31)))

    def test_the_seed_fixes_the_picks(self):
        facs = [(8001, 9001), (8002, 9002), (8003, 9003)] + [(8010 + i, 9001) for i in range(8)]
        a = Sim(self, facs, probe=True)
        b = Sim(self, facs, probe=True)
        picks_a = [a.var(23 + i) for i in range(8)]
        self.assertEqual(picks_a, [b.var(23 + i) for i in range(8)])
        self.assertEqual(set(picks_a), {9002, 9003})                              # varied: not one kind for every factory
        c = Sim(self, facs, probe=True, settings={"seed": "another-seed"})
        self.assertTrue(all(v in (9002, 9003) for v in [c.var(23 + i) for i in range(8)]))

    def test_a_checkpoint_load_puts_back_and_the_save_changes_the_next_try_from_the_start(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002); s.spawn(8004)
        s.checkpoint(steps=2)
        self.assertTrue(s.has("changed spawner(s) put back: checkpoint loaded"), s.ev()[-5:])
        self.assertEqual([s.var(20 + i) for i in range(6)], [9001, 9002, 9001, 9003, 9001, 9002])
        s.g.step(60)                                                              # the next listing, nothing spawned yet
        after = [s.var(20 + i) for i in range(6)]
        orig = [9001, 9002, 9001, 9003, 9001, 9002]
        self.assertTrue(all(a != o for a, o in zip(after, orig)), after)          # every factory, before any spawn
        s.checkpoint()
        self.assertEqual([s.var(20 + i) for i in range(6)], after)                # the same picks on every try
        reg = s.g.lua.eval("RANDO.state.enemy_reg")
        self.assertEqual(sorted(reg.values()), sorted(["enm_grunt|ground|GameBotShooter|enemy", "enm_melee|swarmer|GameBotMeleeSwarmer|enemy",
                                                       "enm_bladeball|swarmer|GameBotMeleeSwarmer|enemy"]))

    def test_a_level_change_puts_back(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)
        s.g.travel("NefCity")
        s.g.step(5)
        self.assertEqual(s.var(22), 9001)
        self.assertTrue(s.has("put back: planet NefCity"), s.ev()[-4:])

    def test_the_key_off_puts_back_at_once_and_on_changes_only_fresh_spawners(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        self.assertEqual(s.var(24), 9002)
        s.g.press("-")
        s.g.step(2)
        self.assertTrue(s.g.note_has("Enemy Randomizer: OFF"))
        self.assertEqual([s.var(20 + i) for i in range(6)], [9001, 9002, 9001, 9003, 9001, 9002])
        self.assertEqual(s.spawn(8005), "enm_grunt")                              # off: the original
        s.g.press("-")
        s.g.step(60)
        self.assertTrue(s.g.note_has("Enemy Randomizer: ON"))
        self.assertEqual(s.var(22), 9001)                                         # 8003 spawned already: never again
        self.assertEqual(s.var(24), 9001)                                         # 8005 spawned while off
        self.assertEqual(s.var(25), 9001)                                         # 8006 fresh: changed again

    def test_ctrl_key_reports(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        s.g.press("-", ctrl=True)
        s.g.step(2)
        self.assertTrue(s.g.note_has("Enemy Randomizer ON: 3 spawner(s) changed here (3 factory, 0 node, 0 group)"), s.g.notes()[-2:])

    def test_a_spawner_that_ignores_the_write_is_put_back_and_the_adapter_stops(self):
        s = Sim(self, A1 + [(8007, 9001), (8008, 9001)])
        s.spawn(8001); s.spawn(8002)
        # SIMULATED: a game that ignores the write - the factory spawns its original anyway
        s.g.lua.execute('local o = PF.spawn_factory; PF.spawn_factory = function(fac, h) local t = PF.var_actors(PF.fvar[fac]); '
                        'PF.var(PF.fvar[fac], 1, 9001, 0x%X); local n = o(fac, h); return n end' % (0x8000000000000000 | 9001))
        s.spawn(8003)
        self.assertTrue(s.has("ORIGINAL SPAWNED"), s.ev()[-3:])
        s.spawn(8005)
        self.assertTrue(s.has("ADAPTER OFF for this session: factory Templates"), s.ev()[-4:])
        self.assertTrue(s.g.note_has("Enemy Randomizer: one kind of spawner cannot be changed"))
        for idx in (25, 26, 27):
            self.assertEqual(s.var(idx), {25: 9002, 26: 9001, 27: 9001}[idx])    # every other change put back

    def test_a_shared_variable_with_a_spent_user_is_never_changed(self):
        s = Sim(self, A1, extra="PF.factory(30, 8031, 22, 150)")                 # 8031 uses 8003's variable 22
        s.spawn(8031)                                                             # grunt, through the shared variable
        s.spawn(8002)
        self.assertEqual(s.var(22), 9001)                                         # 8003 is fresh, its partner is not
        self.assertEqual(s.var(24), 9002)

    def test_a_variable_regenerated_by_the_game_is_left_alone(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)
        s.g.lua.execute("PF.set_gen(22, 7)")                                      # the game made it anew
        s.g.press("-"); s.g.step(2)
        self.assertEqual(s.var(22), 9002)                                         # not ours any more: not written
        self.assertTrue(s.has("skipped (the variable no longer holds what was written)") or s.has("put back"), s.ev()[-4:])

    def test_a_frame_budget_error_in_a_listing_is_retried(self):
        # SIMULATED: rivet_hook's budget error raised inside rivet.script_nodes (where your logs saw it)
        s = Sim(self, A1, extra="""
          local osn = rivet.script_nodes; PF.fails = 0
          rivet.script_nodes = function(f, n) if PF.fails < 2 then PF.fails = PF.fails + 1; error("script ran past the 8 ms frame budget", 0) end return osn(f, n) end""")
        s.spawn(8001, steps=30); s.spawn(8002, steps=30)
        s.g.step(130)
        self.assertGreaterEqual(s.g.lua.eval("RANDO_SPAWNERS.V.budget_hits or 0"), 2)
        self.assertEqual(s.var(22), 9002, s.ev()[-5:])

    def test_a_read_lost_to_the_budget_is_read_again(self):
        # SIMULATED: rivet.read answering nothing (its pcall caught the budget error) on the first listing
        s = Sim(self, A1, extra="""
          local orr = rivet.read; PF.lost = 0
          rivet.read = function(a, n) if PF.lose and a:match("^51") then PF.lost = PF.lost + 1; error("script ran past the 8 ms frame budget", 0) end return orr(a, n) end
          PF.lose = true""")
        s.g.lua.execute("PF.lose = false")
        s.spawn(8001); s.spawn(8002)
        s.g.step(130)
        self.assertGreater(s.g.lua.eval("PF.lost"), 0)
        self.assertEqual(s.var(22), 9002, s.ev()[-5:])
        self.assertFalse(any("RANDO-ERROR" in l for l in s.g.logs()), [l for l in s.g.logs() if "ERROR" in l])

    def test_an_error_is_logged_and_the_next_listing_works(self):
        s = Sim(self, A1, extra='PF.nodes_error = "boom"')
        s.g.step(130)
        self.assertTrue(any("RANDO-ENEMIES\tRANDO-ERROR boom" in l for l in s.g.logs()), s.ev()[-3:])
        s.g.lua.execute("PF.nodes_error = nil")
        s.g.step(130)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)

    def test_helper_v6_says_so_on_screen_and_writes_nothing(self):
        s = Sim(self, A1, dll=6)
        s.g.step(130)
        self.assertTrue(s.g.note_has("Enemy Randomizer cannot work"), s.g.notes())
        self.assertTrue(s.has("BLOCKED: rando_give.dll is v6, v7 is needed"), s.ev())
        self.assertEqual(s.writes(), 0)

    def test_off_by_the_save_nothing_is_read_or_written(self):
        s = Sim(self, A1, enemy=False)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.writes(), 0)
        self.assertFalse(s.has("scan "))

    def test_a_health_bar_makes_a_kind_boss_tier_and_its_changes_go_back(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)
        s.g.fire("HealthBarShowEvent", SenderHandle=70002, IsFriendly=False)     # the melee spawn showed a health bar
        s.g.step(5)
        self.assertTrue(s.has("enm_melee showed a health bar: boss tier"), s.ev()[-3:])
        self.assertEqual(s.var(22), 9001)
        self.assertIn("|hb", s.g.lua.eval("RANDO.state.enemy_reg['%016X']" % (0x8000000000000000 | 9002)))

    def test_a_stuck_encounter_keeps_its_original_enemies(self):
        s = Sim(self, A1)
        s.g.lua.execute("RANDO_SPAWNERS.V.STUCK_SECONDS = 2")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        s.g.step(200)
        self.assertTrue(s.has("kept original for this seed: factory Templates 000000000000F002"), s.ev()[-3:])
        self.assertTrue(s.g.note_has("Enemy Randomizer: an encounter looked stuck"))
        self.assertEqual(s.var(22), 9001)
        s.checkpoint()
        self.assertEqual(s.var(22), 9001)                                         # blocked for the seed

    def test_a_death_keeps_the_watchdog_quiet(self):
        s = Sim(self, A1)
        s.g.lua.execute("RANDO_SPAWNERS.V.STUCK_SECONDS = 2")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        s.g.fire("BotDeathCompleteEvent", SenderHandle=70003)
        s.g.step(200)
        self.assertFalse(s.has("kept original"), s.ev()[-3:])

    def test_five_retries_keep_an_encounter_original(self):
        s = Sim(self, A1)
        for _ in range(5):
            s.spawn(8001); s.spawn(8002); s.spawn(8003)
            s.checkpoint()
        self.assertTrue(s.has("the checkpoint was loaded 5 times while it ran"), s.ev()[-6:])
        self.assertTrue(s.g.note_has("an encounter you retried 5 times has its original enemies now"))
        s.g.step(130)
        self.assertEqual(s.var(22), 9001)

    def test_a_story_boss_area_puts_back(self):
        s = Sim(self, A1)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)
        s.g.lua.execute('RANDO_SPAWNERS.on_checkpoint({ name = "CP_BOSS_ARENA", hash = 5, loaded = false })')
        s.g.step(130)
        self.assertEqual(s.var(22), 9001)

    def test_templates_without_uid_still_change_within_the_level(self):
        # the uid a real Templates variable holds was never logged: a zero uid must work too (written as zero)
        s = Sim(self, A1, extra="for i = 0, 5 do PF.var(20 + i, 1, PF.var_actors(20 + i), 0) end")
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002, s.ev()[-4:])
        self.assertEqual(s.g.lua.eval("PF.var_uid(22)"), "0000000000000000")
        self.assertEqual(s.spawn(8003), "enm_melee")
        self.assertTrue(s.has("REPLACEMENT SPAWNED"))
        self.assertFalse(s.g.lua.eval("next(RANDO.state.enemy_reg or {})"))       # nothing to keep by uid

    def test_spawnproof_stands_down_while_the_enemy_randomizer_is_on(self):
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False}, spawnproof=True, dll_version=7)
        g.travel("Zurkon")
        g.step(30)
        self.assertTrue(g.log_has("standing down: the Enemy Randomizer is ON"), [l for l in g.logs() if "SPAWNPROOF" in l][-3:])
        g.press("-")
        g.step(3)
        self.assertTrue(g.log_has("the Enemy Randomizer is OFF: spawnproof runs again"))

    def test_the_spawner_runtime_switch_stops_it(self):
        s = Sim(self, A1, settings={"spawner_runtime": False})
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.writes(), 0)

    # ---- node Template (one actor) and group adapters: the game's behaviour ASSUMED, not seen yet ----
    def test_a_node_template_is_changed_and_verified(self):
        s = Sim(self, A1, nodes=[(7101, 9001), (7102, 9003)])
        self.assertTrue(s.has("scan 1 on scarstu: 8 spawner variable(s) (8 new): 6 factory Templates, 2 node Template, 0 node Template group"), s.ev())
        self.assertEqual(s.spawn_node(7102), "enm_bladeball")                     # learned through LastSpawn
        s.spawn(8001); s.spawn(8002)                                              # grunt (the node's kind too), melee
        self.assertIn(s.var(60), (9002, 9003), s.ev()[-4:])                       # 7101 fresh: grunt -> another walker
        self.assertEqual(s.var(61), 9003)                                         # 7102 spent
        self.assertNotEqual(s.spawn_node(7101), "enm_grunt")
        self.assertTrue(s.has("VERIFY node Template 000000000000E000: requested") and s.has("REPLACEMENT SPAWNED"), s.ev()[-3:])

    def test_a_group_node_learns_its_members_then_is_changed_on_the_next_try(self):
        s = Sim(self, A1, nodes=[(7201, GROUP)])
        s.spawn(8001); s.spawn(8002); s.spawn(8004)                               # walkers known: grunt, melee, bladeball
        self.assertEqual(s.spawn_node(7201, MUTT[0]), "enm_thugs4less_robomutt")
        self.assertEqual(s.spawn_node(7201, THUG[0]), "enm_thugs4less_mele")
        self.assertTrue(s.has("group node 000000000000E000: member enm_thugs4less_robomutt (swarmer)"), s.ev())
        self.assertEqual(s.var(60), GROUP)                                        # it spawned already: never changed now
        s.checkpoint()                                                            # the next try
        v = s.var(60)
        self.assertIn(v, (9001, 9002, 9003), s.ev()[-4:])                         # one enemy in place of the group
        self.assertEqual(s.g.lua.eval("PF.var_uid(60)"), "%016X" % (0x8000000000000000 | v))
        first = s.spawn_node(7201, MUTT[0])
        self.assertIn(first, ("enm_grunt", "enm_melee", "enm_bladeball"))
        self.assertTrue(s.has("REPLACEMENT SPAWNED"), s.ev()[-3:])
        names = {first} | {s.spawn_node(7201, THUG[0]) for _ in range(5)}
        self.assertGreater(len(names), 1)                                         # re-chosen after each spawn: mixed
        s.checkpoint(steps=1)
        self.assertEqual(s.var(60), GROUP)                                        # the group value put back
        self.assertEqual(s.g.lua.eval("PF.var_uid(60)"), "0000000000000000")

    def test_a_group_with_a_non_bot_is_never_changed(self):
        s = Sim(self, A1, nodes=[(7201, GROUP)], extra='PF.tpl(9201, "vehicle\\\\veh_nnc_amb_ship_01", "Nothing")')
        s.spawn(8001); s.spawn(8002)
        s.spawn_node(7201, 9201)
        s.spawn_node(7201, MUTT[0])
        s.checkpoint()
        s.g.step(130)
        self.assertEqual(s.var(60), GROUP)

    def test_a_group_adapter_the_game_ignores_turns_off(self):
        s = Sim(self, A1, nodes=[(7201, GROUP), (7202, GROUP), (7203, GROUP)])
        s.spawn(8001); s.spawn(8002)
        for a in (7201, 7202, 7203):
            s.spawn_node(a, MUTT[0])
        s.checkpoint()
        # SIMULATED: a game where a group node keeps spawning its members whatever the variable says
        s.g.lua.execute("PF.spawn_node = (function(o) return function(actor, h, m) local i = PF.nvar[actor]; local v, u = PF.var_actors(i), PF.var_uid(i); "
                        "PF.var(i, 1, 0x80C006D9, 0); local n = o(actor, h, m); PF.var(i, 1, v, tonumber(u, 16)); return n end end)(PF.spawn_node)")
        s.spawn_node(7201, MUTT[0]); s.spawn_node(7202, MUTT[0])
        self.assertTrue(s.has("ADAPTER OFF for this session: node Template group"), s.ev()[-5:])
        self.assertEqual(s.var(62), GROUP)                                        # 7203's change put back too
        self.assertEqual(s.var(20), 9002)                                         # factories still changed


# ---------------------------------------------------------------------------------------------- real data
def round37_first_run():
    """round37's first A1 run, from the real log: {factory: original Templates value}, {value: (name, class)}, spawn order"""
    orig, names, order = {}, {}, []
    for line in LOG37.read_text(encoding="utf-8").splitlines():
        if "RANDO-SPAWNPROOF\tput back" in line:
            break
        m = re.search(r"ARMED .* node factory (\d+) .*?: .*\(handle (\d+), [^)]*\) -> ", line)
        if m:
            orig[int(m.group(1))] = int(m.group(2))
        m = re.search(r"spawn \d+ \(SpawnFactory (\d+), location \d+\): .*factory Templates = (\d+); spawned (\S+) \(handle \d+, \w+/(\w+)\)", line)
        if m:
            f, tv, nm, cls = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
            if "[ARMED" not in line:
                orig.setdefault(f, tv)
                names.setdefault(tv, (nm, cls))
            if 1097930 <= f <= 1097960:
                order.append(f)
    arena = {f: v for f, v in orig.items() if 1097930 <= f <= 1097960}
    pub = {f: v for f, v in orig.items() if f < 1097930 and v in names}
    return arena, pub, names, order


class Round37ReplayTests(unittest.TestCase):
    """the REAL factories / Templates values / names of round37's first A1 run; the SIMULATED game spawns what each
    factory's variable holds (the behaviour that run proved). The production engine decides everything else."""

    def build(self):
        arena, pub, names, order = round37_first_run()
        self.assertEqual(len(arena), 9)
        self.assertEqual(arena[1097939], 1097437)                                # the experiment's originals
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False}, dll_version=7)
        g.lua.execute(FIX % {"scene": SCENE, "vars": VARS})
        L = g.lua.execute
        facs = sorted(arena.items()) + sorted(pub.items())
        for i, (f, tv) in enumerate(facs):
            nm, cls = names[tv]
            L('PF.tdef[%d] = { name = "%s", cls = "%s" }' % (tv, nm.replace("\\", "\\\\"), cls))
            L("PF.var(%d, 1, %d, 0x%X)" % (20 + i, tv, 0x8000000000000000 | tv))
            L("PF.var(%d, 1, %d, 0)" % (120 + i, 4000 + i))
            L("PF.factory(%d, %d, %d, %d)" % (i, f, 20 + i, 120 + i))
        g.travel("Zurkon")
        g.step(60)
        return g, arena, names, order

    def test_the_engine_changes_the_arena_like_the_experiment_and_more(self):
        g, arena, names, order = self.build()
        spawned = {}
        h = 90000
        for f in order:
            h += 1
            spawned.setdefault(f, []).append(short(g.lua.eval("PF.spawn_factory(%d, %d)" % (f, h))))
            g.step(12)
        ev = [l for l in g.logs() if "RANDO-ENEMIES" in l]
        changed = {int(m.group(1)) for l in ev for m in [re.search(r"CHANGED factory Templates \S+ \(actor (\d+),", l)] if m} & set(arena)
        # round37's experiment changed 1097939 / 40 / 44 (robot_sh, fresh after the first spawns): so does the engine
        self.assertTrue({1097939, 1097940, 1097944} <= changed, (changed, ev[-6:]))
        for f in changed:
            orig_name = short(names[arena[f]][0])
            self.assertNotIn(orig_name, spawned.get(f, []), (f, spawned.get(f)))  # never the original once changed
        self.assertTrue(all("REPLACEMENT SPAWNED" in l for l in ev if "VERIFY" in l), [l for l in ev if "VERIFY" in l])
        self.assertGreaterEqual(len([l for l in ev if "VERIFY" in l]), 3)
        kinds = {n for f in changed for n in spawned.get(f, [])}
        self.assertTrue(kinds <= {"enm_pirate_robot_sh", "enm_pirate_robot_me", "enm_pirate_bladeball"}, kinds)

    def test_npc_factories_of_the_pub_are_never_touched(self):
        g, arena, names, order = self.build()
        for i, f in enumerate(order):
            g.lua.eval("PF.spawn_factory(%d, %d)" % (f, 91000 + i))
            g.step(12)
        ev = [l for l in g.logs() if "RANDO-ENEMIES" in l and "CHANGED" in l]
        self.assertFalse([l for l in ev if "npc_" in l or "scanner" in l], ev)

    def test_the_write_is_the_format_round37_proved(self):
        # round37: uid +0x00 and handle +0x10 of the variable; a value without uid keeps none (spawnproof v6, P.arm)
        text = (SCRIPTS / "16_rando_spawners.lua").read_text(encoding="utf-8")
        self.assertIn('local ok1 = pcall(rivet.write, string.format("%X", now.addr), le_hex(uid))', text)
        self.assertIn('local ok2 = pcall(rivet.write, string.format("%X", now.addr + 0x10), le32(actors))', text)
        self.assertIn("V.SCENE_VARS = 0x75A0", text)
        self.assertIn("V.MB_SCENE = 0x128", text)
        self.assertIn('elseif now.uid == V.ZERO_UID then new_uid = V.ZERO_UID', text)

    def test_the_benchmark_still_reads_6_of_6_and_20_of_20(self):
        t = LOG37.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"VERIFY node factory \d+ .*REPLACEMENT SPAWNED", t)), 6)
        self.assertEqual(len(re.findall(r"\[ARMED factory variable, spawn \d+ since\]", t)), 20)
        self.assertNotIn("ORIGINAL SPAWNED", t)


if __name__ == "__main__":
    unittest.main()
