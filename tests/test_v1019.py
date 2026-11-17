"""Dev 10.19 (kit 10.0.14), asked for: "no enemy/boss randomized" (rivet.log of 2026-11-17 with dev 10.18,
kept as tests/data/round29_rivet.log).

What that log shows (its dumps, six nodes alike): a SpawnerScriptAction node is 128 bytes, its ddlPriusData
(+0x08) is 0, and +0x60 holds the handle of the component made right after the node (0x406E8E -> 0x406E8F,
0x406E90 -> 0x406E91 ...). The game's type data has that component: "Spawner" (rivet.hash 4233548849 = the
component id of SpawnerPrius, which SpawnerScriptActionPrius extends). Spawn events are sent by the spawned
bot itself (sender == SpawnedHandle), so only the spawn point ties a spawn to its node. The whole-level
"Spawner" component scan ran past the frame budget.

10.19 asks the node's own actor for its Spawner component, uses it only when its handle is the one at +0x60,
and finds that component's Prius (rivet's prius, ddlPriusData, or lists copied into its instance).
ALL IN THE SIMULATOR (modelled on the dumps); nothing of 10.19 has run in the game.
"""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game as _HarnessGame  # noqa: E402


def Game(*args, **kw):
    """dev 10.27: these tests cover the old census / Prius route (the code the Boss and Chaos Randomizers still use);
    enemy.lua takes it only with enemy_route = "census" (its default is the variable route, tests/test_v1027.py)"""
    st = dict(kw.pop("settings", None) or {})
    st.setdefault("enemy_route", "census")
    return _HarnessGame(*args, settings=st, **kw)
from luajson import py  # noqa: E402
from test_v1012 import LEVEL, ENEMY_SLOTS, BOSS_SLOTS, G1, G2, build_level, changed, original, play  # noqa: E402

ALLOWED_ENEMY = ENEMY_SLOTS | {("enc_unknown", 1), ("enc_hb", 1)}     # see test_v1018


def comp(mode):
    return {uid: {"comp": mode} for uid in LEVEL}


def game(extra, enemy=None, boss=None, chaos=None, level=None, steps=300):
    g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False})
    assert not g.load_errors, g.load_errors
    build_level(g, level, extra)
    g.companion_restore()
    for name, v in (("enemy", enemy), ("boss", boss), ("chaos", chaos)):
        if v is not None:
            g.g.RANDO_SPAWNERS.set(name, v, "test")
    g.travel("NefCity")
    g.step(steps)
    return g


def census(g):
    return [l for l in g.logs() if "RANDO-SPAWNERS\tcensus " in l][-1]


def errors(g):
    return [l for l in g.logs() if "RANDO-ERROR" in l]


class TheLogTests(unittest.TestCase):
    def test_the_dumped_node_is_what_the_simulator_builds(self):
        text = (ROOT / "tests" / "data" / "round29_rivet.log").read_text(encoding="utf-8")
        dump = next(l for l in text.splitlines() if "RANDO-SPAWNERS\tdump 8129e049adf415a5" in l)
        b = bytes.fromhex(dump.split(": ", 1)[1].replace(" ", ""))
        self.assertEqual(len(b), 128)
        self.assertEqual(int.from_bytes(b[8:16], "little"), 0)                      # ddlPriusData
        own = int.from_bytes(b[0x1C:0x20], "little")
        self.assertEqual(int.from_bytes(b[0x60:0x64], "little"), own + 1)           # the Spawner component
        self.assertEqual(int.from_bytes(b[0x48:0x50], "little"), 0x8129E049ADF415A5)
        spawn = next(l for l in text.splitlines() if "RANDO-SPAWNERS\tspawn: sender" in l)
        sender = spawn.split("sender ")[1].split(" ")[0]
        self.assertIn("spawned " + sender, spawn)                                    # sent by the bot itself
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False})
        build_level(g, {"enc_a": ([G1], 1, "O")}, {"enc_a": {"comp": "prius"}})
        node = g.sim.nodes[1]
        self.assertEqual(node.size, 128)
        self.assertIsNone(node.prius)


class SpawnerComponentTests(unittest.TestCase):
    def check_all(self, mode, route):
        g = game(comp(mode), enemy=True)
        line = census(g)
        self.assertIn("%d spawner node(s) read" % len(LEVEL), line, (mode, line))
        self.assertIn("0 skipped", line)
        self.assertIn("layout prius/spawner/%s" % route, line)
        ch = changed(g)
        self.assertTrue(ch, mode)
        self.assertTrue(ch <= ALLOWED_ENEMY, ch - ALLOWED_ENEMY)
        for uid in LEVEL:
            play(g, uid)
            self.assertEqual(g.sim.completions[uid], 1, (mode, uid))
        verify = [l for l in g.logs() if "RANDO-SPAWNERS\tverify " in l]
        self.assertTrue(any("TOOK EFFECT" in l for l in verify), verify)
        self.assertFalse(any("DID NOT" in l for l in verify), verify)
        self.assertFalse(errors(g), errors(g))
        return g

    def test_rivet_gives_the_spawner_components_prius(self):
        self.check_all("prius", "rivet")

    def test_only_through_ddlPriusData(self):
        self.check_all("holder", "holder")

    def test_lists_copied_into_the_component(self):
        self.check_all("inline", "inline")

    def test_boss_and_chaos(self):
        g = game(comp("prius"), boss=True)
        ch = changed(g)
        self.assertTrue(ch and ch <= BOSS_SLOTS, ch)
        g = game(comp("prius"), chaos=True)
        self.assertEqual(changed(g), set(original()) - {("enc_friend", 1)})

    def test_spawns_are_matched_by_their_spawn_point(self):
        g = game(comp("prius"), enemy=True)
        play(g, "enc_c")
        lines = [l for l in g.logs() if "RANDO-SPAWNERS\tspawn: " in l]
        self.assertTrue(lines)
        self.assertTrue(all("-> node " in l for l in lines), lines)

    def test_stop_events_name_the_spawner_component(self):
        g = game(comp("prius"), enemy=True)
        play(g, "enc_c")
        rec = g.g.RANDO_SPAWNERS.level.nodes["enc_c"]
        self.assertIsNotNone(rec.stopped)

    def test_a_component_on_another_actor_is_named(self):
        g = game(comp("elsewhere"), enemy=True)
        self.assertEqual(changed(g), set())
        self.assertTrue(g.log_has("is not on the node's actor"))
        self.assertTrue(g.log_has("its components: SpawnerScriptAction"))

    def test_no_level_wide_component_scan(self):
        g = game(comp("prius"), enemy=True)
        self.assertFalse(g.log_has("Spawner components not listed"))
        self.assertFalse(g.g.RANDO_SPAWNERS.SCAN_SPAWNER_COMPONENTS)

    def test_learning_from_spawns_without_template_actors(self):
        level = {"enc_g2": ([G2], 1, "O1"), "enc_g1": ([G1], 1, "O2"), "enc_next": ([G1], 1, "O3")}
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False})
        g.sim.templates_unhatched = True
        build_level(g, level, {u: {"comp": "prius"} for u in level})
        g.companion_restore()
        g.travel("NefCity")
        g.step(300)
        self.assertEqual(g.sim.encounter_template("enc_next", 1), G1)
        play(g, "enc_g2")
        play(g, "enc_g1")
        g.step(120)
        self.assertEqual(g.sim.encounter_template("enc_next", 1), G2)


class FrameBudgetTests(unittest.TestCase):
    def test_a_node_stopped_by_the_budget_is_read_again_without_a_restart(self):
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False})
        build_level(g, None, comp("prius"))
        g.companion_restore()
        g.lua.execute("""
          local real, n = RANDO_SPAWNERS.read_node, 0
          RANDO_SPAWNERS.read_node = function(node)
            n = n + 1
            if n == 3 or n == 7 then error("ran past the 8 ms frame budget") end
            return real(node)
          end""")
        g.travel("NefCity")
        g.step(300)
        self.assertIn("%d spawner node(s) read" % len(LEVEL), census(g))
        self.assertFalse(g.log_has("census interrupted by the frame budget"))
        self.assertTrue(changed(g))


if __name__ == "__main__":
    unittest.main()
