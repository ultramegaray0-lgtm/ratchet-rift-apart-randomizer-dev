# .stage Enemy Randomizer - all-planet build (stage_allgame 2.0.0, v0.76-DEV4)

Seed `allgame-1`. Source: game folder. Reader: built-in (pure Python; pip install lz4 makes the scan ~100x faster). Scan time 121 s.

## Totals

| | |
|---|---|
| zone assets in the game's dag | 32300 |
| zones scanned / decoded | 9046 / 8599 |
| zones not in the toc | 23254 |
| zone status | no actors 7494, no scripts 641, ok 464, not decodable 447 |
| zones that hold spawner factories | 109 |
| spawner factories (all kinds) | 1324 |
| of them enemy spawners | 930 |
| **changed** | **170 (18% of enemy spawners)** |
| zones changed | 38 |
| planets with changes | 7 |
| replacement enemy kinds used | 22 |
| other spawner nodes (`Template` adapter, not handled) | 638 |
| .stage size | - |

Change tiers: proven 79, kin 54, shared-seen 33, confirmed 4.
Spawn-point tiers: volume 127, external-unresolved 39, clue-native 3, external-volume 1.

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
| overlay | 797 | 589 | 127 | 22% |
| savali | 87 | 76 | 20 | 26% |
| ardolis | 68 | 62 | 13 | 21% |
| prisonship | 20 | 19 | 7 | 37% |
| blizar | 82 | 13 | 1 | 8% |
| blizar_destroyed | 7 | 5 | 1 | 20% |
| test | 2 | 2 | 1 | 50% |
| cordelion | 34 | 0 | 0 | 0% |
| malinon_intro | 4 | 3 | 0 | 0% |
| molonoth | 57 | 57 | 0 | 0% |
| nefariouscity | 33 | 12 | 0 | 0% |
| pocketdimensions | 3 | 3 | 0 | 0% |
| sargasso | 24 | 20 | 0 | 0% |
| openarea | 106 | 69 | 0 | 0% |

## By zone (zones with enemy spawners)

| planet | zone | enemy spawners | changed | swaps |
|---|---|---:|---:|---|
| ardolis | ard_bar_sidepath.zone | 13 | 4 | pirate_robot_shooter->pirate_bladeball x3, pirate_bladeball->pirate_robot_melee x1 |
| ardolis | ard_challenge_03_allships_ship_01.zone | 2 | 0 | - |
| ardolis | ard_challenge_03_allships_ship_02.zone | 2 | 0 | - |
| ardolis | ard_challenge_03_allships_ship_03.zone | 2 | 0 | - |
| ardolis | ard_firstvisit_gp.zone | 39 | 9 | indigenous_puffoid->indigenous_crab x5, pirate_robot_shooter->pirate_bladeball x2, pirate_robot_shooter->pirate_robot_melee x1, pirate_robot_melee->pirate_robot_shielded x1 |
| ardolis | ardolis_critters.zone | 4 | 0 | - |
| blizar | i29_blizar_intact_devgp_drillcombat.zone | 8 | 1 | thugs4less_shooter->thugs4less_melee x1 |
| blizar | i29_blizar_intact_ambient.zone | 3 | 0 | - |
| blizar | i29_blizar_intact_devgp_grindrail.zone | 2 | 0 | - |
| blizar_destroyed | i29_blizar_destroyed_devgp_drillcombat.zone | 5 | 1 | neo_nefarious_shooter->neo_nefarious_swarmer x1 |
| malinon_intro | sargasso_passive_gp.zone | 3 | 0 | - |
| molonoth | i29_molonoth_factory_gp.zone | 56 | 0 | - |
| nefariouscity | i29_nefcity_amb_civilians.zone | 11 | 0 | - |
| nefariouscity | i29_nefcity_whitebox_gp_01.zone | 1 | 0 | - |
| pocketdimensions | pd_02_gp.zone | 1 | 0 | - |
| pocketdimensions | pd_03_gp.zone | 2 | 0 | - |
| prisonship | prisonship_main_gameplay.zone | 19 | 7 | neo_nefarious_shooter->neo_nefarious_melee x2, neo_nefarious_melee->neo_nefarious_swarmer x1, pirate_robot_shooter->pirate_robot_shielded x1, pirate_robot_melee->pirate_robot_shielded x1, pirate_bladeball->pirate_robot_melee x1, neo_nefarious_shooter->neo_nefarious_swarmer x1 |
| sargasso | sargasso_gameplay_combat.zone | 14 | 0 | - |
| sargasso | i29_sargasso_m16_trailer_gp.zone | 6 | 0 | - |
| savali | mis_sav_visit_01_gp.zone | 50 | 12 | neo_nefarious_shooter->neo_nefarious_swarmer x3, indigenous_sandshark->indigenous_alien_spitter x2, neo_nefarious_shooter->neo_nefarious_heavy x2, neo_nefarious_swarmer->neo_nefarious_heavy x1, neo_nefarious_hover->neo_nefarious_sniper x1, neo_nefarious_sniper->neo_nefarious_hover x1 |
| savali | savali_encounters.zone | 26 | 8 | indigenous_sandshark->indigenous_alien_spitter x3, neo_nefarious_grenadier->neo_nefarious_hover x1, neo_nefarious_swarmer->neo_nefarious_shooter x1, neo_nefarious_melee->neo_nefarious_swarmer x1, indigenous_alien_spitter->indigenous_sandshark x1, neo_nefarious_shooter->neo_nefarious_melee x1 |
| overlay | zurkons_arena_challenge_a4_plat_a.zone | 1 | 0 | - |
| overlay | zurkons_arena_challenge_a4_plat_c.zone | 1 | 0 | - |
| overlay | ard_skiff_attacks.zone | 15 | 0 | - |
| overlay | mis_ard_pirate_king_ship.zone | 23 | 4 | pirate_robot_shooter->pirate_robot_melee x2, pirate_robot_melee->pirate_bladeball x1, pirate_robot_melee->pirate_robot_shielded x1 |
| overlay | mis_ard_bar_ship.zone | 1 | 0 | - |
| overlay | mis_ard_chaser_ship_01.zone | 4 | 0 | - |
| overlay | mis_ard_skiffs.zone | 1 | 0 | - |
| overlay | mis_ard_chaser_02.zone | 2 | 0 | - |
| overlay | mis_ard_pierre_ship.zone | 3 | 2 | pirate_shingle_q4b->pirate_bladeball x2 |
| overlay | i29_blizar_botsearch_combat_gp.zone | 16 | 4 | thugs4less_melee->thugs4less_shooter x2, thugs4less_shooter->thugs4less_robomutt x1, indigenous_crab->indigenous_puffoid_blizar x1 |
| overlay | i29_blizar_destroyed_worldcombat_gp.zone | 2 | 1 | neo_nefarious_swarmer->neo_nefarious_shooter x1 |
| overlay | i29_blizar_intact_hub_objectives_gp.zone | 1 | 0 | - |
| overlay | i29_blizar_startingarea_gp.zone | 21 | 2 | indigenous_crab->indigenous_puffoid_blizar x1, indigenous_puffoid_blizar->indigenous_crab x1 |
| overlay | i29_blizar_mission_poststate_exploration_combat_gp.zone | 5 | 1 | indigenous_crab->indigenous_puffoid_blizar x1 |
| overlay | i29_blizar_mission_poststate_startingarea_combat_gp.zone | 4 | 1 | indigenous_crab->indigenous_puffoid_blizar x1 |
| overlay | i29_blizar_surveyor_gp.zone | 9 | 0 | - |
| overlay | i29_blizar_surveyor_tdcombat_gp.zone | 22 | 9 | indigenous_crab->indigenous_puffoid_blizar x4, indigenous_puffoid_blizar->indigenous_crab x4, Thugs4Less_ShooterJetpack->thugs4less_biker x1 |
| overlay | mis_cord_01_dim_b_gp.zone | 4 | 0 | - |
| overlay | mis_cord_01_dim_b_gp_combat.zone | 13 | 3 | amoeboid_large_ps4->amoeboid_medium_ps4 x2, amoeboid_medium_ps4->amoeboid_small_ps4 x1 |
| overlay | i29_malinon_intro_gp_parade_planet_float.zone | 27 | 3 | thugs4less_shooter->thugs4less_melee x3 |
| overlay | mis_mega_01_rivet_gp.zone | 7 | 1 | thugs4less_robomutt->thugs4less_melee x1 |
| overlay | mis_mega_02_rivet_gp.zone | 21 | 7 | neo_nefarious_swarmer->neo_nefarious_shooter x3, neo_nefarious_melee->neo_nefarious_swarmer x2, neo_nefarious_swarmer->neo_nefarious_melee x1, thugs4less_shooter->thugs4less_melee x1 |
| overlay | malinon_finale_gp_mech_boss.zone | 25 | 2 | neo_nefarious_grenadier->neo_nefarious_sniper x1, neo_nefarious_hover->neo_nefarious_sniper x1 |
| overlay | malinon_finale_gp_mech_flyer.zone | 8 | 4 | neo_nefarious_shooter->neo_nefarious_heavy x2, pirate_robot_shooter->pirate_shingle_q4b x2 |
| overlay | malinon_finale_gp_start.zone | 18 | 5 | neo_nefarious_shooter->neo_nefarious_swarmer x2, neo_nefarious_sniper->neo_nefarious_grenadier x1, neo_nefarious_shooter->neo_nefarious_heavy x1, neo_nefarious_hover->neo_nefarious_grenadier x1 |
| overlay | mis_mol_01_first_visit_gp.zone | 18 | 1 | pirate_robot_shielded->pirate_robot_shooter x1 |
| overlay | mis_mol_01_first_visit_command_ship.zone | 9 | 2 | pirate_bladeball->pirate_robot_melee x1, pirate_bladeball->pirate_shingle_q4b x1 |
| overlay | mis_mol_01_first_visit_pirate_armada_gp.zone | 10 | 0 | - |
| overlay | mis_mol_01_first_visit_pirate_plateau_gunship_00.zone | 1 | 0 | - |
| overlay | mis_mol_01_first_visit_pirate_plateau_gunship_01.zone | 1 | 0 | - |
| overlay | mis_mol_01_first_visit_pirate_plateau_gunship_02.zone | 1 | 0 | - |
| overlay | mis_mol_01_first_visit_shield_intro_ship.zone | 1 | 0 | - |
| overlay | i29_molonoth_post_mission_gp.zone | 8 | 0 | - |
| overlay | i29_nefcity_01_gp_combat.zone | 21 | 9 | neo_nefarious_shooter->neo_nefarious_melee x3, neo_nefarious_melee->neo_nefarious_shooter x2, neo_nefarious_swarmer->neo_nefarious_melee x2, neo_nefarious_swarmer->neo_nefarious_shooter x1, neo_nefarious_melee->neo_nefarious_swarmer x1 |
| overlay | i29_nefcity_passiveshift_01_gp.zone | 4 | 1 | indigenous_alien_spitter->indigenous_sandshark x1 |
| overlay | i29_malinon_rivet_02_gp_parade_pirate_float.zone | 5 | 1 | neo_nefarious_shooter->neo_nefarious_melee x1 |
| overlay | i29_malinon_rivet_02_gp_parade_planet_float.zone | 15 | 7 | neo_nefarious_shooter->neo_nefarious_swarmer x3, thugs4less_shooter->thugs4less_robomutt x2, thugs4less_robomutt->thugs4less_shooter x1, neo_nefarious_swarmer->neo_nefarious_shooter x1 |
| overlay | i29_malinon_rivet_02_gp_parade_veldin_float.zone | 9 | 5 | neo_nefarious_swarmer->neo_nefarious_shooter x5 |
| overlay | i29_malinon_rivet_02_gp_parade_weapons_float.zone | 3 | 0 | - |
| overlay | mis_sarg_01_centipedepath_combat.zone | 11 | 3 | Thugs4Less_Shooter->thugs4less_melee x3 |
| overlay | mis_sarg_01_centipedepath_gameplay.zone | 2 | 0 | - |
| overlay | mis_sarg_01_first_visit_combat.zone | 8 | 0 | - |
| overlay | mis_sarg_02_dummy_shipnav_arya_gameplay.zone | 4 | 0 | - |
| overlay | mis_sarg_02_dummy_shipnav_hylia_gameplay.zone | 4 | 0 | - |
| overlay | mis_sarg_02_dummy_shipnav_kent_gameplay.zone | 4 | 1 | neo_nefarious_shooter->neo_nefarious_swarmer x1 |
| overlay | mis_sarg_02_dummy_shipnav_kraid_gameplay.zone | 4 | 0 | - |
| overlay | mis_sarg_02_dummy_shipnav_richter_gameplay.zone | 4 | 1 | neo_nefarious_swarmer->neo_nefarious_shooter x1 |
| overlay | mis_sarg_02_dummy_shipnav_starwatch_gameplay.zone | 4 | 0 | - |
| overlay | i29_zordoom_chase_gp.zone | 12 | 0 | - |
| overlay | i29_zordoom_dome_gp.zone | 72 | 26 | neo_nefarious_hover->neo_nefarious_sniper x4, neo_nefarious_sniper->neo_nefarious_grenadier x4, thugs4less_shooter->thugs4less_melee x3, neo_nefarious_grenadier->neo_nefarious_hover x3, neo_nefarious_shooter->neo_nefarious_melee x3, neo_nefarious_shooter->neo_nefarious_heavy x2 |
| overlay | i29_zordoom_evacuationplatform_gp.zone | 21 | 9 | neo_nefarious_grenadier->neo_nefarious_hover x3, neo_nefarious_swarmer->neo_nefarious_melee x2, neo_nefarious_sniper->neo_nefarious_grenadier x1, neo_nefarious_shooter->neo_nefarious_melee x1, neo_nefarious_hover->neo_nefarious_sniper x1, neo_nefarious_grenadier->neo_nefarious_sniper x1 |
| overlay | i29_zordoom_landingpad_gp.zone | 9 | 0 | - |
| overlay | i29_zordoom_processingcenter_gp.zone | 21 | 8 | neo_nefarious_hover->neo_nefarious_sniper x2, neo_nefarious_melee->neo_nefarious_swarmer x2, neo_nefarious_sniper->neo_nefarious_hover x2, neo_nefarious_swarmer->neo_nefarious_heavy x1, neo_nefarious_melee->neo_nefarious_heavy x1 |
| overlay | i29_zordoom_mission_poststate_gp.zone | 15 | 2 | neo_nefarious_shooter->neo_nefarious_swarmer x1, neo_nefarious_swarmer->neo_nefarious_melee x1 |
| overlay | zurkons_anim_pub_visit_02_vignettes.zone | 5 | 0 | - |
| overlay | zurkons_anim_pub_visit_02b_vignettes.zone | 2 | 0 | - |
| overlay | zurkons_anim_pub_visit_03_vignettes.zone | 3 | 0 | - |
| overlay | zurkons_anim_pub_visit_post_game_vignettes.zone | 11 | 0 | - |
| overlay | sav_archives.zone | 13 | 2 | neo_nefarious_shooter->neo_nefarious_melee x1, neo_nefarious_heavy->neo_nefarious_melee x1 |
| test | nef_tower_platform_a.zone | 2 | 1 | neo_nefarious_swarmer->neo_nefarious_melee x1 |
| molonoth | molonoth_enemy_spawn_gp.zone | 1 | 0 | - |
| openarea | tile_b19_amb_civilians.zone | 1 | 0 | - |
| openarea | tile_c18_amb_civilians.zone | 3 | 0 | - |
| openarea | tile_c19_amb_civilians.zone | 4 | 0 | - |
| openarea | tile_d18_amb_civilians.zone | 11 | 0 | - |
| openarea | tile_d19_amb_civilians.zone | 11 | 0 | - |
| openarea | tile_e19_amb_civilians.zone | 2 | 0 | - |
| openarea | tile_e20_amb_civilians.zone | 4 | 0 | - |
| openarea | tile_f19_amb_civilians.zone | 3 | 0 | - |
| openarea | tile_f22_amb_civilians.zone | 5 | 0 | - |
| openarea | tile_g20_amb_civilians.zone | 4 | 0 | - |
| openarea | tile_g21_amb_civilians.zone | 9 | 0 | - |
| openarea | global_art_background.zone | 6 | 0 | - |
| openarea | tile_c22_art.zone | 5 | 0 | - |
| openarea | tile_d17_art.zone | 1 | 0 | - |

## Replacement kinds

- enm_neo_nefarious_swarmer: 21 spawner(s)
- enm_neo_nefarious_melee: 21 spawner(s)
- enm_neo_nefarious_shooter: 17 spawner(s)
- enm_thugs4less_melee: 12 spawner(s)
- enm_neo_nefarious_sniper: 11 spawner(s)
- enm_neo_nefarious_hover: 11 spawner(s)
- enm_neo_nefarious_heavy: 10 spawner(s)
- enm_indigenous_crab: 10 spawner(s)
- enm_neo_nefarious_grenadier: 8 spawner(s)
- enm_indigenous_puffoid_blizar: 8 spawner(s)
- enm_pirate_bladeball: 8 spawner(s)
- enm_pirate_robot_melee: 7 spawner(s)
- enm_indigenous_alien_spitter: 5 spawner(s)
- enm_thugs4less_shooter: 4 spawner(s)
- enm_pirate_robot_shielded: 4 spawner(s)
- enm_pirate_shingle_q4b: 3 spawner(s)
- enm_thugs4less_robomutt: 3 spawner(s)
- enm_amoeboid_medium_ps4: 2 spawner(s)
- enm_indigenous_sandshark: 2 spawner(s)
- enm_amoeboid_small_ps4: 1 spawner(s)
- enm_thugs4less_biker: 1 spawner(s)
- enm_pirate_robot_shooter: 1 spawner(s)

## Why enemy spawners were not changed

| reason | spawners |
|---|---:|
| Templates variable is a external reference | 82 |
| R1 shared variable: 2 owners, co-owner class/plug 783E1BE3/93BF4450 never seen in a runtime success | 42 |
| no compatible replacement:  | 40 |
| R1 shared variable: 2 owners, co-owner class/plug 40A9688E/93BF4450 never seen in a runtime success | 27 |
| R1 shared variable: 2 owners, co-owner class/plug F8774435/6D15F617 never seen in a runtime success | 18 |
| R1 shared variable: 2 owners, co-owner class/plug 735B260F/5C4E164C never seen in a runtime success | 16 |
| R1 shared variable: 2 owners, co-owner class/plug 409FC1C2/A2C03358 never seen in a runtime success | 13 |
| zone data: 3 Templates plugs | 13 |
| no compatible replacement: spawn point: spawn point SV is a group variable (undecoded) x1 | 13 |
| R1 shared variable: 2 owners, co-owner class/plug E13EB1E3/7566B265 never seen in a runtime success | 12 |
| R1 shared variable: 2 owners, co-owner class/plug 31B870E3/79F693E4 never seen in a runtime success | 12 |
| R1 shared variable: 2 owners, co-owner class/plug 7178BE14/C4080766 never seen in a runtime success | 11 |
| no compatible replacement: movement group flyer -> walker x2 | 11 |
| R1 shared variable: co-owner F512DB23/B1C79F97 is a node class whose spawners kept their original at runtime | 10 |
| R1 shared variable: 2 owners, co-owner class/plug 735B260F/B57CF5E2 never seen in a runtime success | 8 |
| original ard_pirate_skiff: family unknown: no rivet.log has seen this kind yet | 8 |
| no compatible replacement: cross-faction pirate -> wildlife x1 | 8 |
| R1 shared variable: 2 owners, co-owner class/plug 771A845A/6D15F617 never seen in a runtime success | 7 |
| R1 shared variable: 2 owners, co-owner class/plug 47AB28F3/C4080766 never seen in a runtime success | 7 |
| R1 shared variable: 2 owners, co-owner class/plug 6ED609C2/EE3992D5 never seen in a runtime success | 6 |
| R1 shared variable: 2 owners, co-owner class/plug 864DD7C9/984A87B9 never seen in a runtime success | 6 |
| original enm_sargasso_flyer: family unknown: no rivet.log has seen this kind yet | 6 |
| R1 shared variable: 2 owners, co-owner class/plug 31B870E3/B57CF5E2 never seen in a runtime success | 6 |
| R1 shared variable: 2 owners, co-owner class/plug 64D6EC3D/93BF4450 never seen in a runtime success | 6 |
| no compatible replacement: spawn point: spawn point SV is a group variable (undecoded) x2 | 6 |
| R1 shared variable: 2 owners, co-owner class/plug 3627CF3D/93BF4450 never seen in a runtime success | 5 |
| no compatible replacement: movement group walker -> flyer x1 | 5 |
| R1 shared variable: 2 owners, co-owner class/plug C03CE2D5/AC563E57 never seen in a runtime success | 5 |
| R1 shared variable: 2 owners, co-owner class/plug 6ED609C2/9C6C9BA5 never seen in a runtime success | 5 |
| no compatible replacement: V.COMPAT_BUILTIN x1 | 5 |
| no compatible replacement: movement group walker -> flyer x6; cross-faction neo -> pirate x4; cross-faction neo -> thugs4less x2 | 5 |
| zone data: 2 Templates plugs | 5 |
| original enm_Sargasso_Flyer: family unknown: no rivet.log has seen this kind yet | 4 |
| R1 shared variable: 2 owners, co-owner class/plug C08CD8F9/4B1C95AD never seen in a runtime success | 4 |
| R1 shared variable: 2 owners, co-owner class/plug BAEB8FDD/93BF4450 never seen in a runtime success | 4 |
| R1 shared variable: 3 owners, co-owner class/plug 22BA7DAC/93BF4450 never seen in a runtime success | 4 |
| R1 shared variable: 2 owners, co-owner class/plug AF4A22D2/93BF4450 never seen in a runtime success | 4 |
| R1 shared variable: 2 owners, co-owner class/plug EFBB0598/B4597C69 never seen in a runtime success | 4 |
| no other regular enemy template in this zone (pool: enm_pirate_robot_shooter) | 4 |
| no compatible replacement: cross-faction thugs4less -> wildlife x2; cross-faction thugs4less -> neo x2; movement group flyer -> walker x2 | 4 |

## Zones that could not be read

- legacy\rcf\levels\sargasso\sargasso_unique.zone: plug 8 -> Script Vars 8 out of range
- levels\i29\i29_global_tutorials.zone: plug 2 -> Script Vars 447 out of range
- levels\i29\instance\ardolis\ardolis_collectibles.zone: plug 0 -> Script Vars 234 out of range
- levels\i29\instance\ardolis\ardolis_crates.zone: plug 5 -> Script Vars 21 out of range
- levels\i29\instance\ardolis\ardolis_main\ard_challenge_03_allships.zone: plug 0 -> Script Vars 234 out of range
- levels\i29\instance\ardolis\ardolis_main\ard_pirate_challenge.zone: plug 13 -> Script Vars 932 out of range
- levels\i29\instance\ardolis\ardolis_main\ardolis_exterior_bar_art.zone: plug 12 -> Script Vars 262 out of range
- levels\i29\instance\ardolis\ardolis_main\ardolis_main_globalgp.zone: plug 3 -> Script Vars 2411 out of range
- levels\i29\instance\ardolis\ardolis_main\ardolis_main_sfx.zone: plug 63 -> Script Vars 904 out of range
- levels\i29\instance\blizar\blizar_destroyed\i29_blizar_destroyed_devart_startarea.zone: plug 76 -> Script Vars 42 out of range
- levels\i29\instance\blizar\blizar_destroyed\i29_blizar_destroyed_devgp_exploration.zone: plug 3 -> Script Vars 29 out of range
- levels\i29\instance\blizar\blizar_destroyed\i29_blizar_destroyed_devgp_startarea.zone: plug 1 -> Script Vars 19 out of range
- levels\i29\instance\blizar\blizar_destroyed\i29_blizar_destroyed_global_gp.zone: plug 15 -> Script Vars 437 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_background.zone: plug 29 -> Script Vars 236 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_drillcombat.zone: plug 0 -> Script Vars 40 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_drillplatform.zone: plug 3 -> Script Vars 3 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_exploration.zone: plug 1 -> Script Vars 142 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_hubarea.zone: plug 0 -> Script Vars 15 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_surveyor_above.zone: plug 4 -> Script Vars 7 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devart_surveyor_below.zone: plug 110 -> Script Vars 132 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devgp_exploration.zone: plug 60 -> Script Vars 246 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devgp_lubetube.zone: plug 1 -> Script Vars 17 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devgp_startarea.zone: plug 16 -> Script Vars 126 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devgp_surveyor_above.zone: plug 3 -> Script Vars 314 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_devgp_swapsetups.zone: plug 1 -> Script Vars 17 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_global_gp.zone: plug 57 -> Script Vars 751 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_greybox.zone: plug 29 -> Script Vars 66 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_sfx.zone: plug 1 -> Script Vars 167 out of range
- levels\i29\instance\blizar\blizar_intact\i29_blizar_intact_vfx.zone: plug 11 -> Script Vars 5 out of range
- levels\i29\instance\blizar\i29_blizar_intact_devart_grindrail.zone: plug 0 -> Script Vars 42 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_destroyed_collectables.zone: plug 1 -> Script Vars 66 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_destroyed_devart_drillcombat.zone: plug 28 -> Script Vars 75 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_destroyed_devgp_grindrail.zone: plug 0 -> Script Vars 75 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_destroyed_devgp_swapsetups.zone: plug 0 -> Script Vars 62 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_destroyed_sfx.zone: plug 2 -> Script Vars 15 out of range
- levels\i29\instance\blizar_destroyed\blizar_destroyed\i29_blizar_global_gp_shared_bothdims.zone: plug 4 -> Script Vars 38 out of range
- levels\i29\instance\blizar_destroyed\i29_blizar_destroyed_devart_dimensional_dmg.zone: plug 7 -> Script Vars 316 out of range
- levels\i29\instance\clank_puzzles\clank_puzzle_04\cpz_seg_27_crates.zone: plug 7 -> Script Vars 8 out of range
- levels\i29\instance\clank_puzzles\cpz_global_gp.zone: plug 6 -> Script Vars 157 out of range
- levels\i29\instance\cordelion\cordelion_a_main\cordelion_a_art_forge.zone: plug 3 -> Script Vars 3 out of range
- levels\i29\instance\cordelion\cordelion_a_main\cordelion_a_crates.zone: plug 32 -> Script Vars 120 out of range
- levels\i29\instance\cordelion\cordelion_a_main\cordelion_a_gp.zone: plug 4 -> Script Vars 564 out of range
- levels\i29\instance\cordelion\cordelion_a_main\cordelion_a_sfx.zone: plug 250 -> Script Vars 196 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_crates.zone: plug 3 -> Script Vars 205 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_fx.zone: plug 0 -> Script Vars 17 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_gp.zone: plug 42 -> Script Vars 163 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_lgt.zone: plug 3 -> Script Vars 34 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_nav.zone: plug 0 -> Script Vars 2 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_sfx.zone: plug 148 -> Script Vars 432 out of range
- levels\i29\instance\cordelion\cordelion_b_main\cordelion_b_water.zone: plug 42 -> Script Vars 69 out of range
- levels\i29\instance\destroyed_planet\destroyed_planet_dead\destroyed_dead_gameplay.zone: plug 60 -> Script Vars 887 out of range
- levels\i29\instance\hacking\hacking_01\hax_01_gp.zone: plug 18 -> Script Vars 2689 out of range
- levels\i29\instance\hacking\hax_02\hax_02_gp.zone: plug 3 -> Script Vars 1717 out of range
- levels\i29\instance\hacking\hax_06\hax_06_gp.zone: plug 2 -> Script Vars 538 out of range
- levels\i29\instance\hacking\hax_06\hax_06_lgt.zone: plug 2 -> Script Vars 17 out of range
- levels\i29\instance\hacking\hax_09\hax_09_gp.zone: plug 1 -> Script Vars 463 out of range
- levels\i29\instance\hacking\hax_09\hax_09_lighting.zone: plug 7 -> Script Vars 18 out of range
- levels\i29\instance\hacking\hax_25\hax_25_gp.zone: plug 2 -> Script Vars 928 out of range
- levels\i29\instance\hacking\hax_27\hax_27_gp.zone: plug 3 -> Script Vars 800 out of range
- levels\i29\instance\hacking\hax_gbl_gp.zone: plug 5 -> Script Vars 7 out of range
- levels\i29\instance\hacking\hax_gbl_lgt.zone: plug 0 -> Script Vars 6 out of range
- levels\i29\instance\interplanetary_space\deep_space_themap\deep_space_themap_gp.zone: plug 1 -> Script Vars 18 out of range
- levels\i29\instance\interplanetary_space\interplanetary_space_gp.zone: plug 4 -> Script Vars 287 out of range
- levels\i29\instance\malinon_actone\malinon_actone\malinon_actone_gp.zone: plug 11 -> Script Vars 720 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_ambient.zone: plug 6 -> Script Vars 1779 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_crates.zone: plug 0 -> Script Vars 39 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_fx.zone: plug 10 -> Script Vars 739 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_gp_parade.zone: plug 8 -> Script Vars 549 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_gp_post_parade.zone: plug 1 -> Script Vars 1036 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_gp_rooftop.zone: plug 1 -> Script Vars 818 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_gp_trainstation.zone: plug 0 -> Script Vars 2934 out of range
- levels\i29\instance\malinon_intro\malinon_intro\malinon_intro_sfx.zone: plug 15 -> Script Vars 43 out of range
- levels\i29\instance\malinon_intro\malinon_intro_anomalies_hazards.zone: plug 64 -> Script Vars 894 out of range
- levels\i29\instance\malinon_intro\molonoth_passive\molonoth_passive_gp.zone: plug 3 -> Script Vars 7 out of range
- levels\i29\instance\molonoth\molonoth_actthree\i29_molonoth_factory_gp_arena.zone: plug 14 -> Script Vars 477 out of range
- levels\i29\instance\molonoth\molonoth_acttwo\i29_molonoth_art_props.zone: plug 24 -> Script Vars 2533 out of range
- levels\i29\instance\molonoth\molonoth_acttwo\i29_molonoth_gp.zone: plug 14 -> Script Vars 14607 out of range
- levels\i29\instance\molonoth\molonoth_acttwo\i29_molonoth_gp_kill_volumes.zone: plug 0 -> Script Vars 1428 out of range
- levels\i29\instance\molonoth\molonoth_acttwo\i29_molonoth_lgt.zone: plug 0 -> Script Vars 4 out of range
- levels\i29\instance\molonoth\molonoth_acttwo\i29_molonoth_sfx.zone: plug 18 -> Script Vars 146 out of range
- levels\i29\instance\molonoth\molonoth_hack\molonoth_hack_gp.zone: plug 3 -> Script Vars 20 out of range
- levels\i29\instance\nefariouscity\i29_nefcity_gp_tower_interior.zone: plug 11 -> Script Vars 147 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_art_tower.zone: plug 0 -> Script Vars 2 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_crates.zone: plug 1 -> Script Vars 116 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_gp.zone: plug 95 -> Script Vars 1469 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_gp_trainstation.zone: plug 3 -> Script Vars 6051 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_sfx.zone: plug 0 -> Script Vars 128 out of range
- levels\i29\instance\nefariouscity\nefariouscity\i29_nefcity_whitebox_art_towerpath.zone: plug 19 -> Script Vars 116 out of range
- levels\i29\instance\nefariouscity\nefariouscity_tower_ratchet\i29_nefcity_whitebox_art_neftower.zone: plug 0 -> Script Vars 1 out of range
- levels\i29\instance\nefariouscity_actone\nefariouscity_actone\nefariouscity_actone_gp.zone: plug 19 -> Script Vars 1620 out of range
- levels\i29\instance\nefariouscity_actone\nefariouscity_actone\nefariouscity_actone_gp_jpb.zone: plug 67 -> Script Vars 33 out of range
- levels\i29\instance\nefariouscity_tower\nefariouscity_demoend\i29_nefcity_demo_art_buildings.zone: plug 3 -> Script Vars 41 out of range
- levels\i29\instance\nefariouscity_tower\nefariouscity_demoend\i29_nefcity_demo_gp.zone: plug 2 -> Script Vars 20 out of range
- levels\i29\instance\nefariouscity_tower\nefariouscity_marketing\i29_nefcity_art_buildings_marketing.zone: plug 10 -> Script Vars 20 out of range
- levels\i29\instance\nefariouscity_tower\nefariouscity_tower\i29_nefcity_art_tower_interior.zone: plug 0 -> Script Vars 100 out of range
- levels\i29\instance\nefariouscity_tower\nefariouscity_tower\i29_nefcity_tower_sfx.zone: plug 15 -> Script Vars 30 out of range
- levels\i29\instance\nefariouscity_vs2\nefariouscity_vs2_passiveshift\neonefarious_vs2_gp.zone: plug 10 -> Script Vars 11 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_00\pd_00_art.zone: plug 0 -> Script Vars 19 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_00\pd_00_gp.zone: plug 13 -> Script Vars 80 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_02\pd_02_geo.zone: plug 2 -> Script Vars 39 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_03\pd_03_geo.zone: plug 2 -> Script Vars 5 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_05\pd_05_gp.zone: plug 0 -> Script Vars 490 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_07\pd_07_gp.zone: plug 0 -> Script Vars 185 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_08\pd_08_gp.zone: plug 2 -> Script Vars 119 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_09\pd_09_geo.zone: plug 5 -> Script Vars 18 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_09\pd_09_gp.zone: plug 1 -> Script Vars 123 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_10\pd_10_gp.zone: plug 33 -> Script Vars 153 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_11\pd_11_gp.zone: plug 6 -> Script Vars 56 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_12\pd_12_gp.zone: plug 26 -> Script Vars 119 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_13\pd_13_geo.zone: plug 7 -> Script Vars 8 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_14\pd_14_gp.zone: plug 19 -> Script Vars 18 out of range
- levels\i29\instance\pocketdimensions\pocketdimension_16\pd_16_gp.zone: plug 12 -> Script Vars 54 out of range
- levels\i29\instance\sargasso\clankpuzzle_vs\clankpuzzle_vs_gameplay.zone: plug 7 -> Script Vars 556 out of range
- levels\i29\instance\sargasso\clankpuzzle_vs\clankpuzzle_vs_pickups.zone: plug 2 -> Script Vars 98 out of range
- levels\i29\instance\sargasso\clankpuzzle_vs\clankpuzzle_vs_sfx.zone: plug 0 -> Script Vars 3 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_amb_creatures.zone: plug 597 -> Script Vars 2293 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_chase_01.zone: plug 50 -> Script Vars 100 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_chase_01_loop.zone: plug 92 -> Script Vars 258 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_chase_02.zone: plug 105 -> Script Vars 115 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_chase_02_loop.zone: plug 216 -> Script Vars 157 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_foliage.zone: plug 1 -> Script Vars 19 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_terrain_island_02.zone: plug 32 -> Script Vars 36 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_terrain_island_03.zone: plug 224 -> Script Vars 353 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_terrain_island_04.zone: plug 33 -> Script Vars 53 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_terrain_island_05.zone: plug 21 -> Script Vars 23 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_vista_zone_01.zone: plug 110 -> Script Vars 181 out of range
- levels\i29\instance\sargasso\sargasso\i29_sargasso_art_vista_zone_02.zone: plug 80 -> Script Vars 218 out of range
- levels\i29\instance\sargasso\sargasso\sargasso_centipedechase_breakables.zone: plug 145 -> Script Vars 101 out of range
- levels\i29\instance\sargasso\sargasso\sargasso_crates.zone: plug 81 -> Script Vars 59 out of range
- levels\i29\instance\sargasso\sargasso\sargasso_sfx.zone: plug 2 -> Script Vars 274 out of range
- levels\i29\instance\sargasso\sargasso\sargasso_vfx.zone: plug 242 -> Script Vars 156 out of range
- levels\i29\instance\sargasso\sargasso_crystal_collection.zone: plug 3 -> Script Vars 2978 out of range
- levels\i29\instance\sargasso\sargasso_marketing\sargasso_art_terrain_marketing.zone: plug 55 -> Script Vars 34 out of range
- levels\i29\instance\sargasso\sargasso_pocket_dimensions_cine\i29_sargasso_pocket_dimensions_art.zone: plug 3 -> Script Vars 793 out of range
- levels\i29\instance\sargasso\sargasso_trailer\i29_sargasso_amb_creatures_demo.zone: plug 443 -> Script Vars 769 out of range
- levels\i29\instance\sargasso\sargasso_trailer\i29_sargasso_art_terrain_island_03_demo.zone: plug 152 -> Script Vars 238 out of range
- levels\i29\instance\sargasso\sargasso_trailer\i29_sargasso_art_vista_demo.zone: plug 216 -> Script Vars 129 out of range
- levels\i29\instance\savali\savali\savali_badlands_art.zone: plug 0 -> Script Vars 220 out of range
- levels\i29\instance\savali\savali\savali_collectables.zone: plug 62 -> Script Vars 263 out of range
- levels\i29\instance\savali\savali\savali_crates.zone: plug 0 -> Script Vars 413 out of range
- levels\i29\instance\savali\savali\savali_gameplay.zone: plug 34 -> Script Vars 2033 out of range
- levels\i29\instance\savali\savali\savali_global_temples.zone: plug 0 -> Script Vars 59 out of range
- levels\i29\instance\savali\savali\savali_gp_hoverboot.zone: plug 1 -> Script Vars 301 out of range
- levels\i29\instance\savali\savali\savali_quest_shrines.zone: plug 26 -> Script Vars 918 out of range
- levels\i29\instance\savali\savali\savali_vfx.zone: plug 17 -> Script Vars 141 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_global_gp.zone: plug 14 -> Script Vars 1066 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_main_lgt.zone: plug 0 -> Script Vars 9 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_art_exterior_01.zone: plug 18 -> Script Vars 779 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_art_interior_gen_pop.zone: plug 18 -> Script Vars 107 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_art_maxsecurityhalls.zone: plug 357 -> Script Vars 248 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_art_startingarea.zone: plug 38 -> Script Vars 348 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_gp_dome.zone: plug 15 -> Script Vars 107 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_gp_lightningstrikes.zone: plug 16 -> Script Vars 85 out of range
- levels\i29\instance\zordoom\zordoom_main\zordoom_rce_main_gp_startingarea.zone: plug 47 -> Script Vars 330 out of range
- levels\i29\instance\zurkons\zurkons_art_visit_01.zone: plug 38 -> Script Vars 442 out of range
- levels\i29\instance\zurkons\zurkons_art_visit_02.zone: plug 0 -> Script Vars 668 out of range
- levels\i29\instance\zurkons\zurkons_art_visit_02b.zone: plug 1 -> Script Vars 850 out of range
- levels\i29\instance\zurkons\zurkons_art_visit_03.zone: plug 0 -> Script Vars 2153 out of range
- levels\i29\instance\zurkons\zurkons_gameplay_pub_common.zone: plug 1 -> Script Vars 593 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_art_arena.zone: plug 29 -> Script Vars 13 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_art_landing_area_rifts.zone: plug 3 -> Script Vars 498 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_art_pub_interior.zone: plug 0 -> Script Vars 8 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_art_weapons_check_room.zone: plug 0 -> Script Vars 161 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_ambientfight.zone: plug 0 -> Script Vars 13 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_a1.zone: plug 1 -> Script Vars 643 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_a2.zone: plug 0 -> Script Vars 1368 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b1.zone: plug 15 -> Script Vars 813 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b2.zone: plug 0 -> Script Vars 688 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b3.zone: plug 10 -> Script Vars 514 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b4.zone: plug 1 -> Script Vars 439 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b5.zone: plug 0 -> Script Vars 569 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_b6.zone: plug 17 -> Script Vars 316 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c1.zone: plug 17 -> Script Vars 505 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c2.zone: plug 0 -> Script Vars 611 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c3.zone: plug 16 -> Script Vars 554 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c4.zone: plug 0 -> Script Vars 622 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c5.zone: plug 6 -> Script Vars 347 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_challenge_c6.zone: plug 8 -> Script Vars 464 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_arena_common.zone: plug 12 -> Script Vars 1522 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_crates_visit1.zone: plug 6 -> Script Vars 63 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_landing_area_common.zone: plug 2 -> Script Vars 953 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_gameplay_pub_common_allvisits.zone: plug 120 -> Script Vars 265 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_music.zone: plug 0 -> Script Vars 77 out of range
- levels\i29\instance\zurkons\zurkons_visit1\zurkons_sfx.zone: plug 2 -> Script Vars 250 out of range
- levels\i29\overlay\arena\arena_challenge_a3\zurkons_gameplay_arena_challenge_a3.zone: plug 1 -> Script Vars 431 out of range
- levels\i29\overlay\arena\arena_challenge_a4\zurkons_gameplay_arena_challenge_a4.zone: plug 2 -> Script Vars 572 out of range
- levels\i29\overlay\arena\arena_challenge_a5\zurkons_gameplay_arena_challenge_a5.zone: plug 37 -> Script Vars 565 out of range
- levels\i29\overlay\arena\arena_challenge_a6\zurkons_gameplay_arena_challenge_a6.zone: plug 2 -> Script Vars 401 out of range
- levels\i29\overlay\arena\arena_challenge_empty\zurkons_gameplay_arena_empty_gp.zone: plug 6 -> Script Vars 165 out of range
- levels\i29\overlay\arena\arena_challenge_secret\zurkons_gameplay_arena_challenge_secret.zone: plug 23 -> Script Vars 327 out of range
- levels\i29\overlay\arena\arena_nefarious_boss_fight\zurkons_art_arena_nef_boss_cover.zone: plug 0 -> Script Vars 1 out of range
- levels\i29\overlay\clankpuzzle\cp_seg_01_puz_02\cp_seg_01_puz_02_crates.zone: plug 16 -> Script Vars 20 out of range
- levels\i29\overlay\clankpuzzle\cp_seg_01_puz_02\cp_seg_01_puz_02_pickups.zone: plug 13 -> Script Vars 148 out of range
- levels\i29\overlay\clankpuzzle\cp_seg_01_puz_03\cp_seg_01_puz_03_gp.zone: plug 177 -> Script Vars 1262 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_05\cpz_seg_05_gp.zone: plug 5 -> Script Vars 1444 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_06\cpz_seg_06_crates.zone: plug 10 -> Script Vars 12 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_06\cpz_seg_06_gp.zone: plug 31 -> Script Vars 1438 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_06\cpz_seg_06_pickups.zone: plug 0 -> Script Vars 124 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_12\cpz_seg_12_crates.zone: plug 23 -> Script Vars 28 out of range
- levels\i29\overlay\clankpuzzle\cpz_seg_14\cpz_seg_14_gp.zone: plug 26 -> Script Vars 1781 out of range
- coretest\anim\core_test_partial_ragdoll\level\instance\ground\containernavdata.zone: in the dag but not in the toc
- coretest\anim\core_test_partial_ragdoll\level\instance\ground\ground.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_lights\levels\instance\primary\containernavdata.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_lights\levels\instance\primary\instanceregion\mainzone.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_lights\levels\instance\primary\instanceregion\zone.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_reload\levels\instance\reload_inst\containernavdata.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_reload\levels\instance\reload_inst\region\main.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_sync_action\levels\instance\primary\containernavdata.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_sync_action\levels\instance\primary\region\main_zone.zone: in the dag but not in the toc
- coretest\cinematics\core_test_cine_sync_action\levels\instance\region\containernavdata.zone: in the dag but not in the toc
- coretest\decal_test\decal_double_sided_material.zone: in the dag but not in the toc
- coretest\decal_test\decal_dynamic_render_modes.zone: in the dag but not in the toc
- coretest\decal_test\decal_neg_scale.zone: in the dag but not in the toc
- coretest\decal_test\decal_order.zone: in the dag but not in the toc
- coretest\decal_test\decal_rot_scale.zone: in the dag but not in the toc
- coretest\decal_test\decal_static_render_modes.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\art.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\bounce_test_light_grid.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\embeddedvolumetest.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\emissive_light_grid.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\env_probe_test.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\fog_test_light_grid.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\lightgridgreen.zone: in the dag but not in the toc
- coretest\levels\light_grid_test\lightgridred.zone: in the dag but not in the toc
- coretest\levels\vertex_paint_test\test1.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\containernavdata.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\posteffects_lighting_test_fx.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\posteffects_lighting_test_gameplay.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\posteffects_lighting_test_ground.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\posteffects_lighting_test_lgt.zone: in the dag but not in the toc
- coretest\posteffects_lighting_test\instance\posteffects_lighting_test_inst\posteffects_lighting_test_light_grid.zone: in the dag but not in the toc
- coretest\rename\levels\jonny_ratchet_level_test\openarea\open_world\hex_region\testzone.zone: in the dag but not in the toc
- coretest\sound\core_test_sound_propagation_simple\instance\core_test_sound_propagation_simple\containernavdata.zone: in the dag but not in the toc
- coretest\sound\core_test_sound_propagation_simple\instance\core_test_sound_propagation_simple\core_test_sound_propagation_simple\core_test_sound_propagation_simple.zone: in the dag but not in the toc
- coretest\voxelization_test\voxelization_order.zone: in the dag but not in the toc
- coretest\voxelization_test\voxelization_test.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\art_a_ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\art_arena.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\art_lobby.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\audio_sfx.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\cinematic.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\fx.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\agorian_arena\gameplay_scenes.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_a_bus_depot.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_b_spaceport.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_c_theatre_district.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_d_tech_center.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_e_tech_center_interior.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_f_boss_battle.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_g_ambient_buildings.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_h_fog_plane.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_i_cinematics.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_j_signs.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_k_cinematic_characters.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\art_l_time_ribbon.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\audio_music.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\breakables.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_1_bus_depot.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_2_spaceport.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_3_theatre_district.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_4_tech_center.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_5_boss_battle.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_scenes.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\gameplay_ties.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\pathfinding.zone: in the dag but not in the toc
- legacy\rcf2\levels\axiom_city\sound.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacticmap\galacticmap.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\art.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\dans_temp_zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\fx.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\gameplay_scenes.zone: in the dag but not in the toc
- legacy\rcf2\levels\galacton_ship\pathfinding.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\ambience.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_bldg.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_breakables.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_dam.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_ground.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_plants.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_rocks.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_a_trees.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_b_bldg.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_b_ground.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_b_plants.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_b_rocks2.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_c_bldg.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_c_ground.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_c_plants1.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_c_rocks.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\art_c_trees.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\audio_sfx.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\gameplay_a.zone: in the dag but not in the toc
- legacy\rcf2\levels\gimlick_valley\gameplay_scenes.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\ambient_cars.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\art_a_ground.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\art_a_hardware.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\art_a_opening_area.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\audio_sfx.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay_bucket_of_win.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay_gca01_start.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay_gca02_middle.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay_gca03_end.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_a\gameplay_gca_dialogue.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_b\art_a_clanks_subconcious.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_b\cinematics_clank_chamber.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_b\cinematics_plumb_set.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\ambient_cars.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\art_a_exterior_bldgs.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\art_a_ground.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\art_a_hardware.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\art_a_rooms.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\art_a_shrubs.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\audio_sfx.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_bucket_of_win.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_gcc01_start.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_gcc02_subcon.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_gcc03_aftersub.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_gcc_dialogue.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_c\gameplay_ties.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_bossarena.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_clock_body.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_facade.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_hoverbootpath1.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_plants.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\art_a_ufrag.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay_bucket_of_win.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay_gcd01_start.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay_gcd02_middle.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay_gcd03_end.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_d\gameplay_gcd_dialogue.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\ambient_cars.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_a_background_bldg.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_b_cinematics.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_b_cinematics_88mph.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_b_cinematics_destruction.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_b_cinematics_gc4_orvus.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\art_c_hoverbootpath_plants.zone.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\fx.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay_gce01_start.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay_gce02_middle.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay_gce03_end.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay_gce_dialogue.zone: in the dag but not in the toc
- legacy\rcf2\levels\great_clock_e\gameplay_scenes.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_a_krell_cave_01.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_b_krell_canyon.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_c_krell_valley_01.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_d_krell_valley_02.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_e_krell_cave_02.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_f_shrubs_outside.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\art_g_shrubs_outside_pt2.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\breakables_kc.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\breakables_large.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\cameras.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\fx.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_01_mine_cave.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_02_agorian_sniper.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_03_agorian_tank.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_04_agorian_fighters.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_05_fongoid_cave.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_krell_dialogue.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\gameplay_ties.zone: in the dag but not in the toc
- legacy\rcf2\levels\krell_canyon\sound.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\ambient.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_a_junkyard.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_b_city_exterior.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_c_city_interior.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_d_grindrail_segment.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_e_grindrail.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_g_ambient_plains.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_h_ambient_plants.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_i_ambient_rocks.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_j_shrubs.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_k_shrubs2.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_l_shrubs3.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\art_m_time_ribbon.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\audio_reverb.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\audio_sfx.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\breakables.zone: in the dag but not in the toc
- legacy\rcf2\levels\molonoth\cinematics_robot_interior.zone: in the dag but not in the toc

## Knowledge used

- 16_rando_spawners.lua: 235 built-in template uids, 27 built-in combat pairs
- uid D7AFB38AC7CA1114 named both enm_indigenous_ali and enm_indigenous_alien_spitter (kept enm_indigenous_ali)
- rivet.log: 17 ASSET, 40 learned, 0 CHANGED, 676 SPAWN lines, 0 spawn(s) tied to the template uid its variable held
- learned anim-clue hosts: 118 clues, 43 clue families
- external spawn points: 265, resolved 8, unresolved 257, ambiguous 0
- enemy-kind family sources: kit knowledge 31, unknown: no rivet.log has seen this kind yet 8, actor file 3
