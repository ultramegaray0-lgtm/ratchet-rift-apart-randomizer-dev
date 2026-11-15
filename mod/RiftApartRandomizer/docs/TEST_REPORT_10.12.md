# Test report: dev 10.12 (kit 10.0.8), Enemy Randomizer and Boss Randomizer

Date: 2026-11-15. Build machine: Linux, Python 3.13, Lua 5.4 (lupa). **No game was available.**

Three kinds of result, never mixed:
- **PASSED (sim)**: the real scripts passed against tests/sim/rivet_sim.lua. The simulator's encounter
  model is SIMULATED from the rivet DDL: it shows the randomizer's own decisions are right *if the
  game behaves like the model*.
- **FAILED**: a test that ran and failed.
- **UNTESTED**: needs the real game. Nothing here is claimed to work in the game.

## Summary

| | |
|---|---|
| Automated suite (`python run_tests.py`) | **481 run, 0 failures, 0 errors, 21 skipped** (skips, all as before: 9 need PowerShell 7, 12 need git history this shallow clone does not have) |
| New suite tests/test_v1012.py | 32 run, 32 passed (sim) |
| Earlier suites changed | only expectations of the file list (13 -> 16 release scripts), the kit version (10.0.8), the banner (dev 10.12) and the event count after retries (28); no behaviour expectation changed |
| Seeds | unchanged (generator 10.11.0 untouched); big_batch was **not** re-run for this build |
| Real game | **not run** |
| FAILED | none |

## Enemy Randomizer

| Case (from the request) | Result | Test |
|---|---|---|
| Enabled: enemies are randomized | PASSED (sim) | EnemyTests.test_key_turns_it_on_and_only_regular_enemies_change |
| Disabled: original enemies remain (not one spawner read or written) | PASSED (sim) | OffByDefaultTests.test_both_off_nothing_read_or_written |
| Defeat randomized enemies, the encounter completes | PASSED (sim) | EnemyTests.test_progression_multi_enemy_encounter, test_every_encounter_completes |
| Doors open | PASSED (sim) | the same (the node's "all dead" output: S.doors) |
| Multiple-enemy encounters: complete only when all are dead, once | PASSED (sim) | test_progression_multi_enemy_encounter (2 of 3 dead: still running; 3rd: complete; no second completion) |
| Checkpoints and reloads (same picks; original never lost) | PASSED (sim) | test_picks_are_the_same_after_a_reload (nodes made anew and nodes kept) |
| Same family, same planet; bosses, story bosses, friendlies, unknown never touched | PASSED (sim) | test_key_turns_it_on..., BossTests.test_story_bosses_and_friendlies_are_never_touched |
| Learning from the game's own spawns; pool grows while playing | PASSED (sim) | test_learning_while_playing |
| A running encounter is never changed | PASSED (sim) | test_running_encounters_are_never_changed |
| OFF in the middle of an encounter | PASSED (sim) | test_off_in_the_middle_of_an_encounter |
| Real game: Templates found at the expected place | UNTESTED | ENEMIES_AND_BOSSES.md section 7, item 1 |
| Real game: spawned actors answer `rivet.component(..., "GameBot...")` (learning) | UNTESTED | item 3 |
| Real game: new enemies spawn, fight, die; doors/objectives follow | UNTESTED | item 4 |
| Real game: deaths, checkpoint reloads, planet changes, hub returns | UNTESTED | item 5 |
| Real game: no geometry clipping / falling / stuck enemies | UNTESTED | only the same-family rule and the 180 s safety net address it |

## Boss Randomizer

| Case | Result | Test |
|---|---|---|
| Enabled: eligible boss-tier enemies are randomized | PASSED (sim) | BossTests.test_bosses_are_permuted_and_never_regular_enemies |
| No duplicates (a permutation per family and planet) | PASSED (sim) | the same |
| Disabled: original bosses remain | PASSED (sim) | IndependenceTests.test_four_combinations, test_each_switch_changes_only_its_own |
| Defeat completes the encounter once; arena door opens | PASSED (sim) | test_boss_defeat_completes_the_encounter_once |
| A spawned enemy with its own boss health bar becomes boss tier (and leaves the enemy pool) | PASSED (sim) | test_a_health_bar_makes_a_regular_bot_boss_tier |
| Story bosses unchanged (8 fights listed in boss.lua) | PASSED (sim) | test_story_bosses_and_friendlies_are_never_touched |
| Story boss areas: every change put back while there, back on after | PASSED (sim) | SafetyNetTests.test_story_boss_area_puts_everything_back |
| Boss phases, health bars, death sequences | UNTESTED | in the game; story bosses are not changed, boss-tier spawns have one death counted by their node |
| Arena exits unlock, story progression and cutscenes after a boss | UNTESTED | in the game |

## Combined

| Case | Result | Test |
|---|---|---|
| Both enabled | PASSED (sim) | test_four_combinations, RemovalTests.test_other_features_unchanged |
| Enemy on, boss off | PASSED (sim) | test_four_combinations |
| Enemy off, boss on | PASSED (sim) | test_four_combinations |
| Both disabled | PASSED (sim) | test_four_combinations, test_both_off_nothing_read_or_written |
| One switch never changes the other | PASSED (sim) | test_each_switch_changes_only_its_own |
| Switches saved, restored, kept over New Game; choice before the restore wins | PASSED (sim) | SaveTests (3) |
| Reading status never changes the save | PASSED (sim) | SaveTests.test_reading_never_changes_the_save |
| Removing 16_rando_spawners.lua, enemy.lua or boss.lua breaks nothing | PASSED (sim) | RemovalTests (3) |
| Items, shop, armor, kit check unchanged | PASSED (sim) | the whole earlier suite (449 tests) still passes; test_other_features_unchanged |
| Safety nets: no spawn 20 s; alive 180 s; 3 reloads; wrong family | PASSED (sim) | SafetyNetTests (4) |
| Layout found by signature at another offset; garbage node skipped | PASSED (sim) | LayoutTests |
| Big levels: writes and put-backs spread over frames | PASSED (sim) | BudgetTests |
| Real game: no conflict with weapon randomization, collectibles, planet shuffle, hub returns, saves | UNTESTED | |
| Real game: frame budget (no "ran past the 8 ms frame budget" lines in 16_rando_spawners) | UNTESTED | |

## What would make a case FAIL in the game, and what then happens

| If the game differs from the model | What the randomizer does |
|---|---|
| Templates is not where the DDL layout says | every node `skipped`; nothing changes |
| Spawned actors cannot be asked for their components | nothing is learned; nothing changes |
| The node copies its Templates before the randomizer writes (so the write has no effect) | the original enemies spawn; nothing breaks |
| A template id cannot spawn outside its own spawner | 20 s later that encounter is put back and kept |
| A replacement spawns somewhere it cannot be killed | 180 s later put back and kept; load the last checkpoint |
| Progression waits for a specific enemy type (not the node's count) | not expected from the DDL; would show as an encounter that does not complete: 3 reloads put it back |
