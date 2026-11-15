# Test report: dev 10.13 (kit 10.0.9), Chaos Randomizer

Date: 2026-11-16. Build machine: Linux, Python 3.13, Lua 5.4 (lupa). **No game was available.**

- **PASSED (sim)**: the real scripts passed against tests/sim/rivet_sim.lua. Its encounter model (10.12) and
  the per-planet node lists (new) are SIMULATED.
- **FAILED**: none.
- **UNTESTED (game)**: everything that needs the real game. No gameplay result is claimed.

## Summary

| | |
|---|---|
| Automated suite | **504 run, 0 failures, 0 errors, 21 skipped** (the same 21 skips as before: 9 PowerShell 7, 12 git history) |
| New: tests/test_v1013.py | 23 run, 23 passed (sim) |
| 10.12 suite (tests/test_v1012.py) | 32 run, 32 passed: Enemy and Boss behaviour unchanged with Chaos installed and OFF |
| Earlier suites changed | only the kit version (10.0.9), the banner (dev 10.13), the file list (17 kit scripts; the player package still 16, without chaos.lua) |
| Seeds | unchanged (generator 10.11.0); big_batch not re-run |
| Real game | **not run** |

## The request's test list

| Case | Result | Test |
|---|---|---|
| The module loads; OFF by default; OFF = nothing read or written | PASSED (sim) | LoadAndToggleTests.test_loads_off_by_default |
| The toggle works (BACKSPACE; on-screen state; Ctrl shows status) | PASSED (sim) | test_backspace_toggles_and_says_so |
| Its own key, not the Enemy / Boss keys | PASSED (sim) | test_its_own_key |
| The setting persists (save, restore, New Game) | PASSED (sim) | test_setting_persists_and_survives_new_game, test_the_setting_decides_the_start |
| Chaos replaces every category (regular, flyer, turret, large, health-bar elite, story boss, unclassified) | PASSED (sim) | AnythingBecomesAnythingTests.test_every_category_is_replaced_and_used |
| Bosses become regular enemies | PASSED (sim) | test_bosses_become_regular_and_regular_become_bosses (3 seeds, each both ways) |
| Regular enemies become bosses | PASSED (sim) | the same |
| Cross-planet replacements | PASSED (sim) | CrossPlanetTests.test_enemies_of_another_planet_appear (Nefarious City templates on Savali) |
| `chaos_cross_planet = false` keeps one planet | PASSED (sim) | test_this_planet_only_when_switched_off |
| Few repeats; one encounter's enemies all different | PASSED (sim) | test_the_same_replacement_repeats_as_little_as_possible |
| Deterministic by seed; another seed differs | PASSED (sim) | test_seed_decides |
| Nothing has to be learned first | PASSED (sim) | test_no_learning_needed |
| Chaos overrides Enemy and Boss Randomizers; their settings untouched | PASSED (sim) | PriorityTests.test_chaos_overrides_and_off_gives_the_normal_randomizers_back |
| Disabling Chaos restores the normal randomizer behaviour (exactly their picks) | PASSED (sim) | the same; test_off_with_the_others_off_is_the_original_game; test_others_resume_by_their_own_rules |
| No guards: no timeout, no stuck put-back, no retry limit, no boss-area put-back, no family block | PASSED (sim) | NoGuardsTests.test_nothing_is_put_back_by_itself, test_a_replacement_of_any_kind_is_learned_not_blocked |
| Running encounters are changed too | PASSED (sim) | test_running_encounters_are_changed_too |
| The randomizer never forces progression | PASSED (sim) | test_the_randomizer_never_forces_progression |
| Code integrity: a node that does not match is never written | PASSED (sim) | IntegrityTests |
| Removing chaos.lua breaks nothing; without 16_rando_spawners Chaos stays off | PASSED (sim) | RemovalTests (2) |
| Existing features intact (items, shop, kit, Enemy/Boss) | PASSED (sim) | RemovalTests.test_other_features_intact; the whole earlier suite |
| chaos.lua is never in a player package | PASSED (builder) | test_v055.PackageTests; the new release_tools/validate_release.py check compiles but was not run (no package was built for release) |

## UNTESTED in the game

Everything in ENEMIES_AND_BOSSES.md section 7 (Templates found, spawned bots answering, events), plus:
- whether a template from **another planet** spawns at all, spawns wrong or makes the game misbehave;
- whether a **story boss template** spawned by an ordinary spawner works anywhere;
- what happens to encounters, doors, objectives and boss fights with any replacement (by design, no
  outcome is expected);
- frame time with Chaos writing every slot of a big level;
- BACKSPACE as a key in the game (does the game pass it to rivet_hook, and does it do something of its
  own?): change `key_chaos` in 04 if it does.
