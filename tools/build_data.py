"""Builds the Randomizer 2.0 game database from real sources:

  data/sources/dag_item_ids.json          your game's dag: asset id -> config path (919 entries)
  data/sources/v1_seed_lombax-ryno-2026.json   the 1.x model as exported with the 1.x seed
                                          (planets, mission codes, event names, Gold Bolt
                                          requirements, side activities, gadget type ids
                                          reported by your game)
  CURATED below                           names and per-entry provenance

Writes data/game_db.json (reference) and mod/RiftApartRandomizer/scripts/01_rando_data.lua.
No item id is typed by hand: every id is looked up in the dag table by config path, except
Mr. Zurkon, whose config is added by ARSENAL_RESTORED (id from the 1.x research, which hashed
the mod's added asset ids).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources")
OUT_JSON = os.path.join(ROOT, "data", "game_db.json")
OUT_LUA = os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts", "01_rando_data.lua")

DATA_VERSION = "5.1.0"

# ---------------------------------------------------------------------------------------------
# curated: what each entry is, and how sure we are
# ---------------------------------------------------------------------------------------------
ARSENAL_RESTORED = {"combuster", "fusion_grenade", "magnamissile", "predator_launcher", "schrodinger",
                    "sheepinator", "thumper", "volcanic_eruptor", "mr_zurkon"}
# delivered into the real inventory in your game (rivet.logs, rounds 8-13)
WEAPONS_VERIFIED_IN_GAME = {"predator_launcher", "headhunter", "warmonger", "schrodinger", "bombardier",
                            "glove_of_doom", "negatron_collider"}
GADGETS_VERIFIED_IN_GAME = {"box_breaker", "hoverboots"}

# ---------------------------------------------------------------------------------------------
# 6.0 the weapon registry: how each weapon is obtained in a randomized game
#   pool         shop-or-reward: one of the 15 normal vendor slots, the start, or a location
#   shop_fixed   sold by the vendor in its own slot, never moved, never a reward
#   start_fixed  the game gives it at the start (no weapon since data 5.1.0)
#   reward       5.1.0: an item of the pool that is always a reward at a location (never sold in one
#                of the 15 normal slots, never a random start weapon); the vendor slot it has in the
#                normal game is closed by 12_rando_shop.lua, so the reward is its only route
#   arsenal_restored  needs the separate ARSENAL_RESTORED mod: off unless include_arsenal_restored
#   disabled     a cut weapon (empty type data, or never answered when given): never placed
# Vanilla routes from the guides (PowerPyx "All Weapons": every weapon is bought from Ms. Zurkon;
# Shatterbomb 1,250 bolts; RYNO after all 10 Spybots for 0 bolts; Bouncer and Pixelizer only in
# Challenge Mode).
WEAPON_ACQUISITION = {
    # 5.1.0 (asked for): Burst Pistol, Shatterbomb and RYNO 8 are items of the pool, found at locations
    "burst_pistol": ("reward", "the starting weapon (owned on a fresh save, round 14); the game still hands it out in the prologue, so its reward adds nothing new until that copy can be taken away"),
    "shatterbomb": ("reward", "Ms. Zurkon, 1,250 bolts, unlocked by the prologue; now a reward (its vendor slot is closed)"),
    "ryno_8": ("reward", "Ms. Zurkon for 0 bolts after all 10 Spybots; now a reward (its vendor slot is closed)"),
    "pixelizer": ("pool", "vanilla: Challenge Mode vendor only, so a normal game never sells it: the randomizer gives it a route"),
    "bouncer": ("pool", "vanilla: Challenge Mode vendor only, so a normal game never sells it: the randomizer gives it a route"),
}
# what each delivery evidence is (rivet.log rounds where the game confirmed the item config)
WEAPON_EVIDENCE = {
    "burst_pistol": "owned from the start on every logged new game (rounds 14-16)",
    "blackhole_storm": "wpn_warprifle confirmed in round 13 (then named Headhunter)",
    "predator_launcher": "confirmed rounds 13, 14, 16", "volcanic_eruptor": "confirmed rounds 14, 16",
    "schrodinger": "confirmed round 13", "warmonger": "confirmed round 13",
    "enforcer": "confirmed round 16", "buzz_blades": "confirmed round 16", "ryno_8": "confirmed round 16",
    "drillhound": "already owned when given in round 16 (seen equipped)",
    "bombardier": "delivered in rounds 8-12", "glove_of_doom": "delivered in rounds 8-12",
    "negatron_collider": "delivered in rounds 8-12",
}
MR_ZURKON = ("configs/equipment/wpn_mr_zurkon_item.config", "B9CBAD67F39CCC3F")

# 7.0 vanilla prices in bolts (gamepressure "List of all weapons", checked against PowerPyx and
# attackofthefanboy). The shop uses them to (1) find the Price field of a vendor slot in memory
# (the slot's own vanilla price must be there, in at least 3 slots at the same offset) and (2)
# price a slot by the weapon it now sells (shop_prices = "weapon"). Pixelizer and Bouncer cost 1
# bolt in Challenge Mode: a slot selling them keeps the slot's own price.
VANILLA_PRICE = {
    "shatterbomb": 1250, "enforcer": 1250, "mr_fungi": 3000, "topiary_sprinkler": 4000,
    "negatron_collider": 5000, "ricochet": 6500, "lightning_rod": 8000, "drillhound": 10000,
    "void_repulser": 17500, "cold_snap": 20000, "glove_of_doom": 22500, "bombardier": 25000,
    "buzz_blades": 27500, "warmonger": 30000, "blackhole_storm": 35000, "headhunter": 40000,
    "ryno_8": 0, "burst_pistol": 0,
}
# 7.0 the asset that only exists with ARSENAL_RESTORED installed (Mr. Zurkon's added item config):
# the companion looks for its id in the game's toc to tell whether the mod is installed
ARSENAL_MARKER = MR_ZURKON[1]
# 7.0 travel: checkpoints seen in your rivet.logs (PlanetMenuAcceptEvent, level-script variables)
# and the name fragments the runtime uses to find a planet's landing checkpoint in
# rivet.checkpoints() (warping you back when you fly to a planet you have no Coordinates for)
PLANET_CHECKPOINTS = {
    "corson_v": {"known": [], "codes": ["MEGA", "MALINON", "CORSON"], "areas": ["megalopolis", "malinon", "corson"]},
    "nefarious_city": {"known": ["CHK_NEFCITY_SHIP"], "codes": ["NEFCITY", "NEFARIOUS"], "areas": ["nefcity", "nefarious"]},
    "sargasso": {"known": ["CHK_SARG_GELFACTORY_LANDINGPAD"], "codes": ["SARG"], "areas": ["sargasso"]},
    "scarstu": {"known": ["CHK_ZURK_00_DEFAULT", "CHK_ZURK_LANDING_SHIP"], "codes": ["ZURK"], "areas": ["zurkon", "scarstu"]},
    "savali": {"known": ["CHK_SAV_01_LANDING"], "codes": ["SAV", "SVALI"], "areas": ["savali"]},
    "blizar_prime": {"known": ["CHK_BLIZAR_A_LANDINGPAD"], "codes": ["BLIZAR"], "areas": ["blizar"]},
    "torren_iv": {"known": [], "codes": ["MOL", "MOLONOTH", "TORREN"], "areas": ["molonoth", "torren"]},
    "cordelion": {"known": ["CHK_CORD_A_TELE_SHIP"], "codes": ["CORD", "KEDARO"], "areas": ["kedaro", "cordelion"]},
    "ardolis": {"known": ["CHK_ARD_START"], "codes": ["ARD", "ARDOLIS"], "areas": ["ardolis"]},
    "viceron": {"known": [], "codes": ["ZORD", "ZORDOOM", "VICERON"], "areas": ["zordoom", "viceron"]},
}
# 8.1: "areas" are fragments of rivet.checkpoints()' area field (round 17: Zurkons, Sargasso (open
# world), Blizar_Intact, Blizar_Destroyed, Zordoom, Megalopolis (open world)); the planet tunnels
# are CHK_TRANSITION_TO_<MOL|SARG|KEDARO|ARDOLIS|BLIZAR|NEFARIOUS_CITY|SAVALI|ZORDOOM|ZURKIES>

# weapon configs in the dag that no normal weapon uses. Granting them is untested: their weapon
# configs may lack models or effects. Only used with include_hidden_weapons (experimental).
HIDDEN_WEAPONS = {
    "blunderbuster": "Blunderbuster", "detcord": "Detcord",
    "groovitron": "Groovitron",
    "pitofdeath": "Pit of Death", "plasma_striker": "Plasma Striker", "pyrocitor": "Pyrocitor",
    "seismicshock": "Seismic Shock", "stickyblaster": "Sticky Blaster",
    "zurkon": "Zurkon (unused vanilla config)",
}

# 5.0 (round 16): the 1.x names of three weapon configs were wrong. The game's own type data
# (neptuwunium/rivet, Types/Weapon*Prius.cs) shows what each weapon config is:
#   wpn_warprifle: WeaponWarpRiflePrius - spin-up time, heat states, bullet spread: the minigun,
#                  Blackhole Storm (it reached your inventory in round 13, named "Headhunter")
#   wpn_fossilizer: WeaponFossilizerPrius - aiming slows time, three zoom levels: the sniper,
#                  Headhunter (was listed as a hidden weapon)
#   wpn_nailgun:   never answered in rounds 15 and 16 (9 tries): a cut weapon, not Blackhole Storm
#   wpn_revolver:  "Executor" is the Enforcer's level-5 name, not a weapon of its own; the config
#                  is a cut weapon (it answered once, late, in round 13)
WEAPON_FIXES = {
    # old key -> (new key, name, source, confidence, note)
    "weapon:headhunter": ("weapon:blackhole_storm", "Blackhole Storm", "vanilla", "high",
                          "WeaponWarpRiflePrius (spin-up, heat, spread); delivered in round 13"),
    "weapon:blackhole_storm": ("weapon:nailgun", "Nailgun (cut weapon)", "hidden", "config name",
                               "never answered in rounds 15-16"),
    "weapon:executor": ("weapon:revolver", "Revolver (cut weapon)", "hidden", "config name",
                        "Executor is the Enforcer at level 5; this config answered once, late (round 13)"),
}
HEADHUNTER = ("weapon:headhunter", "configs/equipment/wpn_fossilizer_item.config", "Headhunter",
              "WeaponFossilizerPrius (aiming slows time, zoom levels)")
# dev 10.15 OMEGA VERSIONS. What the game's own type data says (neptuwunium/rivet's DDL dump):
#   * an Omega weapon is NOT an item of its own: there is no wpn_*_omega item config in your dag
#     (919 item ids, none with "omega"), and AddToInventoryAction can only give an item config;
#   * it is the bool WeaponItemPrius.Omega (DDL hash 0x534A51FB) of the weapon you already own
#     (WeaponItemPrius: XP, ammo, Mods, ModGrid, ModCount, SelectedCell, Test, Omega; its base
#     ItemPrius holds ItemGuid, ItemConfigHash = the item config's 64-bit id, ItemCount, ItemId);
#   * the game sets it only through Ms. Zurkon in Challenge Mode: VendorItemData.OmegaPrice,
#     OmegaRequiredCardBonus (a Holocard set), OmegaOnly; WeaponItemConfig has Omega names and
#     descriptions; GameCampaignSave.FirstOmegaWeaponPurchased / IsChallengeMode;
#   * no script action sets it (no GiveOmega / SetOmega node exists in the type data).
# So an Omega reward is "this weapon, with its Omega flag set", and granting the normal weapon
# never makes it Omega. The randomizer keeps the two as separate items (omega:<weapon>).
# Names: the weapon's level-5 name as the guides give it (vulkk gear guide, ludo.guide weapons,
# geekculture); None = no guide line found, so the item is named after the weapon itself.
# Every one of the 20 vanilla weapons gets an Omega item: Challenge Mode raises every weapon's level
# cap to 10 through its Omega version (guides). The 9 ARSENAL_RESTORED weapons and the cut weapons do
# not (their Omega data in your game is unknown).
OMEGA_NAMES = {
    "burst_pistol": "Blast Pistol", "shatterbomb": "Shatterblast", "topiary_sprinkler": "Toxiary Sprinkler",
    "enforcer": "Executor", "negatron_collider": "Large Negatron Collider", "ricochet": "Wreckochet",
    "mr_fungi": "Ms. Fungal", "lightning_rod": "Lightning Strike", "drillhound": "Drillpack",
    "void_repulser": None, "cold_snap": "Cold Front", "glove_of_doom": "Apocalypse Glove",
    "bombardier": "Bomb Voyage", "buzz_blades": "Doom Blades", "warmonger": None,
    "blackhole_storm": "Blackhole Vortex", "headhunter": "Migraine", "ryno_8": "RYNO Infinite",
    "bouncer": "Heavy Bouncer", "pixelizer": "Pixelizer HD",
}
# the guides that list the weapon's Omega version by name (the rest are assumed from "every weapon")
OMEGA_LISTED = {"blackhole_storm", "bombardier", "bouncer", "burst_pistol", "buzz_blades", "cold_snap", "drillhound",
                "glove_of_doom", "headhunter", "lightning_rod", "mr_fungi", "negatron_collider", "ricochet", "ryno_8"}
WEAPON_ITEM_PRIUS_OMEGA_HASH = "534A51FB"

# the vanilla vendor's weapons (Ms. Zurkon): the shop can sell these. Burst Pistol and Shatterbomb
# are owned from the prologue, RYNO 8 comes from Spybots, Pixelizer and Bouncer are Challenge Mode.
VENDOR_WEAPONS = {"topiary_sprinkler", "enforcer", "lightning_rod", "mr_fungi", "ricochet", "drillhound",
                  "void_repulser", "glove_of_doom", "cold_snap", "buzz_blades", "bombardier", "warmonger",
                  "blackhole_storm", "headhunter", "negatron_collider"}

# abilities the story gives that have no item config (cannot be granted)
ABILITIES = {
    "wallrun": "Wallrun", "phantom_dash": "Phantom Dash", "hurlshot": "Hurlshot",
    "speetle": "Speetle mount", "dragon_mount": "Dragon mount (Trudi)", "magboots": "MagBoots",
}

# 5.0 armor. folder -> (display name, findable). findable:
#   "yes"   one of the 8 sets the game hands out (pocket dimensions, Zurkie's challenges, the Lorb
#           monk on Savali): 24 pieces, see docs/ARMOR.md for the guides used
#   "maybe" Robot Disguise and Wasteland Gear are two of these three folders; which two is not in
#           the game files. Their armor sources only ever hold filler, so a folder the game never
#           hands out costs nothing.
#   "start" owned from the start on PC (Deluxe Edition and free sets): 10 sets = 30 pieces, which
#           is exactly the "30 armor pieces owned before this seed" rounds 14, 15 and 16 logged
#   "no"    not a set you can own (the demo outfit)
# 8.5.2 (the user's edit, round 22): Punk and Reaver are owned from the start in the user's game (the
# game refused all three pieces it was sent, and a new game already owns 6 pieces), so they are
# never rewards. Their armor sources stay in the data as filler-only locations, as in the user's
# edited 01_rando_data.lua (START_SETS_WITH_SOURCES).
START_SETS_WITH_SOURCES = {"punk_armor", "reaver_armor"}
ARMOR_SETS = {
    "galactic ranger": ("Galactic Ranger", "yes"), "pirate": ("Robot Pirate", "yes"),
    "carbonox_armor": ("Carbonox Advanced", "yes"), "lombax_armor": ("Lombax Praetorian", "yes"),
    "qforce_armor": ("Q-Force", "yes"), "starshield_armor": ("Captain Starshield", "yes"),
    "punk_armor": ("Punk", "start"), "reaver_armor": ("Reaver", "start"), "warmachine_armor": ("War Machine", "maybe"),
    "android_armor": ("Android", "start"), "emperor_armor": ("Imperial", "start"), "rebellion_armor": ("Rebel", "start"),
    "holoflux_armor": ("Holoflux", "start"), "quest_armor": ("Quest", "start"), "marauder_armor": ("Marauder", "start"),
    "commando_armor": ("Commando", "start"), "clank_armor": ("Clank", "start"),
    "beginning_armor": ("Beginning (default outfit)", "start"), "carbonox_preorder_armor": ("Carbonox (pre-order)", "start"),
    "handondemo": ("Demo outfit", "no"),
}
ARMOR_PART_NAMES = {"head": "helmet", "torso": "chest", "legs": "boots"}

# 5.0 filler: currency item configs (CurrencyItemConfig) given like any other item, with a count
CURRENCY = {
    "bolts": ("configs/pickup/pup_bolt_item.config", "Bolts", "GainBoltEvent"),
    "raritanium": ("configs/pickup/pup_raritanium_item.config", "Raritanium", "GainRaritaniumEvent"),
}

# experimental pickup items (AddToInventory with a pickup config: effect untested)
PICKUPS = {
    "weapon_upgrade": ("configs/hpz/pup_hpz_weaponupgrade.config", "Weapon upgrade"),
    "major_weapon_upgrade": ("configs/hpz/pup_hpz_majorweaponupgrade.config", "Major weapon upgrade"),
}

# collectibles: key -> (name, count, pickup config, planet, item location). Their pickup is not bound
# to a game event yet (05_rando_bindings.lua collectible_events): a location is "the n-th one found",
# counted in pickup order, so a Spybot location has no planet of its own.
# 5.1.0 (asked for): Spybots and Lorbs hold items. The game has 10 Spybots (all 10 for RYNO 8) and
# 12 Lorbs, all on Savali (guides: PowerPyx, Push Square). They are never in logic (the trigger is
# unproven), so only non-progression rewards go there. CraiggerBears stay unused (3 = a floor).
COLLECTIBLES = {
    "spybot": ("Spybot", 10, "configs/pickup/pup_ryno_plan_item.config", None, True),
    "lorb": ("Lorb", 12, None, "savali", True),
    "craiggerbear": ("CraiggerBear", 3, None, None, False),
}

STORY_HERO = {}   # not used by logic


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def build():
    dag = load("dag_item_ids.json")
    by_path = {v: k for k, v in dag.items()}
    v1 = load("v1_seed_lombax-ryno-2026.json")

    def dag_id(path):
        if path not in by_path:
            raise SystemExit("not in the dag: " + path)
        return by_path[path]

    items = {}

    # weapons: the 1.x pool (31), its names and confidence
    for key, info in sorted(v1["real_items"].items()):
        if info["kind"] != "weapon":
            continue
        short = key.split(":", 1)[1]
        path = info["config"]
        if path == MR_ZURKON[0]:
            wid, src_id = MR_ZURKON[1], "arsenal_restored added asset (1.x research)"
        else:
            wid, src_id = dag_id(path), "dag"
        assert wid == info["id"], key
        entry = {
            "category": "weapon", "name": v1["item_names"][key], "config": path, "id": wid,
            "grant": "inventory", "id_source": src_id,
            "source": "arsenal_restored" if short in ARSENAL_RESTORED else "vanilla",
            "name_confidence": info.get("confidence", "high"),
            "verified_in_game": short in WEAPONS_VERIFIED_IN_GAME,
        }
        if key in WEAPON_FIXES:
            new_key, name, source, conf, note = WEAPON_FIXES[key]
            entry.update({"name": name, "source": source, "name_confidence": conf, "note": note,
                          "verified_in_game": key == "weapon:headhunter"})
            if source == "hidden":
                entry["experimental"] = True
            key = new_key
        if key.split(":", 1)[1] in VENDOR_WEAPONS:
            entry["vendor"] = True
        items[key] = entry
    hkey, hpath, hname, hnote = HEADHUNTER
    items[hkey] = {"category": "weapon", "name": hname, "config": hpath, "id": dag_id(hpath), "grant": "inventory",
                   "id_source": "dag", "source": "vanilla", "name_confidence": "high", "note": hnote,
                   "verified_in_game": False, "vendor": True}
    for short, name in sorted(HIDDEN_WEAPONS.items()):
        found = [pth for pth in by_path if pth.endswith(f"/wpn_{short}_item.config") and "/test/" not in pth]
        if len(found) != 1:
            print("hidden weapon skipped (config not found once in the dag):", short, found)
            continue
        path = found[0]
        items["weapon:" + short] = {
            "category": "weapon", "name": name, "config": path, "id": dag_id(path), "grant": "inventory",
            "id_source": "dag", "source": "hidden", "name_confidence": "config name",
            "verified_in_game": False, "experimental": True,
        }

    # gadgets with item configs (type ids as your game reported them)
    gadget_type = {v: int(k) for k, v in v1["gadget_type_ids"].items()}
    for key, info in sorted(v1["real_items"].items()):
        if info["kind"] != "gadget":
            continue
        assert dag_id(info["config"]) == info["id"], key
        items[key] = {
            "category": "gadget", "name": v1["item_names"][key], "config": info["config"], "id": info["id"],
            "type_id": gadget_type.get(key), "grant": "inventory", "id_source": "dag",
            "verified_in_game": key in GADGETS_VERIFIED_IN_GAME,
        }
    for key, name in sorted(ABILITIES.items()):
        items["ability:" + key] = {"category": "ability", "name": name, "grant": "none",
                                   "note": "given by the story; no item config to grant"}

    # armor: one item per bundle (head/torso/legs) of each set
    armor_sets = []
    for path in sorted(by_path):
        m = re.match(r"configs/hero/vanity/vanitybundles/([^/]+)/hero_vanity_bundle_(head|torso|legs)_.*\.config$", path)
        if not m:
            continue
        folder, part = m.groups()
        name, findable = ARMOR_SETS[folder]
        set_key = re.sub(r"[^a-z0-9]+", "_", folder.lower()).strip("_")
        key = f"armor:{set_key}_{part}"
        items[key] = {
            "category": "armor", "name": f"{name} {ARMOR_PART_NAMES[part]}", "config": path, "id": by_path[path],
            "set": set_key, "part": part, "grant": "vanity", "id_source": "dag",
            "randomizable": findable in ("yes", "maybe"), "findable": findable,
            "owned_from_start": findable == "start",
        }
        if (findable in ("yes", "maybe") or set_key in START_SETS_WITH_SOURCES) and set_key not in [s["key"] for s in armor_sets]:
            armor_sets.append({"key": set_key, "name": name, "findable": findable})

    for key, (path, name, event) in sorted(CURRENCY.items()):
        items["currency:" + key] = {"category": "currency", "name": name, "config": path, "id": dag_id(path),
                                    "grant": "inventory", "id_source": "dag", "event": event,
                                    "note": "CurrencyItemConfig, given with a count (5.0 filler; not run in game yet)"}
    for key, (path, name) in sorted(PICKUPS.items()):
        items["pickup:" + key] = {"category": "pickup", "name": name, "config": path, "id": dag_id(path),
                                  "grant": "inventory (experimental: effect untested)", "id_source": "dag",
                                  "experimental": True}

    # planets
    bind_planets = {"Savali": "savali", "Blizar": "blizar_prime", "Cordelion": "cordelion",
                    "Viceron": "viceron", "Zurkon": "scarstu"}
    event_names = dict(v1["planet_event_names"])
    event_names.update(bind_planets)
    planets = []
    for idx, pid in enumerate(v1["planet_order"]):
        planets.append({
            "id": pid, "name": v1["planet_names"][pid], "story_index": idx + 1,
            "event_names": sorted(n for n, p in event_names.items() if p == pid),
            "codes": v1["planet_codes"][pid],
            "bolt_prefixes": sorted(pre for pre, p in v1["bolt_prefixes"].items() if p == pid),
        })
        items["access:" + pid] = {"category": "coordinates", "name": v1["item_names"]["access:" + pid],
                                  "planet": pid, "grant": "randomizer"}

    # locations
    locs = {}
    order = v1["planet_order"]
    for p in planets:
        pid = p["id"]
        locs["planet:" + pid] = {"kind": "planet", "planet": pid, "name": p["name"] + ": first story mission",
                                 "trigger": "story_mission", "count": 1, "requires": [], "verified": "game",
                                 "progression": True}
        nxt = order.index(pid) + 1
        if nxt < len(order) and pid != order[-1]:
            locs["story2:" + pid] = {"kind": "story", "planet": pid, "name": p["name"] + ": second story mission",
                                     "trigger": "story_mission", "count": 2, "requires": [],
                                     "fallback": "next_planet", "verified": "mechanism (game), count per planet: guide",
                                     "progression": True}
    for lid, loc in sorted(v1["locations"].items()):
        if loc["kind"] == "side":
            locs[lid] = {"kind": "side", "planet": loc["planet"], "name": side_name(lid), "trigger": "binding",
                         "fallback": "with_planet", "requires": [], "verified": "fallback only",
                         "progression": True}
    for pid, bolts in sorted(v1["gold_bolts_by_planet"].items()):
        for b in bolts:
            reqs = []
            for atom in b["requires"]:
                if atom.startswith("main:") or atom.startswith("done:"):
                    continue                       # story progress: always reached eventually
                if atom in ABILITIES:
                    reqs.append("ability:" + atom)
                else:
                    reqs.append(atom)              # a gadget item key
            locs[b["id"]] = {"kind": "goldbolt", "planet": pid, "name": f"{v1['planet_names'][pid]} Gold Bolt",
                             "trigger": "gold_bolt", "requires": sorted(reqs), "verified": "event (game), requirements: guide",
                             "progression": True}
    # 5.0: every armor piece the game hands out is a location (its armor source: a pocket
    # dimension, a Zurkie's challenge, the Lorb monk). rando_give.dll v5 stops the game's own
    # VanityGiveBundleAction for that piece and the randomizer gives the location's item instead.
    for key in sorted(items):
        it = items[key]
        if it["category"] != "armor" or not (it["findable"] in ("yes", "maybe") or it["set"] in START_SETS_WITH_SOURCES):
            continue
        sid = key.split(":", 1)[1]
        locs["source:" + sid] = {"kind": "armor_source", "planet": None, "armor": key,
                                 "name": f"armor source of the {it['name']}", "trigger": "armor_source",
                                 "requires": [], "progression": False,
                                 "holds": "any" if it["findable"] == "yes" else "filler",
                                 "verified": "VanityGiveBundleAction intercept (rando_give.dll v5, not run in game yet)"}
    for key, (name, count, _cfg, planet, holds) in sorted(COLLECTIBLES.items()):
        for n in range(1, count + 1):
            loc = {"kind": "collectible", "collectible": key, "planet": planet,
                   "name": f"{name} found #{n}", "trigger": "collectible", "count": n,
                   "requires": [], "verified": "no event bound yet (experimental)",
                   "progression": False, "experimental": True}
            if holds:
                loc["holds"] = "any"
                loc["verified"] = "item location (5.1.0); pays once its pickup event is bound in 05_rando_bindings.lua (never seen in a rivet.log yet)"
            locs[f"{key}:{n}"] = loc            # "spybot:7": the key R.on_collectible completes

    # 6.0 acquisition and evidence for every weapon (the registry)
    for key, it in items.items():
        if it["category"] != "weapon":
            continue
        short = key.split(":", 1)[1]
        if short in WEAPON_ACQUISITION:
            acq, route = WEAPON_ACQUISITION[short]
        elif it.get("vendor"):
            acq, route = "pool", "Ms. Zurkon, one of the 15 normal vendor slots (unlocked by the story)"
        elif it.get("source") == "arsenal_restored":
            acq, route = "arsenal_restored", "only exists as a weapon with the separate ARSENAL_RESTORED mod"
        else:
            acq, route = "disabled", "cut weapon: " + (it.get("note") or "unused config, never placed")
        it["acquisition"] = acq
        it["vanilla_route"] = route
        if short in VANILLA_PRICE:
            it["price"] = VANILLA_PRICE[short]
        it["evidence"] = WEAPON_EVIDENCE.get(short, "verified_in_game" if it.get("verified_in_game") else "not delivered in a logged round yet")
        it.pop("experimental", None) if acq != "disabled" else it.update({"experimental": True})
    assert sum(1 for it in items.values() if it.get("acquisition") == "pool") == 17
    # dev 10.15: one Omega item per vanilla weapon (see OMEGA_NAMES)
    for short, upgraded in sorted(OMEGA_NAMES.items()):
        w = items["weapon:" + short]
        assert w["source"] == "vanilla" and w["acquisition"] in ("pool", "reward"), short
        items["omega:" + short] = {
            "category": "omega", "weapon": "weapon:" + short, "id": w["id"], "config": w["config"],
            "name": "Omega " + w["name"], "game_name": "Omega " + (upgraded or w["name"]),
            "grant": "omega flag", "omega_field": "WeaponItemPrius.Omega (0x" + WEAPON_ITEM_PRIUS_OMEGA_HASH + ")",
            "evidence": ("Omega version listed by name in the guides" if short in OMEGA_LISTED
                         else "assumed: the guides say every weapon has one, none lists this one by name"),
            "verified_in_game": False,
        }
    assert sum(1 for it in items.values() if it["category"] == "omega") == 20
    assert all(items["weapon:" + k].get("price") for k in VENDOR_WEAPONS)
    for p in planets:
        p["checkpoints"] = PLANET_CHECKPOINTS[p["id"]]
    real_items = {k: {"config": v["config"], "id": v["id"], "kind": v["category"], **({"type_id": v["type_id"]} if v.get("type_id") else {})}
                  for k, v in items.items() if v.get("grant") in ("inventory", "vanity") or v["category"] in ("pickup", "currency")}
    db = {
        "version": DATA_VERSION,
        "planets": planets,
        "items": items,
        "locations": locs,
        "armor_sets": armor_sets,
        "start_kit": v1["starting_gadgets"],
        "real_items": real_items,
        "real_nodes": v1["real_nodes"],
        "bolt_prefixes": v1["bolt_prefixes"],
        "arsenal_marker": ARSENAL_MARKER,
        "filler": {k: {"item": "currency:" + k, "name": v[1]} for k, v in CURRENCY.items()},
        "provenance": {
            "item ids": "your game's dag (data/sources/dag_item_ids.json); Mr. Zurkon from ARSENAL_RESTORED's added assets",
            "gadget type ids": "GadgetItemAddedEvent.ConfigTypeHash reported by your game (round 13)",
            "planets, story order, mission codes, Gold Bolt requirements, side activities": "1.x model (guide + dag), unchanged",
            "armor": "vanity bundle configs in the dag; armor sources are found in the loaded level scripts at runtime (VanityGiveBundleAction)",
            "weapon names (5.0)": "Weapon*Prius types in the game's type data (neptuwunium/rivet): warprifle = Blackhole Storm, fossilizer = Headhunter",
            "start_kit": "1.x model assumption (the gadgets the game gives at the start)",
            "weapon prices (7.0)": "gamepressure 'List of all weapons' (15 vendor weapons + Shatterbomb); used only after the runtime finds the same numbers in your game's vendor config",
            "omega versions (dev 10.15)": "WeaponItemPrius.Omega in the game's type data (neptuwunium/rivet); names from the guides; no separate item id exists",
            "planet checkpoints (7.0)": "PlanetMenuAcceptEvent / level-script variables in your rivet.logs (rounds 13-16); name fragments for rivet.checkpoints()",
        },
    }
    return db


def side_name(lid):
    return {
        "side:ardolis_mapomatic": "Ardolis: Map-O-Matic side activity",
        "side:blizar_chef": "Blizar Prime: the chef's side activity",
        "side:sargasso_trudi": "Sargasso: Trudi activity",
        "side:zurkies_bronze": "Zurkie's Battleplex: Bronze Cup",
        "side:zurkies_silver": "Zurkie's Battleplex: Silver Cup",
        "side:zurkies_gold": "Zurkie's Battleplex: Gold Cup",
    }.get(lid, lid)


def lua(v, ind=""):
    if isinstance(v, dict):
        if not v:
            return "{}"
        parts = []
        for k in sorted(v, key=str):
            key = k if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(k)) and k not in ("end", "and", "or", "not", "nil", "true", "false", "function", "local", "repeat", "until", "then", "do", "in", "if", "else", "elseif", "while", "for", "return", "break", "goto") else "[" + json.dumps(str(k)) + "]"
            parts.append(f"{ind}  {key} = {lua(v[k], ind + '  ')}")
        return "{\n" + ",\n".join(parts) + "\n" + ind + "}"
    if isinstance(v, list):
        if not v:
            return "{}"
        if all(not isinstance(x, (dict, list)) for x in v):
            return "{ " + ", ".join(lua(x) for x in v) + " }"
        return "{\n" + ",\n".join(ind + "  " + lua(x, ind + "  ") for x in v) + "\n" + ind + "}"
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(v, ensure_ascii=True)


def main():
    db = build()
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(OUT_LUA, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Randomizer 7.0 game database (data " + DATA_VERSION + "). Generated by tools/build_data.py from your game's dag and\n"
                "-- the 1.x model - do not edit by hand (see data/game_db.json for provenance).\n")
        f.write('RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["01_rando_data"] = "10.0.36"   -- the kit check (10_rando_runtime.lua)\n')
        f.write("-- 8.5.2: Punk and Reaver are owned from the start in your game (round 22: the game refused all three\n"
                "-- pieces it was sent, and a new game already owns 6 pieces), so they are never rewards.\n")
        f.write("RANDO_DATA = " + lua(db) + "\n")
    cats = {}
    for it in db["items"].values():
        cats[it["category"]] = cats.get(it["category"], 0) + 1
    kinds = {}
    for loc in db["locations"].values():
        kinds[loc["kind"]] = kinds.get(loc["kind"], 0) + 1
    print("items", cats, "locations", kinds)
    # the weapon registry, on its own (docs and the independent validator read it)
    reg = {k: {f: v.get(f) for f in ("name", "config", "id", "source", "acquisition", "vanilla_route", "evidence", "vendor", "verified_in_game", "price")}
           for k, v in db["items"].items() if v["category"] == "weapon"}
    with open(os.path.join(ROOT, "data", "weapon_registry.json"), "w", encoding="utf-8") as f:
        json.dump({"data_version": DATA_VERSION, "weapons": reg}, f, indent=1, sort_keys=True)
        f.write("\n")
    # docs/WEAPONS.md, the readable registry
    acq_text = {"pool": "pool: shop slot, start or reward (decided by the seed)",
                "shop_fixed": "shop, own slot (never moved)", "start_fixed": "start (the game's)",
                "reward": "reward at a location (its own vendor slot closed)",
                "arsenal_restored": "pool, only with ARSENAL_RESTORED installed (restored_weapons)",
                "disabled": "never placed (cut weapon)"}
    order = ["reward", "start_fixed", "shop_fixed", "pool", "arsenal_restored", "disabled"]
    lines = ["# Weapon registry (data " + DATA_VERSION + ")", "",
             "Generated by `tools/build_data.py` from your game's dag (item ids) and `data/weapon_registry.json`.",
             "Every weapon has exactly one route in a seed. Ids are the game's 64-bit asset ids of the item configs.",
             "Ammunition, upgrades, Omega versions and icons are the game's own: the randomizer only decides",
             "how you get a weapon, never what it does.", "",
             "| Weapon | Item config | Asset id | Route in 7.0 | Normal game | Vanilla price | In-game evidence |", "|---|---|---|---|---|---|---|"]
    for a in order:
        for k in sorted(reg, key=lambda k: reg[k]["name"]):
            w = reg[k]
            if w["acquisition"] != a:
                continue
            lines.append(f"| {w['name']} | `{w['config'].split('/')[-1]}` | `{w['id']}` | {acq_text[a]} | {w['vanilla_route']} | {w['price'] if w.get('price') is not None else ''} | {w['evidence']} |")
    lines += ["", "Counts: " + ", ".join(f"{a} {sum(1 for w in reg.values() if w['acquisition'] == a)}" for a in order), ""]
    with open(os.path.join(ROOT, "mod", "RiftApartRandomizer", "docs", "WEAPONS.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
