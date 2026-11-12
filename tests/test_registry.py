"""6.0 independent validation of the weapon registry: the files agree with each other and with
your game's dag, no id is used twice, every weapon has exactly one kind of route, and the
evidence from your rivet.logs is what the registry says."""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

REG = json.load(open(os.path.join(ROOT, "data", "weapon_registry.json"), encoding="utf-8"))["weapons"]
DB = json.load(open(os.path.join(ROOT, "data", "game_db.json"), encoding="utf-8"))
DAG = json.load(open(os.path.join(ROOT, "data", "sources", "dag_item_ids.json"), encoding="utf-8"))
ACQ = {"pool", "shop_fixed", "start_fixed", "arsenal_restored", "disabled"}


class RegistryTests(unittest.TestCase):
    def test_no_duplicates(self):
        ids = [w["id"].upper() for w in REG.values()]
        configs = [w["config"] for w in REG.values()]
        names = [w["name"] for w in REG.values()]
        self.assertEqual(len(ids), len(set(ids)), "duplicate weapon id")
        self.assertEqual(len(configs), len(set(configs)), "duplicate weapon config")
        self.assertEqual(len(names), len(set(names)), "duplicate weapon name")
        # no weapon id is also any other item's id (armor, gadgets, currency)
        others = {it["id"].upper() for k, it in DB["items"].items() if it.get("id") and it["category"] != "weapon"}
        self.assertFalse(set(ids) & others)

    def test_ids_are_the_games(self):
        by_path = {v: k for k, v in DAG.items()}
        for k, w in REG.items():
            if w["config"] in by_path:
                self.assertEqual(w["id"].upper(), by_path[w["config"]].upper(), k)
            else:
                # Mr. Zurkon's item config is added by ARSENAL_RESTORED, not in the vanilla dag
                self.assertEqual((k, w["acquisition"]), ("weapon:mr_zurkon", "arsenal_restored"))
            self.assertTrue(re.fullmatch(r"configs/equipment/wpn_[a-z0-9_]+_item\.config", w["config"]), k)

    def test_routes(self):
        acq = {k: w["acquisition"] for k, w in REG.items()}
        self.assertTrue(set(acq.values()) <= ACQ)
        count = {a: sum(1 for v in acq.values() if v == a) for a in ACQ}
        self.assertEqual(count, {"pool": 17, "shop_fixed": 2, "start_fixed": 1, "arsenal_restored": 9, "disabled": 11})
        vendor = sorted(k for k, w in REG.items() if w["vendor"])
        self.assertEqual(len(vendor), 15)
        self.assertTrue(all(acq[k] == "pool" for k in vendor))
        self.assertEqual({k for k, a in acq.items() if a == "pool"} - set(vendor), {"weapon:pixelizer", "weapon:bouncer"})
        self.assertEqual({k for k, a in acq.items() if a == "shop_fixed"}, {"weapon:shatterbomb", "weapon:ryno_8"})
        self.assertEqual(acq["weapon:burst_pistol"], "start_fixed")
        # 20 weapons in the normal game (PowerPyx: 20, all bought from Ms. Zurkon)
        self.assertEqual(sum(1 for k, w in REG.items() if w["acquisition"] in ("pool", "shop_fixed", "start_fixed")), 20)

    def test_weapon_files_not_display_names(self):
        # the game's type data: warprifle spins up and heats (minigun), fossilizer slows time when
        # aiming (sniper), the nailgun and revolver types are empty (cut)
        self.assertEqual(REG["weapon:blackhole_storm"]["config"], "configs/equipment/wpn_warprifle_item.config")
        self.assertEqual(REG["weapon:headhunter"]["config"], "configs/equipment/wpn_fossilizer_item.config")
        self.assertEqual(REG["weapon:void_repulser"]["config"], "configs/equipment/wpn_magshield_item.config")
        self.assertEqual(REG["weapon:mr_fungi"]["config"], "configs/equipment/wpn_mrfunguy_item.config")
        self.assertEqual(REG["weapon:nailgun"]["acquisition"], "disabled")
        self.assertEqual(REG["weapon:revolver"]["acquisition"], "disabled")

    def test_evidence_matches_the_logs(self):
        """every 'confirmed round N' in the registry is in that round's rivet.log, with that config"""
        logs = {}
        for n in (13, 14, 15, 16):
            p = os.path.join(ROOT, "tests", "data", f"round{n}_rivet.log")
            if os.path.exists(p):
                logs[n] = open(p, encoding="utf-8", errors="replace").read()
        checked = 0
        for k, w in REG.items():
            m = re.match(r"confirmed rounds? ([\d, ]+)", w["evidence"])
            fn = w["config"].split("/")[-1]
            for n in [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []:
                text = logs[n]
                # the line that sent this config, then a confirmation of the same key
                sent = re.findall(r"\tsent\t(\S+)\t" + re.escape(w["config"]), text)
                self.assertTrue(sent, (k, n))
                self.assertTrue(any(f"\tconfirmed\t{s}\t" in text for s in sent), (k, n, fn))
                checked += 1
        self.assertGreater(checked, 8)
        # the Blackhole Storm's evidence is the round 13 delivery of wpn_warprifle
        self.assertIn("\tsent\tweapon:headhunter\tconfigs/equipment/wpn_warprifle_item.config", logs[13])

    def test_three_copies_agree(self):
        """data/weapon_registry.json, data/game_db.json and the shipped 01_rando_data.lua"""
        from lupa import lua54
        L = lua54.LuaRuntime()
        L.execute(open(os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts", "01_rando_data.lua"), encoding="utf-8").read())
        items = L.globals().RANDO_DATA["items"]
        for k, w in REG.items():
            self.assertEqual(DB["items"][k]["id"], w["id"])
            self.assertEqual(DB["items"][k]["acquisition"], w["acquisition"])
            self.assertEqual(items[k]["id"], w["id"])
            self.assertEqual(items[k]["acquisition"], w["acquisition"])
            self.assertEqual(bool(items[k]["vendor"]), bool(w["vendor"]))
            self.assertEqual(L.globals().RANDO_DATA["real_items"][k]["id"], w["id"])
        lua_weapons = [k for k in items.keys() if items[k]["category"] == "weapon"]
        self.assertEqual(sorted(lua_weapons), sorted(REG))

    def test_docs_list_every_weapon(self):
        text = open(os.path.join(ROOT, "mod", "RiftApartRandomizer", "docs", "WEAPONS.md"), encoding="utf-8").read()
        for k, w in REG.items():
            self.assertIn(f"`{w['id']}`", text, k)


if __name__ == "__main__":
    unittest.main()
