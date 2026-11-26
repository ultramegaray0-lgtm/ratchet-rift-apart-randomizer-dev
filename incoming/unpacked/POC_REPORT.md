# Phase A: single-spawner .stage Enemy Randomizer POC (v0.76-DEV4, stage tool 1.0.1)

**Status: BUILT AND STATICALLY VERIFIED. NOT INSTALLED. NOT RUN IN THE GAME.** Nothing in your game folder was touched.

## 1. The change

| | |
|---|---|
| Planet | Ardolis (first visit: mission `MIS_ARD_01_FIRST_VISIT`) |
| Zone | `levels\i29\instance\ardolis\ardolis_main\ard_firstvisit_gp.zone` (asset id `AE530D22FE113E2B`, span 0) |
| Where | Zone Script Vars +4912 (zone offset 413776): one 8-byte template reference |
| Spawner | factory `CECB812E81FB7301` (SunsetSpawnerFactory, its `Templates` variable), encounter `CHK_ARD_START` |
| Original | `enm_pirate_robot_shooter`, template uid `899208BF8F48C554` (ground) |
| Replacement | `enm_pirate_robot_melee` (brawler), template uid `92C793D47A4657B6` (swarmer) |
| Pair | `factory|enm_pirate_robot_sh/ground>enm_pirate_robot_me/swarmer`: tier A, combat-verified |

## 2. Why this candidate is valid (every Phase A rule, with the evidence)

- **Regular enemies.** Both are `role enemy` in your rivet.log (lines 3650, 3652: `GameBotShooter`, `GameBotMeleeSwarmer`). Neither is a boss, NPC, ally or vendor, and no name hits `NAME_EXCLUDE`.
- **Movement compatibility.** ground → swarmer stays in the same `walker` group (`V.FAMILY_GROUP`), the rule the game-side randomizer uses.
- **Combat-verified pair (tier A).** From `V.COMPAT_BUILTIN`: "round37: 20 of 20 spawns, A1 completed twice; round40: A1 completed twice, its replaced brawlers died". Your DEV3 run also made this same swap at runtime on this exact spawner (log line 3657).
- **Replacement already in the zone.** `92C793D47A4657B6` is placed in Zone Actors (+824) and Zone Scene Objects (+10240), and is already referenced by one Script Vars entry (+25584). Your log shows it spawning in this zone from factory `E6705A36656EB7B9` (line 3650). Nothing is added to the zone.
- **Exactly one reference, one spawner.** `899208BF8F48C554` has exactly ONE Script Vars reference in this zone. It appears in no other zone of the 9,009 probed.
- **Which spawner owns that reference** comes from your rivet.log, not from decoded zone structure. Line 3651 is `SPAWN 7378183 | ... | factory Templates CECB812E81FB7301 | ... spawned enm_pirate_robot_shooter`. The next line, 3652, is `learned template 6343594 (uid 899208BF8F48C554) ... (spawn)`. 16_rando_spawners.lua writes both lines in one call (V.ledger_add, then V.learn from that spawner's variable, lines 4141-4144). So CECB812E81FB7301's variable held exactly this uid.
- **Zone loadable by rivet_hook as a patched copy.** The header block sizes 520784 + 18484 add up to the zone's 539268 bytes.
- **Ranking:** score 18, the top candidate. It ties with the same reference → the zone's other brawler template, `AF0189E66C49DA08`. The tool breaks ties deterministically by replacement uid. Both are the same kind placed in this zone, and `92C793D4…` also spawns natively in the same encounter (CHK_ARD_START, factory E6705A36656EB7B9).

## 3. Verification (outputs in `verification/`)

| Check | Result |
|---|---|
| `stage_enemies.py verify` (read-only) | **OK**: 8 bytes differ in 1 place, Zone Script Vars +4912: 899208BF8F48C554 → 92C793D47A4657B6 |
| Independent checker (own DAT1 parser and diff, not the kit's code) | **PASS 26/26** |
| Zone header | identical to the game's toc header (`a00a391f…`, schema 1F390AA0), and equal to the header the probe read from your toc |
| Block sizes | [520784, 18484, 0…] sum = 539268 = patched zone size |
| Zone size | 539268 before and after |
| DAT1 | magic/type/size unchanged, 26-entry section table byte-identical, all sections in bounds |
| Bytes changed | 8, all at 413776-413783; everything else byte-identical |
| Patched slot | type-5 32-byte Script Vars entry; type, flags, name hash `A61BE7D5F39117FF` and zero tail unchanged. Same entry type as the replacement's existing reference and all 40 template references in the section |
| Reference counts | original: Script Vars 1 → 0 (its template actor stays placed); replacement: Script Vars 1 → 2 |
| Backup | `poc_out/backup/AE530D22FE113E2B.zone.orig` = 36-byte header + original zone; sha256 `e6b22e71…0edcf`. Zone sha256 `d40540ed…e016` = what the probe read from your game. Byte-identical to the backup you uploaded |
| Patched zone sha256 | `e019b314…1f80`: identical to the one inside your own POC build |
| Manifests | JSON and Lua agree; the Lua parses (Lua 5.4) |
| Tool selftest / DEV4 Lua tests / dev-zip validator | 53/53, 0 failures, VALIDATION PASSED |

**How it was run without your game here:** `verification/scripts/build_mirror.py` builds a toc/dag/archive holding ONE zone, your real one. It uses the original bytes and the 36-byte toc header from the backup, and checks both against `probe.json` (zone sha256, size, header hex) before writing anything. The unmodified 1.0.0 tool reproduced your build from it: same candidate, same patched zone bytes.

**The .stage sha256 differs from the build you uploaded** (`0264377a…` here, `e19a2bbd…` yours), but **every member is byte-identical** (same CRCs). Your Windows Python and this Linux one compress with different zlib builds and record a different "created on" OS in the zip. The manifest in this build matches this `.stage`. If you rebuild on Windows, compare `zone_sha256_patched`, not the zip hash.

## 4. Tool bug fixed (stage tool 1.0.0 → 1.0.1); see `tool_fix_1.0.1.diff`

**Bug.** `poc` put EVERY spawner of the zone that ever spawned the original *kind* into `spawner_keys`, each listed twice: 8 spawners, 16 entries. Only CECB812E81FB7301 holds the changed uid. The other 7 use the other shooter template, `8416CF7558A4694D` (10 references, unchanged). In the game, 18_rando_stage_enemies.lua treats every listed key as "the spawner the .stage changed". So it would have:

- logged 7 "STAGE VARIABLE … neither the original nor the replacement" lines;
- counted every normal shooter from those 7 spawners as "original" in STAGE SUMMARY;
- labelled them "the spawner the .stage changed: the variable holds 8416CF75…".

A working patch would have read as a partial failure. `verification/spawner_keys_fix_demo_output.txt` shows this in the kit's own Lua harness.

**Fix.** `knowledge.py` ties a template uid to a spawner only when a first-spawn `SPAWN` line is followed directly by that spawn's `learned template … (spawn)` line with the same kind. `stage_enemies.py` then puts only those spawners in `spawner_keys`. The other same-kind spawners stay visible as `same_kind_spawner_keys` (JSON only), and the "test where" encounters come from the identified spawner. With no evidence, `spawner_keys` is left empty rather than guessed. **No validation rule changed.** Ranking is identical (score still uses the same-kind test), and the `.stage` is byte-identical to the 1.0.0 build. Five selftest checks were added, including the cases that must NOT be attributed: another line in between, another kind, a non-first spawn, a template-actor learn. Docs: STAGE_ENEMY_RANDOMIZER.md section 5, CHANGELOG, tool README.

## 5. Remaining blockers before the in-game test

1. **Your game has the DEV3 scripts** (rivet.log line 71: `release v0.76-DEV3 (kit 10.0.42)`). `install` refuses until the DEV4 scripts (`18_rando_stage_enemies.lua`, the DEV4 `16_rando_spawners.lua`) are in `<game>\scripts`. Use the updated kit zip (stage tool 1.0.1).
2. **Your save is past this encounter.** CECB812E81FB7301 was only ever seen at `CHK_ARD_START`, before `OBJ_ARD_START` completed (log 3651, 3796). Your log ends at `OBJ_ARD_BARRACKS` with OBJ_ARD_START done. You need a save that replays the Ardolis landing: before arriving at Ardolis on the first visit, or another slot.
3. **rivet_hook has never loaded an `[assets]` mod on your install.** rivet.log lines 4-6 show all three listed paths missing. Zone replacement through a `.stage` is proven only from rivet_hook's source code, not on your PC. The first in-game proof is `[loader] mod path mods/RandoEnemies.stage is overstrike stage format.`, then `STAGE VARIABLE factory CECB812E81FB7301: … IS loaded`.
4. **Run `verify` against your real game folder before installing** (read-only), WITH `--log`. It re-reads the live toc (catches a game update since the probe), checks rivet.toml order and checks every other listed mod for a clash with this zone. Here it could only run against the one-zone mirror. `verify` knows these two uids only from your rivet.log; they are not in `V.REG_BUILTIN`. Without `--log` it reports "not one known template uid replaced by another" (see `verification/verify_without_log_output.txt`). **Copy your current rivet.log now** (e.g. to `rivet_dev3_ardolis.log`): the game rewrites it on its next start. This was a documentation gap, now fixed in the docs and in poc's "next:" line; verify's rule is unchanged.
5. **Ownership is log evidence, not decoded structure.** The Script Vars ↔ Script Actions linkage is still undecoded. If a second node shared that variable, it would change too; the in-game check would show it.
6. **Reading the in-game summary:** `STAGE SUMMARY` totals also count native brawler spawns of `E6705A36656EB7B9`, which already uses the replacement template, as "replacement". This is a pre-existing uid fallback in 18_rando_stage_enemies.lua, left unchanged. Judge PASS by the `STAGE SPAWNER CECB812E81FB7301` line and the `STAGE SPAWN … (the patched spawner)` lines.
7. **Gameplay note:** a brawler takes a shooter's spawn point. The pair is combat-verified in the Zurkon arena, not on this spot. Watch for `STAGE ALIVE` (a brawler that cannot reach you).

PASS for Phase A (docs section 6): the variable holds the replacement, a brawler spawns from CECB812E81FB7301, takes damage, dies, the landing encounter completes, and a checkpoint reload / leaving and returning neither crashes nor duplicates.

## 6. Install (only after your approval; not run)

```
python tools\stage_enemies\stage_enemies.py verify  --game "E:\Users\Ray\Desktop\Games\Ratchet.and.Clank.Rift.Apart Modded" --stage poc_out\RandoEnemies.stage --log rivet_dev3_ardolis.log
python tools\stage_enemies\stage_enemies.py install --game "E:\Users\Ray\Desktop\Games\Ratchet.and.Clank.Rift.Apart Modded" --build poc_out
```
`install` copies `mods\RandoEnemies.stage` and `scripts\18_rando_stage_manifest.lua`, and appends `mods/RandoEnemies.stage` LAST to rivet.toml `[assets] paths` (backup `rivet.toml.bak-stage-*`). `uninstall` reverses all three.
