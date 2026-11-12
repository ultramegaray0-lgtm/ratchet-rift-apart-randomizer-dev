# Testing (Randomizer 8.5)

Results come in four kinds, and a pass in one is never evidence for another. VERIFICATION_REPORT.md
sorts every feature into them. This page covers how the tests run and what to check in your
first full playthrough.

## 1. Automated tests (this build)

`python run_tests.py`: **340 tests, 0 failures, 0 errors, 17 skipped** (TEST_RESULTS.txt).
The skipped tests:
- 9 need PowerShell 7, which could not run on the build machine;
- 8 need the 5.0 and 6.0 git commits, which are not in this repository (the 8.3 and 8.4 regressions run).

| Suite | Tests | What it covers |
|---|---|---|
| test_generator, test_registry | 39 | seeds, items, prices, currency, the weapon registry, mutation tests (the checkers catch broken seeds) |
| test_campaign, test_levels | 50 | campaign and level-lock replays, mission control, the director |
| test_hub | 32 | hub plans (every order a player could choose), New Game → Zurkie's, destinations to the finale |
| test_runtime | 86 | deliveries, the shop, armor, currency, save/restore, the real event streams of rounds 13-20 |
| test_v81, test_v82, test_v83 | 55 | checkpoint catalog, test travel, story on arrival, keys |
| **test_v84** | 31 | the round 20 fixes, below, and INSTALL.txt naming exactly the kit's files |
| **test_v85** | 20 | the 8.5 fixes, below (17 of them fail on the 8.4 scripts; 3 are controls) |
| test_regression_v83 | 1 (175 seeds) | the same seeds as 8.3 in 7 presets; only 4 heroes and 3 entries differ (8.4's fix) |
| **test_regression_v84** | 2 (175 seeds) | identical seeds to 8.4 in 7 presets, every field; the generation scripts differ only in the version tag |
| test_native | 3 | rando_give.dll: the source rebuilds to the shipped DLL **byte for byte**; its game-code checks match both code dumps |
| test_companion, test_tools | 13 | companion (needs pwsh), spoiler and log tools |

test_v84 pins down each round 20 finding: a stale saved hero is never trusted; "already playing"
counts as confirmed; the story waits for a slow swap; a refused swap is reported; Zurkie's own visit
keeps its hero through a load; a hub trip starts the story before it travels and "go to" finishes on
landing; an on-planet start that waits is reloaded and then moves; test landings never feed the hub;
a load after an equip teaches no weapon type; a save's wrong lessons are dropped; purchases teach a
type in either order and are never a late answer; the shop's slot objects are found through
pointers; ARSENAL_RESTORED is seen by the game itself; the kit check; and the whole round 20 event
stream replays without an error.

test_v85 pins down each 8.5 fix: a mission call waits through a load, and one the helper never took
is taken back and never runs late; a load that never ends still times out; an unanswered item is
taken back and given exactly once on the next planet; currency in flight at a New Game is withdrawn;
a late restore keeps this session's currency, never doubles a payment the save has, never puts a
confirmed item back to queued, and keeps armor sources, shop gifts and the armor baseline; a New
Game clears the hub's and the delivery's session record; the history is capped; the shop's extra
weapons are given without a helper, with a stopped helper and with a vendor never found, and not
with a working shop; a menu landing is saved at once and `TRANSITION_TO` is never kept.

**The simulator is not your game.** Hero swaps and "go to" steps in `tests/sim/rivet_sim.lua` are
modelled on rounds 17 and 20 and marked SIMULATED. 8.5 adds `SIM.mailbox.hold` (a helper that
runs but takes no request), also marked SIMULATED: no round has shown it.

**Seeds.** `python tools/big_batch.py`: **43,000 of 43,000 valid** (BATCH_8.5.txt). Every seed passes
the generator's own audit and the independent Python verifiers: items, the campaign replays, and
every hub order.

**Static checks.**
- All 14 scripts load in Lua 5.4.
- A strict-globals run of 169 tests (the hub, runtime, 8.4 and 8.5 suites) found no stray global in the scripts (`RANDO_STRICT_GLOBALS=file`).
- 8.1's test catches a local used before its definition.

## 2. Your first full playthrough with 8.5 (round 21)

Use preset **`hub`** (the default) on a **spare save slot**, with your saves backed up. Leave
`test_travel = false` (the kit's setting). Start the companion, then the game, **New Game**.

Watch for these, and note anything else that looks wrong:

1. **rivet.log at start:**
   - `RANDO-KIT all 14 scripts are 8.5.0`;
   - `RANDO-SEED ARSENAL_RESTORED is installed (the game has ...)` if you have the mod;
   - no `RANDO-ERROR`.
2. **The parade → Zurkie's**, and the two Coordinates.
3. **Ms. Zurkon:** `RANDO-SHOP vendor ... slot objects by pointer` in the log. Do her weapons and
   prices match the spoiler's SHOP list? Buy one: is it the weapon shown, at the price shown?
4. **Each destination (`]`, Ctrl+`]`):**
   - which hero did you arrive as (HUB.md lists each visit's hero)?
   - did the story run ("the story is running")?
   - log: `hero: ... confirmed`, `prime <id>: ...`, then objective lines.

   If you see "the story did not start; reloading it", say whether it moved after the reload.
5. **Viceron:** Rivet, and is the lighting right? Where did you land (`travel:` line)?
6. **Rewards:**
   - "Added to your inventory: ..." for weapons;
   - armor appears in the menu;
   - did Bolts and Raritanium go up by the amount shown?
7. **Save, quit, load** at Zurkie's and on a destination: `;` shows the same `hub n/13 done`.
8. **The finale** when everything else is done.

9. **If anything stalls** (a reward that never comes, a destination that does nothing), the log
   now says so: `taken back`, `withdrawn`, `direct delivery paused`, `given directly (...)`.

Send `rivet.log`, the companion window's text and its `randomizer_saves` folder.
`python tools/summarize_log.py rivet.log` lists the hub, travel and shop lines.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
