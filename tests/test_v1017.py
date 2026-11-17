"""Dev 10.17 (kit 10.0.12), asked for: "enemy, boss and chaos randomizer didn't work. Fix it" (rivet.log of
2026-11-17, kit 10.0.11 / dev 10.15 with 10.16's defaults).

What that log shows: 32 censuses, every one "0 spawner node(s) read, 0 template(s), N skipped", every node
"cannot read the node". rivet_hook's rivet.component gives `size` = the class's instance size and `prius` =
the component's Prius data (Component.ddlPriusData -> holder -> data, rivet_hook src/scripting.cpp
find_component / l_component). 10.12-10.16 read only min(0x100, size) bytes of the INSTANCE and needed 0x88:
nothing was read, nothing learned, nothing changed, by any of the three randomizers.

The fix and what these tests show (ALL IN THE SIMULATOR, modelled on that log; nothing has run in the game):
  * the census reads the Prius at the DDL's own offsets (FactoryGroup +8) when rivet gives one;
  * a node with a small instance and no Prius is skipped with its real reason (the old failure, named);
  * SpawnerSpawnEvent in the real game has SpawnFactory / SpawnIndex / SpawnLocation / SpawnedHandle and no
    SenderHandle field: the spawn's node is found by ev.sender, else by the SpawnLocation's actor id in one
    node's SpawnLocations list, so templates are learned while playing;
  * the Enemy, Boss and Chaos Randomizers change slots and encounters still complete once;
  * a census stopped by rivet_hook's frame budget starts again (10.16 dropped it until the next load);
  * a spawned actor is classified with one rivet.components call; unknown bot classes are logged once.
"""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402
from luajson import py  # noqa: E402
from test_v1012 import (LEVEL, LEARNED, ENEMY_SLOTS, BOSS_SLOTS, NEVER, G1, G2, F1, CLASS,  # noqa: E402
                        build_level, changed, original, play, slots)

REAL = {uid: {"prius": True} for uid in LEVEL}                 # every node as the real game has it
REAL_NOSENDER = {uid: {"prius": True, "nosender": True} for uid in LEVEL}
SMALL = {uid: {"small": True} for uid in LEVEL}               # the 10.16 read path: small instance, no Prius


def game(learned=True, enemy=None, boss=None, chaos=None, extra=None, level=None, settings=None, before=None):
    st = {"enemy_randomizer": False, "boss_randomizer": False, **(settings or {})}
    g = Game(settings=st)
    assert not g.load_errors, g.load_errors
    build_level(g, level, extra if extra is not None else REAL)
    g.companion_restore()
    if learned:
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
    for name, v in (("enemy", enemy), ("boss", boss), ("chaos", chaos)):
        if v is not None:
            g.g.RANDO_SPAWNERS.set(name, v, "test")
    if before:
        before(g)
    g.travel("NefCity")
    g.step(300)
    return g


def census_lines(g):
    return [l for l in g.logs() if "RANDO-SPAWNERS\tcensus " in l]


class TheLogsFailureTests(unittest.TestCase):
    def test_the_10_16_read_path_fails_like_the_log_and_says_why(self):
        g = game(enemy=True, extra=SMALL)
        lines = census_lines(g)
        self.assertTrue(lines)
        self.assertIn("0 spawner node(s) read", lines[-1])
        # dev 10.18: every route is named, and the bytes are dumped for the next log
        self.assertTrue(any("rivet: no prius; holder: ddlPriusData is 0000000000000000" in l for l in g.logs()),
                        [l for l in g.logs() if "skipped" in l][:3])
        self.assertTrue(any("RANDO-SPAWNERS\tdump enc_" in l for l in g.logs()))
        self.assertEqual(changed(g), set())

    def test_the_prius_is_read_and_every_node_found(self):
        g = game(enemy=True)
        line = census_lines(g)[-1]
        self.assertIn("%d spawner node(s) read" % len(LEVEL), line)
        self.assertIn("0 skipped", line)
        self.assertIn("layout prius/rivet +0x8 x%d" % len(LEVEL), line)
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])


class TheThreeRandomizersWorkTests(unittest.TestCase):
    def test_enemy_randomizer_changes_regular_enemies_and_encounters_complete(self):
        g = game(enemy=True)
        ch = changed(g)
        self.assertTrue(ch, "nothing changed")
        self.assertTrue(ch <= ENEMY_SLOTS, ch - ENEMY_SLOTS)
        self.assertFalse(ch & NEVER)
        for uid in LEVEL:
            play(g, uid)
            self.assertEqual(g.sim.completions[uid], 1, uid)

    def test_boss_randomizer_changes_boss_tier_only(self):
        g = game(boss=True)
        ch = changed(g)
        self.assertTrue(ch)
        self.assertTrue(ch <= BOSS_SLOTS, ch - BOSS_SLOTS)

    def test_chaos_changes_every_category(self):
        g = game(chaos=True)
        ch = changed(g)
        self.assertEqual(ch, set(original()) - {("enc_friend", 1)})
        for uid in LEVEL:
            play(g, uid)
            self.assertEqual(g.sim.completions[uid], 1, uid)

    def test_switching_off_puts_everything_back(self):
        g = game(enemy=True, boss=True)
        self.assertTrue(changed(g))
        g.press("-")
        g.press("=")
        g.step(60)
        self.assertEqual(changed(g), set())


class LearningWithTheRealEventTests(unittest.TestCase):
    def _learns(self, extra):
        g = game(learned=False, enemy=True, extra=extra)
        self.assertEqual(changed(g), set())
        for uid in ("enc_a", "enc_b", "enc_c"):
            play(g, uid)
        g.step(120)
        learned = py(g.state.spawn_learned) or {}
        self.assertEqual(learned.get(G1), "ground")
        self.assertEqual(learned.get(F1), "flyer")
        self.assertNotIn(G2, learned)                     # enc_a mixes G1 and G2: a spawn of it teaches nothing
        return g

    def test_learning_from_the_event_sender(self):
        self._learns(REAL)

    def test_learning_from_the_spawn_location_when_there_is_no_sender(self):
        self._learns(REAL_NOSENDER)
        # and what is learned is used: a second ground type makes a pool of two for the idle encounter
        level = {"enc_g2": ([G2], 1, "O1"), "enc_g1": ([G1], 1, "O2"), "enc_next": ([G1], 1, "O3")}
        g = game(learned=False, enemy=True, level=level, extra={u: {"prius": True, "nosender": True} for u in level})
        play(g, "enc_g2")
        play(g, "enc_g1")
        g.step(120)
        self.assertEqual(g.sim.encounter_template("enc_next", 1), G2)
        self.assertTrue(g.log_has("plan (learned while playing)"))

    def test_classification_uses_rivet_components_and_logs_unknown_classes(self):
        level = {"enc_x": (["8A00000000000001"], 1, "OBJ_X"), "enc_g": ([G1], 1, "OBJ_G")}

        def before(g):
            g.sim.template_class["8A00000000000001"] = "GameBotSomethingNew"
        g = game(learned=False, enemy=True, level=level, extra={u: {"prius": True} for u in level}, before=before)
        play(g, "enc_x")
        play(g, "enc_g")
        learned = py(g.state.spawn_learned) or {}
        self.assertEqual(learned.get(G1), "ground")
        self.assertNotIn("8A00000000000001", learned)
        self.assertTrue(g.log_has("spawned actor not classified (left alone):\tGameBotSomethingNew"))


class FrameBudgetTests(unittest.TestCase):
    def test_a_census_stopped_by_the_budget_starts_again(self):
        def before(g):
            g.lua.execute("""
              local real = rivet.script_nodes
              local n = 0
              rivet.script_nodes = function(...)
                n = n + 1
                if n == 1 then error("ran past the 8 ms frame budget") end
                return real(...)
              end""")
        g = game(enemy=True, before=before)
        g.step(120)
        self.assertTrue(g.log_has("census interrupted by the frame budget - reading again (1/5)"))
        self.assertIn("%d spawner node(s) read" % len(LEVEL), census_lines(g)[-1])
        self.assertTrue(changed(g))


if __name__ == "__main__":
    unittest.main()
