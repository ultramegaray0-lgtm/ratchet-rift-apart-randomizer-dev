# Verification report: Randomizer 9.0 (2026-11-12)

Each feature is placed in four categories. "Game" means one of your rivet.logs (rounds 13-22) shows
it working. **9.0 has not run in the game.** It was built on a Linux machine without the game. A
feature is only listed under "actual game execution" when a round showed it with code 9.0 kept.

| | |
|---|---|
| **A** | verified by automated tests (run_tests.py: 293 tests, 0 failures, 17 skipped; big_batch: 41,000 seeds valid) |
| **S** | verified by static inspection (code review, byte checks, data checked against your logs) |
| **G** | verified by actual game execution (round number) |
| **N** | not verified: needs the game |

| Feature | A | S | G | N: what is still unknown |
|---|---|---|---|---|
| **9.0: no hub: the kit has 13 scripts, no RANDO_HUB, no hub options** | A | S | | |
| **9.0: New Game plays the prologue, Nefarious City, Sargasso; the randomizer warps, flies, writes and swaps nothing** | A (simulated: the parade, the game's own travel) | S (the only warps, flights and mission writes left: test travel, the test-mode lab, the director once mission control is verified, and the locked-level send-back after a planet-menu landing) | the game's own travel itself: G (16: parade → Nefarious City → Sargasso without a planet menu) | N: a full 9.0 New Game |
| **9.0: every mission order starts prologue > Nefarious City > Sargasso** | A (41,000 seeds, independent check) | S | | |
| **9.0: retired presets/options named in rivet.log; your 8.5.2 settings file still loads** | A | | | |
| **9.0: a leftover 15_rando_hub.lua is reported and inert with a 9.0 seed** | A (the real 8.5 file loaded) | S (every action in it waits for a hub plan) | | |
| Your 8.5.1 defaults and 8.5.2 data (Punk/Reaver owned) | A | S (build_data.py reproduces your 01 byte for byte) | Punk/Reaver refused: G (22) | |
| Seed generation, solver, spoiler, share codes | A | S | G (14-22) | |
| rando_give.dll v6 (source = shipped binary, byte for byte) | A | S | G (17-22: "0x7") | |
| Locked levels: planet menu send-back, story planets open | A | | send-back: G (17) | |
| Test travel (off in the kit) | A | | G (19-20) | |
| Checkpoint catalog without frame-budget errors | A | | G (19-20) | |
| Weapon and gadget deliveries | A | | G (14-22) | Glitch is never confirmed |
| Weapon types learned only from purchases | A | S | | N |
| Armor: Gold Bolt → armor, pod interception | A | | G (17, 20, 22) | which pods use it |
| Bolts and Raritanium rewards | A | | sent (20, 22) | N: amount actually added |
| Ms. Zurkon slot map and prices | A | S (DDL: list of pointers) | | **N: never applied in game** (22: frame budget, weapons given directly) |
| Shop fallback (non-vendor weapons given once) | A | | G (18, 20, 22) | |
| ARSENAL_RESTORED loaded by rivet_hook, detected in game | A | | G (18-22) | |
| Save / restore through the companion | A (Lua side) | S (PowerShell by hand) | G (14-22) | pwsh tests skipped |
| Kit check (RANDO-KIT) | A | | G (21-22) | |
| 8.5: mailbox take-back, loads waited through, late restore merge, shop routes | A | S | | N: needs a stalled helper or late companion |
| Finale | A | | | N: never reached |

## What was done for 9.0

1. **The hub removed**: `15_rando_hub.lua` deleted; its presets, seed settings and in-game options
   retired with a rivet.log line each; every `RANDO_HUB` call taken out of 10, 11, 14 and 16; the
   kit check reports a leftover hub script.
2. **The story's start fixed**: 03's `C.STORY_START` (the visits with `arrival = "story"`) begins every
   campaign order; `random_start` retired; the audit checks it.
3. **Your edits kept**: 01-06 and 09 from your upload are the baseline commit. `build_data.py` now
   reproduces your 01; before, re-running it reverted Punk/Reaver.
4. **Tests**: `test_v90.py` (20 tests, above); the older suites pin the settings they were written for
   instead of relying on defaults you changed; the hub's tests are removed.
5. **Seeds**: 41,000 seeds (BATCH_9.0.txt), including 6,000 from your kit 04 file with and without
   ARSENAL_RESTORED.

## Earlier passes (8.5)


1. **Audit of the 17 areas you listed**, by reading the 8.4 code with the question "what happens
   when this step fails, comes late, or happens twice": campaign generation, progression, hero
   switching, story start/recovery, hub travel, mission sync, weapons/inventory, shop, Arsenal
   Restored, rewards, save/persistence, finale, the DLL interface, Lua reliability, the companion,
   error handling, performance. Each defect found is in CHANGELOG.md (8.5). Each has a test in
   `tests/test_v85.py` that **fails on the 8.4 scripts** (17 of 20 tests; the other 3 are controls)
   and passes on 8.5.
2. **Areas read with nothing to fix:** generator and solver (unchanged, still 43,000 seeds valid);
   finale detection (the only Megalopolis "FINAL" mission is `MIS_MEGA_FINALE`); armor ring and
   table (a replayed event can at most give a piece the game would have given); travel lock warp;
   the companion's atomic save and version check; per-frame budgets (no new per-frame work; the
   history cap removes the only unbounded growth found).
3. **rando_give.dll is unchanged.** No reason to change it was found. Its source rebuilds to the
   shipped DLL byte for byte (test_native), the same DLL as 8.3/8.4.
4. **Self-review of every change** (second pass over the diff), which found and fixed:
   - a withdrawal could race a late answer (DONE written between the read and the write). The answer
     now stands and REQ is put back, for items, currency and mission calls alike;
   - after an aux withdrawal that turned out to be answered, 8.4's code would still switch direct
     delivery off. Now it doesn't;
   - a collectible-count merge was written and then removed again: collectibles are retired since
     6.0 and never placed, so it would have been dead code.
5. **Strict-globals run** over 169 tests: only the intended optional globals.
6. **Seeds.** 43,000 generated and verified independently (BATCH_8.5.txt). The 8.4 generator gives
   identical seeds for 175 seeds in 7 presets; the 8.3 regression still passes.

## The exact blockers left

- **Everything in column N needs one playthrough.** TESTING.md section 2 lists what to look at.
- **The failure paths 8.5 fixes** (a stalled helper, a late companion, a vendor not found) only
  show up when something goes wrong. A clean playthrough will not exercise them. The simulator does.
- **PowerShell companion tests**: PowerShell 7 can't run on the build machine (downloading and
  running it was not allowed). The companion's one logic change in 8.5 is checked by reading only.
