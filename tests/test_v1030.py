"""Dev 10.30: combat compatibility after round40 (tests/data/round40_rivet.log, dev 10.29 scripts; Zurkon arena A1 twice,
A3, the pub, Ardolis, Cordelion). The player: "some enemies spawned as randomized replacements but could not be killed";
"the randomized pirates with guns were unkillable".

  * Round40LogTests: what the real game showed (parsed, nothing simulated) - the evidence behind every change here.
  * SimulatorTests: the PRODUCTION engine (16_rando_spawners.lua SP.V, enemy.lua, boss.lua) on synthetic memory (the
    test_v1027 / test_v1029 harness) with the default enemy_compat = "verified" unless a test says otherwise. Deaths are
    simulated with BotDeathCompleteEvent { SenderHandle = the bot } as the real game sends them (round39: 66 deaths,
    19 named one of the randomizer's bots).
  * KitTests: one release in the scripts folder, developer tools apart.
Nothing in SimulatorTests is in-game verification: the simulator cannot tell whether an enemy can be killed - it only
shows what the engine does with the deaths (or their absence) the game reports.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game, script_files, MOD  # noqa: E402
from test_v1027 import GROUP, MUTT, THUG  # noqa: E402
from test_v1029 import sim, spawn_at  # noqa: E402
import combat_audit  # noqa: E402

LOG40 = ROOT / "tests" / "data" / "round40_rivet.log"
SHOOTER_FROM_BLADEBALL = "factory|enm_pirate_bladebal/swarmer>enm_pirate_robot_sh/ground"
SH_TO_ME = "factory|enm_pirate_robot_sh/ground>enm_pirate_robot_me/swarmer"
THUG_TO_SH = "factory|enm_thugs4less_shoo/ground>enm_pirate_robot_sh/ground"


def vsim(test, factories, mode="verified", settings=None, ban=False, **kw):
    st = dict(settings or {})
    st["enemy_compat"] = mode
    s = sim(test, factories, settings=st, **kw)
    if not ban:
        # dev 10.33 bans the pirate robot shooter as a replacement (test_round44.py); these 10.30 tests use it as the
        # generic "ground" replacement of the trial / watch mechanics, so they run without the built-in ban list
        s.g.lua.execute("RANDO_SPAWNERS.V.BAD_REPLACEMENT = {}")
    return s


def kill(s, h, steps=2):
    s.g.fire("BotDeathCompleteEvent", SenderHandle=h)
    s.g.step(steps)


def combat(s):
    t = s.g.lua.eval("RANDO.state.enemy_combat")
    return {k: v for k, v in t.items()} if t else {}


def fast_watch(s, seconds=1, deaths=3):
    s.g.lua.execute("RANDO_SPAWNERS.V.COMBAT_SECONDS = %d; RANDO_SPAWNERS.V.COMBAT_DEATHS = %d" % (seconds, deaths))


# ---------------------------------------------------------------------------------------------- real game
class Round40LogTests(unittest.TestCase):
    """round40 (dev 10.29): parsed, nothing simulated"""

    @classmethod
    def setUpClass(cls):
        cls.L = LOG40.read_text(encoding="utf-8", errors="replace").splitlines()
        cls.visits = combat_audit.audit(cls.L)

    def test_anonymized(self):
        self.assertTrue(any("game = <GAME_FOLDER>\\RiftApart.exe" in l for l in self.L))
        self.assertFalse(any("\\Users\\" in l for l in self.L))

    def _a1(self, n):
        a1 = [v for v in self.visits if sum(len(x) for x in v["replaced"].values()) > 0]
        self.assertEqual(len(a1), 2)                     # only the two A1 runs replaced anything
        return a1[n]

    def test_a1_run1_bots_without_a_death_are_exactly_the_shooters_from_the_bladeball_factory(self):
        v = self._a1(0)
        replaced = sum(len(x) for x in v["replaced"].values())
        self.assertEqual((replaced, v["deaths"], v["ours"]), (20, 18, 12))
        pairs = {p: len(h) for p, h in v["replaced"].items()}
        self.assertEqual(pairs["factory|enm_pirate_bladebal>enm_pirate_robot_sh/ground"], 8)
        self.assertEqual(replaced - v["ours"], 8)       # 12 died = the 10 brawler + 2 bladeball replacements
        self.assertEqual(pairs["factory|enm_pirate_robot_sh>enm_pirate_robot_me/swarmer"]
                         + pairs["factory|enm_pirate_bladebal>enm_pirate_robot_me/swarmer"]
                         + pairs["factory|enm_pirate_robot_sh>enm_pirate_bladebal/swarmer"], 12)

    def test_a1_run2_the_same_pairs_and_7_bots_without_a_death(self):
        v = self._a1(1)
        self.assertEqual((sum(len(x) for x in v["replaced"].values()), v["ours"]), (20, 13))
        self.assertEqual(len(v["replaced"]["factory|enm_pirate_bladebal>enm_pirate_robot_sh/ground"]), 8)

    def test_the_randomizer_called_every_shooter_spawn_a_success(self):
        # the gap this round exposed: a spawn was taken as the proof
        sh = [l for l in self.L if "\tSPAWN " in l and "factory Templates DD6478DACCDD2129" in l]
        self.assertEqual(len(sh), 16)
        self.assertTrue(all(l.endswith("| SUCCESS") for l in sh), sh[:2])
        self.assertTrue(any("VERIFY factory Templates DD6478DACCDD2129: requested enm_pirate_robot_sh, spawned "
                            "enm_pirate_robot_shooter: REPLACEMENT SPAWNED" in l for l in self.L))

    def test_both_a1_runs_completed_and_a3_was_left(self):
        ends = [l for l in self.L if "EndMissionDevstatsEvent" in l and "MIS_ZURK_ARENA_CHALLENGE_A1" in l]
        self.assertEqual(len(ends), 2)
        self.assertTrue(all("EndReason=0" in l for l in ends))
        self.assertTrue(any("MIS_ZURK_ARENA_CHALLENGE_A3 MissionState=1 PreviousState=2" in l for l in self.L))
        a3 = [v for v in self.visits if v["missions"].get("MIS_ZURK_ARENA_CHALLENGE_A3") and v["spawns"] == 14][0]
        self.assertEqual((a3["deaths"], sum(len(x) for x in a3["replaced"].values())), (0, 0))   # nothing replaced there

    def test_the_game_ignored_one_change_and_it_was_put_back(self):
        self.assertTrue(any("VERIFY factory Templates E9C64DEC0178FB98: requested enm_pirate_robot_sh, spawned enm_pirate_robot_me: "
                            "ORIGINAL SPAWNED" in l for l in self.L))
        self.assertTrue(any("put back (the game ignored the change): factory Templates E9C64DEC0178FB98: OK" in l for l in self.L))

    def test_every_put_back_succeeded(self):
        res = [l.rsplit(": ", 1)[-1] for l in self.L if re.search(r"\tput back \(", l)]
        self.assertGreater(len(res), 30)
        self.assertEqual(set(res), {"OK"})

    def test_every_frame_budget_error_came_from_the_developer_probe(self):
        err = [l for l in self.L if "RANDO-ERROR" in l]
        self.assertEqual(len(err), 10)
        self.assertTrue(all("dev(spawnprobe).lua:103: ran past the 8 ms frame budget" in l for l in err))
        self.assertFalse(any("16_rando_spawners" in l or "enemy.lua" in l for l in err))
        self.assertTrue(any("budget retries 26" in l for l in self.L))     # the production engine retried, it did not fail

    def test_the_install_was_one_release_plus_developer_files(self):
        self.assertTrue(any("RANDO-KIT all 12 required scripts are 10.0.18" in l for l in self.L))
        self.assertTrue(any("variable route loaded (dev 10.29)" in l for l in self.L))
        self.assertTrue(any("Randomizer dev 10.29 - seed" in l for l in self.L))
        dev = [l for l in self.L if "developer files loaded" in l][0]
        self.assertIn("dev(spawnprobe)", dev)
        self.assertIn("dev(spawnproof)", dev)

    def test_no_boss_tier_swap_happened(self):
        self.assertTrue(any("Boss Randomizer ON: 0 boss spawner(s) changed here" in l for l in self.L))
        self.assertFalse(any(", role boss" in l for l in self.L))
        self.assertFalse(any("HealthBarShowEvent" in l for l in self.L))

    def test_why_enemy_spawns_kept_their_enemy(self):
        why = {}
        for l in self.L:
            m = re.search(r"NOT CHANGED: (.*)$", l)
            if m:
                why[m.group(1)] = why.get(m.group(1), 0) + 1
        self.assertEqual(why["spawned before the randomizer planned it"], 34)
        self.assertEqual(why["already spawned on this level"], 34)
        self.assertEqual(why["spawned before the randomizer read its spawner"], 31)
        self.assertEqual(why["not tied to a spawner: its spawn point belongs to no listed spawner"], 9)


# ---------------------------------------------------------------------------------------------- simulator
# round40's A1 kinds: robot shooter 9201, robot brawler 9202, bladeball 9203; factory i holds var 20+i
A1_40 = [(8001, 9201), (8002, 9202), (8003, 9203)] + [(8004 + i, 9203) for i in range(6)]


class SimulatorTests(unittest.TestCase):
    """SYNTHETIC memory; the production engine (dev 10.30)"""

    def learn_a1(self, s):
        s.spawn(8001); s.spawn(8002); s.spawn(8003)

    # ---- the pool: only in-game verified pairs
    def test_round40s_failing_pair_is_never_armed_by_default(self):
        s = vsim(self, A1_40)
        self.learn_a1(s)
        picks = [s.var(23 + i) for i in range(6)]
        self.assertNotIn(9201, picks, s.ev()[-6:])                     # never a robot shooter for a bladeball
        self.assertEqual(set(picks), {9202}, picks)                     # the verified bladeball -> brawler
        self.assertTrue(s.has("combat-verified pair"), [l for l in s.ev() if "CHANGED" in l][:2])
        # what 10.29 did with the same level (enemy_compat = "any" keeps its rules): the shooter was among its picks
        old = vsim(self, A1_40, mode="any")
        self.learn_a1(old)
        self.assertIn(9201, [old.var(23 + i) for i in range(6)])

    def test_an_unverified_kind_never_enters_the_pool(self):
        facs = [(8001, 9201), (8002, 9202), (8003, 9203), (8004, 9204), (8005, 9201), (8006, 9201)]
        s = vsim(self, facs)
        for f in (8001, 8002, 8003, 8004):
            s.spawn(f)
        self.assertNotIn(s.var(24), (9204,), s.ev()[-4:])              # 10.29 picked the thug (another species)
        self.assertIn(s.var(24), (9202, 9203))
        self.assertIn(s.var(25), (9202, 9203))
        old = vsim(self, facs, mode="any")
        for f in (8001, 8002, 8003, 8004):
            old.spawn(f)
        self.assertEqual(old.var(24), 9204)

    def test_with_no_verified_replacement_the_spawner_keeps_its_enemy(self):
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9204)])
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9204)                               # thug shooter: no pair of it is verified
        s.checkpoint()
        self.assertTrue(s.has("no combat-verified replacement here"), [l for l in s.ev() if "level detail" in l])

    def test_the_default_is_verified(self):
        # dev 10.31 made "all" the default (the 10.30 "verified" pool is kept as an option)
        g = Game(settings={"enemy_randomizer": True})
        self.assertEqual(g.lua.eval("RANDO.config.enemy_compat"), "all")
        self.assertEqual(g.lua.eval("RANDO_SPAWNERS.V.compat_mode()"), "all")
        g = Game(settings={"enemy_randomizer": True, "enemy_compat": "verified"})
        self.assertEqual(g.lua.eval("RANDO_SPAWNERS.V.compat_mode()"), "verified")
        self.assertEqual(g.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % SHOOTER_FROM_BLADEBALL), "rejected")
        self.assertEqual(g.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % SH_TO_ME), "verified")
        self.assertEqual(g.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % THUG_TO_SH), "unverified")
        self.assertTrue(g.log_has("combat compatibility verified"), [l for l in g.logs() if "compatibility" in l])

    # ---- trial mode: unverified pairs of the same bot class, one at a time, proven by a death
    def test_a_trial_is_the_same_bot_class_and_one_spawner_at_a_time(self):
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9202), (8004, 9204), (8005, 9204)], mode="trial")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        armed = [v for v in (s.var(23), s.var(24)) if v != 9204]
        self.assertEqual(armed, [9201], s.ev()[-5:])                    # robot shooter (GameBotShooter), never the brawler
        self.assertTrue(s.has("TRIAL: an unverified pair of the same bot class"))

    def test_a_death_verifies_a_trial_pair_for_the_save(self):
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9202), (8004, 9204), (8005, 9204)], mode="trial")
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        f = 8004 if s.var(23) == 9201 else 8005
        self.assertEqual(s.spawn(f), "enm_pirate_robot_sh")
        h = s.next_h
        kill(s, h)
        self.assertTrue(s.has("DEATH %d | enm_pirate_robot_sh replacing enm_thugs4less_shoo" % h), s.ev()[-3:])
        self.assertTrue(s.has("COMBAT VERIFIED " + THUG_TO_SH))
        self.assertEqual(combat(s)[THUG_TO_SH], "ok:1")
        s.g.step(130)                                                   # the next listing: no trial cap for a verified pair
        self.assertEqual([s.var(23), s.var(24)].count(9201), 2, s.ev()[-4:])

    def test_a_replacement_that_lives_through_the_fight_is_rejected_and_put_back(self):
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9202), (8004, 9204), (8005, 9204)], mode="trial")
        fast_watch(s)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        f = 8004 if s.var(23) == 9201 else 8005
        idx = 23 if f == 8004 else 24
        s.spawn(f)
        h = s.next_h
        for k in range(3):                                               # the fight goes on: 3 other bots die
            kill(s, 60001 + k)
        s.g.step(130)
        self.assertTrue(s.has("COMBAT CHECK FAILED " + THUG_TO_SH), s.ev()[-4:])
        self.assertTrue(s.has("(bot %d) was alive" % h))
        self.assertTrue(combat(s)[THUG_TO_SH].startswith("bad:"))
        self.assertEqual(s.var(idx), 9204)                              # put back at once
        self.assertEqual(s.spawn(f), "enm_thugs4less_shoo")            # its next enemy is the original
        self.assertTrue(s.g.note_has("could not be killed"), s.g.notes())
        s.checkpoint()
        self.assertTrue(s.has("COMBAT %s: replaced bots spawned 1, died 0, gone 0, alive at the end 0 | REJECTED here" % THUG_TO_SH),
                        [l for l in s.ev() if l.find("\tCOMBAT ") >= 0])

    def test_a_rejected_pair_stays_rejected_after_a_checkpoint_and_a_new_session(self):
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9202), (8004, 9204), (8005, 9204)], mode="trial")
        fast_watch(s)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        s.spawn(8004 if s.var(23) == 9201 else 8005)
        for k in range(3):
            kill(s, 60001 + k)
        s.g.step(130)
        s.checkpoint(steps=200)
        self.assertEqual((s.var(23), s.var(24)), (9204, 9204), s.ev()[-4:])
        saved = combat(s)
        self.assertEqual(s.g.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % THUG_TO_SH), "rejected")
        # a new game session (a new Lua VM) with the save: still rejected
        s.g.lua.execute("RANDO_SPAWNERS.V.session = { said_blocked = false, said_ok = false, said_off = {}, retries = {}, probe_tried = 0, probe_ok = 0 }")
        self.assertEqual(s.g.lua.eval('(RANDO_SPAWNERS.V.compat_status("%s"))' % THUG_TO_SH), "rejected")
        self.assertIn(THUG_TO_SH, saved)
        self.assertIn("enemy_combat", list(s.g.lua.eval("RANDO_SPAWNERS.KEEP_OVER_NEW_GAME").values()))

    def test_a_built_in_verified_pair_is_rejected_only_after_two_failures(self):
        s = vsim(self, [(8001, 9201), (8002, 9202), (8003, 9201)])
        fast_watch(s)
        s.spawn(8001); s.spawn(8002)
        self.assertEqual(s.var(22), 9202)
        s.spawn(8003)
        for k in range(3):
            kill(s, 60001 + k)
        s.g.step(130)
        self.assertTrue(s.has("COMBAT CHECK FAILED %s" % SH_TO_ME), s.ev()[-3:])
        self.assertEqual(combat(s)[SH_TO_ME], "suspect:1")
        self.assertTrue(s.has("failure 1 of 2 for this save"))
        self.assertEqual(s.var(22), 9201)                                # put back for this session
        s.g.lua.execute("RANDO_SPAWNERS.V.session.compat_bad = nil")     # a new session
        s.checkpoint(steps=200)
        self.assertEqual(s.var(22), 9202, s.ev()[-3:])                   # one failure: still verified
        s.spawn(8003)
        for k in range(3):
            kill(s, 60101 + k)
        s.g.step(130)
        self.assertTrue(combat(s)[SH_TO_ME].startswith("bad:"), combat(s))

    # ---- re-entrant processing and the frame budget
    def test_a_death_is_counted_once_and_the_budget_never_drops_the_watch(self):
        s = vsim(self, A1_40)
        s.g.lua.execute("""local V = RANDO_SPAWNERS.V; local op = V.process_one; PF.kills = 0
          V.process_one = function(sc, e) if PF.kill_on and PF.kills < 8 then PF.kills = PF.kills + 1; error("script ran past the 8 ms frame budget", 0) end return op(sc, e) end""")
        self.learn_a1(s)
        s.g.lua.execute("PF.kill_on = true")
        s.spawn(8004, steps=40)
        h = s.next_h
        self.assertEqual(s.g.lua.eval("#RANDO_SPAWNERS.V.lvl.watch"), 1)
        kill(s, h); kill(s, h)                                            # the same death twice
        self.assertEqual(s.g.lua.eval('RANDO_SPAWNERS.V.lvl.combat["factory|enm_pirate_bladebal/swarmer>enm_pirate_robot_me/swarmer"].died'), 1)
        self.assertEqual(sum(1 for l in s.ev() if "\tDEATH %d " % h in l), 1)

    def test_a_frame_budget_error_is_no_answer_to_is_it_still_there(self):
        s = vsim(self, [(8001, 9201), (8002, 9202), (8003, 9201)])
        fast_watch(s)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        h = s.next_h
        s.g.lua.execute("""local oc = rivet.components; PF.busy = %d
          rivet.components = function(x) if x == PF.busy then error("script ran past the 8 ms frame budget", 0) end return oc(x) end
          local on = rivet.name; rivet.name = function(x) if x == PF.busy then error("script ran past the 8 ms frame budget", 0) end return on(x) end""" % h)
        for k in range(3):
            kill(s, 60001 + k)
        s.g.step(200)
        self.assertFalse(s.has("COMBAT CHECK FAILED"), s.ev()[-3:])       # busy frames: undecided, not "alive"
        s.g.lua.execute("PF.busy = -1")
        s.g.step(130)
        self.assertTrue(s.has("COMBAT CHECK FAILED"), s.ev()[-3:])

    def test_a_replacement_removed_without_a_death_is_gone_not_failed(self):
        # actor cleanup: the game removed the bot (nothing answers for its handle any more) - no evidence either way
        s = vsim(self, [(8001, 9201), (8002, 9202), (8003, 9201)])
        fast_watch(s)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        h = s.next_h
        s.g.lua.execute("PF.classes[%d] = nil; PF.names[%d] = nil" % (h, h))
        for k in range(3):
            kill(s, 60001 + k)
        s.g.step(130)
        self.assertFalse(s.has("COMBAT CHECK FAILED"), s.ev()[-3:])
        self.assertEqual(s.g.lua.eval('RANDO_SPAWNERS.V.lvl.combat["%s"].gone' % SH_TO_ME), 1)
        self.assertEqual(s.var(22), 9202)                                 # still changed

    # ---- initialization: the replacement against the game's own enemies of that kind
    def test_a_replacement_that_spawns_without_a_component_the_originals_have_is_rejected(self):
        s = vsim(self, A1_40)
        self.learn_a1(s)                                                  # an original brawler: SceneObject + GameBotMeleeSwarmer
        s.next_h += 1
        h = s.next_h
        s.g.lua.eval("PF.spawn_factory(8004, %d)" % h)
        s.g.lua.execute('PF.classes[%d] = { "GameBotMeleeSwarmer" }' % h)  # ... the replacement lacks one
        s.g.step(12)
        # dev 10.31+: the initialization check is advisory ("noted only; the combat watch decides")
        self.assertTrue(s.has("initialization MISSING SceneObject (noted only; the combat watch decides)"), [l for l in s.ev() if "VERIFY" in l])
        self.assertFalse(s.has("COMBAT CHECK FAILED factory|enm_pirate_bladebal/swarmer>enm_pirate_robot_me/swarmer"))
        self.assertEqual(s.var(23), 9202)                                 # stays changed until the watch decides

    def test_a_complete_replacement_passes_the_initialization_check(self):
        s = vsim(self, A1_40)
        self.learn_a1(s)
        s.spawn(8004)
        self.assertTrue(s.has("initialization OK (1 original(s) compared)"), [l for l in s.ev() if "VERIFY" in l])
        self.assertTrue(s.has("a death of it is the proof"))

    # ---- group spawners, bosses
    def test_a_group_spawner_needs_verified_pairs_for_every_member(self):
        for mode, changed in (("verified", False), ("any", True)):
            s = vsim(self, [(8001, 9201), (8002, 9202), (8003, 9204)], mode=mode, nodes3=[(7301, GROUP, 41001)])
            s.spawn(8001); s.spawn(8002); s.spawn(8003)
            spawn_at(s, 7301, MUTT[0]); spawn_at(s, 7301, THUG[0])
            s.checkpoint()
            self.assertEqual(s.var(300) != GROUP, changed, (mode, s.ev()[-4:]))

    def test_story_bosses_never_and_boss_tier_only_with_proof(self):
        facs = [(8001, 9210), (8002, 9211), (8003, 9210), (8004, 9212)]
        s = vsim(self, facs, settings={"boss_randomizer": True})
        s.g.fire("HealthBarShowEvent", SenderHandle=1)                    # nothing: no handle of ours
        s.spawn(8001); s.spawn(8002); s.spawn(8004)
        self.assertEqual(s.var(22), 9210, s.ev()[-4:])                    # Grunthor -> tank is unverified: not changed
        self.assertEqual(s.var(23), 9212)                                 # the story boss: never
        old = vsim(self, facs, mode="any", settings={"boss_randomizer": True})
        old.spawn(8001); old.spawn(8002); old.spawn(8004)
        self.assertEqual(old.var(22), 9211)                               # 10.29 swapped boss tiers without proof
        self.assertEqual(old.var(23), 9212)

    # ---- spawn coverage: factories first
    def test_factories_are_planned_before_the_nodes_are_listed(self):
        s = vsim(self, A1_40, extra="local osn = rivet.script_nodes; rivet.script_nodes = function(f, n) "
                                    "if f == 'SpawnerScriptAction' then error('node listing failed', 0) end return osn(f, n) end")
        self.learn_a1(s)
        self.assertEqual(s.var(23), 9202, s.ev()[-4:])                    # 10.29 planned nothing while nodes failed
        self.assertEqual(s.spawn(8004), "enm_pirate_robot_me")

    def test_a_node_listed_late_that_shares_a_changed_factorys_variable_puts_it_back(self):
        s = vsim(self, A1_40)
        self.learn_a1(s)
        self.assertEqual(s.var(23), 9202)
        # a node listed later uses the same variable (23) and has spawned already
        s.g.lua.execute("PF.node3(0, 7501, 23, 500, 43001)")
        s.g.lua.execute("PF.var(23, 1, 9202, 0x%X)" % (0x8000000000000000 | 9202))
        spawn_at(s, 7501, steps=200)
        self.assertTrue(s.has("put back (shares its variable with a spent spawner): factory Templates 000000000000F003: OK"), s.ev()[-4:])
        self.assertEqual(s.var(23), 9203)

    # ---- what you see
    def test_the_level_summary_holds_every_pair_against_its_deaths(self):
        s = vsim(self, A1_40)
        self.learn_a1(s)
        s.spawn(8004); h1 = s.next_h
        s.spawn(8004); h2 = s.next_h
        kill(s, h1)
        s.checkpoint()
        self.assertTrue(s.has("COMBAT factory|enm_pirate_bladebal/swarmer>enm_pirate_robot_me/swarmer: replaced bots spawned 2, died 1, "
                              "gone 0, alive at the end 1 | pair verified"), [l for l in s.ev() if "\tCOMBAT " in l])
        self.assertNotEqual(h1, h2)

    def test_ctrl_minus_says_how_many_pairs_are_verified_and_rejected(self):
        s = vsim(self, A1_40)
        s.g.press("-", ctrl=True)
        s.g.step(2)
        subs = [(n.opts and n.opts["sub"]) or "" for n in s.g.sim.notes.values()]
        self.assertTrue(any("combat: 3 pair(s) verified, 3 rejected (verified)" in t for t in subs), subs)


# ---------------------------------------------------------------------------------------------- the install
class KitTests(unittest.TestCase):
    def test_the_scripts_folder_holds_one_release_and_no_developer_file(self):
        names = sorted(p.name for p in (MOD / "scripts").glob("*.lua"))
        self.assertFalse([n for n in names if n.startswith("dev(")])
        for p in (MOD / "scripts").glob("*.lua"):
            tags = re.findall(r'RANDO_FILES\["[^"]+"\] = "([^"]+)"', p.read_text(encoding="utf-8"))
            self.assertEqual(tags, ["10.0.35"], p.name)
        self.assertTrue((MOD / "dev_scripts" / "dev(spawnprobe).lua").exists())

    def test_the_release_label_is_one(self):
        g = Game(settings={"enemy_randomizer": True})
        g.step(3)
        self.assertTrue(g.log_has("RANDO-KIT release v0.70 (kit 10.0.35)"), [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.log_has("variable route loaded (v0.70, kit 10.0.35)"))

    def test_an_old_developer_file_left_in_the_scripts_folder_is_named_for_deletion(self):
        g = Game(files=script_files(), spawnprobe=True)
        g.lua.execute('RANDO_FILES["dev(spawnprobe)"] = "10.0.18"')
        g.step(3)
        self.assertTrue(g.log_has("RANDO-ERROR RANDO-KIT delete from the scripts folder: dev(spawnprobe).lua (10.0.18)"),
                        [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.note_has("delete the old developer file(s)"))
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.35"))   # the release itself is whole

    def test_the_dll_is_unchanged_v7(self):
        import hashlib
        dll = (MOD / "rando_give.dll").read_bytes()
        self.assertEqual(hashlib.sha256(dll).hexdigest(), "8055703e7dd7f48e16aa5a081d6795c15d515a52802bd0d70aafe88b54640744")


if __name__ == "__main__":
    unittest.main()
