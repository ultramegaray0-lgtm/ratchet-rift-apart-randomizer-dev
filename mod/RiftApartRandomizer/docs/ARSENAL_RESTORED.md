# ARSENAL_RESTORED and the Randomizer (7.0, 8.1)

## 8.1: the rivet_hook version

ARSENAL_RESTORED also comes as a rivet_hook version (5.7 Beta). rivet_hook loads loose asset mods
only from the paths under `[assets] paths` in rivet.toml. 8.0's rivet.toml listed only
`mods/default`, so a copied mod folder was never loaded. 8.1's rivet.toml lists
`mods/ARSENAL_RESTORED` and `mods/ARSENAL_RESTORED.stage`. `companion\Install-ArsenalRestored.bat`
(drag the zip onto it) does three things:

- copies the mod's info.json folder or .stage there;
- copies the mod's .lua files into `scripts` (never over a randomizer file);
- adds the path to rivet.toml if it is missing.

The companion finds this version through rivet.toml: a listed path whose name, info.json or file
names say ARSENAL_RESTORED, or that holds the Mr. Zurkon asset id. It also warns about a copy in
`mods` that rivet.toml doesn't list. The mod itself is still not shipped in the randomizer's
folder (the author's files, the author's permission). rivet.log shows it loading:
`[loader] mod path mods/ARSENAL_RESTORED is overstrike format.`


## Status

ARSENAL_RESTORED's 9 weapons are **part of the unified weapon pool**, and are used **only when the
mod is installed**. They are **not bundled** into the randomizer: the mod's assets (models,
effects, sounds, configs) were not available to this build, and re-shipping them needs the mod
author's permission. You install the mod as before (Overstrike), and the randomizer detects it.

## How 7.0 detects it (`restored_weapons = "auto"`, the default)

1. The base game ships the **item configs** of 8 of these weapons (their ids are in your game's
   dag). The mod makes them work and **adds** one asset of its own: Mr. Zurkon's item config (asset
   id `B9CBAD67F39CCC3F`, from the phase 1 research).
2. Overstrike lists an installed mod's assets in the game's `toc`. The companion reads the `toc`
   (next to RiftApart.exe, found from the running game, or `-GameDir`) and looks for that id.
   It only reads the file.
3. Found: the companion tells the game, and the seed is generated with the 9 weapons in the pool
   (shop slots, start, reward locations). Not found, or the toc can't be read: they stay out.
   rivet.log says which (`RANDO-SEED ARSENAL_RESTORED ...`), and so does the companion window.
4. Without the companion, the game waits 1 minute for its answer, then treats the mod as not
   installed. A restored weapon is never handed out on a guess.

The answer is part of the seed's settings, so installing or removing the mod gives a different
seed (start it with New Game). `restored_weapons = true` / `false` skips the check.

## Investigation: what is actually known about these weapons

| Weapon | Item config | In your game |
|---|---|---|
| Predator Launcher | `wpn_predator_launcher_item.config` | delivered and confirmed in rounds 13, 14, 16 (mod installed) |
| Volcanic Eruptor | `wpn_volcaniceruptor_item.config` | confirmed in rounds 14, 16 |
| Schrodinger | `wpn_schrodinger_item.config` | confirmed in round 13 |
| Combuster, Fusion Grenade, Magnamissile, Sheepinator, Thumper | see WEAPONS.md | in the base game's dag; not delivered in a logged round yet |
| Mr. Zurkon | `wpn_mr_zurkon_item.config` | added by the mod (not in the base game's dag) |

"Confirmed" means the game reported the weapon added to the inventory (`WeaponAddedEvent`) when
the randomizer gave it by config. Whether each one fires correctly without the mod hasn't been
tested. That's why the pool takes them only when the mod is there.

**Other cut weapons.** 7.0 re-checked the 11 other unused weapon configs (Nailgun, Revolver,
Groovitron, Blunderbuster, Detcord, Pit of Death, Plasma Striker, Pyrocitor, Seismic Shock, Sticky
Blaster, Zurkon). None was found to be functional:
- Nailgun and Revolver have empty weapon types in the game's type data;
- Nailgun never answered in 9 tries;
- the rest have never been delivered.

They stay out ("never sell a weapon that can't be equipped or fired").

**If the mod also sells them in slots of its own,** those slots are left alone, so a restored
weapon could be sold there and be in the seed too. rivet.log says so (`also sells ... it may come
twice`). That isn't a softlock.

## What bundling would still take

To make the randomizer one install that *contains* these weapons:
1. the `.stage` file (or the installed `d\mods\mod0` plus the dag) to read every asset;
2. per weapon: weapon config, model/material/texture chain, effects, sounds, ammo and upgrade
   data, vendor entry, localization;
3. any Lua the mod ships;
4. the author's permission to redistribute.

The randomizer side is already complete: the weapons are in the registry with their ids, and the
pool takes them when enabled.
