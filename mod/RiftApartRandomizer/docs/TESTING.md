# Testing (Randomizer 9.0)

Results come in four kinds, and a pass in one is never evidence for another. VERIFICATION_REPORT.md
sorts every feature into them. This page covers how the tests run and what to check in your
first full playthrough.

## 1. Automated tests (this build)

`python run_tests.py`: **293 tests, 0 failures, 0 errors, 17 skipped** (TEST_RESULTS.txt).
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

## 2. Your first playthrough with 9.0 (round 23)

Use the kit's `04_rando_settings.lua` (preset **`balanced`**, your defaults) on a **spare save slot**,
with your saves backed up. Leave `test_travel = false`. Delete any `15_rando_hub.lua` from
`<game>\scripts`. Start the companion, then the game, **New Game**.

Watch for these, and note anything else that looks wrong:

1. **rivet.log at start:**
   - `RANDO-KIT all 13 scripts are 9.0.0` (and no "delete from the scripts folder" line);
   - `RANDO-SEED ARSENAL_RESTORED is installed (the game has ...)` if you have the mod;
   - no `RANDO-ERROR`, no `is gone in 9.0` (the kit's 04 file has no hub options).
2. **The prologue:** `Randomizer: new game - seed ... starts over` and the start items arrive. The
   parade plays to its end; nothing takes you anywhere.
3. **Nefarious City, then Sargasso:** the game takes you there itself. No `RANDO-TRAVEL warped`,
   no `travel` line from the randomizer, no hero change by the randomizer.
4. **Ms. Zurkon:** `RANDO-SHOP vendor ... slot objects by pointer` in the log. Do her weapons and
   prices match the spoiler's SHOP list? Buy one: is it the weapon shown, at the price shown?
5. **Rewards:**
   - each Gold Bolt: "Gold Bolt n/25: ..." with the spoiler's item;
   - "Added to your inventory: ..." for weapons; armor appears in the menu;
   - Bolts and Raritanium go up by the amount shown;
   - a story mission on a planet whose Coordinates you lack says "Banked"; finding the
     Coordinates pays it.
6. **The ship's planet menu** after Sargasso: which planets does it offer?
7. **Save, quit, load:** `;` shows the same Gold Bolts and rewards.
8. **The finale:** "campaign complete" when you finish the game.

9. **If anything stalls** (a reward that never comes), the log says so: `taken back`,
   `withdrawn`, `direct delivery paused`, `given directly (...)`.

Send `rivet.log`, the companion window's text and its `randomizer_saves` folder.
`python tools/summarize_log.py rivet.log` lists the travel, delivery and shop lines.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
