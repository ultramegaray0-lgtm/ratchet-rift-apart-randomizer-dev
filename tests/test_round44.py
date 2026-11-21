"""Round44: dev 10.33 (kit 10.0.22) in the real game (tests/data/round44_rivet.log; Zurkon arena A1, C5, B3, then
Cordelion), and the 10.33 mechanisms in the simulator.

  * Round44LogTests: what the REAL GAME showed (parsed, nothing simulated). This is the in-game evidence the v0.60
    public release ships the Enemy Randomizer on.
  * SimulatorTests: the production engine on synthetic memory (the test_v1029 / test_v1030 harness). Not in-game
    verification: the simulator cannot tell whether an enemy can be killed.
"""
import os
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from test_v1030 import vsim, kill, fast_watch  # noqa: E402

LOG44 = ROOT / "tests" / "data" / "round44_rivet.log"


class Round44LogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.T = LOG44.read_text(encoding="utf-8", errors="replace")
        cls.L = cls.T.splitlines()

    def test_it_is_dev_10_33_and_the_kit_is_whole(self):
        self.assertIn("RANDO-KIT release dev 10.33 (kit 10.0.22)", self.T)
        self.assertIn("RANDO-KIT all 12 required scripts are 10.0.22", self.T)
        self.assertNotIn("RANDO-ERROR", self.T)
        self.assertNotIn("Users\\", self.T)                                   # the game path was replaced

    def test_the_three_arena_challenges_were_randomized(self):
        spawns = [l for l in self.L if "ENEMY SPAWNS on this level:" in l]
        got = [tuple(int(x) for x in re.search(r"on this level: (\d+), replaced (\d+)", l).groups()) for l in spawns]
        self.assertIn((71, 61), got)                                           # A1
        self.assertIn((16, 12), got)                                           # C5
        self.assertIn((45, 19), got)                                           # B3

    def test_no_replaced_enemy_was_left_alive(self):
        combat = [l for l in self.L if "\tCOMBAT factory|" in l and "replaced bots spawned" in l]
        self.assertGreaterEqual(len(combat), 8)
        spawned = died = gone = 0
        for l in combat:
            m = re.search(r"replaced bots spawned (\d+), died (\d+), gone (\d+), alive at the end (\d+)", l)
            self.assertEqual(m.group(4), "0", l)
            spawned += int(m.group(1)); died += int(m.group(2)); gone += int(m.group(3))
        self.assertEqual((spawned, died, gone), (92, 64, 28))
        self.assertFalse([l for l in self.L if "COMBAT CHECK FAILED" in l])

    def test_10_33_kills_without_death_events_verified_b3s_pairs(self):
        # B3: the jetpacks and bikers never sent BotDeathCompleteEvent; "gone soon after the spawn" proved them
        self.assertGreaterEqual(sum(1 for l in self.L if "killed: gone" in l), 19)
        self.assertIn("COMBAT VERIFIED factory|enm_thugs4less_bike/flyer>enm_thugs4less_shoo/flyer", self.T)
        self.assertIn("COMBAT VERIFIED factory|enm_thugs4less_shoo/flyer>enm_thugs4less_bike/flyer", self.T)

    def test_10_33_never_used_the_robot_shooter_as_a_replacement(self):
        self.assertFalse([l for l in self.L if re.search(r"CHANGED factory .*-> enm_pirate_robot_sh", l)])
        self.assertTrue([l for l in self.L if "every replacement here is rejected (could not be killed in your game)" in l])

    def test_10_33_late_changes_stayed_armed(self):
        self.assertIn("late change - the factory still makes the enemies it queued before; the change stays for its next run", self.T)
        self.assertNotIn("the game ignored the change", self.T)

    def test_cordelion_is_still_unchanged(self):
        # the known limitation v0.60 ships with (KNOWN_ISSUES): the built-in registry planned amoeboids / puffoids,
        # but every spawn came before the randomizer had read its factory
        i = next(n for n, l in enumerate(self.L) if "level summary (planet Cordelion)" in l)
        later = "\n".join(self.L[i:])
        self.assertIn("enm_amoeboid_small_ps4", later)
        self.assertFalse(re.search(r"SPAWN \d+ \| cordelion .*\| SUCCESS", later))


class SimulatorTests(unittest.TestCase):
    """SYNTHETIC memory; the production engine (kit 10.0.23)"""

    def test_the_robot_shooter_is_never_a_replacement(self):
        # thug shooters and robot shooters are both GameBotShooter (the pair round40-43 could not kill)
        s = vsim(self, [(8001, 9204), (8002, 9201), (8003, 9202), (8004, 9204), (8005, 9204), (8006, 9203)],
                 mode="all", ban=True)
        s.spawn(8001); s.spawn(8002); s.spawn(8003); s.spawn(8006)
        s.g.step(200)
        picks = [s.var(20 + i) for i in range(6)]
        self.assertEqual([p for i, p in enumerate(picks) if p == 9201 and i != 1], [], s.ev()[-6:])
        self.assertTrue(s.g.lua.eval('RANDO_SPAWNERS.V.rep_ban({ name = "enm_pirate_robot_sh", family = "ground" }) ~= nil'))

    def test_a_kind_rejected_for_two_originals_is_banned_for_the_save(self):
        g = Game(settings={"enemy_randomizer": True})
        V = "RANDO_SPAWNERS.V"
        g.lua.execute(V + '.note_rep_failure("factory|enm_a/ground>enm_x/ground")')
        self.assertIsNone(g.lua.eval(V + '.rep_ban({ name = "enm_x", family = "ground" })'))
        g.lua.execute(V + '.note_rep_failure("factory|enm_a/ground>enm_x/ground")')       # the same original again
        self.assertIsNone(g.lua.eval(V + '.rep_ban({ name = "enm_x", family = "ground" })'))
        g.lua.execute(V + '.note_rep_failure("factory|enm_b/ground>enm_x/ground")')
        self.assertIsNotNone(g.lua.eval(V + '.rep_ban({ name = "enm_x", family = "ground" })'))
        self.assertTrue(g.log_has("REPLACEMENT BANNED enm_x/ground"))

    def test_a_replaced_bot_gone_soon_after_its_spawn_counts_as_killed(self):
        s = vsim(self, [(8001, 9201), (8002, 9202), (8003, 9201)], mode="all")
        fast_watch(s)
        s.spawn(8001); s.spawn(8002); s.spawn(8003)
        h = s.next_h
        s.g.lua.execute("PF.classes[%d] = nil; PF.names[%d] = nil" % (h, h))
        for k in range(3):
            kill(s, 60001 + k)
        s.g.step(130)
        self.assertTrue(s.has("killed: gone"), s.ev()[-4:])
        self.assertFalse(s.has("COMBAT CHECK FAILED"))

    def test_the_built_in_registry_knows_the_logged_kinds_on_a_new_save(self):
        g = Game(settings={"enemy_randomizer": True})
        V = "RANDO_SPAWNERS.V"
        self.assertEqual(g.lua.eval("(function() local n = 0 for _ in pairs(%s.REG_BUILTIN) do n = n + 1 end return n end)()" % V) >= 17, True)   # 10.33: 17; DEV3: +112; DEV5: +53 (round45 harvest)
        self.assertEqual(g.lua.eval(V + '.reg_get("D5C79D3A26DF1EB9").name'), "enm_amoeboid_small_ps4")
        self.assertEqual(g.lua.eval(V + '.reg_get("A49ABC9129557DC6").name'), "enm_indigenous_puffoid")


if __name__ == "__main__":
    unittest.main()
