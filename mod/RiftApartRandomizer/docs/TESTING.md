# Testing (Randomizer 10.0, Public Release v0.52; dev 10.15)

Results come in four kinds, and a pass in one is never evidence for another. VERIFICATION_REPORT.md
sorts every feature into them. This page covers how the tests run and what to check in your
first full playthrough.

## 1. Automated tests (this build)

`python run_tests.py`: **536 tests, 0 failures, 0 errors, 21 skipped** (TEST_RESULTS.txt; dev 10.11 adds tests/test_v1011.py, 20;
dev 10.12 adds tests/test_v1012.py, 32 - see TEST_REPORT_10.12.md; dev 10.13 adds tests/test_v1013.py, 23 - TEST_REPORT_10.13.md;
dev 10.15 adds tests/test_v1015.py, 32 - TEST_REPORT_10.15.md).
All of these are SIMULATOR tests: none of them is a result from the real game.
The skipped tests:
- 9 need PowerShell 7, which could not run on the build machine;
- 8 need the 5.0 and 6.0 git commits, which are not in this repository.

| Suite | Tests | What it covers |
|---|---|---|
| **test_v1015** | 32 | dev 10.15: Omega weapons: the 20 items (the weapon's own id, never a real item); omega off = every seed is the 10.13 seed (git); on = the same seed plus each Omega once, never Gold Bolt / shop / random start, start_items and exclude, the audit; weapon -> Omega, Omega -> weapon, Omega with neither owned, both at once, repeats, all 20 weapons; a non-flag byte never written; omega_runtime off; without 17; learning the byte from two purchases, never from one with an upgrade, never from a byte every record holds as 1, never from a new weapon; kept over New Game; save/load, a save that lost the flag, the late-restore merge, loads moving the records, the inventory restore and a New Game+ Omega never downgraded; a seed's locations paying Omegas; held back from player packages |
| **test_v1013** | 23 | dev 10.13: Chaos Randomizer: loads OFF, BACKSPACE toggles and says so, saved and kept over New Game; every category replaced and used both ways (bosses <-> regular, story bosses, unclassified); other planets' templates; few repeats; seeded; priority over Enemy/Boss and their exact picks back when OFF; no guard of any kind; integrity (unmatched nodes never written); removal; never in a player package |
| **test_v1012** | 32 | dev 10.12: Enemy / Boss Randomizer against the simulated encounter model: off = nothing read or written; only template ids change and the node completes the encounter once, after the last enemy; tiers and families never mix; story bosses and friendlies never touched; bosses permuted; each switch only its own, saved and kept over New Game; safety nets (no spawn, stuck, retries, wrong family, story boss areas); layout by signature; frame budget; any of the three files removed |
| **test_v1011** | 20 | dev 10.11: Coordinates never on revisits and always opening a playable first visit (an independent Python check of the rules, both fills, your settings, fewer locations), the audit catching both, the switch; open planets' visits made active between stories (never while a story runs, never on your planet); a primed landing loads nothing; a landing started there loads the intro (Blizar's destroyed pad); a stuck first step reloaded at the intro; Viceron before Torren IV sent back with the reason; first visits listed first; the game's trip to an open Sargasso played |
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

## 2-dev9. Dev 10.22 (kit 10.0.16): Factories replacements (Zurkon)

Build: commit of dev 10.22 on main. Files: the kit's whole `scripts` folder with `dev(spawnproof).lua` v2, but
**without** `dev(spawnprobe).lua` (delete it from <game>\scripts: it costs frame budget and v2 logs what is
needed), AND `rando_give_source/dev_build/rando_give.dll` (v7) over the game folder's rando_give.dll.
1. Load your save, go to Zurkon (Zurkie's Battleplex). Play ONE multi-wave challenge of ordinary enemies to the
   end (A1 is fine). The file learns from the first waves and arms nodes of later waves.
2. If a later wave brings an enemy type that does not belong there, that is the replacement. Finish the
   challenge (that it completes is part of the test). A second challenge in the same session is welcome.
3. Quit normally and send rivet.log.
Expected `RANDO-SPAWNPROOF` lines: `v2 loaded`; `scan N on scarstu: ... X Template, Y Factories ...`;
`spawn H (SpawnFactory F, ...): node U via LastSpawn|Spawner slot; slot factory = F; spawned ...`;
`factory F: classes ...; node variables ...`; `learned: ...`; then `ARMED k/4 node ... read back OK; ...`,
`VERIFY node ...: REPLACEMENT SPAWNED` (or ORIGINAL / SOMETHING ELSE), `put back (...)`, `level summary`.
What each answer means: REPLACEMENT SPAWNED = the mechanism for Enemy / Boss / Chaos is proven; ORIGINAL
SPAWNED = the node does not read the variable/copy at spawn time (the factory's own variables, logged, are the
next place); no `ARMED` = read `learned:` and `level summary` (fewer than 2 factories with enemies, or MIXED).

## 2-dev8. Dev 10.21 (kit 10.0.16): ONE controlled enemy replacement (Zurkon)

Build: commit of dev 10.21 on main. Files: the kit's whole `scripts` folder (dev(spawnproof).lua and
dev(spawnprobe).lua included) AND `rando_give_source/dev_build/rando_give.dll` copied over the game
folder's rando_give.dll (it must say v7; the kit's top-level DLL is the older v6).
1. Load your save, go to Zurkon (Zurkie's Battleplex). Start an arena challenge with several waves of
   ordinary enemies (the A1 challenge you replayed is fine) and play it to the end. The file only acts on
   Zurkon, once per session, only in memory.
2. Watch for the first enemy of a later wave: if the file armed a node, one encounter should spawn a
   different ordinary enemy than usual. Finish the challenge (that it completes is part of the test).
3. Quit normally and send rivet.log.
Expected `RANDO-SPAWNPROOF` lines: `SceneManager ... (signature matched 1 x)`; `scan N on scarstu: X node(s)
...; Y with a Template variable`; `spawn H is node U's (its LastSpawn) ...`; then `ARMED node ... read back
OK`, `VERIFY node ...: REPLACEMENT SPAWNED` (or ORIGINAL SPAWNED / SOMETHING ELSE SPAWNED) and `put back
(its Spawner stopped) ...: OK`. Each line answers one open question: Y = 0 means arena nodes do not use the
Template variable; no `spawn ... is node` line means LastSpawn does not tie spawns to nodes; ORIGINAL
SPAWNED means the node does not read the variable at each spawn.

## 2-dev7. Dev 10.20 (kit 10.0.15): ONE focused test - where the encounter's Templates live

Nothing is randomized by this test and nothing is written to the game: dev(spawnprobe).lua only reads.
1. Install the whole dev kit's `scripts` folder, `dev(spawnprobe).lua` included (delete the old *_rando_*,
   enemy/boss/chaos and dev(*) files first). The Enemy / Boss / Chaos switches do not matter.
2. Load your save and go to Zurkon (Zurkie's Battleplex). Start one arena challenge you can replay and fight
   until at least two waves have spawned (finishing it is better). Then go back to the table once
   (a checkpoint load) and quit the game normally.
3. Send rivet.log. Needed: every `RANDO-SPAWNPROBE` line. Expected kinds:
   `index N (...)` (one per load: how many nodes, whether every Spawner matched +0x60, where Spawners hold
   pointers), `spawn N:` (what the game actually created: uid, actor asset, classes, Template flag),
   `sweep N:` / `stopped:` (which Spawner bytes change while an encounter runs), `probe ...` (type data,
   bytes, pointer targets) and, most important, `UID HIT` lines (a loaded actor's uid found in or one / two
   pointers from the node or its Spawner: a template bot there marks the Templates list).
What decides the next step: a `UID HIT` naming a TEMPLATE bot whose actor asset matches a `spawn` line is the
list; then ONE slot of ONE encounter is changed (with read-back and a `verify` of the next spawn) before
anything else is enabled. If there is no such hit, the list is not reachable from the node, and the next
step is the spawn function itself (rando_give.dll), not more offsets.

## 2-dev5. Dev 10.15 (kit 10.0.11): Omega weapons (gameplay test plan)

Needs a Challenge Mode save (finish the story once) and the developer kit (`17_rando_omega.lua`).
Read OMEGA.md first. Use a spare save slot.

0. **Install.** `RANDO-KIT all 12 required scripts are 10.0.11`; `RANDO-OMEGA loaded (Omega flag not learned yet)`.
1. **The records.** On any planet: `RANDO-OMEGA inventory: N weapon record(s) in <class> (array at +0x..)`,
   N = the weapons you own. If it says `inventory not found`, send rivet.log (it has the component's bytes).
2. **Learning.** At Ms. Zurkon buy the Omega of one weapon: `Omega purchase 1 of 2 (...): candidate byte(s) ...`.
   Leave, come back, buy a second weapon's Omega: `LEARNED: the Omega flag is the byte at +0x..` and the HUD
   message. If no line appears after a purchase, the game reports no `PurchaseWeaponEvent` for Omegas: send rivet.log.
3. **A seed with Omegas.** `omega_weapons = true` in 04 (a new seed: New Game in Challenge Mode). The spoiler's
   OMEGA VERSIONS section lists where each is.
4. **Omega first.** Find an Omega whose weapon you do not have: the weapon arrives first, then `... is yours`.
   Check in the weapon menu: Omega name, level cap 10, the Omega upgrade nodes. Save, quit, load: still Omega.
5. **Weapon after its Omega.** Find that weapon's own reward: `you have its Omega version already (kept)`;
   the weapon stays Omega.
6. **Weapon first, then its Omega**: the weapon you have becomes Omega; nothing is added twice.
7. **Restore.** Ctrl+0 twice (items sent again): every Omega stays Omega (`RANDO-OMEGA kept ...` if the game
   had cleared one).
8. **Status.** `;` / F9: `Omega n/m`.

## 2-dev3. Dev 10.13 (kit 10.0.9): Chaos Randomizer (gameplay test plan)

Read CHAOS.md first: Chaos has no protection, so a stuck run is an expected result, not a failure.
Use a spare save. What is tested here is that Chaos does what it says, not that the game stays beatable.

0. **Install.** `RANDO-KIT all 12 required scripts are 10.0.9`; `RANDO-CHAOS installed (OFF ...)`;
   banner `Randomizer dev 10.13`.
1. **The key.** Does `BACKSPACE` reach the game (`RANDO-KEY BACKSPACE` in rivet.log) without a game
   action of its own? "CHAOS RANDOMIZER: ON" on screen; `Ctrl+BACKSPACE` shows the status.
2. **Everything changes.** `RANDO-SPAWNERS plan (...): N slot(s) changed ... chaos (priority, P
   template(s))`. Play encounters: what spawns? Note whether each replacement spawns, moves, fights,
   dies, and whether the encounter completes (no outcome is required).
3. **Bosses <-> regular.** A large enemy encounter that now spawns small ones and the other way round.
4. **Cross-planet.** Play a planet with Chaos on, travel to another: `RANDO-CHAOS pool: N new
   template(s) from <planet>`, and `Ctrl+BACKSPACE` "N from elsewhere here". **Do other planets'
   templates spawn, spawn wrong, or make the game misbehave or crash?** If it crashes, try
   `chaos_cross_planet = false`.
5. **Priority.** With `-` and `=` ON, switch Chaos on: their changes are replaced; switch it off:
   their own picks come back (Ctrl+- / Ctrl+= counts as before Chaos).
6. **Persistence.** Restart the game (companion running) and start a New Game: Chaos still ON.
7. **Getting unstuck.** In a broken encounter: BACKSPACE, then load the last checkpoint: the
   original encounter.
8. **Frame time.** Any `ran past the 8 ms frame budget` line naming 16_rando_spawners or chaos.lua?

## 2-dev2. Dev 10.12 (kit 10.0.8): Enemy Randomizer and Boss Randomizer (gameplay test plan)

Seeds are unchanged: a 10.11 save continues. Copy `16_rando_spawners.lua`, `enemy.lua`, `boss.lua`
with the rest of `scripts\`. Both features start OFF. Test whole encounters from start to finish,
not only whether enemies look different. Note for every case: PASS / FAIL / not reached, and keep
rivet.log. ENEMIES_AND_BOSSES.md section 7 says which lines to look for.

0. **Install.** `RANDO-KIT all 12 required scripts are 10.0.8`; `RANDO-ENEMY installed (OFF ...)`,
   `RANDO-BOSS installed (OFF ...)`; banner `Randomizer dev 10.12`.
1. **Both OFF (play 2-3 encounters).** No `RANDO-SPAWNERS census` line at all. Enemies as usual.
2. **Enemy ON (`-`).** "Enemy Randomizer: ON". `census 1 (...): N spawner node(s) read ... layout ...`
   (send the line). Play a few encounters: `learned <id> = <family>` lines, then `plan (...): N slot(s)
   changed`. Later encounters on the planet: different regular enemies?
3. **Encounter completion (the key test).** In a changed encounter (`Ctrl+-` shows the count): kill
   all but one: the door / wave / objective must NOT advance; kill the last: it must advance once.
   Arena doors, "defeat the enemies" objectives, wave spawners.
4. **Death and reload.** Die in a changed encounter, retry, finish it. Load the last checkpoint once.
   A third death there puts it back (`kept original`): is that encounter then normal?
5. **Planet change and hub return.** Fly away and back (planet shuffle on and off): census again,
   nothing wrong in other features (weapons given, shop, Gold Bolts, collectibles).
6. **Enemy OFF in the middle of an encounter.** The remaining spawns are the originals; it completes.
7. **Boss ON (`=`), enemy OFF.** On a planet with large enemies (Grunthors, tanks, Manglers): are they
   other large enemies (none added, none doubled)? Health bar, death, arena exit.
8. **A story boss** (e.g. Sargasso's Seekerpede, Cordelion, Viceron's warden, the finale) with both
   ON: the boss and its adds are the game's own; `story boss area ... every change put back` if the
   checkpoint name contains BOSS/FINALE/HEAVY_FIGHT/CHASE. Cutscene, health bar, next area as usual.
9. **Both ON, enemy ON + boss OFF, enemy OFF + boss ON, both OFF**: one encounter of each kind per
   combination; the switches survive a game restart (the companion) and a New Game.
10. **Frame time.** Any `ran past the 8 ms frame budget` line naming 16_rando_spawners?

## 2-dev. Dev 10.11 (kit 10.0.7): new planets start at their intro

A new seed (generator 10.11.0): start with **New Game**, planet shuffle on (`0`).

1. **Install check.** `RANDO-KIT all 12 required scripts are 10.0.7`; the banner reads
   `Randomizer dev 10.11 (kit 10.0.7)`.
2. **After Nefarious City's story** (or at the hub when it is done): `making the next visit of N
   open planet(s) active` and `prime <visit>: start MIS_... (Available -> Active)` lines. No warp,
   no hero swap.
3. **Coordinates found (the key test).** "X is open: ..." on screen. Fly there with the ship's
   planet menu. Does the planet's **intro** play and the first mission start? Logged: `planet menu:
   landed on X at <checkpoint>` and either `... was active before the landing - its arrival is the
   game's own; nothing loaded` or a warp `travel: warp to <intro> ... (its intro)`. Then the story's
   `objective MIS_... OBJ_..._GO_TO_...` should turn 2 (done). Please note which checkpoint the
   game landed at (`RANDO-CHECKPOINT` right after the landing).
4. **A planet whose first visit is not open yet.** A planet shown as "its first visit needs ...
   first" sends you back from the planet menu with that reason. (Viceron's Coordinates now come from
   Torren IV's story, so this should be rare.)
5. **The `]` list** (dev keys only): first visits before revisits; no "revisit" entry for a planet
   whose first visit is still to come.
6. **Nefarious City's end** with Sargasso's Coordinates held: the game's own trip to Sargasso is
   played (`its first visit is open: hub_follow_new`); without them it is undone as before.

## 2. Round 27: v0.54 (build 10.0.5)

Your round 26 save carries over (same seed, same fingerprint). No New Game is needed.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.5`; RANDO-KEYS lists `planet shuffle 0`;
   the banner reads `Randomizer v0.54 (kit 10.0.5)`.
2. **Load the Viceron save.** `arrived on viceron (a load) - nothing changed` and **no** `the
   game's own story took you to`. Then, 7 s later, `RANDO-RESTORE after the load on viceron: ...`:
   do your weapons come back ("Given back: ...")? If not, press `Ctrl+0` twice.
3. **`0`.** `planet shuffle OFF`; `]` / `Ctrl+]` answer "planet shuffle is off"; travel with the
   ship: nothing sends you back. Press `0` again: `planet shuffle ON`. Restart the game: the
   choice is kept (`planet shuffle is OFF in this save` when it was off).
4. **A trip with `Ctrl+]`.** After landing: `RANDO-RESTORE after the trip to <planet>: ... nothing
   to do` with your weapons intact. If the inventory is emptied, the line says so and the items come
   back. Please send the log either way: the lines around the landing show what emptied it.
5. **`[`** shows "only cancels the trip back"; no warp.
6. **The shop:** look for `as pointers:` and `slot object 0 of the array` in RANDO-SHOP lines.

## 2a. Round 26: v0.53 (build 10.0.4)

Your round 25 save carries over (same seed, same fingerprint). Load it; no New Game is needed.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.4`.
2. **Load the save in Nefarious City.** `planetary travel and level bits left to the game while
   nefcity_1 runs` (and **no** `planetary travel: done (0x0 -> 0x1)` while the city's story runs).
3. **The boss fight (the key test).** At the shift to Savali / Sargasso: does Ratchet arrive
   **without** the ship, on solid ground? Logged: `arrived on savali during nefcity_1`, then on the
   way back `back on nefarious_city from savali during nefcity_1 - the story's own travel` (no
   "destinations open" message in the fight).
4. **After the city's story.** Once MIS_NEFCITY_01 completes and you are back in the city:
   `planetary travel: done (0x0 -> 0x1)` and the level bits again; the ship's planet menu works.
5. Then continue with the round 25 list below from step 4.

## 2b. Round 25: v0.52 (build 10.0.3)

Use a spare save slot and the kit's settings (hub = true). Your round 24 seed carries over (same
fingerprint), but start a **New Game**: the new start only runs from the parade. Send the whole
rivet.log afterwards. Each step names the log line that shows it worked.

1. **Install check.** `RANDO-KIT all 14 scripts are 10.0.3`.
2. **New Game → Nefarious City (the key test).** Play the parade until the warp. In this order:
   - `going to the hub (Nefarious City): the parade handed Ratchet back after his wrench`
   - `prologue: MIS_INTRO written Complete Finished` (now **before** the story starts)
   - `made available MIS_NEFCITY_01`, `start MIS_NEFCITY_01 done (available -> active)`
   - `with nefcity_1: made available MIS_NEFCITY_01_TRAINSTATION`
   - `opening of nefcity_1: <NAME> (hash 3046787773, ...)` **(note the name)**, or
     `hash 3046787773 is not among the checkpoints your game lists` plus `checkpoints listed for
     nefarious_city:` (send that line)
   - `travel: warp to <NAME>`, then `RANDO-CHECKPOINT <NAME>` and `opening of nefcity_1 loaded`

   **Most important:** does the arrival cutscene play, then gameplay? Look for
   `objective MIS_NEFCITY_01 OBJ_NEFCITY_GO_TO_NEFCITY 2` and the next objective lines.
3. **If it still waits at "go to Nefarious City":** don't press anything for a minute (the hub
   reloads the opening once, `[STORY RELOAD]`). Then try `/` once. Note what each did.
4. **The city's story to its end.** Does the train station part work? Then the game flies you to
   Sargasso: is `[ORDER KEPT]` logged, and are you back in Nefarious City (at `CHK_NEFCITY_SHIP`)?
5. **Battle Arena.** `]` to "Battle Arena", `Ctrl+]`. Does Zurkon's arena intro play? Finish it:
   are you brought back to Nefarious City?
6. **A shuffled planet.** Once a "Coordinates" reward arrives, `]` shows that planet. Go there. Note
   whether its story starts, and the `RANDO-CHECKPOINT` lines (`learned the start of ...`).
7. **Planet menu.** From the ship, pick a planet you have no Coordinates for: are you sent back to
   Nefarious City?
8. **Rewards.** Every Gold Bolt gives an item (weapon, gadget, armor or Coordinates), matching the
   spoiler.

## 3. Running the automated tests yourself

`pip install lupa capstone`, then `python run_tests.py`; `python tools/big_batch.py` for the
43,000-seed batch (about 5 minutes). Optional, each skipped when missing:
- PowerShell 7, for the companion tests;
- a C compiler, for the DLL core test;
- clang + lld-link + llvm-dlltool, for the byte-for-byte DLL rebuild;
- git history, for the regression tests.
