"""v0.62-DEV9: round49 (tests/data/round49_rivet.log, DEV8 in the game).

The component walk finished in the game (141 components), but the inventories InventoryChangedEvent names on the hero
(2129937 / 2129951 / 2129975 / 2129997 / 2129999) are not in the hero's component list. DEV9 resolves those handles
through the SceneManager (rando_give.dll v7, as the Enemy Randomizer does) and also reads arrays of item handles.
The simulator's SceneManager inventory (SIM.inv_scene) is SYNTHETIC: it shows the code's logic, not the game's layout.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game, ROOT, DEV_DIR, script_files  # noqa: E402

OMEGA_AT = 0x5B
LOG = os.path.join(ROOT, "tests", "data", "round49_rivet.log")


def scene_game(**kw):
    g = Game(dll_version=7, before_scripts=lambda gg: gg.lua.execute(
        "SIM.inv_live = true; SIM.inventory_component = false; SIM.inv_scene = true"), **kw)
    assert not g.load_errors, g.load_errors
    g.ready()
    return g


def wid(g, w):
    return g.data["items"]["weapon:" + w].id


def omega_logs(g, n=10):
    return [l for l in g.logs() if "OMEGA" in l][-n:]


class Round49LogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(LOG, encoding="utf-8") as f:
            cls.text = f.read()

    def test_dev8_was_installed_whole_and_the_walk_finished(self):
        self.assertIn("RANDO-KIT release v0.62-DEV8 (kit 10.0.28)", self.text)
        self.assertIn("RANDO-KIT all 12 required scripts are 10.0.28", self.text)
        self.assertIn("hero component list walked: 141 components", self.text)
        self.assertNotIn("search:\tscripts\\17_rando_omega.lua", self.text)          # no budget kill of the search

    def test_the_event_named_inventories_are_not_in_the_hero_list(self):
        self.assertIn("InventoryChangedEvent\tActor=1072366 Component=2129937", self.text)
        self.assertIn("GadgetItemAddedEvent\tConfigTypeHash=565053540 InventoryHandle=2129937", self.text)
        cands = [l for l in self.text.splitlines() if "inventory candidate" in l]
        self.assertTrue(cands)
        self.assertTrue(all("(its class name)" in l for l in cands), cands)        # none came from an event
        self.assertIn("inventory not found:", self.text)

    def test_every_purchase_was_a_new_weapon_and_no_challenge_mode(self):
        self.assertEqual(self.text.count("VendorPurchaseEvent"), 5)
        self.assertEqual(self.text.count("PurchaseWeaponEvent"), 5)
        self.assertIn("RANDO-NOTIFY\t[DEBUG] press HOME first to choose a planet", self.text)

    def test_the_game_path_is_anonymised(self):
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", self.text)
        self.assertNotIn("Users", self.text)


class SceneInventoryTests(unittest.TestCase):
    def own(self, g, *ws):
        for w in ws:
            g.R.grant("weapon:" + w)
        g.step(900)

    def test_the_inventory_is_resolved_by_handle_and_its_item_handles_read(self):
        g = scene_game()
        self.own(g, "enforcer", "mr_fungi")
        g.step(1500)
        self.assertTrue(g.log_has("hero component list walked: 4 components"), omega_logs(g))
        self.assertTrue(g.log_has("inventory candidate HeroItemInventoryX handle=2129937 size=512"), omega_logs(g))
        self.assertTrue(any("InventoryChangedEvent, by handle" in l for l in g.logs()), omega_logs(g))
        self.assertTrue(any("weapon record(s) in HeroItemInventoryX#2129937" in l for l in g.logs()), omega_logs(g))

    def test_two_omega_purchases_teach_the_byte_through_item_handles(self):
        g = scene_game()
        g.R.grant("omega:ricochet")
        self.own(g, "mr_fungi", "drillhound")
        g.step(1500)
        self.assertEqual(g.sim.omega_of(wid(g, "ricochet")), 0)
        g.sim.buy_omega_live(wid(g, "mr_fungi"), "MrFunGuy")
        g.step(120)
        self.assertTrue(g.log_has("Omega purchase 1 of 2 (mr_fungi)"), omega_logs(g))
        g.step(700)
        g.sim.buy_omega_live(wid(g, "drillhound"), "Tunneler")
        g.step(120)
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT, omega_logs(g))
        g.step(900)
        self.assertEqual(g.sim.omega_of(wid(g, "ricochet")), 1)
        self.assertEqual(g.state.omega["ricochet"].status, "applied")

    def test_an_unresolvable_handle_is_logged_once_with_its_reason(self):
        g = scene_game()
        g.sim.emit("InventoryChangedEvent", {"Actor": g.lua.eval("SIM.hero_handle"), "Component": 0x20FFF0})
        self.own(g, "enforcer")
        g.step(1500)
        lines = [l for l in g.logs() if "inventory handle\t2162672" in l]
        self.assertEqual(len(lines), 1, omega_logs(g))
        self.assertIn("not resolved", lines[0])

    def test_without_the_v7_helper_it_says_why_and_still_walks(self):
        g = Game(before_scripts=lambda gg: gg.lua.execute(
            "SIM.inv_live = true; SIM.inventory_component = false; SIM.inv_scene = true"))
        g.ready()
        self.own(g, "enforcer")
        g.step(1500)
        self.assertTrue(any("inventory handle\t2129937" in l and "v7 is needed" in l for l in g.logs()), omega_logs(g))
        self.assertTrue(g.log_has("hero component list walked"))

    def test_the_first_item_handles_are_probed_once(self):
        g = scene_game()
        g.lua.execute("RANDO_OMEGA.item_probed = 0")
        self.own(g, "enforcer")
        g.lua.execute("SIM.live_layout()")
        ih = g.lua.eval("SIM.item_handle['%s']" % wid(g, "enforcer"))
        g.sim.emit("GadgetItemAddedEvent", {"ConfigTypeHash": 1, "InventoryHandle": 2129937, "ItemHandle": ih})
        g.step(60)
        self.assertTrue(g.log_has("item handle %d: WeaponItemX size=128" % ih), omega_logs(g))
        self.assertTrue(g.log_has("item handle %d: prius data at" % ih))


class DebugEndKeyTests(unittest.TestCase):
    def test_end_before_home_chooses_this_planet_and_end_again_warps(self):
        files = sorted(script_files(release=False) + [DEV_DIR / "dev(debug).lua"], key=lambda p: p.name)
        g = Game(files=files)
        g.ready()
        g.step(300)
        g.press("END")
        g.step(5)
        self.assertFalse(g.note_has("press HOME first"))
        self.assertTrue(any("END before HOME: chose" in l for l in g.logs()), [l for l in g.logs() if "DEBUG" in l][-5:])
        self.assertTrue(any("[DEBUG] " in n and "/" in n for n in g.notes()), g.notes()[-3:])


if __name__ == "__main__":
    unittest.main()
