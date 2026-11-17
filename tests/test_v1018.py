"""Dev 10.18 (kit 10.0.13), asked for: "Still nothing randomized. Take your time, investigate and fix, and make
no mistake. Next try HAVE to work." (rivet.log of 2026-11-17, kit 10.0.12 / dev 10.17).

What that log shows: every census "0 spawner node(s) read", every node "no Prius and the instance is only 128
bytes". So rivet_hook gives no `prius` for SpawnerScriptAction, and the 128-byte instance is ScriptAction's
header (Component 0x48, uids, plugs +0x58; rivet_hook src/game/script.hpp) plus 32 bytes.

The fix, and what these tests show (ALL IN THE SIMULATOR; the simulator now models exactly what both logs
proved: 128-byte instance, no rivet prius, real SpawnerSpawnEvent fields, a fresh save with nothing learned):
  * the Prius is reached by hand: Component.ddlPriusData (+0x08) -> holder -> data (route "holder"), or a
    pointer among the node's own bytes (route "scan", only with ActionType 60 or a loaded actor's uid);
  * template ids are template actors' uids: their bot class is learned at once (rivet.find_uid +
    rivet.components), so the first level already randomizes - no fight needed first;
  * when template actors carry no bot class, spawns teach them (sender field, ev.sender or spawn point);
  * a spawner that spawned before the census read the level is never changed;
  * placed actors' Spawner components (SpawnerPrius) are read too;
  * a factory-only spawner (no Templates) is named, not dumped; a holder shared by several Priuses is never written;
  * each changed encounter's first spawn is checked: "verify ... TOOK EFFECT" / "DID NOT take effect";
  * when no route finds the Prius, the node's bytes are dumped to rivet.log.
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
from test_v1012 import (LEVEL, LEARNED, ENEMY_SLOTS, BOSS_SLOTS, NEVER, G1, G2, G3, F1, F2, B1, STORY, FRIEND,  # noqa: E402
                        build_level, changed, original, play, slots)

HOLDER = {uid: {"holder": True} for uid in LEVEL}                      # what your game has (both logs)
HOLDER_SENDER = {uid: {"holder": True, "sender_field": "component"} for uid in LEVEL}
PTR = {uid: {"ptr": True} for uid in LEVEL}


def game(learned=False, enemy=None, boss=None, chaos=None, extra=None, level=None, settings=None, before=None,
         steps=300):
    st = {"enemy_randomizer": False, "boss_randomizer": False, **(settings or {})}
    g = Game(settings=st)
    assert not g.load_errors, g.load_errors
    build_level(g, level, extra if extra is not None else HOLDER)
    g.companion_restore()
    if learned:
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
    for name, v in (("enemy", enemy), ("boss", boss), ("chaos", chaos)):
        if v is not None:
            g.g.RANDO_SPAWNERS.set(name, v, "test")
    if before:
        before(g)
    g.travel("NefCity")
    g.step(steps)
    return g


def census(g):
    return [l for l in g.logs() if "RANDO-SPAWNERS\tcensus " in l][-1]


def errors(g):
    return [l for l in g.logs() if "RANDO-ERROR" in l]


class TheRealLogsTests(unittest.TestCase):
    """the facts of your two logs that 10.18 is built on (tests/data/round27_rivet.log, round28_rivet.log)"""

    def test_the_simulated_node_is_what_the_log_reports(self):
        text = (ROOT / "tests" / "data" / "round28_rivet.log").read_text(encoding="utf-8")
        skips = [l for l in text.splitlines() if "RANDO-SPAWNERS\t  skipped" in l]
        self.assertTrue(skips)
        self.assertTrue(all("no Prius and the instance is only 128 bytes" in l for l in skips))
        spawn = next(l for l in text.splitlines() if "SpawnerSpawnEvent" in l)
        for field in ("SpawnFactory=", "SpawnIndex=", "SpawnLocation=", "SpawnedHandle="):
            self.assertIn(field, spawn)
        g = Game(settings={"enemy_randomizer": False, "boss_randomizer": False})
        build_level(g, {"enc_a": ([G1], 1, "O")}, {"enc_a": {"holder": True}})
        node = g.sim.nodes[1]
        self.assertEqual(node.size, 128)
        self.assertIsNone(node.prius)
        old = (ROOT / "tests" / "data" / "round27_rivet.log").read_text(encoding="utf-8")
        self.assertIn("cannot read the node", old)


class YourGamesLayoutTests(unittest.TestCase):
    """the save of your log: Enemy/Boss ON, nothing learned yet, 128-byte nodes, no rivet prius"""

    def test_every_node_is_read_through_ddlPriusData(self):
        g = game(enemy=True)
        line = census(g)
        self.assertIn("%d spawner node(s) read" % len(LEVEL), line)
        self.assertIn("0 skipped", line)
        self.assertIn("layout prius/holder +0x8 x%d" % len(LEVEL), line)
        self.assertTrue(g.log_has("Prius routes (census 1): holder x%d" % len(LEVEL)))
        self.assertFalse(errors(g), errors(g))
        self.assertFalse(g.log_has("RANDO-SPAWNERS\tdump"))

    def test_templates_are_learned_from_their_template_actors_before_any_fight(self):
        g = game(enemy=True)
        learned = py(g.state.spawn_learned) or {}
        for tid in (G1, G2, G3, F1, F2, B1):
            self.assertIn(tid, learned, tid)
        self.assertEqual(learned[STORY], "story_boss")
        self.assertEqual(learned[FRIEND], "friendly")
        self.assertTrue(g.log_has("(template actor GameBotShooter)"))

    def test_enemy_randomizer_changes_the_first_level_at_once_and_everything_completes(self):
        g = game(enemy=True)
        ch = changed(g)
        self.assertTrue(ch, "nothing changed")
        # with template actors, UNKNOWN (never spawned in 10.12's test) is a known ground bot, and HB's boss
        # health bar is only learned when it shows: until then both are regular enemies
        allowed = ENEMY_SLOTS | {("enc_unknown", 1), ("enc_hb", 1)}
        self.assertTrue(ch <= allowed, ch - allowed)
        self.assertFalse(ch & {("enc_story", 1), ("enc_friend", 1), ("enc_turret", 1)})
        for uid in LEVEL:
            play(g, uid)
            self.assertEqual(g.sim.completions[uid], 1, uid)
        self.assertFalse(errors(g), errors(g))

    def test_the_first_spawn_of_a_changed_encounter_is_verified(self):
        g = game(enemy=True)
        for uid in LEVEL:
            play(g, uid)
        lines = [l for l in g.logs() if "RANDO-SPAWNERS\tverify " in l]
        self.assertTrue(lines)
        self.assertTrue(any("TOOK EFFECT" in l for l in lines), lines)
        self.assertFalse(any("DID NOT" in l for l in lines), lines)

    def test_boss_randomizer(self):
        g = game(boss=True)
        ch = changed(g)
        self.assertTrue(ch)
        self.assertTrue(ch <= BOSS_SLOTS, ch - BOSS_SLOTS)

    def test_chaos_randomizer(self):
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

    def test_explicitly_off_reads_and_writes_nothing(self):
        g = game()
        self.assertEqual(changed(g), set())
        self.assertFalse(g.log_has("RANDO-SPAWNERS\tcensus"))


class OtherLayoutsTests(unittest.TestCase):
    def test_a_pointer_among_the_nodes_own_bytes(self):
        g = game(enemy=True, extra=PTR)
        self.assertIn("layout prius/scan +0x8 x%d" % len(LEVEL), census(g))
        self.assertTrue(changed(g))

    def test_a_runtime_object_holding_the_fields_or_pointing_at_them(self):
        for mode, label in (("embed", "deep"), ("ptr", "deep")):
            g = game(enemy=True, extra={uid: {"deep": mode} for uid in LEVEL})
            line = census(g)
            self.assertIn("%d spawner node(s) read" % len(LEVEL), line, mode)
            self.assertIn("layout prius/%s" % label, line, mode)
            self.assertTrue(changed(g), mode)
            for uid in LEVEL:
                play(g, uid)
                self.assertEqual(g.sim.completions[uid], 1, (mode, uid))
            self.assertFalse(errors(g), errors(g))

    def test_template_actors_without_components_learn_from_spawns(self):
        def before(g):
            g.sim.templates_unhatched = True
        level = {"enc_g2": ([G2], 1, "O1"), "enc_g1": ([G1], 1, "O2"), "enc_next": ([G1], 1, "O3")}
        for sender in (None, "component", "actor"):
            extra = {u: {"holder": True, "sender_field": sender} for u in level}
            g = game(enemy=True, level=level, extra=extra, before=before)
            self.assertEqual(g.sim.encounter_template("enc_next", 1), G1)          # nothing known yet
            play(g, "enc_g2")
            play(g, "enc_g1")
            g.step(120)
            self.assertEqual(g.sim.encounter_template("enc_next", 1), G2, sender)
            self.assertTrue(g.log_has("plan (learned while playing)"))

    def test_a_spawner_already_running_before_the_census_is_never_changed(self):
        level = {"enc_early": ([G1], 2, "O1"), "enc_g2": ([G2], 1, "O2"), "enc_late": ([G1], 1, "O3")}
        extra = {u: {"holder": True, "planet": "NefCity"} for u in level}     # listed once the planet is loaded
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": False})
        build_level(g, level, extra)
        g.companion_restore()
        g.travel("NefCity")
        g.step(5)
        g.sim.start_encounter("enc_early")          # spawns at the load, before the census reads the level
        self.assertIsNone(g.g.RANDO_SPAWNERS.level)    # not read yet
        g.step(300)
        self.assertIn("3 spawner node(s) read", census(g))
        self.assertEqual(g.sim.encounter_template("enc_early", 1), G1)
        self.assertEqual(g.sim.encounter_template("enc_late", 1), G2)

    def test_placed_spawner_components_are_read(self):
        level = {"sp_a": ([G1], 1, "O1"), "sp_b": ([G2], 1, "O2"), "sp_c": ([G3], 1, "O3")}
        extra = {u: {"spawner_component": True} for u in level}

        def scan_on(g):                         # dev 10.19: off by default (it ran past the budget in your game)
            g.g.RANDO_SPAWNERS.SCAN_SPAWNER_COMPONENTS = True
        g = game(enemy=True, level=level, extra=extra, before=scan_on)
        self.assertTrue(g.log_has("; 3 Spawner component(s)"))
        self.assertIn("3 spawner node(s) read", census(g))
        moved = [u for u in level if g.sim.encounter_template(u, 1) != level[u][0][0]]
        self.assertTrue(moved)
        for u in level:
            play(g, u)
            self.assertEqual(g.sim.completions[u], 1)

    def test_factory_only_spawner_is_named_and_not_dumped(self):
        level = {"enc_fac": ([], 1, "O1"), "enc_g1": ([G1], 1, "O2"), "enc_g2": ([G2], 1, "O3")}
        g = game(enemy=True, level=level, extra={u: {"holder": True} for u in level})
        self.assertTrue(g.log_has("factory-only spawner (no Templates)"))
        self.assertFalse(g.log_has("RANDO-SPAWNERS\tdump"))
        self.assertIn("2 spawner node(s) read", census(g))

    def test_a_holder_count_above_one_is_only_noted(self):
        extra = {uid: {"holder": True, "holder_count": 3} for uid in LEVEL}
        g = game(enemy=True, extra=extra)
        self.assertTrue(changed(g))
        self.assertTrue(g.log_has("%d holder(s) with a count other than 1" % len(LEVEL)))

    def test_two_nodes_reaching_the_same_prius_are_never_written(self):
        level = {"enc_a": ([G1], 1, "O1"), "enc_b": ([G1], 1, "O2"), "enc_c": ([G2], 1, "O3")}
        extra = {"enc_a": {"holder": True}, "enc_b": {"holder": True, "same_prius_as": "enc_a"}, "enc_c": {"holder": True}}
        g = game(chaos=True, level=level, extra=extra)
        self.assertEqual(g.sim.encounter_template("enc_a", 1), G1)      # enc_a's list is enc_b's too
        self.assertNotEqual(g.sim.encounter_template("enc_c", 1), G2)

    def test_nothing_found_dumps_the_bytes(self):
        extra = {uid: {"small": True} for uid in LEVEL}
        g = game(enemy=True, extra=extra)
        dumps = [l for l in g.logs() if "RANDO-SPAWNERS\tdump " in l]
        self.assertTrue(dumps)
        self.assertLessEqual(len([l for l in dumps if "instance at" in l]), 6)
        self.assertEqual(changed(g), set())


if __name__ == "__main__":
    unittest.main()
