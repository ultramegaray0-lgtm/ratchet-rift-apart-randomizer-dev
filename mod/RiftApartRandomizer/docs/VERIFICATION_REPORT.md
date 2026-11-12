# Verification report: Randomizer 8.4 release candidate (2026-11-12)

Each feature is placed in the four categories you asked for. "Game" means one of your rivet.logs
(rounds 13-20) shows it working. **8.4 itself has not run in the game.** It was built on a Linux
machine without the game. A feature is only listed under "actual game execution" when a round
showed it with code that 8.4 kept unchanged.

| | |
|---|---|
| **A** | verified by automated tests (run_tests.py: 318 tests, 0 failures; big_batch: 43,000 seeds valid) |
| **S** | verified by static inspection (code review, byte checks, data checked against your logs) |
| **G** | verified by actual game execution (round number) |
| **N** | not verified: needs the game |

| Feature | A | S | G | N: what is still unknown |
|---|---|---|---|---|
| Seed generation, solver, spoiler, share codes | A | S | G (14-20) | |
| Same seeds as 8.3 (saved progress carries over) | A | S | | |
| New Game → Zurkie's at the wrench, MIS_INTRO written complete | A | | G (17) | |
| Two starting Coordinates, level bits, travel flag | A | | G (17-20) | |
| rando_give.dll v6 (source = shipped binary, byte for byte) | A | S | G (17-20: "0x7") | |
| Hub trips: warp, ship's flight, planet menu send-back | A | | G (17-20) | |
| Destination ladder: available → start, inactive → available → start | A | | G (17: Zurkie's 1 played to the end) | replay step |
| **8.4: hero checked with the game before a start** | A | S (rivet_hook source: "already playing as that hero") | | N: first run |
| **8.4: four registry heroes corrected** | A | S (walkthroughs, rounds 17/20) | | N: each visit as its hero |
| **8.4: story started before the trip** | A | | partly (20: Savali, active before the warp, finished "go to") | N: deliberate prime |
| **8.4: reload of a story stuck at "go to"** | A | | partly (20: Viceron moved on after a reload) | N: the automatic reload |
| **8.4: entry points CHK_ZORDOOM_START, CHK_CORD_A_START** | A | S (listed by your game) | CHK_ARD_START (20) | N: the two new ones |
| Viceron's broken lighting | | | | N: cause unproven (KNOWN_ISSUES.md 1.5) |
| Story on arrival (test travel, menu) | A | | G (20: Ardolis, Savali) | |
| Test travel (off in the kit) | A | | G (19-20) | |
| Checkpoint catalog without frame-budget errors | A | | G (19-20) | |
| Weapon and gadget deliveries | A | | G (14-20) | Glitch is never confirmed |
| **8.4: weapon types learned only from purchases** | A | S | | N |
| Armor: Gold Bolt → armor, pod interception | A | | G (17, 20: "armor give verified", "intercepting 25") | which pods use it |
| Bolts and Raritanium rewards | A | | sent (20) | N: amount actually added |
| Ms. Zurkon slot map and prices | A | S (DDL: list of pointers) | | **N: never applied in game** (rounds 18-20 failed: fixed in 8.4) |
| Shop fallback (non-vendor weapons given once) | A | | G (18, 20) | |
| ARSENAL_RESTORED loaded by rivet_hook | | | G (18-20) | |
| **8.4: ARSENAL_RESTORED detected by the game** | A | | | N: whether the config is loaded at start |
| AR weapons as rewards | A | | | N |
| Save / restore through the companion | A (Lua side) | S (PowerShell by hand) | G (14-20) | pwsh tests skipped |
| **8.4: kit check (RANDO-KIT)** | A | | | N |
| Finale | A | | | N: never reached |

## What was done in this pass

1. **Round 20's log, read in full.** Every finding is in CHANGELOG.md and has a test in
   `tests/test_v84.py`.
2. **Audit.**
   - Rebuilt rando_give.dll from source: byte for byte identical to the shipped DLL (only the link
     time differed; `build.sh` now pins it).
   - Strict-globals run over 250 tests: no stray globals.
   - Every script loads.
   - Generator, travel, hub, test travel, delivery, shop and runtime read in the parts round 20
     touched.
3. **Independent review of the changes** (second pass), which found and fixed:
   - two hero-swap requests could overlap and fight. Now one at a time, and the newer one wins;
   - a trip with no landing point known would switch hero and start the story before failing.
     Now nothing changes first;
   - the delayed "back to Ratchet" could undo the hero of a trip being prepared;
   - a failed way back from a reload was silent;
   - the 8.3 regression baseline was missing, so one was added. It also showed that the spoiler
     examples were stale since 7.0; they are regenerated;
   - a scripts folder mixing kits went unnoticed. The kit check now reports it.
4. **Seeds.** 43,000 generated and verified independently. The 8.3 generator gives the same 175
   seeds in 7 presets.

## The exact blockers left

- **Everything in column N needs one playthrough.** TESTING.md section 2 lists what to look at.
- **PowerShell companion tests**: PowerShell 7 can't be installed on the build machine. The
  companion's changes in 8.4 are version strings only.
