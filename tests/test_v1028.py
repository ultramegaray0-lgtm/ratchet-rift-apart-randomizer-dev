"""Dev 10.28: the Enemy Randomizer after its first real run (tests/data/round38_rivet.log, dev 10.27 scripts, v7 helper;
NefCity, Zurkon arena challenges A1 twice, A3, A5, Sargasso, NefCity).

  * Round38LogTests: what the real game showed (parsed from the log, nothing simulated).
  * FixTests: the 10.28 fixes on the PRODUCTION code in the simulator (synthetic memory, the same harness as
    test_v1027): the stuck rule, deaths found by asking for the actor, the 10.27 false blocks dropped, the resumable job
    (frame budget), put-backs that survive the budget, kinds told apart by family, the spawn-list ring, the end of the
    template-actor asks, and the per-level detail the next test needs.
Nothing in FixTests is in-game verification.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_v1027 import Sim, A1, GROUP, MUTT, THUG, lua_engine  # noqa: E402

LOG38 = ROOT / "tests" / "data" / "round38_rivet.log"


def log38():
    return LOG38.read_text(encoding="utf-8", errors="replace").splitlines()


class Round38LogTests(unittest.TestCase):
    """the real game (round38): parsed, nothing simulated"""

    def test_the_log_is_anonymized(self):
        text = LOG38.read_text(encoding="utf-8", errors="replace")
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", text)
        self.assertNotIn("\\Users\\", text)

    def test_every_verified_factory_spawned_the_replacement(self):
        v = [l for l in log38() if "\tVERIFY " in l]
        self.assertEqual(len(v), 11)
        self.assertTrue(all(l.endswith("REPLACEMENT SPAWNED") for l in v), v)
        self.assertTrue(all("VERIFY factory Templates" in l for l in v))      # only the factory route ran
        # off Zurkon and for flyers too: a jetpack thug factory on Sargasso spawned the Sargasso wasp
        self.assertTrue(any("requested enm_indigenous_wasp, spawned enm_indigenous_wasp" in l for l in v))
        self.assertGreater(len([l for l in log38() if "\tCHANGED factory Templates" in l]), 50)
        self.assertFalse([l for l in log38() if "\tCHANGED node Template" in l])   # 0 node, 0 group changes

    def test_the_false_stuck_of_10_27(self):
        L = log38()
        stuck = [l for l in L if "kept original for this seed" in l and "without a death" in l]
        self.assertEqual(len(stuck), 5)
        # ... while the fight went on and A1 was completed (EndReason=0), and death events did come
        self.assertTrue(any("BotDeathCompleteEvent" in l for l in L))
        self.assertTrue(any("EndReason=0" in l and "MIS_ZURK_ARENA_CHALLENGE_A1" in l for l in L))

    def test_template_actors_never_answered(self):
        asked = answered = 0
        for l in log38():
            m = re.search(r"template actors asked before a spawn: (\d+), answered (\d+)", l)
            if m:
                asked = max(asked, int(m.group(1)))
                answered += int(m.group(2))
        self.assertGreater(asked, 90)
        self.assertEqual(answered, 0)

    def test_two_thugs_one_cut_name(self):
        L = log38()
        self.assertTrue(any("enm_thugs4less_shoo = ground/GameBotShooter," in l for l in L))
        self.assertTrue(any("enm_thugs4less_shoo = flyer/GameBotShooterJetPack," in l for l in L))

    def test_the_budget_storm(self):
        errs = [l for l in log38() if re.search(r"16_rando_spawners\.lua:\d+: ran past the 8 ms frame budget", l)]
        self.assertGreater(len(errs), 90)
        self.assertGreater(len([l for l in errs if ":2369:" in l]), 80)      # 10.27's arm pass loop

    def test_group_members_were_learned(self):
        L = log38()
        for m in ("enm_thugs4less_mele (swarmer)", "enm_thugs4less_robomutt (swarmer)", "enm_pirate_bladeball (swarmer)"):
            self.assertTrue(any("group node" in l and m in l for l in L), m)


class FixTests(unittest.TestCase):
    """SYNTHETIC memory; the production engine (dev 10.28)"""

    # ---- the stuck rule ----
    def test_deaths_that_name_no_bot_keep_a_running_fight_from_being_stuck(self):
        # round38: death events came, none named a bot; other factories kept spawning
        s = Sim(self, A1 + [(8007, 9001), (8008, 9002)])
        s.g.lua.execute("RANDO_SPAWNERS.V.STUCK_SECONDS = 2")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        self.assertTrue(s.has("REPLACEMENT SPAWNED"))
        for _ in range(4):
            s.g.fire("BotDeathCompleteEvent")                                    # no sender at all
            s.g.step(60)
        self.assertFalse(s.has("quiet"), s.ev()[-3:])
        self.assertFalse(s.has("kept original"))
        self.assertEqual(s.var(22), 9002)

    def test_a_killed_bot_is_found_gone_and_the_encounter_is_not_stuck(self):
        s = Sim(self, A1)
        s.g.lua.execute("RANDO_SPAWNERS.V.STUCK_SECONDS = 2")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)                              # 70003: the replacement
        s.g.lua.execute("PF.names[70003] = nil; PF.classes[70003] = nil")        # killed and removed
        s.g.step(300)
        self.assertFalse(s.has("quiet"), s.ev()[-3:])
        self.assertEqual(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.gone_seen"), 1)
        self.assertEqual(s.var(22), 9002)

    def test_five_stuck_or_retried_runs_keep_it_original(self):
        s = Sim(self, A1)
        s.g.lua.execute("RANDO_SPAWNERS.V.STUCK_SECONDS = 2")
        for _ in range(5):
            s.spawn(8001); s.spawn(8002); s.spawn(8003)
            s.g.step(200)
            s.checkpoint()
        self.assertTrue(s.has("kept original for this seed: factory Templates 000000000000F002"), s.ev()[-6:])
        s.g.step(130)
        self.assertEqual(s.var(22), 9001)

    def test_10_27_false_blocks_are_dropped_and_real_ones_kept(self):
        s = Sim(self, A1)
        s.g.lua.execute("""
          RANDO.state.spawn_blocked = RANDO.state.spawn_blocked or {}
          RANDO.state.spawn_blocked["v:000000000000F002"] = "its enemies stayed alive 180 s without a death"
          RANDO.state.spawn_blocked["v:000000000000F004"] = "the checkpoint was loaded 5 times while it ran"
          RANDO_SPAWNERS.V.migrated_state = nil""")                        # as a save loaded with 10.28
        s.g.step(2)
        self.assertTrue(s.has("1 spawner(s) 10.27 wrongly kept original"), s.ev())
        self.assertIsNone(s.g.lua.eval('RANDO.state.spawn_blocked["v:000000000000F002"]'))
        self.assertIsNotNone(s.g.lua.eval('RANDO.state.spawn_blocked["v:000000000000F004"]'))
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)                                         # randomized again

    # ---- the frame budget ----
    def test_a_budget_error_outside_any_pcall_loses_no_spawn(self):
        # round38: the hook's error came at the arm pass's own lines (not inside a guarded call) and killed the job
        s = Sim(self, A1, extra="""
          local V = RANDO_SPAWNERS.V
          local od = V.drain_pending
          PF.kills = 0
          V.drain_pending = function() if PF.kill_on and PF.kills < 5 then PF.kills = PF.kills + 1; error("script ran past the 8 ms frame budget", 0) end return od() end""")
        s.g.lua.execute("PF.kill_on = true")
        s.spawn(8001, steps=30); s.spawn(8002, steps=30)
        self.assertEqual(s.g.lua.eval("PF.kills"), 5)
        self.assertEqual(s.var(22), 9002, s.ev()[-4:])                           # both spawns learned, plan done
        self.assertFalse([l for l in s.ev() if "RANDO-ERROR" in l])
        self.assertGreaterEqual(s.g.lua.eval("RANDO_SPAWNERS.V.budget_hits"), 5)
        self.assertEqual(s.spawn(8003), "enm_melee")

    def test_a_job_that_never_progresses_is_dropped_quietly(self):
        s = Sim(self, A1, extra="""
          local V = RANDO_SPAWNERS.V
          V.drain_pending = function() if PF.kill_on then error("script ran past the 8 ms frame budget", 0) end return true end""")
        s.g.lua.execute("PF.kill_on = true")
        s.spawn(8001, steps=120)
        self.assertGreaterEqual(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.jobs_dropped"), 1)
        self.assertFalse([l for l in s.ev() if "RANDO-ERROR" in l])
        s.g.lua.execute("PF.kill_on = false")
        s.spawn(8003, steps=30); s.spawn(8002, steps=30)                          # 8001's spawn was dropped with the job
        self.assertEqual(s.var(24), 9002, s.ev()[-3:])                           # the next spawns are followed again

    def test_a_put_back_lost_to_the_budget_finishes_before_anything_is_read(self):
        s = Sim(self, A1, extra="""
          local ow = rivet.write
          PF.lose_writes = 0
          rivet.write = function(a, h) if PF.lose_writes > 0 then PF.lose_writes = PF.lose_writes - 1; error("script ran past the 8 ms frame budget", 0) end return ow(a, h) end""")
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9002)
        s.g.lua.execute("PF.lose_writes = 2")
        s.g.fire("CheckpointTriggeredEvent", CheckpointHash=1, Loaded=True)
        s.g.step(2)
        self.assertEqual(s.var(22), 9001, s.ev()[-4:])                           # restored on the next frame
        s.g.step(60)
        # the new level read the TRUE original (9001) and changed it again
        self.assertEqual(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.order[3].orig.actors"), 9001)
        self.assertEqual(s.var(22), 9002)

    # ---- kinds, slots, probes ----
    def test_same_name_other_family_is_another_kind(self):
        g, V = lua_engine()
        self.assertTrue(V.same_kind("enm_thugs4less_shoo", "ground", "characters\\enemy\\x\\actors\\enm_thugs4less_shoo", "ground"))
        self.assertFalse(V.same_kind("enm_thugs4less_shoo", "ground", "enm_thugs4less_shoo", "flyer"))
        self.assertTrue(V.same_kind("enm_thugs4less_shoo", None, "enm_thugs4less_shooter", "flyer"))

    def test_the_spawn_list_ring_is_read_whole(self):
        g, V = lua_engine()
        g.lua.execute("""
          SIM.map(0x6100000000, 0x200)
          SIM.put_u32(0x6100000000 + 0x9C, 22)
          SIM.put_u32(0x6100000000 + 0xDC + 16 * 12, 4242)
          SIM.put_u32(0x6100000000 + 0xDC + 0 * 12, 4141)""")
        sl = g.lua.eval("RANDO_SPAWNERS.V.spawner_slots(0x6100000000)")
        got = [sl[i] for i in range(1, len(sl) + 1)]
        self.assertIn(4242, got)
        self.assertIn(4141, got)

    def test_template_actor_asks_stop_when_none_is_answered(self):
        s = Sim(self, A1, extra="RANDO_SPAWNERS.V.PROBE_GIVEUP = 2")
        self.assertTrue(s.has("template actors never answered before a spawn (2 asked)"), s.ev())
        self.assertEqual(s.g.lua.eval("RANDO_SPAWNERS.V.session.probe_tried"), 2)

    # ---- node / group coverage and what the next log says about it ----
    def test_the_level_detail_says_why_a_group_was_not_changed(self):
        s = Sim(self, A1, nodes=[(7201, GROUP)])
        s.spawn(8001); s.spawn(8002)
        s.checkpoint()
        self.assertTrue(s.has("node Template group: 1 members not learned yet (changes from its next run)"), s.ev()[-4:])

    def test_an_enemy_spawn_tied_to_no_spawner_is_logged(self):
        s = Sim(self, A1)
        s.g.lua.execute("PF.names[71000] = PF.tdef[9002].name; PF.classes[71000] = { 'SceneObject', 'GameBotMeleeSwarmer' }")
        s.g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=8, SpawnLocation=5555, SpawnedHandle=71000)
        s.g.step(20)
        self.assertTrue(s.has("spawn 71000 of enm_melee (swarmer) at location 5555 index 8: tied to no spawner variable"), s.ev()[-3:])

    def test_a_location_that_ties_to_nothing_is_not_searched_forever(self):
        s = Sim(self, A1, nodes=[(7101, 9001)])
        for h in range(72000, 72005):
            s.g.lua.execute("PF.names[%d] = 'vehicle\\\\veh_car'; PF.classes[%d] = { 'SceneObject' }" % (h, h))
            s.g.fire("SpawnerSpawnEvent", SpawnFactory=0, SpawnIndex=0, SpawnLocation=6666, SpawnedHandle=h)
            s.g.step(10)
        self.assertIs(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.loc[6666]"), False)
        self.assertEqual(s.g.lua.eval("RANDO_SPAWNERS.V.lvl.untied"), 5)

    def test_two_nodes_sharing_a_spawn_point_are_told_apart(self):
        s = Sim(self, A1, nodes=[(7201, GROUP), (7202, GROUP)])
        s.spawn(8001); s.spawn(8002)
        s.spawn_node(7201, MUTT[0])                                              # both nodes use location 4012
        s.spawn_node(7202, THUG[0])
        self.assertTrue(s.has("group node 000000000000E000: member enm_thugs4less_robomutt"), s.ev())
        self.assertTrue(s.has("group node 000000000000E001: member enm_thugs4less_mele"), s.ev())

    def test_the_group_changes_on_the_next_try_and_spawns_a_regular_enemy(self):
        s = Sim(self, A1, nodes=[(7201, GROUP)])
        s.spawn(8001); s.spawn(8002)
        s.spawn_node(7201, MUTT[0]); s.spawn_node(7201, THUG[0])
        s.checkpoint()
        self.assertIn(s.var(60), (9001, 9002), s.ev()[-4:])
        self.assertIn(s.spawn_node(7201, MUTT[0]), ("enm_grunt", "enm_melee"))
        self.assertTrue(s.has("VERIFY node Template group 000000000000E000"), s.ev()[-3:])


if __name__ == "__main__":
    unittest.main()
