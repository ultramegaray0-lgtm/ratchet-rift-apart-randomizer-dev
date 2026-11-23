"""v0.62-DEV5 (kit 10.0.25): round45 (tests/data/round45_rivet.log, kit 10.0.24 / v0.62-DEV4 in the game).

Round45 facts (real game, read from the log):
  * Enemy Randomizer: 6 of 68 enemy spawns replaced on Ardolis (9%), 0 of 5 per NefCity bazaar visit; 49 of Ardolis' 51
    unchanged spawns were "kind not known yet" - the bladeball / robot shooter / crab / pool shark templates of uids
    that were not in V.REG_BUILTIN. Pool sharks became replacements of land enemies (crab -> pool shark).
  * Omega: "inventory not found" on every load; the live hero's item components are GameInventoryManager,
    HeroWeaponManagerLocal, GameEquipManager, VanityInventoryManager (none of the four names searched).
  * Shop: "only 0 vendor weapon(s) in the array at +0x48" 5 times, then "Ms. Zurkon could not be changed".
  * No Spybot / Lorb event was ever bound (05 collectible_events = {}).

What DEV5 does, tested here against the SIMULATOR (tests/sim/rivet_sim.lua) - nothing of it has run in the game:
  registry harvest (tools/harvest_enemy_uids.py), pool sharks source-only, name-based template classification,
  Omega search of the live components, start_omega, Spybot/Lorb pickups (RYNOPlayPickedUpEvent / RuinPlayPickedUpEvent,
  names from neptuwunium/rivet's DDL), the planet-menu cancel of the trip back (test_v060 covers the playthrough),
  the read-only vendor config probe, and dev(debug).lua (every developer tool in one file + warp / unstuck).
"""
import os
import pathlib
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game, MOD, DEV_DIR, script_files  # noqa: E402
from test_v100 import hub_game, to_hub  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "tests" / "data" / "round45_rivet.log"
V = "RANDO_SPAWNERS.V"


def py(t):
    return dict(t.items()) if t is not None and hasattr(t, "items") else t


class Round45LogTests(unittest.TestCase):
    """facts of the real log the fixes rest on"""

    @classmethod
    def setUpClass(cls):
        cls.text = LOG.read_text(encoding="utf-8")

    def test_the_log_is_the_dev4_kit_and_anonymised(self):
        self.assertIn("RANDO-KIT release v0.60 (kit 10.0.24)", self.text)
        self.assertIn("game = <GAME_FOLDER>\\RiftApart.exe", self.text)
        self.assertNotRegex(self.text, r"[A-Z]:\\Users\\")

    def test_ardolis_replaced_6_of_68_and_kind_not_known_was_the_reason(self):
        self.assertIn("ENEMY SPAWNS on this level: 68, replaced 6 (9%)", self.text)
        self.assertIn("49 kind not known yet", self.text)

    def test_the_hero_has_the_live_inventory_components(self):
        for c in ("GameInventoryManager", "HeroWeaponManagerLocal", "GameEquipManager"):
            self.assertIn("hero component candidate\t" + c, self.text)
        self.assertIn("inventory not found:\tthe hero has no component ItemInventory", self.text)

    def test_the_vendor_was_never_changed(self):
        self.assertIn("only 0 vendor weapon(s) in the array at +0x48", self.text)
        self.assertIn("Ms. Zurkon could not be changed", self.text)

    def test_pool_sharks_were_put_where_walkers_spawn(self):
        self.assertIn("enm_indigenous_crab -> enm_indigenous_poolshark", self.text)


class RegistryTests(unittest.TestCase):
    def test_every_logged_enemy_uid_is_built_in(self):
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "harvest_enemy_uids.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_round45_ardolis_templates_are_known_on_a_new_save(self):
        g = Game(settings={"enemy_randomizer": True})
        for uid, name in (("D573FD6C7356185A", "enm_pirate_bladeball"), ("EC937BD706908861", "enm_pirate_robot_shooter"),
                          ("DA549D2B38D986A2", "enm_indigenous_crab"), ("F59DA44E48BF9954", "enm_indigenous_puffoid"),
                          ("BA312C9E31A934D2", "enm_pirate_robot_melee"), ("A7D580A815B5D5E1", "enm_neo_nefarious_shooter"),
                          ("99CBD30445460E36", "enm_indigenous_poolshark")):
            self.assertEqual(g.lua.eval(V + '.reg_get("%s").name' % uid), name, uid)

    def test_a_template_answering_only_its_name_is_classified(self):
        g = Game(settings={"enemy_randomizer": True})
        k = g.lua.eval(V + '.kind_by_name("enm_pirate_bladeball")')
        self.assertEqual(k.family, "swarmer")
        self.assertEqual(g.lua.eval(V + '.kind_by_name("enm_indigenous_crab").class'), "GameBotMeleeSwarmer")
        # the ground and the jetpack shooter thug share their cut name: never guessed
        self.assertIsNone(g.lua.eval(V + '.kind_by_name("enm_thugs4less_shoo")'))
        self.assertIsNone(g.lua.eval(V + '.kind_by_name("npc")'))

    def test_a_pool_shark_is_never_a_replacement_and_its_spawner_takes_only_flyers(self):
        g = Game(settings={"enemy_randomizer": True})
        g.lua.execute(V + '.new_level("test")')
        lua = g.lua.eval
        lua(V + '.tpl_of(101, "99CBD30445460E36")')       # pool shark
        lua(V + '.tpl_of(102, "D573FD6C7356185A")')       # bladeball (walker)
        lua(V + '.tpl_of(103, "C526EC5AC2659D09")')       # wasp (flyer)
        walkers = lua("(function() local t = {} for _, T in ipairs(%s.pool('walker', {})) do t[#t + 1] = T.name end "
                      "table.sort(t) return table.concat(t, ',') end)()" % V)
        self.assertNotIn("poolshark", walkers)
        self.assertIn("bladeball", walkers)
        self.assertEqual(lua(V + '.SOURCE_ONLY.GameBotPoolShark'), "flyer")


class OmegaTests(unittest.TestCase):
    def test_the_live_components_are_searched(self):
        g = Game(settings={"omega_weapons": True})
        O = g.g.RANDO_OMEGA
        self.assertEqual(list(O.CLASSES_LIVE.values()), ["GameInventoryManager", "HeroWeaponManagerLocal", "GameEquipManager"])
        self.assertGreaterEqual(O.MAX_HEADER, 0x2168)

    def test_start_omega_starts_one_omega_and_its_seed_is_valid(self):
        g = Game(settings={"omega_weapons": True, "start_omega": 1, "seed": "dev5-omega"})
        self.assertTrue(g.wait_seed())
        items = list(g.seed.start["items"].values())
        omegas = [i for i in items if i.startswith("omega:")]
        self.assertEqual(len(omegas), 1, items)
        self.assertEqual(g.seed.registry[omegas[0]], "start (start_omega)")
        self.assertFalse(any("RANDO-ERROR" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l])

    def test_start_omega_0_keeps_the_seed(self):
        a = Game(settings={"omega_weapons": True, "seed": "dev5-same"})
        b = Game(settings={"omega_weapons": True, "start_omega": 0, "seed": "dev5-same"})
        self.assertTrue(a.wait_seed() and b.wait_seed())
        self.assertEqual(a.seed.fingerprint, b.seed.fingerprint)

    def test_the_dev_settings_start_with_an_omega(self):
        text = (MOD / "scripts" / "04_rando_settings.lua").read_text(encoding="utf-8")
        self.assertIn("start_omega = 1,", text)
        self.assertIn("omega_weapons = true,", text)


class CollectibleTests(unittest.TestCase):
    def game(self):
        g = hub_game("dev5-spy", {"collectibles": True})
        g.ready()
        return g

    def test_a_spybot_pickup_pays_once_per_plan(self):
        g = self.game()
        g.fire("RYNOPlayPickedUpEvent", RynoId="Sargasso_01")
        g.step(30)
        self.assertTrue(g.state.collected["spybot:1"])
        g.fire("RYNOScriptPickupEvent", RynoId="Sargasso_01")       # the same plan again: nothing new
        g.fire("RYNOPlayPickedUpEvent", RynoId="Sargasso_01")
        g.step(30)
        self.assertFalse(g.state.collected["spybot:2"])
        g.fire("RYNOPlayPickedUpEvent", RynoId="Ardolis_01")
        g.step(30)
        self.assertTrue(g.state.collected["spybot:2"])
        self.assertTrue(g.log_has("RANDO-COLLECTIBLE\tspybot\tArdolis_01"))

    def test_a_lorb_pickup_pays(self):
        g = self.game()
        g.fire("RuinPlayPickedUpEvent", RuinId="Lorb_03")
        g.step(30)
        self.assertTrue(g.state.collected["lorb:1"])

    def test_the_none_id_pays_nothing(self):
        g = self.game()
        g.fire("RYNOPlayPickedUpEvent", RynoId="None")
        g.step(30)
        self.assertFalse(g.state.collected["spybot:1"])


class ShopTests(unittest.TestCase):
    def test_the_dev_settings_shuffle_the_shop_again(self):
        # v0.71-DEV1: the vendor's slots are also looked for as config pointers (tests/test_v071_dev1.py), so the dev
        # settings go back to "shuffle"; "vanilla" stays a setting (test below)
        text = (MOD / "scripts" / "04_rando_settings.lua").read_text(encoding="utf-8")
        self.assertRegex(text, r'\n  shop = "shuffle",')

    def test_a_vanilla_shop_seed_never_places_a_vendor_weapon(self):
        g = Game(settings={"shop": "vanilla", "seed": "dev5-shop"})
        self.assertTrue(g.wait_seed())
        vendor = [k for k, it in g.data["items"].items() if it.category == "weapon" and it.vendor]
        placed = {l.item for l in g.seed.locations.values() if l.item}
        self.assertEqual([k for k in vendor if k in placed], [])

    def test_the_vendor_config_is_probed_read_only(self):
        g = Game(settings={"seed": "dev5-probe"})
        g.ready()
        self.assertTrue(g.log_has("PROBE vendor config"), [l for l in g.logs() if "SHOP" in l][-5:])


class DevDebugTests(unittest.TestCase):
    DEBUG = DEV_DIR / "dev(debug).lua"

    def game(self, extra=()):
        files = script_files(release=True) + [self.DEBUG] + [DEV_DIR / n for n in extra]
        files = sorted(files, key=lambda p: p.name)
        g = to_hub(hub_game("dev5-debug", files=files))
        return g

    def test_it_is_built_from_the_single_files(self):
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_dev_debug.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_loads_with_its_sections_and_names_one_developer_file(self):
        g = self.game()
        self.assertEqual(g.load_errors, [])
        ran = py(g.g.RANDO_DEV_DEBUG.ran)
        for s in ("warp", "keys", "testtravel", "testmode", "omega_probe"):
            self.assertTrue(ran.get(s), s)
        for s in ("probe", "spawnprobe", "spawnproof"):
            self.assertFalse(ran.get(s), s)
        self.assertTrue(g.log_has("developer files loaded (diagnostics, not part of a release - remove them for normal play): dev(debug)"))
        self.assertFalse(any("RANDO-ERROR" in l or "[sim]" in l for l in g.logs()), [l for l in g.logs() if "ERROR" in l or "[sim]" in l])

    def test_a_single_file_next_to_it_stands_down(self):
        g = self.game(extra=("dev(keys).lua",))
        self.assertFalse(g.log_has("is used twice"), [l for l in g.logs() if "twice" in l])

    def test_warp_to_any_planet_and_room(self):
        g = self.game()
        W = g.g.RANDO_DEV_DEBUG.warp
        target = "savali"
        for _ in range(12):
            g.press("HOME")
            if W.selected() == target:
                break
        self.assertEqual(W.selected(), target)
        rooms = list(W.rooms(target).values())
        self.assertGreater(len(rooms), 0)
        g.press("PAGEDOWN")
        cp = rooms[1 % len(rooms)]
        n = len(g.sim.warps)
        g.press("END")
        self.assertEqual(len(g.sim.warps), n + 1)
        self.assertEqual(list(g.sim.warps.values())[-1], cp)
        for _ in range(30):
            g.step(30)
        self.assertEqual(g.state.current_planet, target)
        self.assertTrue(any("[DEBUG WARP] warp to savali" in str(h) for h in g.state.history.values()))

    def test_unstuck_warps_back_to_the_last_checkpoint(self):
        g = self.game()
        g.sim.checkpoint("CHK_NEFCITY_SHIP")
        g.step(5)
        n = len(g.sim.warps)
        g.press("INSERT")
        self.assertEqual(len(g.sim.warps), n + 1)
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_SHIP")
        g.press("INSERT")                                          # again within 5 s: the one before it
        self.assertEqual(list(g.sim.warps.values())[-1], "CHK_NEFCITY_START")


class KitTests(unittest.TestCase):
    def test_one_version_everywhere(self):
        for p in list((MOD / "scripts").glob("*.lua")) + list(DEV_DIR.glob("*.lua")):
            tags = set(re.findall(r'RANDO_FILES\["[^"]+"\] = "([^"]+)"', p.read_text(encoding="utf-8")))
            self.assertEqual(tags, {"10.0.39"}, p.name)

    def test_the_banner(self):
        g = Game(settings={"seed": "dev5-banner"})
        g.ready()
        self.assertTrue(g.log_has("RANDO-KIT release v0.75 (kit 10.0.39)"))


if __name__ == "__main__":
    unittest.main()
