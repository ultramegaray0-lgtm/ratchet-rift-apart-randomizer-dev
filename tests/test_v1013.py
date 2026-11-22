"""Dev 10.13 (kit 10.0.9), asked for: a third, independent CHAOS RANDOMIZER (chaos.lua): anything can become
anything (any enemy or boss, from any planet), NO safety guards, OFF by default, its own key, saved; while
ON it takes priority over the Enemy and Boss Randomizers; OFF gives their own behaviour back.

SIMULATOR ONLY (tests/sim/rivet_sim.lua, the encounter model of 10.12; nodes can now belong to one planet).
Nothing here says that a replacement spawns, fights or completes anything in the real game.
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
from test_v1012 import (LEVEL, LEARNED, CLASS, G1, G2, G3, F1, F2, T1, B1, B2, B3, HB, STORY, FRIEND, UNKNOWN,  # noqa: E402
                        ENEMY_SLOTS, BOSS_SLOTS, build_level, slots, original, changed, play, alive)

REGULAR = {G1, G2, G3, F1, F2, T1, UNKNOWN}
BOSSY = {B1, B2, B3, HB, STORY}
# another planet's encounters (Savali) with its own templates
P1, P2, P3 = "8900000000000001", "8900000000000002", "8900000000000003"
SAVALI = {"sav_1": ([P1], 1, "OBJ_SAV_1"), "sav_2": ([P2], 1, "OBJ_SAV_2"), "sav_3": ([P3, P1], 2, "OBJ_SAV_3")}


def game(learned=True, chaos=None, enemy=None, boss=None, level=None, settings=None, seed=None, **kw):
    st = dict(settings or {})
    if seed:
        st["seed"] = seed
    g = Game(settings=st, **kw)
    assert not g.load_errors, g.load_errors
    build_level(g, level)
    g.companion_restore()
    if learned:
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
    for name, v in (("enemy", enemy), ("boss", boss), ("chaos", chaos)):
        if v is not None:
            g.g.RANDO_SPAWNERS.set(name, v, "test")
    g.travel("NefCity")
    g.step(300)
    return g


def owners(g):
    lvl = g.g.RANDO_SPAWNERS.level
    out = {}
    for uid in lvl.order.values():
        rec = lvl.nodes[uid]
        for k, sl in rec.slots.items():
            out[(uid, k)] = sl.owner
    return out


class LoadAndToggleTests(unittest.TestCase):
    def test_loads_off_by_default(self):
        g = game()
        self.assertTrue(g.log_has("RANDO-CHAOS\tinstalled (OFF"))
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.26"), [l for l in g.logs() if "KIT" in l])
        self.assertFalse(g.R.config.chaos_randomizer)
        self.assertEqual(g.R.config.key_chaos, "BACKSPACE")
        self.assertFalse(g.g.RANDO_CHAOS.enabled())
        self.assertEqual(changed(g), set())
        self.assertFalse(g.log_has("RANDO-SPAWNERS\tcensus"))
        self.assertIsNone(g.state.chaos_rando)
        self.assertIsNone(g.state.chaos_seen)

    def test_backspace_toggles_and_says_so(self):
        g = game()
        g.press("BACKSPACE")
        self.assertTrue(g.note_has("CHAOS RANDOMIZER: ON"))
        self.assertIs(g.state.chaos_rando, True)
        g.step(200)
        self.assertTrue(changed(g))
        self.assertIn("CHAOS ON", g.R.status_text())
        g.press("BACKSPACE", ctrl=True)
        self.assertTrue(any(n.startswith("Chaos Randomizer ON:") for n in g.notes()), g.notes()[-2:])
        self.assertIs(g.state.chaos_rando, True)                 # Ctrl only shows
        g.press("BACKSPACE")
        self.assertTrue(g.note_has("CHAOS RANDOMIZER: OFF"))
        self.assertIs(g.state.chaos_rando, False)
        self.assertEqual(changed(g), set())
        self.assertNotIn("CHAOS", g.R.status_text())

    def test_its_own_key(self):
        g = game()
        self.assertEqual(len({g.R.config.key_chaos, g.R.config.key_enemies, g.R.config.key_bosses, g.R.config.key_shuffle}), 4)
        g.press("-")
        g.press("=")
        self.assertIsNone(g.state.chaos_rando)                  # the other keys never touch Chaos

    def test_setting_persists_and_survives_new_game(self):
        g = game(chaos=True)
        text = g.companion_export()
        self.assertIn('["chaos_rando"]=true', text)
        g2 = Game()
        build_level(g2)
        g2.companion_restore(text)
        self.assertTrue(g2.g.RANDO_CHAOS.enabled())
        self.assertTrue(py(g2.state.chaos_seen))
        g2.travel("NefCity")
        g2.step(200)
        g2.sim.new_game()
        g2.step(200)
        self.assertTrue(g2.g.RANDO_CHAOS.enabled())
        self.assertTrue(py(g2.state.chaos_seen))

    def test_the_setting_decides_the_start(self):
        g = game(settings={"chaos_randomizer": True})
        self.assertTrue(g.g.RANDO_CHAOS.enabled())
        self.assertTrue(changed(g))


class AnythingBecomesAnythingTests(unittest.TestCase):
    def test_every_category_is_replaced_and_used(self):
        g = game(chaos=True)
        s, o = slots(g), original()
        ch = changed(g)
        # every slot changes except the friendly bot (not an enemy)
        self.assertEqual(ch, set(o) - {("enc_friend", 1)}, set(o) - ch)
        new = {s[x] for x in ch}
        self.assertNotIn(FRIEND, new)
        self.assertTrue(new & REGULAR and new & BOSSY)
        self.assertTrue(new & {STORY, UNKNOWN})                 # story bosses and unclassified ones are used too
        self.assertNotEqual(s[("enc_story", 1)], STORY)          # the story boss itself is replaced
        self.assertNotEqual(s[("enc_turret", 1)], T1)

    def test_bosses_become_regular_and_regular_become_bosses(self):
        seen_up = seen_down = 0
        for seed in ("chaos-a", "chaos-b", "chaos-c"):
            g = game(chaos=True, seed=seed)
            s, o = slots(g), original()
            up = [x for x in s if o[x] in REGULAR and s[x] in BOSSY]
            down = [x for x in s if o[x] in BOSSY and s[x] in REGULAR]
            self.assertTrue(up, (seed, s))
            self.assertTrue(down, (seed, s))
            seen_up += len(up)
            seen_down += len(down)
        self.assertGreater(seen_up + seen_down, 6)

    def test_the_same_replacement_repeats_as_little_as_possible(self):
        g = game(chaos=True)
        picks = [slots(g)[x] for x in sorted(changed(g))]
        pool = len(REGULAR | BOSSY)                             # 12 templates, 15 changed slots
        self.assertEqual(len(picks), 15)
        self.assertGreaterEqual(len(set(picks)), pool - 1)
        within = [slots(g)[("enc_a", k)] for k in (1, 2, 3)]
        self.assertEqual(len(set(within)), 3)                    # one encounter's enemies all different

    def test_no_learning_needed(self):
        g = game(learned=False, chaos=True)
        self.assertEqual(changed(g), set(original()))           # nothing known: even the friendly one changes

    def test_seed_decides(self):
        a = slots(game(chaos=True, seed="same"))
        b = slots(game(chaos=True, seed="same"))
        c = slots(game(chaos=True, seed="other"))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


class CrossPlanetTests(unittest.TestCase):
    def two_planets(self, **kw):
        level = {uid: v for uid, v in LEVEL.items()}
        g = Game(settings=kw.pop("settings", None))
        g.sim.uid_actor = g.sim.uid_actor or g.lua.table()
        g.sim.actor_uid = g.sim.actor_uid or g.lua.table()
        build_level(g, level, extra={uid: {"planet": "NefCity"} for uid in level})
        build_level(g, SAVALI, extra={uid: {"planet": "Savali"} for uid in SAVALI})
        for t in (P1, P2, P3):
            g.sim.template_class[t] = "GameBotShooter"
        g.companion_restore()
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
        g.g.RANDO_SPAWNERS.set("chaos", True, "test")
        g.travel("NefCity")
        g.step(300)
        if kw.get("before_savali"):
            kw["before_savali"](g)
        g.travel("Savali")
        g.step(300)
        return g

    def test_enemies_of_another_planet_appear(self):
        # dev 10.18: a Templates entry is the uid of a template actor (a TUID): another planet's template is
        # used only where its template actor is loaded (here: Nefarious City's G1/G2 loaded on Savali too)
        def load_here(g):
            for i, t in enumerate((G1, G2)):
                g.sim.uid_actor[t] = 7100000 + i
                g.sim.actor_uid[7100000 + i] = t
        g = self.two_planets(before_savali=load_here)
        seen = py(g.state.chaos_seen)
        self.assertEqual(seen[G1], "nefarious_city")
        self.assertEqual(seen[P1], "savali")
        sav = {(u, k): g.sim.encounter_template(u, k) for u, (t, _, _) in SAVALI.items() for k in range(1, len(t) + 1)}
        here = {P1, P2, P3}
        self.assertTrue([x for x, v in sav.items() if v not in here], sav)   # from Nefarious City
        self.assertEqual(g.g.RANDO_CHAOS.last.foreign, sum(1 for v in sav.values() if v not in here))

    def test_another_planets_template_that_is_not_loaded_is_never_used(self):
        # dev 10.18: it could not spawn (no template actor here), and Chaos has no guard to put it back
        g = self.two_planets()
        sav = [g.sim.encounter_template(u, k) for u, (t, _, _) in SAVALI.items() for k in range(1, len(t) + 1)]
        self.assertTrue(set(sav) <= {P1, P2, P3}, sav)
        self.assertEqual(g.g.RANDO_CHAOS.last.foreign, 0)

    def test_this_planet_only_when_switched_off(self):
        g = self.two_planets(settings={"chaos_cross_planet": False})
        sav = [g.sim.encounter_template(u, k) for u, (t, _, _) in SAVALI.items() for k in range(1, len(t) + 1)]
        self.assertTrue(set(sav) <= {P1, P2, P3}, sav)


class PriorityTests(unittest.TestCase):
    def test_chaos_overrides_and_off_gives_the_normal_randomizers_back(self):
        normal = game(enemy=True, boss=True)
        normal_slots = slots(normal)
        g = game(enemy=True, boss=True)
        self.assertEqual(slots(g), normal_slots)
        g.press("BACKSPACE")
        g.step(10)
        own = owners(g)
        self.assertEqual({o for x, o in own.items() if x in changed(g)}, {"chaos"})
        self.assertEqual(set(own.values()) - {"chaos", None}, set())
        self.assertIs(g.state.enemy_rando, True)                 # their settings are not touched
        self.assertIs(g.state.boss_rando, True)
        self.assertTrue(g.note_has("CHAOS RANDOMIZER: ON"))
        g.press("-")                                             # the enemy key still works on its own setting
        self.assertIs(g.state.enemy_rando, False)
        self.assertEqual({o for o in owners(g).values()} - {"chaos", None}, set())   # but changes nothing now
        g.press("-")
        g.press("BACKSPACE")
        g.step(10)
        self.assertEqual(slots(g), normal_slots)                 # exactly the normal Enemy + Boss picks
        self.assertEqual(set(owners(g).values()) - {None}, {"enemy", "boss"})
        subs = [n.opts.sub for n in g.sim.notes.values() if n.opts is not None and n.opts.sub is not None]
        self.assertTrue(any("Enemy Randomizer ON, Boss Randomizer ON as you set them" in x for x in subs), subs[-2:])

    def test_off_with_the_others_off_is_the_original_game(self):
        g = game(chaos=True)
        self.assertTrue(changed(g))
        g.press("BACKSPACE")
        self.assertEqual(changed(g), set())
        g.step(600)
        self.assertEqual(changed(g), set())

    def test_others_resume_by_their_own_rules(self):
        g = game(enemy=True, chaos=True)
        g.sim.start_encounter("enc_c")                            # started while Chaos ran
        g.press("BACKSPACE")
        g.step(10)
        self.assertEqual(g.sim.encounter_template("enc_c", 1), G1)   # the enemy randomizer never changes a running one
        self.assertIn(("enc_a", 1), changed(g))
        self.assertEqual(changed(g) & BOSS_SLOTS, set())          # boss off: originals


class NoGuardsTests(unittest.TestCase):
    def test_nothing_is_put_back_by_itself(self):
        g = game(chaos=True)
        before = slots(g)
        new = before[("enc_c", 1)]
        g.sim.unspawnable[new] = True                            # its replacement cannot spawn
        g.sim.start_encounter("enc_c")
        g.sim.encounter_tick(25)                                 # past 20 s
        self.assertEqual(g.sim.encounter_template("enc_c", 1), new)
        g.sim.start_encounter("enc_a")
        g.step(60 * 185)                                         # alive past 3 minutes
        for _ in range(3):                                       # three reloads during it
            g.sim.start_encounter("enc_b")
            g.sim.reload_encounters("CHK_NEFCITY_START", False)
            g.step(300)
        T = g.g.RANDO_TRAVEL
        T.hash_names[T.hash("CHK_STATION_FORGE_BOSS")] = "CHK_STATION_FORGE_BOSS"
        g.sim.emit("CheckpointTriggeredEvent", g.lua.table_from({"CheckpointHash": T.hash("CHK_STATION_FORGE_BOSS"), "Loaded": False}))
        g.step(60)
        self.assertEqual(slots(g), before)                        # still every chaos pick
        self.assertIsNone(g.state.spawn_blocked)
        self.assertFalse(g.log_has("kept so:"))

    def test_running_encounters_are_changed_too(self):
        g = Game()
        build_level(g)
        g.companion_restore()
        g.state.spawn_learned = g.lua.table_from(dict(LEARNED))
        g.travel("NefCity")
        g.sim.start_encounter("enc_c")
        g.g.RANDO_SPAWNERS.set("chaos", True, "test")
        g.step(300)
        self.assertNotEqual(g.sim.encounter_template("enc_c", 1), G1)

    def test_a_replacement_of_any_kind_is_learned_not_blocked(self):
        g = game(chaos=True)
        new = slots(g)[("enc_c", 1)]
        g.sim.template_class[new] = "GameBotDarterBat"           # whatever it really is
        play(g, "enc_c")
        self.assertIsNone(g.state.spawn_blocked)
        self.assertNotEqual(g.sim.encounter_template("enc_c", 1), G1)

    def test_the_randomizer_never_forces_progression(self):
        g = game(chaos=True)
        g.sim.start_encounter("enc_a")
        bots = alive(g, "enc_a")
        g.sim.kill("enc_a", bots[0])
        g.step(600)
        self.assertIsNone(g.sim.completions["enc_a"])            # only the node completes it
        self.assertEqual(list(g.sim.set_state_calls.values()), [])


class IntegrityTests(unittest.TestCase):
    def test_garbage_and_shared_lists_are_never_written(self):
        level = dict(LEVEL)
        level["enc_garbage"] = ([G1], 1, "O_GARBAGE")
        g = Game()
        build_level(g, level, extra={"enc_garbage": {"garbage": True}})
        g.companion_restore()
        g.g.RANDO_SPAWNERS.set("chaos", True, "test")
        g.travel("NefCity")
        g.step(300)
        self.assertEqual(g.sim.encounter_template("enc_garbage", 1), G1)
        lvl = g.g.RANDO_SPAWNERS.level
        self.assertTrue(all(sl.shared is None for uid in lvl.order.values() for sl in lvl.nodes[uid].slots.values()))


class RemovalTests(unittest.TestCase):
    def test_without_chaos_lua(self):
        g = game(enemy=True, boss=True, without=("chaos.lua",))
        self.assertIsNone(g.g.RANDO_CHAOS)
        self.assertEqual(changed(g) & ENEMY_SLOTS, ENEMY_SLOTS)
        g.press("BACKSPACE")
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])

    def test_without_the_shared_layer(self):
        g = Game(without=("16_rando_spawners.lua",))
        self.assertEqual(g.load_errors, [])
        g.ready()
        self.assertTrue(g.log_has("16_rando_spawners.lua is not installed: the Chaos Randomizer stays off"))

    def test_other_features_intact(self):
        g = game(chaos=True, enemy=True, boss=True)
        for uid in sorted(LEVEL):
            g.sim.start_encounter(uid)
            g.sim.kill_all(uid)
        g.step(300)
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])
        self.assertTrue(g.log_has("RANDO-SHOP"))
        self.assertGreater(len([x for x in g.state.real.values() if x.status == "confirmed"]), 0)


if __name__ == "__main__":
    unittest.main()
