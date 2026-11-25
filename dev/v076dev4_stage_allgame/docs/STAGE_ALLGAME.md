# stage_allgame 2.0.0: the all-planet .stage Enemy Randomizer

This document is for the kit and the next development session.

## Commands

All commands run from `tools/stage_enemies/`, with Python 3.9+ and the standard library only. The free `lz4` package
is used automatically when installed.

```
python -I stage_allgame.py scan    --game GAME --out DIR          inventory + coverage report, no .stage
python -I stage_allgame.py build   --game GAME --out DIR          DIR = the max profile, DIR/safe = the fallback
        [--seed S] [--planet NAME ...] [--profile max|safe|all] [--verdicts FILE ...] [--rate 0..1]
        [--strict-external] [--no-actor-family] [--no-evidence] [--no-pins] [--log rivet.log ...] [--scripts DIR] [--cross-planet]
python -I stage_allgame.py check   --game GAME --build DIR        re-read the .stage, compare with the game's zones
python -I stage_allgame.py install --game GAME --build DIR        back up, then copy .stage + 2 Lua files
python -I stage_allgame.py uninstall --game GAME                  put the newest backup back
python -I stage_check_log.py rivet.log [...] --manifest DIR/stage_enemies_manifest.json [--json v.json] [--save-dir D]
python -I test_stage_allgame.py --zone AE530D22FE113E2B.zone.orig [--phaseb-stage .. --phaseb-manifest ..]
python -I ../../tests/test_stage_lua_scale.py ../../scripts [18_rando_stage_manifest.lua]
```

- Offline mode, without a game folder: `--zone-file "levels\...\x.zone=FILE"` (repeatable). FILE is either a 36-byte
  toc header followed by the zone, or a bare zone.
- `--out ...\AUTO` names the folder `build-<time>` and writes its path to `LAST_BUILD.txt`.

## Pipeline

1. **Zones.** The tool takes every `zone` asset of the dag, finds it in the toc (span 0 first), and reads it in
   archive order so chunks are reused.
2. **Decode.** It uses stage_multi 1.2.0's decoder: actor-asset table, Zone Actors, Script Vars, Script Plugs and
   Script Actions. A zone with no actor tables is "no actors", not an error. An undecodable zone is listed in the
   report.
3. **Inventory.** For every SunsetSpawnerFactory (class `2E910F8C`) it records:
   - the Templates variable, its form and owners, and each co-owner's node class/plug;
   - the template kind;
   - every Locations point;
   - the count plug `90D607B0`.
   It also counts other spawner nodes, script nodes with a `Template` plug (they are not changed).
4. **Game-wide tables.**
   - Every actor uid of every zone, used to resolve EXTERNAL spawn points to the actor they really are (a volume, or an
     anim clue of a given kind).
   - Every anim clue mapped to the kinds the game spawns at it (`clue_hosts`), and each clue family
     `animclue_<w1>_<w2>` mapped to its kinds.
5. **Plan, per zone.** Seeded with `seed|zone id`, so the same input gives a byte-identical `.stage`.
   - Options per factory under R1 to R6.
   - Pins: the 4 confirmed changes, plus WORKED verdicts.
   - Anchors: each replacement template keeps one native user. A user that cannot change anyway is preferred.
   - A weighted pick: proven pairs count 3x, and each kind already used in the zone lowers its own weight, which
     spreads the kinds.
6. **Write, streaming.** Each zone is re-read and its sha256 checked against the scan. The tool then applies
   `{u16 index at +4, u64 uid at +16}` per change and verifies:
   - only those bytes differ;
   - size, header and section table are identical;
   - C1 holds (every local reference's index is its uid's record);
   - every replacement still has an unchanged native user.

   The zone is then written as `<span>/<ASSET ID>` (36-byte header plus zone), in the layout of tool 1.1.0's
   `rcra.write_stage`. A zone that fails is left out, with the reason.
7. **Outputs per profile.**

   | File | What it holds |
   |---|---|
   | `RandoEnemies.stage` | every changed zone |
   | `18_rando_stage_manifest.lua` | format 1, plus `planet` and `tier` per change |
   | `stage_enemies_manifest.json` | the same, with every zone's sha256 original and patched |
   | `changes.csv` | one row per change |
   | `inventory.csv` | every factory of the game: decision and reason |
   | `inventory.json` | the decoded data, `clue_hosts` and the external resolution |
   | `COVERAGE_REPORT.md` | the totals and tables below |
   | `18_rando_stage_enemies.lua` | the scale version, copied into the build |

   `COVERAGE_REPORT.md` has: totals, totals per planet and per zone, the replacement kinds, the reasons table,
   unreadable zones, and the knowledge used.
8. **Self-check.** `check` runs on the result automatically, and the build fails if the check fails.

## Tiers in the manifest (`tier`)

| Tier | Meaning |
|---|---|
| `confirmed` | WORKED in your game (bundled evidence, or your `--verdicts`) |
| `proven/<spawn tier>` | the pair has in-game evidence elsewhere |
| `kin/<spawn tier>` | same faction and movement group only (the kit's KILLABLE rule) |
| `shared-seen/<spawn tier>` | a shared variable whose co-owner classes were all seen in a success |
| `UNVERIFIED-shared` | `--profile all` only |

Spawn tiers, from strongest to weakest:

| Spawn tier | Meaning |
|---|---|
| `volume` | a local non-clue actor |
| `clue-native` | an anim clue where the game itself spawns the replacement kind |
| `external-volume` | another zone's non-clue actor |
| `clue-family` | a clue of the same `animclue_<w1>_<w2>` family as one the replacement uses |
| `external-unresolved` | an actor no zone holds; 2 of 2 such changes worked in game |

## Evidence the rules rest on

| Fact | Source |
|---|---|
| uid + index rewrite spawns the replacement | 2026-11-25 log: FF06CCC2, 9C3139C7 (volume), FA5FB32C, DAFCA25C (external) WORKED |
| Anim clue of another kind: no spawn | CECB812E 0/3 loads (Phase B); 28/28 native clue points hold their own kind; DEV3 6/6 clue swaps ORIGINAL |
| Shared variable can take a change | `V.write_var` writes the variable (uid, handle at +0x10); DEV3 SUCCESS on F3D033F9, F4A34D9C, F607A5D7, FE80D89C |
| Co-owner `F512DB23` blocks | DEV3 ORIGINAL on 88259456 (3 volumes), D26E32B8 (external) |
| Cross-faction replacements are unkillable | V.COMPAT_BUILTIN "bad" pairs, round 63 (Zordoom): spawned, 0 died |
| melee/bladeball → shooter is bad | V.COMPAT_BUILTIN |

Families come from the kit's knowledge first: `V.REG_BUILTIN`, the logs' `ASSET` and `learned template` lines, and
your `GAME\rivet.log`, which is read automatically. A kind no log has seen is refused, unless its actor file names
exactly one known bot class. That inference is labelled "UNVERIFIED inference" in the report and can be turned off
with `--no-actor-family`.

## In game: 18_rando_stage_enemies.lua, scale 2.0.0

The 16/18 handshake `ST.STAGE_LUA = "1.1.0"` and the `RANDO_FILES` tag `10.0.43` are unchanged.

- **Up to 20 changes:** identical output to before.
- **More than 20 changes:**
  - At the start: one `STAGE ZONE <planet> | <zone> | n change(s): kinds` line per zone, then
    `STAGE MODE: N change(s) in Z zone(s) on P planet(s)`.
  - `STAGE CHANGE n` is written when its spawner is first listed in a level. It is never written twice, and its
    format is unchanged, so the old log checker still reads it.
  - `STAGE VARIABLES` counts cover only the spawners listed in the current level.
- **Cost in lupa** with 600 changes: index 3 ms, once; a 240-spawner listing look under 1 ms.

## Limits

- **Cross-planet templates (experimental).** Add `--cross-planet` to admit globally unique enemy actor UIDs already
  used by native factories in another scanned zone. The target variable is encoded as an external actor reference
  (`index = 0xFFFF`); the build self-check verifies the UID and kind in the recorded source zone. Engine acceptance is
  not proven until the game spawns it. The default build remains same-zone.
- **Spawner nodes with a `Template` plug** (another adapter) are counted, not changed: there is no `.stage` evidence
  for them yet.
- **Large builds.** rivet loads the `.stage` members as Overstrike stage entries. Many zone members are untested in
  game: watch the first load. `--planet` limits a build to the planets you name.
- **A game update** changes zone hashes. `check` and `install` refuse a stale build, so rebuild after an update.