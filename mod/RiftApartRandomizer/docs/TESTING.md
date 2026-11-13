# Testing (Randomizer 10.0)

Results come in four kinds, and a pass in one is never evidence for another. VERIFICATION_REPORT.md
sorts every feature into them. This page covers how the tests run and what to check in your
first full playthrough.

## 1. Automated tests (this build)

`python run_tests.py`: **332 tests, 0 failures, 0 errors, 17 skipped** (TEST_RESULTS.txt).
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

## 2. Round 24: your first playthrough with v0.51 (build 10.0.2)

Use a spare save slot and the kit's settings (hub = true). Send the whole rivet.log afterwards. Each
step names the log line that shows it worked.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.2`.
2. **New Game → Nefarious City.** Play the parade until Ratchet picks up the wrench, then keep
   walking. The warp should come a few seconds later, not at the wrench. Look for:
   - `RANDO-HUB	going to the hub (Nefarious City): the parade handed Ratchet back after his wrench`
   - `made available MIS_NEFCITY_01`, then `start MIS_NEFCITY_01 done (available -> active)`
   - `travel: warp to CHK_NEFCITY_START`, then `RANDO-CHECKPOINT CHK_NEFCITY_START`
   - `prologue: MIS_INTRO written Complete Finished`

   **Most important:** can Ratchet walk right after the warp? Does the city's story play from its
   beginning, and does the objective leave "go to Nefarious City"?
3. **The city's story to its end.** Then the game flies you to Sargasso: is `[ORDER KEPT]` logged,
   and are you back in Nefarious City (at `CHK_NEFCITY_SHIP`)?
4. **Battle Arena.** `]` to "Battle Arena", `Ctrl+]`. Does Zurkon's arena intro play? Finish it:
   are you brought back to Nefarious City?
5. **A shuffled planet.** Once a "Coordinates" reward arrives, `]` shows that planet. Go there. Note
   whether its story starts, and the `RANDO-CHECKPOINT` lines (`learned the start of ...`).
6. **Planet menu.** From the ship, pick a planet you have no Coordinates for: are you sent back to
   Nefarious City?
7. **Shop.** Open Ms. Zurkon's shop. `RANDO-SHOP ... search done` and no "frame budget" lines? Do
   closed slots show the Burst Pistol? Does the list match the spoiler's SHOP section?
8. **Rewards.** Every Gold Bolt gives an item (weapon, gadget, armor or Coordinates), matching the
   spoiler.
9. **If a destination will not start:** wait 20 s (`STORY RELOAD`), then try `/`, then `Ctrl+[`
   twice. Note which step got it going.
10. **If Ratchet still cannot move after the warp:** note it, and try `/` (loads the city's story
    start again). The `RANDO-HUB` and `RANDO-DISCOVER ... MIS_INTRO` lines around the warp show which
    parade step was running.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
