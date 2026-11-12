# Testing report (Randomizer 8.0)

Results come in three separate kinds. A pass in one is never evidence for another.

## 1. Automated tests (this build)

### Seed validation: real generator code, no simulation

`tools/big_batch.py` runs every seed through **all** of:
- the generator's own audit (`G.audit`, 8.0: the hub plan too);
- the **independent** Python item verifier (`tests/test_generator.py` `verify`);
- for level-locked and reordered seeds, the **independent** visit-by-visit replays
  (`verify_campaign`, `verify_fallback`);
- 8.0, for every hub seed, the **independent** hub verifier (`tests/test_hub.py` `verify_hub`),
  written from the documented rules, not from the Lua. It checks:
  - the starting Coordinates (count, different planets, each playable first, never Zurkie's or
    Corson V);
  - every planet's Coordinates opened exactly once;
  - unlocks per destination;
  - the finale last and opening at the right count;
  - by exploring **every** subset of finished destinations a player could reach: something is
    always open until the finale.

| Batch | Seeds | Result |
|---|---|---|
| 8.0 `hub` and `hub_chaos` presets x 3,000 | 6,000 | **6,000 valid** |
| 8.0 hub variants x 500: 3 starting Coordinates, 2 unlocks, `hub_finale = half`, no revisits, restored weapons, 4 starts + 3 unlocks | 3,000 | **3,000 valid** |
| 7.0 presets (balanced, chaos, full, campaign, everything) x 2,000 | 10,000 | **10,000 valid** |
| `standard`, `coordinates` x 1,000; restored weapons, vanilla shop, levels + restored weapons, `start_items` + levels x 1,000 | 6,000 | **6,000 valid** |
| random settings: 2,000 combinations x 4 seeds over all presets (hub included). Every toggle, `hub` on/off, hub ranges partly out of range on purpose | 8,000 | **8,000 valid**, 0 refused |
| experimental mission orders: 4 presets x 2,000, plus x 500 with locked levels | 10,000 | **10,000 valid** |
| **Total** | **43,000** | **43,000 valid, 0 invalid** (`BATCH_8.0.txt`) |

### Do the checkers catch broken seeds? (mutation tests)

7.0's six (`VerifierMutationTests`), all caught:
- an item duplicated;
- Coordinates on their own planet;
- the story's planet closed;
- currency out of range;
- a wrong price;
- a Coordinates item removed.

8.0 adds three (`HubGeneratorTests.test_audit_catches_a_broken_plan`), all caught:
- the same planet twice at the start;
- Viceron (needs two story abilities) as a starting destination;
- a planet dropped from the unlock queue.

### Unit and simulated tests (`python run_tests.py`)

**231 tests: 222 passed, 0 failed, 9 skipped.** The skipped ones are the companion tests, which need
PowerShell 7; it couldn't be run on the build machine (`TEST_RESULTS.txt`).

| Suite | Covers |
|---|---|
| `test_hub.py` (32, new) | **generator (9):** 300 hub seeds through the independent verifier; the start pair varies; deterministic; settings variants; `hub_chaos`; level locks switched off in a hub seed; hub keys never change a 7.0 seed; mutations; spoiler; share code. **Simulated game (23):** see the next table |
| `test_generator.py` (32) | 7.0's generator suite; share codes are `RA8` now |
| `test_campaign.py` (29) | campaign orders, the solver, the 3.x director; state names now from the DDL (`inactive`, ...) |
| `test_levels.py` (21) | 7.0 levels, prices, start currency, restored weapons auto, 36 level-locked New Game to finale runs |
| `test_runtime.py` (86) | delivery, Gold Bolts, New Game, saving, armor, shop, currency, your round 13-16 logs replayed; the script folder now has `15_rando_hub.lua` |
| `test_registry.py` (7) | the weapon registry against your dag |
| `test_regression_v6.py` (4), `test_regression_v5.py` (4) | 6.0's and 5.0's generators from git beside 8.0 (same locations and rules). The helper keeps every v5 byte array, RVA, mailbox offset, kind and result code |
| `test_native.py` (3) | `rando_give.dll` v6 core (C), including the new state write / probe, level and travel kinds and their refusals. Every expected byte array equals **both** code dumps; the v6 handlers name exactly the globals and functions used; the shipped DLL = a rebuild |
| `test_tools.py` (4) | spoiler generator, share codes, batch tool, the log summarizer |
| `test_companion.py` (9) | **skipped**: needs PowerShell 7. The companion's 8.0 change is its version text only |

The 23 simulated-game hub tests:

| Test | What it shows (in the SIMULATED game) |
|---|---|
| in-game seed = offline seed | the seed generated in slices in the game (the hub check yields) is the offline one: fingerprint, hub plan, locations |
| New Game goes to Zurkie's | parade → wrench → warp to `CHK_ZURK_00_DEFAULT` → Zurkon. The 2 Coordinates open, the prologue's reward is paid, MIS_INTRO is written 2 → 4, the travel byte is set to 1, levels 1-10 are set, the research lines appear, the start inventory arrives |
| triggers | first control (`hub_trigger = "control"`); the wrench never coming (timeout) |
| a save load | never starts the hub; Ctrl+F6 starts it by hand on any save |
| story forced, then finished | fly with a ship near; hero swap for Rivet; inactive → written available → started. Finishing the visit's missions pays the destination, opens the next queued Coordinates, warps back after the delay and announces "New Coordinates" |
| available mission | started without any write |
| no force / no v6 | replay, then explore; with v5 no intro write and no level bits, the hub still runs |
| replay that works | the story runs through replay |
| explore and by hand | unknown missions → explore → Ctrl+F5 twice finishes and pays, recorded |
| the ship's menu | a planet without Coordinates sends you back (once); an open one starts its destination |
| the parade on a load | back to Zurkie's |
| a late restore | a restore that comes after the load: on Corson V back to Zurkie's; at Zurkie's the travel byte and level bits are put back |
| saved progress | finished destinations and open Coordinates survive export / restore; a load at Zurkie's moves nothing |
| the warp fails everywhere | "could not reach Zurkie's", Coordinates open anyway |
| `hub_runtime = false` | nothing happens |
| startup guard | the game's own travel right after the start is undone |
| keys and status | F9 `hub 0/13 done`, F6 listing, F5 at Zurkie's |
| **campaigns** | 4 seeds to the finale (first-open and last-open choices), and 1 with three visits whose missions don't exist (finished by hand). Every destination done, every destination reward paid, campaign complete |
| **your real logs** | rounds 14, 15 and 16's New Game event streams start the hub exactly at `OBJ_INTRO_PARADE_PICKUP_WRENCH` = 2, with no error; round 13 (save loads) never starts it |
| log summary | `summarize_log.py` lists the hub milestones and research lines |

The simulator (`tests/sim/rivet_sim.lua`) lists at its top what it models and on what evidence.
For 8.0, these are **simulated assumptions, not observations**:
- warps and flights land on the checkpoint's planet;
- a state write changes the state and nothing else;
- start makes a mission active;
- the level mask and travel byte are plain memory.

These tests prove the scripts' decisions, not the game's behaviour.

## 2. Verified in the game

**Nothing of 8.0 has run in your game.** Neither has anything of 5.0-7.0. What 8.0 builds on, from
your rivet.logs, is in VERIFIED_IN_GAME.md:
- the New Game objective sequence;
- `PlanetMenuAcceptEvent` / `PlanetChangedEvent` with `CHK_ZURK_00_DEFAULT`;
- the mission and Gold Bolt events;
- the helper's item gives.

## 3. Not yet verified in the game

Each item comes with its `RANDO-HUB` log line:
- the warp out of the parade (`warp to Zurkie's at ...`, then `Coordinates opened`);
- the MIS_INTRO write (`MIS_INTRO set to Complete Finished: ...`);
- the travel byte and level bits (`planetary travel: ...`, `levels at the hub: ...`, `level N unlocked`);
- the ship's flight from Zurkie's (`travel: fly to ...`) and warps to other planets;
- the ladder on real missions (`destination X mission M is ...`, `force available ...`,
  `start ...`, `replay ...`);
- hero swaps (`hero: ratchet -> rivet ...`);
- completion on real missions (`HUB: X finished (story: ...)`);
- the return (`warp to Zurkie's ... destination finished`);
- the keeper;
- the ship's menu at Zurkie's;
- 7.0's open items (`## Optional` below).

## Your first session with 8.0 (the hub checklist)

Use preset **`hub`** (the default) on a **spare save slot**, with your saves backed up. Start the
companion, then the game, **New Game**. At the end send `rivet.log`, the companion window's text,
the spoiler (`companion\randomizer_saves\spoilers`) and what you saw at each numbered step.

1. **The parade:** after "Randomizer: new game ..." and the start items, pick up the wrench.
   Expected: "to Zurkie's Battleplex", then a fade, then Zurkie's and "Zurkie's Battleplex:
   Coordinates for X and Y". Where did you end up? Could you move?
2. **Look around Zurkie's:**
   - is Ratchet's ship there? Its planet menu: which planets does it list?
   - Zurkie's itself (the Battleplex, Ms. Zurkon's shop): what works?
3. **F6, then Ctrl+F6** to the first destination. Did the ship fly, or did it fade (warp)? Where
   did you land?
4. **The destination's story:** what does the HUD say ("the story is running" or "explore")? If
   it runs: objectives, cutscenes, enemies? Play it to the end if you can. If it says explore:
   look around, then Ctrl+F5 twice.
5. **The return:** "Destination complete ... Back to Zurkie's in 12 s", then Zurkie's and "New
   Coordinates".
6. **The ship's menu:** choose a planet the spoiler's hub section says is not open yet. Expected:
   "no Coordinates for X yet - back to Zurkie's".
7. **Save, quit to the menu, load:** where are you? Does F9 show the same `hub n/13 done`?
8. **A second destination,** ideally one of Rivet's (the spoiler lists the hero).
9. If the parade comes back at any point, or anything is stuck: F5 twice, Ctrl+F6, or
   `hub_runtime = false` (HUB.md, "If it goes wrong").

`python tools/summarize_log.py rivet.log` prints every hub milestone and research line.

## Optional: the 7.0 checks (round 17 checklist, a 7.0 preset)

Use preset **`campaign`** (`everything` also works). Start the companion, then the game, **New
Game**. At the end send `rivet.log` (next to RiftApart.exe) and the companion window's text.

1. **Companion window:** `ARSENAL_RESTORED is installed ...` (or not installed: say which is
   true), `spoiler log written`.
2. **Start:** "Randomizer start: Hoverboots, Map-O-Matic, ..." and no `RANDO-ERROR` in the log.
3. **Story travel:** play through the parade to Nefarious City and on to Sargasso. Nothing may send
   you back (`RANDO-TRAVEL arrived on ... without the planet menu`).
4. **Locked planet:** at the first planet-menu choice, pick a planet the spoiler's LEVELS section
   says is locked. Expected: "no Coordinates for X yet - back to Y", then a warp to Y about
   3 seconds after landing. Tell me where you ended up and whether anything looked wrong.
5. **Open planet:** fly to Zurkie's (open with `campaign`). Nothing happens.
   `RANDO-TRAVEL arrived on scarstu (open) at CHK_ZURK_00_DEFAULT`.
6. **Coordinates:** when "you can fly to X now" appears, fly there. No warp.
7. **Shop:** at Ms. Zurkon, do the weapons and prices match the spoiler's SHOP list?
   (`RANDO-SHOP ... Price at ...` or `prices left as they are`.) Buy one: is it the shown weapon,
   at the shown price?
8. **Currency:** when a reward says "N Bolts" / "N Raritanium", did your count go up by N? Did the
   start currency (`everything`) arrive?
9. Optional: an armor pod; quit and reload (F9 unchanged).

`python tools/summarize_log.py rivet.log` lists the travel, price and ARSENAL_RESTORED lines.

## Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`, and `python tools/big_batch.py` for the
43,000-seed release batch (about 6 minutes). Optional (each skipped when missing): PowerShell 7
for the companion tests, a C compiler for the DLL core test, clang + lld-link + llvm-dlltool for
the DLL rebuild check, git for the 5.0 and 6.0 regression tests.
