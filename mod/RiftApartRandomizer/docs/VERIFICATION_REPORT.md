# Verification report: Randomizer 8.5 (2026-11-12)

Each feature is placed in the four categories you asked for. "Game" means one of your rivet.logs
(rounds 13-20) shows it working. **Neither 8.5 nor 8.4 has run in the game** (there is no round 21
log). Both were built on a Linux machine without the game. A feature is only listed under "actual
game execution" when a round showed it with code that 8.5 kept unchanged.

| | |
|---|---|
| **A** | verified by automated tests (run_tests.py: 340 tests, 0 failures; big_batch: 43,000 seeds valid) |
| **S** | verified by static inspection (code review, byte checks, data checked against your logs) |
| **G** | verified by actual game execution (round number) |
| **N** | not verified: needs the game |

| Feature | A | S | G | N: what is still unknown |
|---|---|---|---|---|
| Seed generation, solver, spoiler, share codes | A | S | G (14-20) | |
| Same seeds as 8.3 (saved progress carries over) | A | S | | |
| **8.5: identical seeds to 8.4** (every field, 175 seeds, 7 presets) | A | S (generation scripts differ only in the version tag) | | |
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
| **8.5: late restore keeps this session's currency, confirmed items, armor/shop/hub records** | A | S | | N: a late companion in game |
| **8.5: companion keeps a refused save aside** | | S (by hand; pwsh can't run here) | | N |
| **8.4: kit check (RANDO-KIT)** (8.5: all 14 scripts say 8.5.0) | A | | | N |
| **8.5: mission calls wait through loads; unanswered requests are taken back** | A (simulated helper) | S (rando_give.dll source: one request per pump, DONE written last) | | N: needs a helper that stalls, which no round has shown |
| **8.5: New Game clears the hub's and the delivery's session record** | A | S | | N |
| **8.5: shop-only weapons given without a working helper** | A | S | | N |
| **8.5: planet-menu landing saved at once (levels seeds)** | A | | | N |
| Finale | A | | | N: never reached |

## What was done in this pass

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
