"""Randomizer 8.3: keyboard keys instead of F1-F12.

8.3 also started a planet's story where you landed (story_on_arrival, the story key, the stuck-story
restart). That lived in the Zurkie's hub script and is gone with it in 9.0, together with its tests;
the keys stay: ; status, . and , test travel, ' the campaign key, and the old F keys while
legacy_f_keys is on. The game here is the simulator (tests/sim/rivet_sim.lua), NOT your game.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from harness import Game  # noqa: E402
from story_helpers import level_game, started  # noqa: E402

VK_F7 = 0x76


def game(seed="v83-1", settings=None, missions=None, **kw):
    st = {"test_travel": True}
    st.update(settings or {})
    g = started(level_game(seed, st, missions=missions, **kw))
    g.step(1200)                     # the checkpoint catalog (test travel's landing points)
    return g


def select(g, pid, key="."):
    TT = g.g.RANDO_TEST_TRAVEL
    for _ in range(12):
        g.press(key)
        if TT.selected() == pid:
            return
    raise AssertionError("never selected " + pid)


def settle(g, frames=900):
    for _ in range(frames // 30):
        g.step(30)


def warp(g, pid):
    select(g, pid)
    g.press(".", ctrl=True)
    settle(g)


class KeyTests(unittest.TestCase):
    def test_keyboard_keys_and_the_old_f_keys(self):
        g = game("v83-keys")
        self.assertTrue(g.log_has("RANDO-KEYS\tkeyboard keys on"))
        g.press(";")
        self.assertTrue(g.note_has("Gold Bolts 0/25"))
        g.press("F9")                                    # legacy_f_keys
        self.assertTrue(g.log_has("RANDO-KEY\tF9"))
        warp(g, "ardolis")
        self.assertEqual(g.state.current_planet, "ardolis")
        self.assertTrue(g.log_has("RANDO-KEY\t.\twith Ctrl"))

    def test_legacy_keys_off(self):
        g = game("v83-nolegacy", {"legacy_f_keys": False})
        self.assertIsNone(g.R.bound[VK_F7])
        self.assertIsNotNone(g.R.bound[0xBE])            # .

    def test_any_key_name(self):
        g = game("v83-names", {"key_status": "K", "key_test_point": "NUMPAD5", "key_test_travel": "HOME"})
        self.assertEqual(g.R.vk("K"), 0x4B)
        self.assertEqual(g.R.vk("NUMPAD5"), 0x65)
        self.assertEqual(g.R.vk("HOME"), 0x24)
        self.assertEqual(g.R.vk("\\"), 0xDC)
        self.assertEqual(g.R.config.key_status, "K")
        self.assertIsNotNone(g.R.bound[0x4B])
        self.assertIsNotNone(g.R.bound[0x65])
        self.assertIsNotNone(g.R.bound[0x24])

    def test_bad_key_name_keeps_the_default(self):
        g = game("v83-bad", {"key_status": "NOPE"})
        self.assertEqual(g.R.config.key_status, ";")
        self.assertTrue(g.log_has("is not a key name"))

    def test_rivet_key_without_windows_codes_falls_back_to_f_keys(self):
        g = Game(settings={"seed": "v83-old", "preset": "balanced"},
                 before_scripts=lambda gm: gm.lua.execute(
                     "local k = rivet.key; rivet.key = function(n) local v = k(n); return v and (v + 1000) end"))
        self.assertFalse(g.R.keys_numeric)
        self.assertEqual(g.R.config.key_status, "F9")
        self.assertEqual(g.R.config.key_test_travel, "F7")
        self.assertTrue(g.log_has("cannot be bound here - using"))

    def test_settings_file_uses_keyboard_keys(self):
        g = Game(settings_file=True)
        c = g.R.config
        self.assertEqual((c.key_status, c.key_campaign, c.key_test_travel, c.key_test_point), (";", "'", ".", ","))
        for gone in ("key_hub", "key_hub_return", "key_story", "story_on_arrival", "story_reload_stuck"):
            self.assertIsNone(c[gone], gone)                    # 9.0: gone with the hub
        self.assertFalse(c.test_travel)                         # 8.4: off for a real playthrough
        self.assertTrue(c.legacy_f_keys)

    def test_seed_is_unchanged(self):
        a = level_game("v83-same")
        b = level_game("v83-same", {"key_status": "K", "legacy_f_keys": False, "test_travel": True})
        for g in (a, b):
            g.companion_restore()
            g.wait_seed()
        self.assertEqual(a.seed.fingerprint, b.seed.fingerprint)


if __name__ == "__main__":
    unittest.main()
