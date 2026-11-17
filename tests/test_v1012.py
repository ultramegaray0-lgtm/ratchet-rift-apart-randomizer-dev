"""Dev 10.12 (kit 10.0.8), asked for: an Enemy Randomizer (enemy.lua) and a Boss Randomizer (boss.lua),
separate and independently switchable in the game (ON by default in the dev kit, remembered by the save), and
above all: randomized enemies and bosses must still open doors, finish objectives and advance the story.

These tests run the real scripts against tests/sim/rivet_sim.lua. The encounter model there (a
SpawnerScriptAction node that reads its Templates list from memory at each spawn, counts its dead and
fires its "all dead" output) is SIMULATED from the rivet DDL: none of it has been seen in the real game.
What they show is that the randomizer's own decisions are right under that model:
  * when explicitly OFF; off = not one byte of a spawner read or written;
  * only template ids change; the encounter node still spawns, counts and completes it once, after the
    last enemy, never earlier (multi-enemy encounters);
  * enemy and boss tiers never mix; story bosses, friendlies and unknown templates are never touched;
  * the boss randomizer permutes (no boss appears more often than before);
  * each switch changes only its own slots, at once; the save keeps the switches and what was learned;
  * the safety nets only ever put an encounter back (spawn timeout, retries, story boss areas);
  * the layout is found by its signature, a node that does not match is left alone;
  * removing either file (or the shared layer) breaks nothing else.
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

G1, G2, G3 = "8100000000000001", "8100000000000002", "8100000000000003"      # ground bots
F1, F2 = "8200000000000001", "8200000000000002"                              # flyers
T1 = "8300000000000001"                                                      # a turret (alone in its family)
B1, B2, B3 = "8400000000000001", "8400000000000002", "8400000000000003"      # large bots (boss tier)
HB = "8500000000000001"                                                      # a ground bot with a boss health bar
STORY = "8600000000000001"                                                   # a story boss
FRIEND = "8700000000000001"                                                  # a friendly bot
UNKNOWN = "8800000000000001"                                                 # never spawned: not learned

CLASS = {G1: "GameBotShooter", G2: "GameBotShooterExtermibot", G3: "GameBotMeleeBase",
         F1: "GameBotMeleeFlier", F2: "GameBotDarterBat", T1: "GameBotShooterTurret",
         B1: "GameBotGrunthor", B2: "GameBotMangler", B3: "GameBotTankBase", HB: "GameBotShooter",
         STORY: "BossBotZordoomMonster", FRIEND: "GameBotClankLemming", UNKNOWN: "GameBotShooter"}
LEARNED = {G1: "ground", G2: "ground", G3: "ground", F1: "flyer", F2: "flyer", T1: "turret",
           B1: "large", B2: "large", B3: "large", HB: "ground|hb", STORY: "story_boss", FRIEND: "friendly"}
GROUND, FLYERS, LARGE = {G1, G2, G3}, {F1, F2}, {B1, B2, B3}

# the level: encounter uid -> (templates, spawns (0 = each template once), objective)
LEVEL = {
    "enc_a": ([G1, G1, G2], 3, "OBJ_TEST_ARENA_A"),
    "enc_b": ([F1], 2, "OBJ_TEST_SKY"),
    "enc_sky2": ([F2], 1, "OBJ_TEST_SKY_2"),
    "enc_c": ([G1], 2, "OBJ_TEST_C"),
    "enc_boss1": ([B1], 1, "OBJ_TEST_BIG_1"),
    "enc_boss2": ([B2], 1, "OBJ_TEST_BIG_2"),
    "enc_boss3": ([B3], 1, "OBJ_TEST_BIG_3"),
    "enc_hb": ([HB], 1, "OBJ_TEST_ELITE"),
    "enc_mixed": ([G3, B2], 2, "OBJ_TEST_MIXED"),
    "enc_story": ([STORY], 1, "OBJ_TEST_STORY_BOSS"),
    "enc_friend": ([FRIEND], 1, None),
    "enc_turret": ([T1], 1, "OBJ_TEST_TURRET"),
    "enc_unknown": ([UNKNOWN], 1, "OBJ_TEST_UNKNOWN"),
}
ENEMY_SLOTS = {("enc_a", 1), ("enc_a", 2), ("enc_a", 3), ("enc_b", 1), ("enc_sky2", 1), ("enc_c", 1), ("enc_mixed", 1)}
BOSS_SLOTS = {("enc_boss1", 1), ("enc_boss2", 1), ("enc_boss3", 1), ("enc_mixed", 2)}
NEVER = {("enc_story", 1), ("enc_friend", 1), ("enc_turret", 1), ("enc_unknown", 1), ("enc_hb", 1)}


def build_level(g, level=None, extra=None):
    t = g.lua.table_from
    for uid, (tpls, num, obj) in sorted((level or LEVEL).items()):
        spec = {"uid": uid, "templates": t(tpls), "num": num, "mission": "MIS_TEST_ENCOUNTERS" if obj else None,
                "objective": obj}
        spec.update((extra or {}).get(uid, {}))
        g.sim.add_encounter(t({k: v for k, v in spec.items() if v is not None}))
    for tid, cls in CLASS.items():
        g.sim.template_class[tid] = cls
    g.sim.hb_templates[HB] = True


def game(learned=True, enemy=None, boss=None, level=None, extra=None, **kw):
    """a game with the test level, the companion's restore and a planet loaded; learned=True: the save
    already knows the templates (as after playing them once)"""
    kw["settings"] = {"enemy_randomizer": False, "boss_randomizer": False, **(kw.get("settings") or {})}
    g = Game(**kw)
    assert not g.load_errors, g.load_errors
    build_level(g, level, extra)
    g.companion_restore()
    if learned:
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
    if enemy is not None:
        g.g.RANDO_SPAWNERS.set("enemy", enemy, "test")
    if boss is not None:
        g.g.RANDO_SPAWNERS.set("boss", boss, "test")
    g.travel("NefCity")
    g.step(300)
    return g


def tpl(g, uid, k):
    return g.sim.encounter_template(uid, k)


def slots(g):
    return {(uid, k): tpl(g, uid, k) for uid, (tpls, _, _) in LEVEL.items() for k in range(1, len(tpls) + 1)}


def original():
    return {(uid, k): tpls[k - 1] for uid, (tpls, _, _) in LEVEL.items() for k in range(1, len(tpls) + 1)}


def changed(g):
    orig = original()
    return {s for s, v in slots(g).items() if v != orig[s]}


def alive(g, uid):
    return list(g.sim.alive_of(uid).values())


def play(g, uid):
    """start an encounter and kill everything it spawns; returns the classes that spawned"""
    g.sim.start_encounter(uid)
    classes = [g.sim.actor_class[h] for h in alive(g, uid)]
    g.sim.kill_all(uid)
    return classes


class ExplicitlyOffTests(unittest.TestCase):
    def test_dev_settings_enable_enemy_boss_and_omega_by_default(self):
        settings = (ROOT / "mod" / "RiftApartRandomizer" / "scripts" / "04_rando_settings.lua").read_text(encoding="utf-8")
        self.assertIn("omega_weapons = true", settings)
        self.assertIn("enemy_randomizer = true", settings)
        self.assertIn("boss_randomizer = true", settings)

    def test_explicitly_off_nothing_read_or_written(self):
        g = game(learned=True)
        self.assertFalse(g.g.RANDO.config.enemy_randomizer)
        self.assertFalse(g.g.RANDO.config.boss_randomizer)
        self.assertFalse(g.g.RANDO_SPAWNERS.any_enabled())
        g.step(600)
        self.assertEqual(changed(g), set())
        self.assertFalse(g.log_has("RANDO-SPAWNERS\tcensus"))
        self.assertIsNone(g.state.enemy_rando)
        self.assertIsNone(g.state.boss_rando)
        play(g, "enc_a")
        self.assertEqual(g.sim.completions["enc_a"], 1)
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])

    def test_the_kit_check_lists_them_as_optional(self):
        # dev 10.16 made them ON in 04; the harness runs the classic test settings, so ON is set here
        g = Game(settings={"enemy_randomizer": True, "boss_randomizer": True})
        g.step(2)
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.15"), [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.log_has("RANDO-ENEMY\tinstalled (ON"))
        self.assertTrue(g.log_has("RANDO-BOSS\tinstalled (ON"))

    def test_the_settings_only_decide_the_start(self):
        g = game(settings={"enemy_randomizer": True})
        self.assertTrue(g.g.RANDO_SPAWNERS.enabled("enemy"))
        self.assertFalse(g.g.RANDO_SPAWNERS.enabled("boss"))
        g.press("-")                                    # the key wins, and the save remembers it
        self.assertFalse(g.g.RANDO_SPAWNERS.enabled("enemy"))
        self.assertIs(g.state.enemy_rando, False)


class EnemyTests(unittest.TestCase):
    def test_key_turns_it_on_and_only_regular_enemies_change(self):
        g = game()
        g.press("-")
        self.assertTrue(g.note_has("Enemy Randomizer: ON"))
        self.assertIs(g.state.enemy_rando, True)
        self.assertIsNone(g.state.boss_rando)
        g.step(300)
        ch = changed(g)
        self.assertEqual(ch, ENEMY_SLOTS, ch)
        s = slots(g)
        for uid, k in ENEMY_SLOTS:
            fam = GROUND if original()[(uid, k)] in GROUND else FLYERS
            self.assertIn(s[(uid, k)], fam, (uid, k))      # same family, from this level
        for sl in BOSS_SLOTS | NEVER:
            self.assertEqual(s[sl], original()[sl], sl)

    def test_learning_while_playing(self):
        g = game(learned=False, enemy=True)
        g.step(200)
        self.assertEqual(changed(g), set())                # nothing is known yet: nothing changes
        for uid in ("enc_c", "enc_b"):                    # vanilla spawns teach G1, F1
            play(g, uid)
        g.step(120)
        learned = py(g.state.spawn_learned)
        self.assertEqual(learned.get(G1), "ground")
        self.assertEqual(learned.get(F1), "flyer")
        self.assertEqual(changed(g), set())                # one ground and one flyer: pools of one
        # a second ground type is seen in a level made of the same templates later: the pool grows
        g2 = game(learned=False, enemy=True, level={"enc_g2": ([G2], 1, "O1"), "enc_g1": ([G1], 1, "O2"),
                                                    "enc_next": ([G1], 1, "O3")})
        play(g2, "enc_g2")
        play(g2, "enc_g1")
        g2.step(120)
        self.assertEqual(g2.sim.encounter_template("enc_next", 1), G2)
        self.assertTrue(g2.log_has("plan (learned while playing)"))

    def test_progression_multi_enemy_encounter(self):
        g = game(enemy=True)
        self.assertTrue(changed(g) & {("enc_a", 1), ("enc_a", 2), ("enc_a", 3)})
        g.sim.start_encounter("enc_a")
        bots = alive(g, "enc_a")
        self.assertEqual(len(bots), 3)
        classes = {g.sim.actor_class[h] for h in bots}
        self.assertTrue(classes <= {CLASS[x] for x in GROUND}, classes)
        g.sim.kill("enc_a", bots[0])
        g.sim.kill("enc_a", bots[1])
        self.assertIsNone(g.sim.completions["enc_a"])      # two of three: the encounter is still running
        self.assertIsNone(g.sim.doors["enc_a"])
        g.sim.kill("enc_a", bots[2])
        self.assertEqual(g.sim.completions["enc_a"], 1)    # the node's own completion, once
        self.assertTrue(g.sim.doors["enc_a"])
        g.step(120)
        self.assertEqual(g.sim.completions["enc_a"], 1)    # and never again
        # the randomizer itself never wrote a mission or an objective
        self.assertEqual(list(g.sim.set_state_calls.values()), [])

    def test_every_encounter_completes(self):
        g = game(enemy=True, boss=True)
        for uid in sorted(LEVEL):
            play(g, uid)
            self.assertEqual(g.sim.completions[uid], 1, uid)

    def test_off_puts_everything_back_at_once(self):
        g = game(enemy=True)
        self.assertTrue(changed(g))
        g.press("-")
        self.assertTrue(g.note_has("Enemy Randomizer: OFF"))
        self.assertEqual(changed(g), set())
        g.step(600)
        self.assertEqual(changed(g), set())

    def test_off_in_the_middle_of_an_encounter(self):
        g = game(enemy=True, extra={"enc_c": {"num": 4}})
        orig_new = tpl(g, "enc_c", 1)
        self.assertNotEqual(orig_new, G1)
        g.sim.unspawnable[G1] = False
        g.sim.start_encounter("enc_c")                     # spawns 4 replacements at once in the simulator
        g.press("-")
        self.assertEqual(tpl(g, "enc_c", 1), G1)
        g.sim.kill_all("enc_c")
        self.assertEqual(g.sim.completions["enc_c"], 1)

    def test_running_encounters_are_never_changed(self):
        g = Game()
        build_level(g)
        g.companion_restore()
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
        g.travel("NefCity")
        g.sim.start_encounter("enc_c")                     # starts at the load, before the census
        g.g.RANDO_SPAWNERS.set("enemy", True, "test")
        g.step(300)
        self.assertEqual(tpl(g, "enc_c", 1), G1)
        self.assertIn(("enc_a", 1), changed(g))

    def test_picks_are_the_same_after_a_reload(self):
        g = game(enemy=True)
        before = slots(g)
        g.sim.reload_encounters("CHK_NEFCITY_START", True)    # the level makes its nodes anew
        self.assertEqual(changed(g), set())                    # authored templates again
        g.step(300)
        self.assertEqual(slots(g), before)
        g.sim.reload_encounters("CHK_NEFCITY_START", False)   # nodes kept: our write is still there
        g.step(300)
        self.assertEqual(slots(g), before)
        g.press("-")                                           # and its original is still known
        self.assertEqual(changed(g), set())


class BossTests(unittest.TestCase):
    def test_bosses_are_permuted_and_never_regular_enemies(self):
        g = game(boss=True)
        ch = changed(g)
        self.assertEqual(ch, {("enc_boss1", 1), ("enc_boss2", 1), ("enc_boss3", 1)} | (ch & {("enc_mixed", 2)}), ch)
        s = slots(g)
        bosses = [s[("enc_boss1", 1)], s[("enc_boss2", 1)], s[("enc_boss3", 1)]]
        self.assertEqual(sorted(bosses), sorted([B1, B2, B3]))      # a permutation: no boss twice
        self.assertEqual(s[("enc_mixed", 2)] in LARGE, True)
        for sl in ENEMY_SLOTS | NEVER:
            self.assertEqual(s[sl], original()[sl], sl)
        self.assertIsNone(g.state.enemy_rando)

    def test_boss_defeat_completes_the_encounter_once(self):
        g = game(boss=True)
        for uid in ("enc_boss1", "enc_boss2", "enc_boss3"):
            classes = play(g, uid)
            self.assertIn(classes[0], {CLASS[b] for b in LARGE})
            self.assertEqual(g.sim.completions[uid], 1)
            self.assertTrue(g.sim.doors[uid])

    def test_story_bosses_and_friendlies_are_never_touched(self):
        g = game(enemy=True, boss=True)
        for sl in NEVER:
            self.assertEqual(tpl(g, *sl), original()[sl], sl)
        self.assertEqual(len(py(g.g.RANDO_BOSS.STORY)), 8)

    def test_a_health_bar_makes_a_regular_bot_boss_tier(self):
        g = game(learned=False, enemy=True, level={"enc_hb": ([HB], 1, "O"), "enc_g": ([G1], 1, "O2"),
                                                   "enc_g2": ([G2], 1, "O3"), "enc_x": ([HB], 1, "O4")})
        play(g, "enc_hb")
        g.step(120)
        self.assertEqual(py(g.state.spawn_learned)[HB], "ground|hb")
        self.assertEqual(g.g.RANDO_SPAWNERS.role_of(HB)[0], "boss")
        play(g, "enc_g")
        play(g, "enc_g2")
        g.step(120)
        self.assertEqual(g.sim.encounter_template("enc_x", 1), HB)   # the enemy randomizer never uses or replaces it


class IndependenceTests(unittest.TestCase):
    def test_each_switch_changes_only_its_own(self):
        g = game(enemy=True, boss=True)
        self.assertEqual(changed(g) & ENEMY_SLOTS, ENEMY_SLOTS)
        boss_changed = changed(g) & BOSS_SLOTS
        self.assertTrue(boss_changed)
        g.press("-")                                         # enemies off
        self.assertEqual(changed(g) & ENEMY_SLOTS, set())
        self.assertEqual(changed(g) & BOSS_SLOTS, boss_changed)
        self.assertIs(g.state.boss_rando, True)
        g.press("-")                                         # enemies on again
        g.step(10)
        self.assertEqual(changed(g) & ENEMY_SLOTS, ENEMY_SLOTS)
        g.press("=")                                         # bosses off
        self.assertEqual(changed(g) & BOSS_SLOTS, set())
        self.assertEqual(changed(g) & ENEMY_SLOTS, ENEMY_SLOTS)
        self.assertIs(g.state.enemy_rando, True)

    def test_four_combinations(self):
        for enemy in (False, True):
            for boss in (False, True):
                g = game(enemy=enemy, boss=boss)
                ch = changed(g)
                self.assertEqual(bool(ch & ENEMY_SLOTS), enemy, (enemy, boss))
                self.assertEqual(bool(ch & BOSS_SLOTS), boss, (enemy, boss))
                self.assertEqual(ch & NEVER, set())
                for uid in sorted(LEVEL):
                    play(g, uid)
                    self.assertEqual(g.sim.completions[uid], 1, (uid, enemy, boss))

    def test_ctrl_key_shows_status(self):
        g = game(enemy=True)
        g.press("-", ctrl=True)
        self.assertTrue(g.note_has("Enemy Randomizer ON: 7 enemy slot(s) changed in 5 encounter(s) here"),
                        g.notes()[-3:])
        self.assertIs(g.state.enemy_rando, True)            # Ctrl only shows


class SaveTests(unittest.TestCase):
    def test_switches_and_learning_survive_save_and_new_game(self):
        g = game(learned=False, enemy=True)
        play(g, "enc_c")
        text = g.companion_export()
        g2 = Game()
        build_level(g2)
        g2.companion_restore(text)
        self.assertTrue(g2.g.RANDO_SPAWNERS.enabled("enemy"))
        self.assertFalse(g2.g.RANDO_SPAWNERS.enabled("boss"))
        self.assertEqual(py(g2.state.spawn_learned).get(G1), "ground")
        g2.travel("NefCity")
        g2.step(200)
        g2.sim.new_game()
        g2.step(200)
        self.assertTrue(g2.g.RANDO_SPAWNERS.enabled("enemy"))
        self.assertEqual(py(g2.state.spawn_learned).get(G1), "ground")

    def test_a_choice_made_before_the_restore_wins(self):
        g = game(enemy=True)
        text = g.companion_export()
        g2 = Game()
        g2.wait_seed()
        g2.g.RANDO_SPAWNERS.set("enemy", False, "test before the restore")   # nothing to toggle yet: no state
        g2.companion_restore(text)
        self.assertTrue(g2.g.RANDO_SPAWNERS.enabled("enemy"))
        g2.press("-")
        text2 = g2.companion_export()
        g3 = Game()
        g3.companion_restore(text2)
        self.assertFalse(g3.g.RANDO_SPAWNERS.enabled("enemy"))

    def test_reading_never_changes_the_save(self):
        g = game(learned=False)
        g.step(300)
        g.g.RANDO.status_text()
        g.press("-", ctrl=True)
        g.press("=", ctrl=True)
        text = g.companion_export()
        for key in ("spawn_learned", "spawn_blocked", "enemy_rando", "boss_rando"):
            self.assertNotIn('["' + key + '"]', text)


class SafetyNetTests(unittest.TestCase):
    def test_a_replacement_that_cannot_spawn_is_put_back(self):
        g = game(enemy=True)
        new = tpl(g, "enc_c", 1)
        self.assertNotEqual(new, G1)
        for t in GROUND - {G1}:
            g.sim.unspawnable[t] = True
        g.sim.start_encounter("enc_c")
        self.assertEqual(alive(g, "enc_c"), [])
        g.sim.encounter_tick(25)
        self.assertEqual(tpl(g, "enc_c", 1), G1)                   # put back
        self.assertIn("enc_c", py(g.state.spawn_blocked))
        self.assertTrue(g.log_has("spawned nothing for 20 s"))
        self.assertEqual(len(alive(g, "enc_c")), 2)          # the node spawns its originals
        g.sim.kill_all("enc_c")
        self.assertEqual(g.sim.completions["enc_c"], 1)
        g.sim.reload_encounters("CHK_NEFCITY_START", True)
        g.step(300)
        self.assertEqual(tpl(g, "enc_c", 1), G1)                   # kept original for this seed

    def test_retries_put_an_encounter_back(self):
        g = game(enemy=True)
        self.assertNotEqual(tpl(g, "enc_c", 1), G1)
        for i in range(3):
            g.sim.start_encounter("enc_c")
            g.sim.reload_encounters("CHK_NEFCITY_START", False)
            g.step(300)
        self.assertEqual(tpl(g, "enc_c", 1), G1)
        self.assertIn("loaded 3 times", py(g.state.spawn_blocked)["enc_c"])
        self.assertTrue(g.note_has("has its original enemies now"))
        play(g, "enc_c")
        self.assertEqual(g.sim.completions["enc_c"], 1)

    def test_enemies_that_stay_alive_too_long(self):
        g = game(enemy=True)
        g.sim.start_encounter("enc_c")
        g.step(60 * 185)
        self.assertEqual(tpl(g, "enc_c", 1), G1)
        self.assertTrue(g.log_has("stayed alive 180 s without a death"))
        g.sim.kill_all("enc_c")
        self.assertEqual(g.sim.completions["enc_c"], 1)

    def test_story_boss_area_puts_everything_back(self):
        g = game(enemy=True, boss=True)
        self.assertTrue(changed(g))
        T = g.g.RANDO_TRAVEL
        name = "CHK_STATION_FORGE_BOSS"
        T.hash_names[T.hash(name)] = name
        g.sim.emit("CheckpointTriggeredEvent", g.lua.table_from({"CheckpointHash": T.hash(name), "Loaded": False}))
        g.step(2)
        self.assertEqual(changed(g), set())
        g.step(300)
        self.assertEqual(changed(g), set())                  # nothing new while you are there
        g.sim.emit("CheckpointTriggeredEvent", g.lua.table_from({"CheckpointHash": T.hash("CHK_NEFCITY_START"), "Loaded": False}))
        g.step(2)
        self.assertEqual(changed(g) & ENEMY_SLOTS, ENEMY_SLOTS)

    def test_a_replacement_of_another_family_is_put_back(self):
        g = game(enemy=True)
        new = tpl(g, "enc_c", 1)
        g.sim.template_class[new] = "GameBotDarterBat"        # the game says it is a flyer after all
        play(g, "enc_c")
        self.assertEqual(tpl(g, "enc_c", 1), G1)
        self.assertIn("turned out to be a flyer", py(g.state.spawn_blocked)["enc_c"])
        self.assertEqual(g.sim.completions["enc_c"], 1)


class BudgetTests(unittest.TestCase):
    def test_big_levels_are_changed_and_put_back_over_several_frames(self):
        level = {f"enc_{i:03d}": ([G1 if i % 2 else G2], 1, None) for i in range(120)}
        level["enc_g3"] = ([G3], 1, None)
        g = Game()
        build_level(g, level)
        g.companion_restore()
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
        SP = g.g.RANDO_SPAWNERS
        SP.BUDGET_SECONDS = 0                               # the smallest budget: one encounter per frame
        SP.set("enemy", True, "test")
        g.travel("NefCity")
        g.step(400)
        orig = {uid: tpls[0] for uid, (tpls, _, _) in level.items()}
        now = {uid: g.sim.encounter_template(uid, 1) for uid in level}
        self.assertEqual(sum(1 for u in level if now[u] != orig[u]), len(level))
        SP.set("enemy", False, "test")
        self.assertTrue(any(g.sim.encounter_template(u, 1) != orig[u] for u in level))   # not all in one frame
        g.step(200)
        self.assertEqual({u: g.sim.encounter_template(u, 1) for u in level}, orig)


class LayoutTests(unittest.TestCase):
    def test_signature_finds_another_offset_and_skips_garbage(self):
        level = dict(LEVEL)
        level["enc_shift"] = ([G1], 1, "O_SHIFT")
        level["enc_garbage"] = ([G1], 1, "O_GARBAGE")
        g = Game()
        build_level(g, level, extra={"enc_shift": {"x": 0x58}, "enc_garbage": {"garbage": True}})
        g.companion_restore()
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
        g.g.RANDO_SPAWNERS.set("enemy", True, "test")
        g.travel("NefCity")
        g.step(300)
        self.assertNotEqual(g.sim.encounter_template("enc_shift", 1), G1)
        self.assertEqual(g.sim.encounter_template("enc_garbage", 1), G1)
        self.assertTrue(g.log_has("layout +0x50 x13, +0x58 x1"), [l for l in g.logs() if "census" in l])
        self.assertTrue(g.log_has("skipped\tenc_garbage: no Templates list found"))


class RemovalTests(unittest.TestCase):
    def test_without_the_shared_layer(self):
        g = Game(without=("16_rando_spawners.lua",))
        self.assertEqual(g.load_errors, [])
        build_level(g)
        g.ready()
        self.assertTrue(g.log_has("16_rando_spawners.lua is not installed: the enemy randomizer stays off"))
        g.press("-")
        g.press("=")
        g.step(300)
        self.assertEqual(changed(g), set())
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.15"))
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])

    def test_without_enemy_lua_bosses_still_work(self):
        g = game(enemy=None, boss=True, without=("enemy.lua",))
        g.state.enemy_rando = True                           # an old save that had it on
        g.g.RANDO_SPAWNERS.plan("test")
        ch = changed(g)
        self.assertEqual(ch & ENEMY_SLOTS, set())
        self.assertTrue(ch & BOSS_SLOTS)
        self.assertIsNone(g.g.RANDO_ENEMY)

    def test_without_boss_lua_enemies_still_work(self):
        g = game(enemy=True, without=("boss.lua",))
        g.state.boss_rando = True
        g.g.RANDO_SPAWNERS.plan("test")
        ch = changed(g)
        self.assertEqual(ch & BOSS_SLOTS, set())
        self.assertEqual(ch & ENEMY_SLOTS, ENEMY_SLOTS)

    def test_other_features_unchanged(self):
        """items, the shop and the kit run as before with both randomizers on"""
        g = game(enemy=True, boss=True)
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])
        self.assertTrue(g.R.status_text().find("enemies ON") >= 0)
        self.assertTrue(g.R.status_text().find("bosses ON") >= 0)
        for uid in sorted(LEVEL):
            play(g, uid)
        g.step(300)
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])


if __name__ == "__main__":
    unittest.main()
