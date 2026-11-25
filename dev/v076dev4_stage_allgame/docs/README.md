# Rift Apart Randomizer v0.76-DEV4: all-planet .stage Enemy Randomizer (stage_allgame 2.0.0)

## What your last run proved

Your 2026-11-25 log shows **4 of the 5** Phase B spawners worked, not 2:

| Spawner | Change | Spawn point | Result |
|---|---|---|---|
| FF06CCC2A9AC1EA2 | shooter → brawler | volume | **WORKED** |
| 9C3139C7FFED7137 | shooter → bladeball | volume | **WORKED** (killed 8 s after it spawned) |
| FA5FB32C7AAB4C4A | puffoid → crab ×3 | external | **WORKED** |
| DAFCA25C58FD387F | puffoid → crab ×4 | external | **WORKED** |
| F93E9AE445CCEF41 | shooter ×5 → brawler | external | NO SPAWN |

So both spawn-point routes work in the game: local volumes, and spawn points that live in another zone. This build keeps
all 4. F93E9AE4 goes back to the game's own shooters. The new tool can also resolve its external spawn point when it
scans the whole game: if that point is a shooter anim clue, the same rule that caught CECB812E explains the NO SPAWN.

## Read this first: what is built here and what runs on your PC

The `.stage` method can only edit zones the builder can read. I have exactly **one** of the game's zones,
`ard_firstvisit_gp.zone`, which was inside your current `.stage`. I rebuilt it from that file, and its sha256 matches
the game's. Every other planet's zones are in your game's archives, and they never leave your PC.

So this package has two parts:

1. **`BUILD_ALL_PLANETS.bat`**: the all-planet builder. It reads every zone your game's `dag` lists (all planets,
   revisits, mission variants). It decides every enemy spawner with the rules below, writes one `RandoEnemies.stage`
   with every changed zone, checks it against your game files, and offers to install it. It is read-only on the game
   until you say yes to install, and install backs up first. The scan takes minutes; the free `pip install lz4`
   makes decompression about 100x faster.
2. **`prebuilt_ardolis/`**: the Ardolis zone built here and ready now. 9 spawners (about 25 enemies) instead of 5.

The all-planet numbers (how many spawners, per planet) exist only after the builder has run on your game. Its
`COVERAGE_REPORT.md` gives them. I did not guess them.

## Install

**All planets (recommended):** put this folder anywhere. Double-click `BUILD_ALL_PLANETS.bat` and drag your game folder
in. It needs Python 3 (free); the old stage tool already used it. When it asks, answer Y to install.

Install copies three files, after backing up the current ones to `<game>\rando_stage_backup\<time>\`:

- `mods\RandoEnemies.stage`
- `scripts\18_rando_stage_manifest.lua`
- `scripts\18_rando_stage_enemies.lua`

The last one is updated so it scales to hundreds of changes; your other scripts and `rivet.toml` are not touched.

**Ardolis only (by hand):** copy `prebuilt_ardolis\RandoEnemies.stage` to `<game>\mods\`. Copy
`prebuilt_ardolis\18_rando_stage_manifest.lua` and `prebuilt_ardolis\18_rando_stage_enemies.lua` to `<game>\scripts\`.

**Fallback:** every build also writes a `safe\` folder with single-owner spawners only. Use it if the main build
misbehaves somewhere: same install, from `...\safe`.

**Uninstall:** run `python -I tools\stage_enemies\stage_allgame.py uninstall --game "<game>"`. It restores the newest
backup.

## After playing

Keep the Enemy Randomizer **ON** (the `-` key) while you play: it is what lists the spawners, and the log check needs
it.

Then run `CHECK_MY_LOG.bat`. For each changed spawner it gives WORKED, ORIGINAL SPAWNED, NO SPAWN or NOT REACHED, with
totals per planet and per tier. It saves the verdicts in `verdicts\`.

The next `BUILD_ALL_PLANETS.bat` reads those verdicts automatically:

- spawners that WORKED are kept as "confirmed";
- spawners with ORIGINAL SPAWNED or NO SPAWN go back to the game's own enemy;
- a shared-variable spawner that WORKED unlocks its node class for the whole game.

So each play session makes the next build more reliable and, through that last point, larger.

## The rules (why a spawner is or is not changed)

| | Rule | Why |
|---|---|---|
| R1 | The spawner's Templates variable has one owner. **Max profile:** also a shared one, if every co-owner node class was seen on a shared variable whose change worked. | The kit's runtime writes the variable itself (`V.write_var`), so DEV3's 4 shared-variable successes on Ardolis are the same change. Co-owner class `F512DB23` is never changed: both of its spawners kept their original. |
| R2 | The reference is local and consistent: uid plus Zone Actors index. | The proven method, unchanged |
| R3 | Both kinds are regular enemies: ground, swarmer, flyer or turret. | Bosses, mounts, vehicles, NPCs, "unclear" bot classes stay. |
| R4 | The replacement is a template a native factory of the same zone spawns from, and one native factory keeps it (the anchor). | A zone can only reference its own actors. |
| R5 | The pair is proven in game, or same faction and same movement group (the kit's KILLABLE rule). | Your round 63 log: cross-faction replacements spawned and never died. |
| R6 | Every spawn point can host the replacement: a volume always, an anim clue only if the game itself spawns that kind there. | The CECB812E root cause, now learned from the whole game's data |

Every enemy spawner of the game is in `inventory.csv` with its decision and reason. `COVERAGE_REPORT.md` has totals
per planet and per zone, the replacement kinds, and the reasons table.

## Not possible with this method

**Mixing enemies from other planets.** A spawner can only point at a template actor of its own zone. Each zone offers
the enemy kinds it already holds, so variety comes from shuffling those. Adding foreign actors to a zone would mean
rewriting its tables and asset references. That is a different, unproven method, and I did not attempt it.

## Status

| | |
|---|---|
| Builder on the real Ardolis zone | 9 changes; 3 independent checkers agree (see `verification/`) |
| Test suite | 34/34 on a fake game folder built around the real zone (with and without lz4); Lua scale 17/17 |
| 300-zone stress test | 3,000 changes in 41 s, about 200 MB of memory; its own check passed |
| In game | Only the 4 confirmed changes are proven in game. Everything else is marked *proven pair*, *shared-seen* or *kin*: unverified at that spawner until your log says WORKED. |
| Not run here | The two `.bat` files (no Windows here), and any zone except Ardolis. |

`docs/STAGE_ALLGAME.md` has the details. Every command has `--help`.