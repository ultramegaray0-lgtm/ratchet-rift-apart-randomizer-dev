# Randomizer 8.0: completion report

8.0 changes how a randomized campaign begins and runs. A new game is taken to **Zurkie's
Battleplex**, which becomes the hub. Two random Coordinates are open at once, every destination
you finish opens the next ones, and you return to Zurkie's after each. All 7.0 systems are kept.
8.0 is built on 7.0 (git branch `v8` on top of `v7`).

**Nothing of 8.0 (or of 5.0-7.0) has run in your game yet.** This page separates what was checked
automatically from what only your game can show.

## What 8.0 adds

| Area | 8.0 | Docs |
|---|---|---|
| **New Game at Zurkie's** | Once Ratchet has the wrench in the parade, the runtime warps him to `CHK_ZURK_00_DEFAULT` (the planet menu's Zurkie's destination, from your logs). Fallbacks: other ZURK checkpoints, then "open the Coordinates where you are". The skipped prologue is written complete in the save (experimental) and its reward is paid. A parade on a later load is undone. | HUB.md, RESEARCH_8.0.md 1 |
| **Two starting Coordinates** | From the seed, on two different planets whose first visit needs nothing but the starting kit. Saved with the progress. | HUB.md |
| **Destinations** | All 13 registry visits after the parade (12 + the finale), Zurkie's own two included. F6 / Ctrl+F6, the ship's flight or a warp. The planet menu works too; a planet without Coordinates sends you back. | HUB.md |
| **Planet / mission access** | The mission ladder: start an available mission (the game's own call) → write "Available" into an inactive mission's saved state, then start it (new, `rando_give.dll` v6) → replay → explore (always works, Ctrl+F5 twice finishes). Rivet's visits swap the hero. | RESEARCH_8.0.md 3 |
| **Hub loop** | Finish → rewards → next Coordinates → back to Zurkie's after 12 s → choose again → finale | HUB.md |
| **Progression table** | `seed.hub`: start pair, unlock queue, destinations with the game's own dependencies, finale. Checked over **every** order a player could choose (up to 4,096 situations per seed); no dead end before the finale | RESEARCH_8.0.md 4 |
| **Ship's menu** | At Zurkie's: planetary travel on (the `SetPlanetaryTravelAction` byte); every level bit set (`UnlockLevelAction`'s mask, in case the menu reads it). Both logged before and after. | RESEARCH_8.0.md 2 |
| **rando_give.dll v6** | New request kinds: mission state record (write / probe), level mask (set / read), travel byte. Each is enabled only if its code matches your exe byte for byte (expected bytes from both your code dumps). All v5 behaviour is unchanged. | rando_give_source/ |
| **Research** | Once per session at Zurkie's, read-only: every destination mission's state, MIS_INTRO's record, the level masks on every planet, the LANDING / ZURK / MEGA checkpoints, the loaded Mission configs | HUB.md "What to send" |
| **Presets** | `hub` (the new default) and `hub_chaos`; settings `hub_start_coordinates`, `hub_unlocks`, `hub_finale`, `hub_revisits` + 12 in-game options | CONFIGURATION.md, HUB.md |
| **Spoiler** | ZURKIE'S BATTLEPLEX HUB section: start pair, unlock order, destinations and their rules, one way through | examples/spoiler_example-hub.txt |

7.0's systems are kept in every seed, hub or not:
- vanilla weapons and the unified registry;
- ARSENAL_RESTORED auto-detection;
- armor;
- gadgets;
- Bolts, Raritanium and their budgets;
- Ms. Zurkon's shop with prices;
- spoiler logs, seed generation and share codes (now `RA8`);
- the start, with Hoverboots and the Map-O-Matic always in it.

A seed with `hub = false` (any 7.0 preset) plays exactly like 7.0, with 8.0's generator version.

## Status: four categories

### Implemented and verified automatically

- **Hub generation** on 9,000 hub seeds plus hub settings within 8,000 random-setting seeds. Each
  passes the generator's audit, the 7.0 independent item verifier, and an **independent** Python
  hub verifier (every order, start pair, Coordinates coverage). It also runs inside the 43,000-seed
  release batch: 0 invalid.
- **Mutation tests:** a duplicated starting planet, Viceron as a start, and a dropped queue entry
  are all caught.
- **Determinism** and share-code round trips. Hub settings never change a non-hub seed.
- **rando_give.dll v6:**
  - its C core is unit-tested (state write and probe, refusals, levels, travel, the v6
    verification);
  - every new expected byte array equals your round 14 **and** round 15 code dumps;
  - the handlers' globals and calls are the ones the helper uses;
  - the shipped DLL is rebuilt from the shipped source (only the PE timestamp differs);
  - every v5 array, RVA, mailbox offset, kind and result is unchanged (regression test against
    the 7.0 and 6.0 sources from git).
- **The hub runtime against the simulated game** (23 of the 32 tests in `test_hub.py`; the other 9 are the generator tests above):
  - the in-game seed (generated in slices) equals the offline one;
  - New Game → Zurkie's: by the wrench, by first control, by timeout; never on a save load;
    Ctrl+F6 by hand;
  - the two Coordinates;
  - the prologue's reward and state write;
  - travel byte, level bits, research lines;
  - fly with a ship, warp without;
  - the ladder: available → start; inactive → write → start; no v6 or `hub_force_missions = false`
    → replay → explore; a working replay;
  - finishing by story and by hand, rewards, new Coordinates, the automatic return;
  - the ship's menu to a locked planet (sent back) and to an open one;
  - the parade on a load; a restore that comes after the load;
  - save and restore;
  - the warp to Zurkie's failing everywhere;
  - `hub_runtime = false`; the startup guard; keys and status;
  - **five whole campaigns to the finale** (first-open and last-open choices, and one with three
    visits whose missions don't exist).
- **Your real event streams:** rounds 14, 15 and 16's New Games, replayed into hub seeds, start the
  hub exactly at `OBJ_INTRO_PARADE_PICKUP_WRENCH` = 2. Round 13 (save loads only) never starts it.
- **All 7.0 tests** still pass. Full suite: see TESTING.md.

### Implemented but not verified in the game

Everything the runtime does in the game:
- the warp out of the parade;
- the MIS_INTRO state write;
- the travel byte and level bits;
- the ship's flight from Zurkie's;
- warps to each planet's landing checkpoint;
- the mission ladder's start, state write and replay on real missions;
- hero swaps;
- completion detection on real missions;
- the return warp;
- the keeper;
- research reads;
- the companion saving the hub state (same mechanism as 7.0, never run with hub data).

The simulator's assumptions for these are listed at the top of `tests/sim/rivet_sim.lua`.

### Investigated but unsuccessful

- **Starting a new game directly at Zurkie's as data** (`NewGameLoadInfo` in the mission graph
  asset): needs the asset and a DDL writer, not available here.
- **Making a mission available the game's way:** `MakeMissionAvailableAction` is a no-op in your
  game's mission system (round 15).
- **Direct mission loading** through `ReloadToObjectiveAction`: too many calls outside the dumps to
  replay safely; can't be borrowed (string vars).
- **Loading other planets' missions inside the Battleplex:** a planet's missions live in that
  planet's story overlays, which only its mission state loads, at its own place in the level.
  `rivet.overlay` refuses story overlays.
- **Vetoing travel:** impossible (7.0 finding), so travel is undone after landing instead.

### Still technically unknown

These need your first session; each one's `RANDO-HUB` log line is listed in TESTING.md:
- whether the warp from the parade lands;
- whether a written state makes the mission system act (load the story overlays, let it start);
- whether replay opens a mission;
- what the level bits mean;
- whether the ship is at Zurkie's after a warp;
- which landing checkpoints the unknown planets have;
- how story missions started out of order behave.

## Files

| Kind | Files |
|---|---|
| New | `scripts/15_rando_hub.lua`; docs `HUB.md`, `RESEARCH_8.0.md`, `KNOWN_ISSUES.md`; `tests/test_hub.py` |
| Changed | `02` (hub settings, presets, plan, audit, spoiler; generator 8.0.0); `03` (hub planner and checker); `04` (default preset `hub`, hub options); `10` (hub hooks, options, the current-planet fix); `11` (v6 request kinds, the DDL state names); `rando_give.dll` + source (v6); the simulator; tools `rando.py`, `big_batch.py`, `summarize_log.py`; the companion's version text |
| Unchanged | `01` (data 5.0.0), `05`, `06`, `09`, `12`, `13`, `14` |

## Engine limits that remain

See KNOWN_ISSUES.md. Most important: the game decides what a started mission does. The hub can
start missions out of order only as far as the mission system accepts it. Explore mode and
finishing by hand keep every seed finishable whatever happens.
