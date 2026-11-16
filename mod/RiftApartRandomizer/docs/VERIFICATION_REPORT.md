# Verification report: Randomizer 10.0 (2026-11-13)

Each feature is placed in four categories. "Game" means one of your rivet.logs (rounds 13-23) shows it
working. **10.0 has not run in the game.** It was built on a Linux machine without the game. Nothing is
listed under G unless a round showed exactly that code path working.

| | |
|---|---|
| **A** | verified by automated tests (run_tests.py: 332 tests, 0 failures, 17 skipped; big_batch: 56,600 seeds valid) |
| **S** | verified by static inspection (code review, data checked against your logs) |
| **G** | verified by actual game execution (round number) |
| **N** | not verified: needs the game |

| Feature (10.0) | A | S | G | N: what is still unknown |
|---|---|---|---|---|
| Hub seeds: three start choices, Coordinates-driven order, every order finishable | A (19,600 hub seeds, independent sphere walk) | S | | |
| New Game → Zurkie's at the parade's wrench | A (simulated; round 23's real events start it at the wrench; round 13's save loads never do) | | the warp: G (17, kit 8.0) | N: with the prologue left active |
| Prologue resumes at the parade's checkpoint | A (simulated) | S (a warp to the last checkpoint with the mission unchanged = a save load) | | **N** |
| Battle Arena: `MIS_ZURK_01_VISIT_01` started at Zurkie's | A | | the same calls: G (17, played to completion) | N: with the warp to `CHK_ZURK_00_DEFAULT` after the start |
| Nefarious City at `CHK_NEFCITY_START` | A (simulated rule) | S (rounds 16/23: the game's own load of the story is hash 2052464476 = that name) | | **N: the key test of round 24** |
| Mission ladder (write "available", then start) | A | S | G (17: NEFCITY_01, ZURK_01, ZURK_02B) | |
| Hero set before a story | A | S | | N (round 20 showed every swap failing under 8.3; the 8.4 check never ran in a log) |
| A story stuck at "go to" reloaded on the same planet | A (simulated) | | | **N** |
| The game's follow-on travel undone (`[ORDER KEPT]`) | A (simulated chain from round 23, including its order: complete on Ardolis, then the rift) | S (round 23 lines 695-729) | warps: G (17, 19) | **N** |
| Planet menu: locked → Zurkie's; open → its destination starts | A | | send-back: G (17) | N: the start on an open planet |
| Travel flag + level bits on every arrival | A | | G (17) | |
| Checkpoint names from hashes (`RANDO-CHECKPOINT`) | A (29 names match real logs) | S | | |
| Learned starts (kept over a New Game) | A | | | N |
| Rewards spread; early weapons and Coordinates | A (statistics over 200+ seeds; verifier) | | | |
| Gold Bolts stay real (the game counts them; the randomizer adds a reward) | A | S (no Gold Bolt event is changed or faked) | the game's count: G (16-23) | |
| One route per weapon; no ARSENAL_RESTORED weapon sold | A (56,600 seeds) | | | |
| Closed vendor slots (Burst Pistol) and other vendors' duplicate slots closed | A (simulated memory) | | | **N: never applied in game; whether the screen accepts it** |
| Shop search within the frame budget | A (parse 512 bytes well under 2 ms here) | S | | **N: rounds 17-23 all overran** |
| 9.0 story start with `hub = false` | A | | G (23) | |
| rando_give.dll v6 (unchanged) | A | S | G (17-23) | |
| Spybots (10) and Lorbs (12) as reward locations (dev 10.1) | A (test_v101, 56,600 seeds) | | | **N: their pickup event has never been seen, so they do not pay in game yet** |
| Burst Pistol, Shatterbomb, RYNO 8 as rewards; Shatterbomb/RYNO slots closed (dev 10.1) | A (test_v101, simulated vendor) | | | **N: never run in game** |
| Real Gold Bolts as rewards or shop items | | | | **not done**: no verified way to grant one |

## What was done for 10.0

1. **Round 23 read in full.** It showed why planet shuffle never ran (the director waits for lab lines
   that were never written) and that the shop overran its budget again. Reading the checkpoint
   hashes against every name your game listed also showed that the hash is the engine's CRC-32, and
   that Nefarious City's story loads at `CHK_NEFCITY_START`.
2. **Generator**: hub mode, fixpoint reach, spread fill, shop split, audit rules (destinations
   reachable, start planets only, one route per weapon, no ARSENAL_RESTORED weapon sold, closed
   slots, early weapons), and a spoiler with the route.
3. **Runtime**: `15_rando_hub.lua` (new), hooks in 10 and 14, closed slots and parsing in 12.
4. **Tests**: `test_v100.py` (39 tests). The older suites run their original rules with
   `PRE10_SETTINGS`. The simulator gained checkpoint events, the start-checkpoint rule and the
   game's own next-mission chain, each marked SIMULATED with its log evidence.
5. **Seeds**: 56,600 (BATCH_10.0.txt): 19,600 hub seeds (your 04 file, every preset, with and
   without ARSENAL_RESTORED, random settings) plus 37,000 pre-10.0-mode seeds.

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
5. **Seeds**: 41,000 seeds (BATCH_9.0.txt, replaced by BATCH_10.0.txt), including 6,000 from your kit 04 file with and without
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

## Dev 10.15 (kit 10.0.11): Omega weapons

Nothing of dev 10.15 has run in the game (A = automated, S = static inspection, G = game: none).

| Feature | | Evidence |
|---|---|---|
| An Omega is the flag `WeaponItemPrius.Omega` of the owned weapon, not an item id | S | the game's type data (rivet DDL), your dag (no Omega config) - OMEGA.md section 1 |
| omega_weapons off: every seed is the 10.13 seed | A | test_v1015 GeneratorTests (git commit 376a887) |
| omega_weapons on: each Omega once, never Gold Bolt / shop / random start, rest of the seed unchanged | A | GeneratorTests (90 seeds, audit) |
| Tier logic: prerequisite, no downgrade, no duplicate send, repeats, save/load, merge, New Game | A | OwnershipTests, PersistenceTests (simulator) |
| Setting the game's flag (record search, learning from two Omega purchases, guarded write, keeping it) | A | LearningTests, PersistenceTests - **simulated layout only; N: everything of it in the game** |
| Never in a player package | A | test_v055 PackageTests, test_v1015 ReleaseTests |

## Dev 10.13 (kit 10.0.9): Chaos Randomizer

Nothing of dev 10.13 has run in the game (A = automated simulator tests, G = game: none).

| Feature | | Evidence |
|---|---|---|
| chaos.lua loads, OFF by default, BACKSPACE toggles, saved, kept over New Game | A | tests/test_v1013.py LoadAndToggleTests |
| Any template -> any template (both tiers, story bosses, unclassified), few repeats, seeded | A | AnythingBecomesAnythingTests |
| Cross-planet pool | A | CrossPlanetTests (simulated per-planet node lists); in the game: unknown whether such templates spawn |
| Priority over Enemy/Boss; their picks back when OFF | A | PriorityTests |
| No guards; never forces progression | A | NoGuardsTests |
| Never in a player package | A | test_v055 PackageTests (builder) |

## Dev 10.12 (kit 10.0.8): Enemy Randomizer and Boss Randomizer

Nothing of dev 10.12 has run in the game. A = automated (simulator), S = static inspection of the
game's type data (neptuwunium/rivet DDL dump), G = game execution (none).

| Feature | | Evidence |
|---|---|---|
| Both OFF by default; off = no spawner read or written | A | tests/test_v1012.py OffByDefaultTests |
| In-game keys `-` / `=`, saved, kept over New Game, independent | A | IndependenceTests, SaveTests |
| Templates found by the DDL layout's signature | A, S | SpawnerScriptActionPrius field offsets (rcra_ddl.json); LayoutTests. Real memory layout: not seen |
| Only template ids change; the node completes the encounter itself, once, after the last enemy | A, S | the DDL's spawner fields (NumSpawns, OnNumDeadTrigger, spawned actor group); simulated node model; EnemyTests, BossTests |
| Family classification from bot components | A, S | GameBot* / BossBot* component classes in the DDL; whether rivet.component answers for spawned actors: not seen |
| Boss tier permuted; story bosses never touched | A, S | BossTests; BossBot* components and boss-specific script actions in the DDL |
| Safety nets (spawn timeout, stuck, retries, wrong family, story boss areas) | A | SafetyNetTests |
| Frame budget (sliced census, 3 ms write budget) | A | BudgetTests; real timing not measured |
| Events SpawnerSpawnEvent / SpawnerStartedEvent / BotDeathCompleteEvent / HealthBarShowEvent fields | S | DDL event types; never seen in a rivet.log yet |

## Dev 10.11 (kit 10.0.7, generator 10.11.0): new planets start at their intro

Nothing of dev 10.11 has run in the game.

| Feature | | Evidence |
|---|---|---|
| Coordinates never on a revisit / the finale; a planet's Coordinates only where its first visit is playable at once | A | tests/test_v1011.py (independent Python rule check), G.audit, big_batch (check_seed on every hub seed with the rule on) |
| Open planets' next visits made active between stories | A, S | simulator tests; the game does the same at a visit's end (round 17 lines 1019-1028, round 16 line 384) |
| A primed visit's planet-menu landing is left to the game | A | simulator only: whether the game then lands at the intro is untested |
| A landing started on the planet loads the visit's intro | A, S | intros from the game's own menu landings (rounds 14, 16, 17, 23), a warp that ran (round 20, Ardolis), catalog names (rounds 24-26) |
| Sargasso's arrival scene (hash 2498464355) | S | rounds 16 and 23: first checkpoint after CHK_TRANSITION_TO_SARG with MIS_SARG_01_FIRST_VISIT active; name unknown |
| A blocked first visit sends you back, never a revisit; ] lists first visits first | A | simulator tests |
| The game's own trip to an open first visit is played | A | simulator (round 16's chain: MIS_SARG_01_FIRST_VISIT started, then Sargasso) |
