# .stage Enemy Randomizer - all-planet build (stage_allgame 2.0.0, v0.76-DEV4)

Seed `allgame-1`. Source: zone files given on the command line. Reader: lz4 package. Scan time 0 s.

## Totals

| | |
|---|---|
| zone assets in the game's dag | 1 |
| zones scanned / decoded | 1 / 1 |
| zones not in the toc | 0 |
| zone status | ok 1 |
| zones that hold spawner factories | 1 |
| spawner factories (all kinds) | 43 |
| of them enemy spawners | 39 |
| **changed** | **5 (13% of enemy spawners)** |
| zones changed | 1 |
| planets with changes | 1 |
| replacement enemy kinds used | 3 |
| other spawner nodes (`Template` adapter, not handled) | 1 |
| .stage size | 0.2 MB on disk, 1 zone members |

Change tiers: confirmed 4, proven 1.
Spawn-point tiers: external-unresolved 3, volume 2.

- **confirmed**: worked in your 2026-11-25 run (kept as they were).
- **proven**: the pair has in-game evidence (built-in table, your logs, the .stage runs). NOT yet seen at this spawner.
- **kin**: same faction and movement group, the kit's KILLABLE rule. Unverified in game.
- spawn points: `volume` local volume; `clue-native` an anim clue the game itself uses for the replacement; `external-volume` another zone's non-clue actor; `clue-family` a clue of the same family; `external-unresolved` an actor no zone holds (2 of 2 worked in game).

## The confirmed changes

- FF06CCC2A9AC1EA2 -> 92C793D47A4657B6: kept (shooter -> brawler, WORKED 2026-11-25)
- 9C3139C7FFED7137 -> C37DB04A5A1F0972: kept (shooter -> bladeball, WORKED 2026-11-25)
- FA5FB32C7AAB4C4A -> B69D08BA44EE560E: kept (puffoid -> crab, WORKED 2026-11-25)
- DAFCA25C58FD387F -> D7677BCD9AAF5963: kept (puffoid -> crab, WORKED 2026-11-25)

## By planet

| planet | factories | enemy spawners | changed | % |
|---|---:|---:|---:|---:|
| ardolis | 43 | 39 | 5 | 13% |

## By zone (zones with enemy spawners)

| planet | zone | enemy spawners | changed | swaps |
|---|---|---:|---:|---|
| ardolis | ard_firstvisit_gp.zone | 39 | 5 | indigenous_puffoid->indigenous_crab x3, pirate_robot_shooter->pirate_robot_melee x1, pirate_robot_shooter->pirate_bladeball x1 |

## Replacement kinds

- enm_indigenous_crab: 3 spawner(s)
- enm_pirate_robot_melee: 1 spawner(s)
- enm_pirate_bladeball: 1 spawner(s)

## Why enemy spawners were not changed

| reason | spawners |
|---|---:|
| R1 shared variable: co-owner F512DB23/B1C79F97 is a node class whose spawners kept their original at runtime | 3 |
| R1 shared variable: 2 owners, co-owner class/plug 783E1BE3/93BF4450 (profile safe) | 3 |
| R1 shared variable: 2 owners, co-owner class/plug 0AC0B46C/93BF4450 (profile safe) | 3 |
| no compatible replacement: cross-faction pirate -> wildlife x3; spawn point: local anim clue animclue_pirate_melee_taunt_pierre, never used for the re | 2 |
| R1 shared variable: 2 owners, co-owner class/plug 40A9688E/93BF4450 (profile safe) | 2 |
| R1 shared variable: 2 owners, co-owner class/plug 31B870E3/F7EDFFC8 (profile safe) | 2 |
| kept native: the last unchanged user of enm_pirate_bladeball <uid> (a replacement elsewhere in this zone) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 3627CF3D/93BF4450 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 651365AF/02872CB8 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 735B260F/5C4E164C (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 651365AF/B805C362 (profile safe) | 1 |
| no compatible replacement: cross-faction pirate -> wildlife x3; spawn point: local anim clue animclue_pirate_melee_balance_sword, never used for the r | 1 |
| R1 shared variable: 2 owners, co-owner class/plug F8774435/6D15F617 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 6ED609C2/EE3992D5 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 692617F1/7566B265 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 651365AF/B57CF5E2 (profile safe) | 1 |
| no compatible replacement: cross-faction pirate -> wildlife x3; spawn point: spawn point SV is a group variable (undecoded) x2; V.COMPAT_BUILTIN x2 | 1 |
| R1 shared variable: 2 owners, co-owner class/plug E13EB1E3/7566B265 (profile safe) | 1 |
| R1 shared variable: 3 owners, co-owner class/plug 0AC0B46C/93BF4450, 40A9688E/93BF4450 (profile safe) | 1 |
| no compatible replacement: spawn point: local anim clue animclue_pirate_shooter_group_stand_conversation_idle_02, never used for the replacement x4; c | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 7178BE14/C4080766 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 735B260F/B57CF5E2 (profile safe) | 1 |
| R1 shared variable: 2 owners, co-owner class/plug 1FDCA5D3/93BF4450 (profile safe) | 1 |
| in-game verdict NO SPAWN (stage_check_log --json): left native | 1 |
| R1 shared variable: 3 owners, co-owner class/plug A3DF6F8E/93BF4450, DBCB7A59/320B57AF (profile safe) | 1 |

## Knowledge used

- log rivet_phaseb.log: [Errno 2] No such file or directory: 'rivet_phaseb.log'
- 16_rando_spawners.lua: 235 built-in template uids, 27 built-in combat pairs
- round13_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round14_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round15_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round16_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round17_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round18_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round19_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round20_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round23_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- round24_rivet.log: 0 ASSET, 0 learned, 0 CHANGED, 0 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- learned anim-clue hosts: 18 clues, 4 clue families
- external spawn points: 6, resolved 0, unresolved 6, ambiguous 0
- enemy-kind family sources: kit knowledge 7
