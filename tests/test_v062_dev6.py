"""v0.62-DEV6 (kit 10.0.26): round46 (tests/data/round46_rivet.log, DEV5 in the game) - "I bought Omegas, nothing registers".

Round46 facts (real game, read from the log):
  * 17_rando_omega.lua searched GameInventoryManager, HeroWeaponManagerLocal and GameEquipManager: "no array of weapon
    records" in all three, on every load; the NUMPAD1 / NUMPAD2 tools all answered "no weapon records" (they use the
    same search).
  * The hero's real inventories were named only by HANDLE: InventoryChangedEvent { Actor = 1072366 (the hero),
    Component = 2129937 / 2129951 / 2129975 / 2129997 / 2129999 }, GadgetItemAddedEvent { InventoryHandle = 2129937 };
    the probe's component list was cut by rivet.log after 47 of 132 names.
  * The Omega purchases (MagShield, Warmonger) sent ONLY VendorPurchaseEvent - no PurchaseWeaponEvent (which the
    learning listened to) - and EnteredVendorEvent (which took the "before" read) never came in 20 purchases.
  * The search's header loop ran past the 8 ms frame budget 60+ times ("17_rando_omega.lua:263"), killing the job.

DEV6, tested against the SIMULATOR only (tests/sim/rivet_sim.lua S.inv_live, an INVENTED class name for the
inventory): the hero's own component list is walked (rivet_hook's Actor / Component / ComponentInfo layout), the
components inventory events name are searched first, Omega purchases are learned from VendorPurchaseEvent alone
against a read taken when the records were found, and the header loop pauses.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game, MOD  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "tests", "data", "round46_rivet.log")
OMEGA_AT = 0x5B


def live_game(settings=None):
    g = Game(settings=dict(settings or {}), before_scripts=lambda gg: gg.lua.execute("SIM.inv_live = true; SIM.inventory_component = false"))
    assert not g.load_errors, g.load_errors
    g.ready()
    return g


def wid(g, w):
    return g.data["items"]["weapon:" + w].id


class Round46LogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(LOG, encoding="utf-8") as f:
            cls.text = f.read()

    def test_the_log_is_dev5_and_anonymised(self):
        self.assertIn("RANDO-KIT release v0.62-DEV5 (kit 10.0.25)", self.text)
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", self.text)
        self.assertNotRegex(self.text, r"[A-Z]:\\Users\\")

    def test_no_records_in_the_three_live_components(self):
        self.assertIn("no array of weapon records in GameInventoryManager; no array of weapon records in "
                      "HeroWeaponManagerLocal; no array of weapon records in GameEquipManager", self.text)

    def test_the_inventories_are_named_by_handle_on_the_hero(self):
        self.assertIn("InventoryChangedEvent\tActor=1072366 Component=2129937", self.text)
        self.assertIn("GadgetItemAddedEvent\tConfigTypeHash=565053540 InventoryHandle=2129937", self.text)
        self.assertIn("hero handle\t1072366", self.text)

    def test_omega_purchases_send_vendor_purchase_alone(self):
        lines = self.text.splitlines()
        for name in ("MagShield", "Warmonger"):
            i = max(k for k, l in enumerate(lines) if "VendorPurchaseEvent\tShowRemapTutorial=false WeaponName=" + name in l)
            after = lines[i + 1:i + 6]
            self.assertFalse(any("PurchaseWeaponEvent" in l for l in after), (name, after))
        self.assertNotIn("EnteredVendorEvent", self.text)

    def test_the_header_loop_overran_the_budget(self):
        self.assertGreater(self.text.count("17_rando_omega.lua:263: ran past the 8 ms frame budget"), 30)


class VendorNameTests(unittest.TestCase):
    def test_every_round46_vendor_name_maps_to_the_weapon_its_purchase_named(self):
        with open(LOG, encoding="utf-8") as f:
            lines = f.read().splitlines()
        g = Game()
        O, RR = g.g.RANDO_OMEGA, g.g.RANDO_REAL
        pairs = 0
        for k, l in enumerate(lines):
            m = re.search(r"VendorPurchaseEvent\tShowRemapTutorial=\w+ WeaponName=(.+)$", l)
            if not m:
                continue
            for nxt in lines[k + 1:k + 5]:
                p = re.search(r"PurchaseWeaponEvent\tWeaponConfig=\d+ WeaponName=(\w+)", nxt)
                if p:
                    item = RR.weapon_item(p.group(1))
                    if item and O.ID_OF[item[7:]]:
                        self.assertEqual(O.weapon_of_vendor_name(m.group(1)), item[7:], m.group(1))
                        pairs += 1
                    break
        self.assertGreaterEqual(pairs, 10)        # round46: 11 purchases of weapons that have an Omega item
        self.assertEqual(O.weapon_of_vendor_name("MagShield"), "magshield" if O.ID_OF["magshield"] else O.weapon_of_vendor_name("MagShield"))


class LiveInventoryTests(unittest.TestCase):
    def own(self, g, *ws):
        for w in ws:
            g.R.grant("weapon:" + w)
        g.step(900)
        for w in ws:
            self.assertTrue(g.owns("weapon:" + w), w)

    def test_the_walk_finds_the_records_in_the_component_the_event_named(self):
        g = live_game()
        self.own(g, "enforcer", "mr_fungi")
        g.step(1200)
        self.assertTrue(g.log_has("hero component list walked: 5 components"), [l for l in g.logs() if "OMEGA" in l][-8:])
        self.assertTrue(g.log_has("inventory candidate HeroItemInventoryX handle=2129937 size=512"))
        self.assertTrue(g.log_has("RANDO-OMEGA\tinventory:"), [l for l in g.logs() if "OMEGA" in l][-8:])
        self.assertTrue(any("in HeroItemInventoryX#2129937" in l for l in g.logs()))
        self.assertFalse(g.log_has("ran past"))

    def test_two_vendor_purchase_omegas_teach_the_byte_and_the_start_omega_is_set(self):
        g = live_game()
        g.R.grant("omega:ricochet")
        self.own(g, "mr_fungi", "drillhound")
        g.step(1200)
        self.assertEqual(g.sim.omega_of(wid(g, "ricochet")), 0)          # not learned yet: nothing written
        g.sim.buy_omega_live(wid(g, "mr_fungi"), "MrFunGuy")
        g.step(120)
        self.assertTrue(g.log_has("Omega purchase seen: MrFunGuy (mr_fungi)"), [l for l in g.logs() if "OMEGA" in l][-6:])
        self.assertTrue(g.log_has("Omega purchase 1 of 2 (mr_fungi)"))
        g.step(700)                                                       # a fresh read for the next purchase
        g.sim.buy_omega_live(wid(g, "drillhound"), "Tunneler")
        g.step(120)
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT, [l for l in g.logs() if "OMEGA" in l][-6:])
        self.assertTrue(g.log_has("LEARNED: the Omega flag is the byte at +0x5B"))
        g.step(900)
        self.assertEqual(g.sim.omega_of(wid(g, "ricochet")), 1)
        self.assertEqual(g.state.omega["ricochet"].status, "applied")

    def test_buying_a_new_weapon_teaches_nothing(self):
        g = live_game()
        self.own(g, "mr_fungi")
        g.step(1200)
        # a normal purchase: VendorPurchaseEvent, then PurchaseWeaponEvent for the same weapon
        g.sim.emit("VendorPurchaseEvent", {"ShowRemapTutorial": False, "WeaponName": "Tunneler"})
        g.sim.emit("PurchaseWeaponEvent", {"WeaponName": "WEAPON_TUNNELER"})
        g.step(120)
        self.assertFalse(g.log_has("Omega purchase seen"))
        self.assertIsNone(g.state.omega_cal)

    def test_the_debug_compare_finds_the_byte(self):
        from harness import DEV_DIR, script_files
        files = sorted(script_files(release=False) + [DEV_DIR / "dev(debug).lua"], key=lambda p: p.name)
        g = Game(files=files, before_scripts=lambda gg: gg.lua.execute("SIM.inv_live = true; SIM.inventory_component = false"))
        g.ready()
        self.own(g, "mr_fungi")
        g.step(1200)
        g.press("NUMPAD1")
        g.step(200)
        self.assertTrue(g.log_has("omega: "), [l for l in g.logs() if "DEBUG" in l][-4:])
        g.sim.set_omega(wid(g, "mr_fungi"), 1)
        g.press("NUMPAD2")
        g.step(200)
        self.assertTrue(any("omega candidates (0 -> 1):\t1\tmr_fungi +0x5B" in l for l in g.logs()),
                        [l for l in g.logs() if "DEBUG" in l][-4:])
        g.press("NUMPAD2", ctrl=True)
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT)


if __name__ == "__main__":
    unittest.main()


class Round47MixedInstallTests(unittest.TestCase):
    """round47 (tests/data/round47_rivet.log): DEV5 scripts + DEV6 dev(debug).lua; the kit check said to delete the new file"""

    def test_the_log_is_a_mixed_install(self):
        with open(os.path.join(ROOT, "tests", "data", "round47_rivet.log"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("RANDO-KIT release v0.62-DEV5 (kit 10.0.25)", text)
        self.assertIn("delete from the scripts folder: dev(debug).lua (10.0.26)", text)
        self.assertIn("17_rando_omega.lua:263: ran past the 8 ms frame budget", text)   # DEV5's search still ran
        # the vendor config answers only plain numbers: no ItemDatas for rivet.config_set
        self.assertIn("UpgradeCellYOffset number=31.0", text)
        self.assertNotIn("ItemDatas", text)

    def test_a_newer_developer_file_names_the_old_scripts_folder(self):
        import tempfile, pathlib
        from harness import DEV_DIR, script_files
        src = (DEV_DIR / "dev(debug).lua").read_text(encoding="utf-8").replace('RANDO_FILES["dev(debug)"] = "10.0.35"',
                                                                             'RANDO_FILES["dev(debug)"] = "10.0.99"')
        d = pathlib.Path(tempfile.mkdtemp())
        p = d / "dev(debug).lua"
        p.write_text(src, encoding="utf-8")
        g = Game(files=sorted(script_files(release=True) + [p], key=lambda q: q.name))
        g.ready()
        self.assertTrue(g.log_has("the scripts folder is OLDER than its developer file(s): kit 10.0.35, developer file 10.0.99"),
                        [l for l in g.logs() if "KIT" in l])
        self.assertFalse(g.log_has("delete from the scripts folder"))
        self.assertTrue(g.note_has("copy the whole new scripts folder"))


class Round48BudgetTests(unittest.TestCase):
    """round48 (tests/data/round48_rivet.log, DEV7): the search job was killed 19 times by rivet_hook's frame budget at
    the walk's reads, and the walk never finished. DEV8: jobs only run in frames with room, the walk resumes."""

    def test_the_log_shows_the_walk_killed(self):
        with open(os.path.join(ROOT, "tests", "data", "round48_rivet.log"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("RANDO-KIT release v0.62-DEV7 (kit 10.0.27)", text)
        self.assertGreaterEqual(text.count("search:\tscripts\\17_rando_omega.lua:23"), 15)
        self.assertNotIn("hero component list walked", text)
        # every purchase of this run was a new weapon (PurchaseWeaponEvent follows): no Omega for sale outside Challenge Mode
        self.assertEqual(text.count("VendorPurchaseEvent"), text.count("PurchaseWeaponEvent"))

    def test_a_walk_killed_by_the_budget_continues_and_finishes(self):
        g = live_game()
        # the first six times, every 7th pause raises the budget error inside the job (what rivet_hook's count hook does)
        g.lua.execute("""
          RANDO_OMEGA.walked, RANDO_OMEGA.walk_logged = nil, nil
          local orig, n = RANDO_OMEGA.pause, 0
          RANDO_OMEGA.pause = function()
            n = n + 1
            if n % 7 == 0 and n <= 42 then error("ran past the 8 ms frame budget", 0) end
            return orig()
          end""")
        for w in ("enforcer", "mr_fungi"):
            g.R.grant("weapon:" + w)
        g.step(4000)
        self.assertGreaterEqual(sum("ran past the 8 ms frame budget" in l for l in g.logs()), 3)   # it was killed
        self.assertTrue(g.log_has("hero component list walked: 5 components"), [l for l in g.logs() if "OMEGA" in l][-6:])
        self.assertTrue(g.log_has("RANDO-OMEGA\tinventory:"))

    def test_no_job_runs_in_a_busy_frame(self):
        g = Game(before_scripts=lambda gg: gg.lua.execute("SIM.inv_live = true; SIM.inventory_component = false"))
        # every frame counts as busy, and (v0.62-DEV10's starvation guard) also as past the hard limit
        g.lua.execute("RANDO_OMEGA.FRAME_ROOM = -1; RANDO_OMEGA.FRAME_HARD_SAVED = RANDO_OMEGA.FRAME_HARD; RANDO_OMEGA.FRAME_HARD = -1")
        g.ready()
        g.R.grant("weapon:enforcer")
        g.step(2000)
        self.assertFalse(g.log_has("hero component list walked"))
        g.lua.execute("RANDO_OMEGA.FRAME_ROOM = 0.003; RANDO_OMEGA.FRAME_HARD = RANDO_OMEGA.FRAME_HARD_SAVED")
        g.step(1500)
        self.assertTrue(g.log_has("hero component list walked"))
