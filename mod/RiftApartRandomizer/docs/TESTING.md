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

## 2. Round 24: your first playthrough with 10.0

Use a spare save slot and the kit's settings (hub = true). Send the whole rivet.log afterwards. Each
step names the log line that shows it worked.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.0`.
2. **New Game → Zurkie's.** Play the parade until Ratchet picks up the wrench. Look for:
   - `RANDO-HUB	the parade is at checkpoint ...`
   - `warp to Zurkie's at CHK_ZURK_00_DEFAULT`
   - `start menu: 1. Prologue ...`

   Note whether you landed on Zurkie's and could move.
3. **Nefarious City (most important).** At Zurkie's press `]` until it says Nefarious City, then
   `Ctrl+]`. Look for:
   - `hero: ratchet confirmed`
   - `made available MIS_NEFCITY_01`
   - `start MIS_NEFCITY_01`
   - `travel: warp to CHK_NEFCITY_START`
   - `RANDO-CHECKPOINT CHK_NEFCITY_START`

   Does the city's story play from its beginning? Does the objective leave "go to Nefarious City"?
   Play it to the end: is `[ORDER KEPT]` logged, and are you back at Zurkie's?
4. **Battle Arena.** `]` to "Battle Arena", `Ctrl+]`. Does Zurkon's arena intro play? Finish it.
5. **Prologue.** `]` to "Prologue", `Ctrl+]`. Are you back in the parade where you left it? Finish it.
   The game then takes you to Nefarious City: are you brought back to Zurkie's once the city has
   loaded (`the new planet loaded` in the log), and does the game stay stable after that warp?
   Then choose Nefarious City: the log should say `already active` (the game started it itself).
6. **A shuffled planet.** Once a "Coordinates" reward arrives, `]` shows that planet. Go there. Note
   whether its story starts, and the `RANDO-CHECKPOINT` lines (`learned the start of ...`).
7. **Planet menu.** From the ship, pick a planet you have no Coordinates for: are you sent back to
   Zurkie's?
8. **Shop.** Open Ms. Zurkon's shop. `RANDO-SHOP ... search done` and no "frame budget" lines? Do
   closed slots show the Burst Pistol? Does the list match the spoiler's SHOP section? Does the game
   behave normally there?
9. **Rewards.** Armor pods and early Gold Bolts give weapons, armor or Coordinates
   (`RANDO-REAL`, the on-screen messages).
10. **If a destination will not start:** wait 20 s (`STORY RELOAD`), then try `/`, then `Ctrl+[`
    twice. Note which step got it going.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
