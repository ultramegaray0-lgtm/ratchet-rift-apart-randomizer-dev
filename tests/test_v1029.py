"""Dev 10.29: the Enemy Randomizer overhaul after round39 (tests/data/round39_rivet.log, dev 10.28 scripts; NefCity,
Sargasso, Zurkon arena A1 / A3 / pub, NefCity, Cordelion; the player: "enemies were the same, didn't notice new ones").

  * Round39LogTests: what the real game showed (parsed, nothing simulated) - the evidence behind every change here.
  * SimulatorTests: the PRODUCTION engine (16_rando_spawners.lua SP.V, enemy.lua, boss.lua) on synthetic memory laid
    out like the real script variables (the test_v1027 harness, plus nodes with a Location variable as round39's
    spawnprobe showed them). The simulated game spawns what a variable holds at spawn time: PROVEN for factories
    (round37-39), ASSUMED for node Template and group variables.
Nothing in SimulatorTests is in-game verification.
"""
import os
import pathlib
import re
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v1027 import Sim, A1, GROUP, MUTT, THUG, short, lua_engine  # noqa: E402

LOG39 = ROOT / "tests" / "data" / "round39_rivet.log"

# nodes with a Location variable (2761897147) holding their spawn point, as in round39; no LastSpawn plug, so a spawn
# can only be tied through the spawn-point index. PF.node3(i, actor, tidx, locidx, loc_handle)
FIX2 = r"""
-- more script variables than test_v1027's 250 (a busy level: 150 nodes, each a Template and a Location)
SIM.map(0x5100000000 + 250 * 0x40, 450 * 0x40); SIM.put_u32(0x5000000000 + 0x75BC, 700)
function PF.node3(i, actor, tidx, locidx, loc)
  local a, p = 0x5A00000000 + i * 0x100, 0x5B00000000 + i * 0x100
  SIM.map(a, 0x80); SIM.map(p, 0x80)
  SIM.put_u64(a + 0x48, 0xD000 + i); SIM.put_u64(a + 0x58, p); SIM.put_u32(a + 0x60, 6500 + i)
  SIM.put_u64(p + 8, p + 0x28); SIM.mem[p + 0x1A] = 2
  SIM.put_u32(p + 0x28, 1835115251); SIM.mem[p + 0x2C] = tidx & 0xFF; SIM.mem[p + 0x2D] = tidx >> 8; SIM.mem[p + 0x2E] = 1
  SIM.put_u32(p + 0x30, 2761897147); SIM.mem[p + 0x34] = locidx & 0xFF; SIM.mem[p + 0x35] = locidx >> 8; SIM.mem[p + 0x36] = 1
  PF.var(locidx, 1, loc, 0x7000 + i)
  PF.nodes[#PF.nodes + 1] = { component = 750 + i, actor = actor, uid = string.format("%016x", 0xD000 + i),
                              class = "SpawnerScriptAction", addr = a }
  PF.nvar[actor] = tidx; PF.nloc = PF.nloc or {}; PF.nloc[actor] = loc
end
function PF.spawn_at(actor, h, member)
  local t = PF.var_actors(PF.nvar[actor])
  local d = ((t & 0x80000000) ~= 0) and PF.tdef[member] or PF.tdef[t]
  local n = PF.made(h, d)
  SIM.emit("SpawnerSpawnEvent", { SpawnFactory = 0, SpawnIndex = 0, SpawnLocation = PF.nloc[actor], SpawnedHandle = h })
  return n
end
PF.reads = 0
local orr = rivet.read
rivet.read = function(a, n) PF.reads = PF.reads + 1; return orr(a, n) end
"""

# templates with the game's names (round31-39), var index = handle - 9000 for those a factory holds
PIR_SH = (9201, "characters\\\\enemy\\\\enm_pirate_robot_q4b\\\\actors\\\\enm_pirate_robot_sh", "GameBotShooter")
PIR_ME = (9202, "characters\\\\enemy\\\\enm_pirate_robot_q4b\\\\actors\\\\enm_pirate_robot_me", "GameBotMeleeSwarmer")
BLADE = (9203, "characters\\\\enemy\\\\enm_pirate_q4b\\\\actors\\\\enm_pirate_bladeball", "GameBotMeleeSwarmer")
THUG_SH = (9204, "characters\\\\enemy\\\\enm_thug_brawler_rcn\\\\actors\\\\enm_thugs4less_shoo", "GameBotShooter")
THUG_JET = (9205, "characters\\\\enemy\\\\enm_thug_brawler_rcn\\\\actors\\\\enm_thugs4less_shoo", "GameBotShooterJetPack")
WASP = (9206, "characters\\\\enemy\\\\enm_wasp_rcf\\\\actors\\\\enm_indigenous_wasp", "GameBotShooterJetPack")
TOAD = (9207, "characters\\\\enemy\\\\enm_horned_toad_ps4\\\\actors\\\\enm_indigenous_horne", "GameBotMeleeSwarmerJumper")
AMO_S = (9208, "enm_amoeboid_small_ps4", "GameBotAmoeboid")
AMO_L = (9209, "enm_amoeboid_large_ps4", "GameBotAmoeboid")
GRUN = (9210, "characters\\\\enemy\\\\enm_spondylosaur_rcf\\\\actors\\\\enm_indigenous_grun", "GameBotGrunthor")
TANK2 = (9211, "characters\\\\enemy\\\\enm_tank\\\\actors\\\\enm_juggernaut", "GameBotTankBase")
SEABOSS = (9212, "characters\\\\enemy\\\\enm_seabase_boss\\\\enm_seabase_boss", "BossBotUnderwaterBaseJuice")
GAME = (PIR_SH, PIR_ME, BLADE, THUG_SH, THUG_JET, WASP, TOAD, AMO_S, AMO_L, GRUN, TANK2, SEABOSS)


def sim(test, factories, nodes3=(), settings=None, extra=""):
    """factories: (actor, template handle) -> Templates var 20+i; nodes3: (actor, template or GROUP, loc handle) ->
    Template var 300+i, Location var 500+i"""
    lines = [FIX2]
    for h, name, cls in GAME:
        lines.append('PF.tpl(%d, "%s", "%s", %d)' % (h, name, cls, h - 9000))
    lines.append('PF.tpl(%d, "%s", "%s")' % MUTT)
    lines.append('PF.tpl(%d, "%s", "%s")' % THUG)
    for i, (actor, tpl, loc) in enumerate(nodes3):
        uid = 0 if tpl == GROUP else (0x8000000000000000 | tpl)
        lines.append("PF.var(%d, 1, %d, 0x%X)" % (300 + i, tpl, uid))
        lines.append("PF.node3(%d, %d, %d, %d, %d)" % (i, actor, 300 + i, 500 + i, loc))
    lines.append(extra)
    return Sim(test, factories, settings=settings, extra="\n".join(lines))


def spawn_at(s, actor, member=None, steps=12):
    s.next_h += 1
    n = s.g.lua.eval("PF.spawn_at(%d, %d, %s)" % (actor, s.next_h, member if member else "nil"))
    s.g.step(steps)
    return short(n)


def ledger(s):
    return s.g.lua.eval("RANDO_SPAWNERS.V.lvl.ledger")


def notes_full(s):
    return [(n.text, (n.opts and n.opts["sub"]) or "") for n in s.g.sim.notes.values()]


# ---------------------------------------------------------------------------------------------- real game
class Round39LogTests(unittest.TestCase):
    """round39 (dev 10.28): parsed, nothing simulated"""

    @classmethod
    def setUpClass(cls):
        cls.L = LOG39.read_text(encoding="utf-8", errors="replace").splitlines()

    def test_anonymized(self):
        self.assertTrue(any("game = <GAME_FOLDER>\\RiftApart.exe" in l for l in self.L))
        self.assertFalse(any("\\Users\\" in l for l in self.L))

    def test_the_only_replacements_were_amoeboid_sizes(self):
        v = [l for l in self.L if "\tVERIFY " in l]
        self.assertEqual(len(v), 3)
        self.assertTrue(all("enm_amoeboid_" in l and l.endswith("REPLACEMENT SPAWNED") for l in v), v)
        # the same creature in another size: why "the enemies were the same"
        self.assertTrue(any("enm_amoeboid_large_ps4 -> enm_amoeboid_small_ps4" in l for l in self.L))

    def test_a1s_changes_came_after_the_fight(self):
        i_changed = max(i for i, l in enumerate(self.L) if "CHANGED factory Templates A73A0DEC6E3AEB0A" in l)
        i_end = next(i for i, l in enumerate(self.L) if "EndReason=0" in l and "MIS_ZURK_ARENA_CHALLENGE_A1" in l)
        self.assertLess(i_end - i_changed, 10)                               # changed just before A1 ended
        self.assertTrue(any("SpawnFactory-0 spawns tied to nothing 513" in l for l in self.L))

    def test_node_spawns_were_never_tied_and_their_kinds_never_known(self):
        self.assertTrue(any("node Template: 116 kind not known yet" in l for l in self.L))
        # ... while spawnprobe shows the node's Location variable holds exactly the spawn's location
        self.assertTrue(any("spawn 2: index 0 location 1103873" in l for l in self.L))
        self.assertTrue(any("node 8cfa5b53dd20ab17" in l and "2761897147:actors={1103873}" in l for l in self.L))

    def test_the_pub_group_wave_mixes_thugs_and_pirates(self):
        names = [re.search(r"of (\S+) \(", l).group(1) for l in self.L if "tied to no spawner variable" in l and "location 11197" in l]
        self.assertIn("enm_thugs4less_robomutt", names)
        self.assertIn("enm_pirate_robot_sh", names)

    def test_deaths_name_their_bot_now(self):
        self.assertTrue(any("deaths seen 66 (of our bots 19)" in l for l in self.L))

    def test_story_boss_and_hazards_were_protected(self):
        self.assertTrue(any("enm_seabase_boss = story_boss/BossBotUnderwaterBaseJuice, role never" in l for l in self.L))
        self.assertTrue(any("enm_indigenous_poolsh = unclear/GameBotPoolShark, role never" in l for l in self.L))


# ---------------------------------------------------------------------------------------------- simulator
ZURK = [(8001, 9201), (8002, 9202), (8003, 9201), (8004, 9204), (8005, 9201), (8006, 9202)]


class SimulatorTests(unittest.TestCase):
    """SYNTHETIC memory; the production engine (dev 10.29)"""

    # 1 original detection / 4 no accidental original / 13 failure reporting
    def test_every_enemy_spawn_is_in_the_ledger_with_its_reason(self):
        s = sim(self, ZURK)
        s.spawn(8001)
        L = ledger(s)
        self.assertEqual(L.eligible, 1)
        self.assertEqual(L.unchanged, 1)
        self.assertTrue(s.has("NOT CHANGED: kind not known yet (learned from its first spawn)"), s.ev()[-3:])
        s.spawn(8002); s.spawn(8004)
        s.spawn(8003)                                                             # changed after the pool was known
        L = ledger(s)
        self.assertEqual((L.replaced, L.original, L.other), (1, 0, 0))
        self.assertTrue(s.has("| SUCCESS"), s.ev()[-4:])
        s.checkpoint()
        self.assertTrue(s.has("ENEMY SPAWNS on this level: 4, replaced 1 (25%)"), [l for l in s.ev() if "ENEMY SPAWNS" in l])

    # 2 correct replacement selection: another species first
    def test_a_pirate_becomes_a_thug_when_the_level_has_one(self):
        s = sim(self, ZURK)
        s.spawn(8001); s.spawn(8002); s.spawn(8004)                               # pirate sh, pirate me, thug sh known
        self.assertEqual(s.var(22), 9204, s.ev()[-4:])                           # 8003 pirate shooter -> thug, not pirate
        self.assertEqual(s.var(24), 9204)
        self.assertEqual(s.var(25), 9204)                                         # 8006 pirate brawler -> thug too
        self.assertEqual(s.spawn(8003), "enm_thugs4less_shoo")

    def test_without_another_species_another_kind_of_the_same_species(self):
        s = sim(self, [(8001, 9201), (8002, 9202), (8003, 9201)])
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9202)

    def test_size_variants_never_replace_each_other(self):
        s = sim(self, [(8001, 9208), (8002, 9209), (8003, 9208), (8004, 9209)])
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9208, s.ev()[-3:])                           # small stays small
        self.assertEqual(s.var(23), 9209)
        s.checkpoint()
        self.assertTrue(s.has("only size variants of it are loaded on this level"), [l for l in s.ev() if "level detail" in l])

    # 3 actual replacement creation / 14 notification accuracy
    def test_the_note_names_original_replacement_and_result(self):
        s = sim(self, ZURK)
        s.spawn(8001); s.spawn(8002); s.spawn(8004); s.spawn(8003)
        s.g.step(5)
        n = [x for x in notes_full(s) if x[0].startswith("[ENEMY RANDOMIZER]")]
        self.assertEqual(n[0][0], "[ENEMY RANDOMIZER] SUCCESS")
        self.assertIn("Original: Pirate Robot Shooter", n[0][1])
        self.assertIn("Replacement: Goons-4-Less Shooter", n[0][1])

    def test_notes_are_queued_and_can_be_switched_off(self):
        facs = [(8001, 9201), (8002, 9202), (8003, 9204)] + [(8010 + i, 9201) for i in range(8)]
        s = sim(self, facs)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        for i in range(8):
            s.spawn(8010 + i, steps=1)
        s.g.step(5)
        shown = [x for x in notes_full(s) if x[0].startswith("[ENEMY RANDOMIZER]")]
        self.assertEqual(len(shown), 1)                                           # one at a time
        s.g.step(181 * 5)
        shown = [x for x in notes_full(s) if x[0].startswith("[ENEMY RANDOMIZER]")]
        self.assertLessEqual(len(shown), 5)                                       # the queue holds 4 (+ the one shown)
        self.assertGreaterEqual(len(shown), 4)
        self.assertTrue(any("more)" in x[1] for x in shown), shown)              # the rest are counted, not lost
        q = sim(self, ZURK, settings={"enemy_notify": False})
        q.spawn(8001); q.spawn(8002); q.spawn(8004); q.spawn(8003)
        q.g.step(200)
        self.assertFalse([x for x in notes_full(q) if x[0].startswith("[ENEMY RANDOMIZER]")])
        self.assertTrue(q.has("| SUCCESS"))                                     # the log keeps it

    def test_a_write_the_game_ignores_is_reported_as_failed(self):
        s = sim(self, ZURK, extra="""
          local osf = PF.spawn_factory
          PF.spawn_factory = function(fac, h)                                     -- this game ignores the variable
            local d = PF.tdef[({[8003] = 9201})[fac] or PF.var_actors(PF.fvar[fac])]
            local n = PF.made(h, d)
            SIM.emit("SpawnerSpawnEvent", { SpawnFactory = fac, SpawnIndex = 0, SpawnLocation = 4011, SpawnedHandle = h })
            return n
          end""")
        s.spawn(8001); s.spawn(8002); s.spawn(8004)
        s.spawn(8003)
        s.g.step(5)
        self.assertTrue(s.has("| ORIGINAL: the game spawned something else than the variable held"), s.ev()[-5:])
        self.assertTrue(any(x[0].startswith("[ENEMY RANDOMIZER] FAILED") for x in notes_full(s)))
        self.assertEqual(ledger(s).original, 1)

    # 5 group spawners through the spawn-point index
    def test_a_group_node_is_tied_by_its_spawn_point_learned_then_changed(self):
        s = sim(self, ZURK, nodes3=[(7301, GROUP, 41001)])
        s.spawn(8001); s.spawn(8002); s.spawn(8004)
        self.assertEqual(spawn_at(s, 7301, MUTT[0]), "enm_thugs4less_robomutt")
        self.assertEqual(spawn_at(s, 7301, THUG[0]), "enm_thugs4less_mele")
        self.assertTrue(s.has("group node 000000000000D000: member enm_thugs4less_robomutt (swarmer)"), s.ev()[-4:])
        s.checkpoint()
        v = s.var(300)
        self.assertIn(v, (9201, 9202, 9203), s.ev()[-4:])                         # another species (pirates) for the thugs
        first = spawn_at(s, 7301, MUTT[0])
        self.assertTrue(first.startswith("enm_pirate"), first)
        self.assertTrue(s.has("VERIFY node Template group 000000000000D000"), s.ev()[-3:])

    def test_a_node_listed_after_its_first_spawn_is_tied_on_the_next_listing(self):
        # round39: Sargasso's nodes were listed ~40 s after the planet loaded
        s = sim(self, ZURK, extra="PF.hide_nodes = true; local osn = rivet.script_nodes; rivet.script_nodes = function(f, n) if PF.hide_nodes and f == 'SpawnerScriptAction' then return {} end return osn(f, n) end")
        s.g.lua.execute("PF.var(300, 1, 9206, 0x%X); PF.node3(0, 7401, 300, 500, 42001)" % (0x8000000000000000 | 9206))
        s.g.step(30)
        s.g.lua.execute("PF.hide_nodes = false")
        spawn_at(s, 7401, steps=200)
        self.assertTrue(s.has("learned template 9206"), s.ev()[-5:])            # tied after the listing it asked for
        self.assertFalse(s.has("tied to no spawner variable"))

    # 6 flying compatibility / 7 ground and jetpack variants
    def test_flyers_for_flyers_and_the_two_thugs_are_two_kinds(self):
        s = sim(self, [(8001, 9205), (8002, 9206), (8003, 9205), (8004, 9204), (8005, 9204), (8006, 9207)])
        s.spawn(8001); s.spawn(8002); s.spawn(8004); s.spawn(8006)
        self.assertEqual(s.var(22), 9206, s.ev()[-4:])                            # jetpack thug -> wasp (a flyer)
        self.assertEqual(s.var(24), 9207)                                         # ground thug -> horned toad, never the jetpack
        self.assertEqual(s.spawn(8003), "enm_indigenous_wasp")
        st = s.g.lua.eval("RANDO_SPAWNERS.V.status()")
        self.assertEqual(st.kinds, 4)                                             # thug ground and thug jetpack counted apart

    def test_a_jetpack_spawned_for_a_ground_request_is_not_success(self):
        g, V = lua_engine()
        self.assertFalse(V.same_kind("enm_thugs4less_shoo", "flyer", "enm_thugs4less_shoo", "ground"))
        self.assertEqual(V.display("enm_thugs4less_shoo", "flyer"), "Goons-4-Less Jetpack")
        self.assertEqual(V.display("enm_thugs4less_shoo", "ground"), "Goons-4-Less Shooter")

    # 8 checkpoint reloads / 9 repeated encounters
    def test_the_same_pick_after_every_reload_and_every_run_changed_again(self):
        s = sim(self, ZURK)
        s.spawn(8001); s.spawn(8002); s.spawn(8004)
        first = (s.var(22), s.var(24), s.var(25))
        for _ in range(3):
            s.checkpoint()
            self.assertEqual((s.var(22), s.var(24), s.var(25)), first)
            self.assertEqual(s.spawn(8003), "enm_thugs4less_shoo")

    # 10 multiple planets
    def test_a_kind_learned_on_one_planet_changes_the_first_wave_on_the_next_visit(self):
        s = sim(self, [(8001, 9206), (8002, 9207), (8003, 9205), (8004, 9204)])
        s.spawn(8001); s.spawn(8002); s.spawn(8003); s.spawn(8004)              # Sargasso's kinds learned (by uid)
        s.g.travel("Sargasso")
        s.g.lua.execute("PF.factories = {}; PF.fac_spawned = {}")
        s.g.lua.execute("PF.var(30, 1, 9206, 0x%X); PF.factory(30, 8101, 30, 130)" % (0x8000000000000000 | 9206))
        s.g.lua.execute("PF.var(31, 1, 9205, 0x%X); PF.factory(31, 8102, 31, 131)" % (0x8000000000000000 | 9205))
        s.g.step(150)
        self.assertEqual(s.var(30), 9205, s.ev()[-4:])                           # changed before any spawn here
        self.assertEqual(s.spawn(8101), "enm_thugs4less_shoo")

    # 11 boss safety
    def test_boss_tier_swaps_only_with_boss_tier_and_story_bosses_never(self):
        facs = [(8001, 9210), (8002, 9211), (8003, 9210), (8004, 9212), (8005, 9212), (8006, 9201), (8007, 9202)]
        s = sim(self, facs, settings={"boss_randomizer": True})
        for f in (8001, 8002, 8004, 8006, 8007):
            s.spawn(f)
        self.assertEqual(s.var(22), 9211, s.ev()[-4:])                           # grunthor -> the other large bot
        self.assertEqual(s.var(24), 9212)                                         # the story boss: untouched
        self.assertNotIn(s.var(22), (9201, 9202))
        off = sim(self, facs, settings={"boss_randomizer": False})
        for f in (8001, 8002):
            off.spawn(f)
        self.assertEqual(off.var(22), 9210)                                       # Boss Randomizer off: grunthor stays
        self.assertTrue(off.g.lua.eval("RANDO_SPAWNERS.V.lvl.order[3].why_said") == "Boss Randomizer off")

    def test_regular_enemies_never_get_a_boss(self):
        facs = [(8001, 9201), (8002, 9210), (8003, 9201)]
        s = sim(self, facs, settings={"boss_randomizer": True})
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9201)                                         # no other regular kind: stays

    def test_switching_the_boss_randomizer_off_keeps_the_enemy_changes(self):
        facs = [(8001, 9210), (8002, 9211), (8003, 9210), (8004, 9201), (8005, 9204), (8006, 9201)]
        s = sim(self, facs, settings={"boss_randomizer": True})
        for f in (8001, 8002, 8004, 8005):
            s.spawn(f)
        self.assertEqual((s.var(22), s.var(25)), (9211, 9204))
        s.g.press("=")
        s.g.step(3)
        self.assertEqual((s.var(22), s.var(25)), (9210, 9204))

    # 12 performance and the frame budget
    def test_a_busy_level_is_followed_without_searching(self):
        nodes = [(7500 + i, 9201, 43000 + i) for i in range(150)]
        s = sim(self, ZURK, nodes3=nodes)
        s.g.step(150)
        reads0 = s.g.lua.eval("PF.reads")
        t0 = time.time()
        for k in range(600):                                                      # ambient spawns at 150 spawn points
            s.next_h += 1
            s.g.lua.execute("PF.names[%d] = 'vehicle\\\\veh_car'; PF.classes[%d] = { 'SceneObject' }" % (s.next_h, s.next_h))
            s.g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=43000 + (k % 150), SpawnedHandle=s.next_h)
            if k % 10 == 0:
                s.g.step(1)
        for _ in range(60):                                                      # the simulator's Lua is slower than
            if s.g.lua.eval("#RANDO_SPAWNERS.V.lvl.queue") == 0:                  # the game's: wait for the 1 ms slices
                break
            s.g.step(60)
        per_spawn = (s.g.lua.eval("PF.reads") - reads0) / 600.0
        self.assertEqual(s.g.lua.eval("#RANDO_SPAWNERS.V.lvl.queue"), 0)          # every spawn followed
        self.assertEqual(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.untied"), 0)          # every one tied by its spawn point
        self.assertLess(per_spawn, 6, per_spawn)                                   # no node search per spawn
        self.assertFalse([l for l in s.ev() if "RANDO-ERROR" in l])
        self.assertLess(time.time() - t0, 30)

    def test_the_budget_never_drops_a_spawn(self):
        s = sim(self, ZURK, extra="""
          local V = RANDO_SPAWNERS.V
          local op = V.process_one
          PF.kills = 0
          V.process_one = function(sc, e) if PF.kill_on and PF.kills < 12 then PF.kills = PF.kills + 1; error("script ran past the 8 ms frame budget", 0) end return op(sc, e) end""")
        s.g.lua.execute("PF.kill_on = true")
        for f in (8001, 8002, 8004):
            s.spawn(f, steps=40)
        self.assertEqual(ledger(s).eligible, 3)                                    # none lost, none twice
        self.assertFalse([l for l in s.ev() if "RANDO-ERROR" in l])


if __name__ == "__main__":
    unittest.main()
