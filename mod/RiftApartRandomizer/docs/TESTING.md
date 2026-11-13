# Testing (Randomizer 10.0, Public Release v0.52)

Results come in four kinds, and a pass in one is never evidence for another. VERIFICATION_REPORT.md
sorts every feature into them. This page covers how the tests run and what to check in your
first full playthrough.

## 1. Automated tests (this build)

`python run_tests.py`: **371 tests, 0 failures, 0 errors, 17 skipped** (TEST_RESULTS.txt; v0.52 adds tests/test_v052.py, 15).
The skipped tests:
- 9 need PowerShell 7, which could not run on the build machine;
- 8 need the 5.0 and 6.0 git commits, which are not in this repository.

| Suite | Tests | What it covers |
|---|---|---|
| **test_v90** | 20 | 9.0: no hub; retired presets and settings; every mode starts prologue > Nefarious City > Sargasso; your 9.0 and 8.5.2 settings files; a New Game played to Sargasso with no warp, flight, mission write or hero swap; a leftover hub script reported and inert; locked levels still send you back |
| test_generator, test_registry | 39 | seeds, items, prices, currency, the weapon registry, mutation tests (the checkers catch broken seeds) |
| test_campaign, test_levels | 48 | campaign and level-lock replays (9.0's fixed start), mission control, the director |
| test_runtime | 86 | deliveries, the shop, armor, currency, save/restore, the real event streams of rounds 13-20 |
| test_v81, test_v82, test_v83 | 34 | checkpoint catalog, test travel, keys |
| test_v84 | 24 | registry, weapon types, the shop's pointer layout, ARSENAL_RESTORED, landings, the kit check, INSTALL.txt naming exactly the kit's files |
| test_v85 | 19 | the 8.5 fixes: mailbox take-back, late restore, New Game resets, shop routes |
| test_native | 3 | rando_give.dll: the source rebuilds to the shipped DLL **byte for byte**; its game-code checks match both code dumps |
| test_companion, test_tools, test_regression_v5/v6 | 21 | companion (needs pwsh), spoiler and log tools; 5.0/6.0 regressions (need git history) |

The older suites pin the settings they were written for (`tests/harness.py`, CLASSIC_TEST_SETTINGS:
no Coordinates, the game's own order, Raritanium 20-150). Your defaults changed in 8.5.1; test_v90
runs them, and your kit 04 file, as they are.

## 2. Round 26: v0.53 (build 10.0.4)

Your round 25 save carries over (same seed, same fingerprint). Load it; no New Game is needed.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.4`.
2. **Load the save in Nefarious City.** `planetary travel and level bits left to the game while
   nefcity_1 runs` (and **no** `planetary travel: done (0x0 -> 0x1)` while the city's story runs).
3. **The boss fight (the key test).** At the shift to Savali / Sargasso: does Ratchet arrive
   **without** the ship, on solid ground? Logged: `arrived on savali during nefcity_1`, then on the
   way back `back on nefarious_city from savali during nefcity_1 - the story's own travel` (no
   "destinations open" message in the fight).
4. **After the city's story.** Once MIS_NEFCITY_01 completes and you are back in the city:
   `planetary travel: done (0x0 -> 0x1)` and the level bits again; the ship's planet menu works.
5. Then continue with the round 25 list below from step 4.

## 2b. Round 25: v0.52 (build 10.0.3)

Use a spare save slot and the kit's settings (hub = true). Your round 24 seed carries over (same
fingerprint), but start a **New Game**: the new start only runs from the parade. Send the whole
rivet.log afterwards. Each step names the log line that shows it worked.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.3`.
2. **New Game → Nefarious City (the key test).** Play the parade until the warp. In this order:
   - `going to the hub (Nefarious City): the parade handed Ratchet back after his wrench`
   - `prologue: MIS_INTRO written Complete Finished` (now **before** the story starts)
   - `made available MIS_NEFCITY_01`, `start MIS_NEFCITY_01 done (available -> active)`
   - `with nefcity_1: made available MIS_NEFCITY_01_TRAINSTATION`
   - `opening of nefcity_1: <NAME> (hash 3046787773, ...)` **(note the name)**, or
     `hash 3046787773 is not among the checkpoints your game lists` plus `checkpoints listed for
     nefarious_city:` (send that line)
   - `travel: warp to <NAME>`, then `RANDO-CHECKPOINT <NAME>` and `opening of nefcity_1 loaded`

   **Most important:** does the arrival cutscene play, then gameplay? Look for
   `objective MIS_NEFCITY_01 OBJ_NEFCITY_GO_TO_NEFCITY 2` and the next objective lines.
3. **If it still waits at "go to Nefarious City":** don't press anything for a minute (the hub
   reloads the opening once, `[STORY RELOAD]`). Then try `/` once. Note what each did.
4. **The city's story to its end.** Does the train station part work? Then the game flies you to
   Sargasso: is `[ORDER KEPT]` logged, and are you back in Nefarious City (at `CHK_NEFCITY_SHIP`)?
5. **Battle Arena.** `]` to "Battle Arena", `Ctrl+]`. Does Zurkon's arena intro play? Finish it:
   are you brought back to Nefarious City?
6. **A shuffled planet.** Once a "Coordinates" reward arrives, `]` shows that planet. Go there. Note
   whether its story starts, and the `RANDO-CHECKPOINT` lines (`learned the start of ...`).
7. **Planet menu.** From the ship, pick a planet you have no Coordinates for: are you sent back to
   Nefarious City?
8. **Rewards.** Every Gold Bolt gives an item (weapon, gadget, armor or Coordinates), matching the
   spoiler.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
