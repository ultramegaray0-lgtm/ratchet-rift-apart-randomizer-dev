# Changelog

Newest first. 8.4 and 8.5 are stabilization releases: no new features, the same seeds as 8.3.

## Dev 10.19 (kit 10.0.14, generator 10.11.0; not released): the node's Spawner component

Asked: "no enemy/boss randomized" (rivet.log of 2026-11-17 with dev 10.18, tests/data/round29_rivet.log).
Seeds unchanged. **Tested in the simulator only.**

- Cause (10.18's dumps): SpawnerScriptAction's ddlPriusData is 0; +0x60 holds the handle of its Spawner
  component (own handle + 1 in all six dumps). Spawner = SpawnerPrius's component (hash 4233548849).
- 16_rando_spawners: SP.spawner_of (the node actor's Spawner component, handle checked against +0x60), its
  Prius via SP.find_prius (short layout; new `inline` route for lists copied into the component); rec
  remembers the component's handle (SpawnerStopped/Started events match it); diagnostics when it is not on
  the node's actor; first start/stop events logged per level.
- The census retries a node interrupted by the frame budget (pcall + yield) instead of restarting; 8
  restarts allowed. The level-wide Spawner scan is off by default.
- Simulator: `comp` node model (prius / holder / inline / elsewhere), bot-sent spawn events.
- Tests: tests/test_v1019.py (11; 8 fail and 1 errors against 10.18). 578 run, 0 failures, 21 skipped.

## Dev 10.18 (kit 10.0.13, generator 10.11.0; not released): spawner Prius reached by hand

Asked: "Still nothing randomized. Take your time, investigate and fix, and make no mistake." (rivet.log of
2026-11-17 with dev 10.17). Seeds unchanged. **Tested in the simulator only** (now modelled on both logs).

- Cause: rivet_hook returns no `prius` for SpawnerScriptAction (its find_component follows only
  ComponentInfo.prius); the 128-byte instance is ScriptAction's header + 32 bytes. 10.17 relied on rivet's
  `prius`, so every node was skipped again.
- 16_rando_spawners: SP.find_prius - rivet's prius, then `ddlPriusData` (+0x08) -> holder -> data, then
  pointers in the node (as Prius or holder), then a bounded deep search; strict candidates need
  ActionType 60 or a loaded actor's uid; the path that worked is followed first; bytes dumped when nothing
  works. Placed `Spawner` components read too. Capacity of the lists no longer checked (only the count).
- Learning from template actors at the census (`rivet.find_uid` + `rivet.components`; Templates are TUIDs).
- Verification log on each changed fight's first spawn; `spawn:` match lines for the first 5 spawns a level.
- Fixes: a census of the previous level is dropped on a level change; spawns before the census mark their
  spawner started; template learning survives the save being replaced; census yields inside long searches.
- Chaos: another planet's template only where its template actor is loaded.
- Simulator: `rivet.uid` / `rivet.components` were defined inside `rivet.component` since 10.17 (only after
  it ran); moved out. New node models: holder (your game), ptr, deep embed/ptr, Spawner components, shared
  Prius, template actors. Real logs kept as tests/data/round27_rivet.log, round28_rivet.log.
- Tests: tests/test_v1018.py (18); 567 run, 0 failures, 21 skipped.

## Dev 10.17 (kit 10.0.12, generator 10.11.0; not released): Enemy / Boss / Chaos Randomizers fixed

Asked: "enemy, boss and chaos randomizer didn't work. Fix it" (rivet.log of 2026-11-17, dev 10.15 kit with
10.16's defaults). Seeds unchanged (generator untouched). **Tested in the simulator only.**

- Cause: all 32 censuses in that log read 0 spawner nodes; every node "cannot read the node". rivet_hook's
  `rivet.component` returns the instance (`size` = class size) and, separately, the Prius data (`prius`).
  The census read only min(0x100, size) bytes of the instance and needed 0x88, so nothing was read,
  nothing learned and nothing changed, for all three randomizers (they share 16_rando_spawners.lua).
- 16_rando_spawners: the census reads the Prius at the DDL's offsets (FactoryGroup +8) with the same
  signature check; the instance search is kept only when rivet gives no Prius. The census line says
  `layout prius +0x8 xN`; a skipped node says why (the Prius, or the instance's size).
- Spawns: handlers also take `ev.sender`; a spawn with no sender is matched by its SpawnLocation actor id
  (`rivet.uid`) in one node's SpawnLocations list (the real event has SpawnFactory / SpawnIndex /
  SpawnLocation / SpawnedHandle).
- Learning: one `rivet.components` call per spawned actor (the old ~90 failing `rivet.component` calls stay as
  fallback); unknown bot classes are logged once (`spawned actor not classified`).
- Frame budget: a census stopped by the 8 ms budget starts again 20 frames later (up to 5 times) instead
  of waiting for the next load.
- Tests: tests/test_v1017.py (10, a simulator model of what the log shows: small instance, Prius, no sender);
  test_v1012's kit-check test fixed for 10.16's ON defaults. 548 run, 0 failures, 21 skipped.

## Dev 10.15 (kit 10.0.11, generator 10.11.0; not released): Omega weapons

Asked: Omega weapons (Challenge Mode / New Game+) in the randomized item pool as items of their own,
with weapon and Omega ownership kept apart and never downgraded. **Nothing of this has run in the
game.** Built on dev 10.13 (the repository's latest; the 10.14 patch was never pushed, so it is not in
here). Seeds unchanged unless `omega_weapons` is turned on. OMEGA.md has everything.

- Research: an Omega weapon is not an item id; it is the bool `WeaponItemPrius.Omega` of the weapon you
  own, set only by Ms. Zurkon's Omega purchase (the game's type data; no Omega config in your dag).
- Data: 20 items `omega:<weapon>` (one per vanilla weapon; category `omega`, the weapon's own id,
  in-game names from the guides). Data version stays 5.1.0.
- Generator: `omega_weapons = false`. On: the same seed plus the 20 Omega versions on locations that
  would give currency (own stream; the placement random streams ignore the new setting); never Gold
  Bolts, shop or random start; `start_items` / `exclude` take `omega:` keys; the audit checks them; the
  spoiler lists them. Off: same fingerprint and spoiler as 10.13 (tested against git).
- Runtime (10): a tier per weapon (`state.weapons`, `state.omega`, `state.omega_prereq`). An Omega
  first gives its weapon first; a weapon after its Omega sends nothing and keeps the Omega; repeated
  rewards are recorded once; saved, merged (furthest status), reset by a New Game.
- `scripts/17_rando_omega.lua` (new, optional, **never in a player package** until it has run in the
  game): finds the weapon records in the hero's inventory component by the item ids, learns the flag's
  byte from two Omega purchases at Ms. Zurkon (or `omega_flag_offset`), writes one byte with read-back
  for weapons the game has confirmed, and sets a cleared flag again after loads and resends.
- 10: `omega_runtime = true`, `omega_flag_offset = -1`; status `Omega n/m`; 17 is an optional kit file.
  Kit 10.0.11, banner `Randomizer dev 10.15`.
- Release tools: `17_rando_omega.lua` is in `HELD_BACK` (builder) and rejected by `validate_release.py`.
  The public release and `release/` are untouched.
- Tests: tests/test_v1015.py (32); 536 run, 0 failures, 21 skipped. Older tests changed only where the
  kit version, the banner, the script list or the subscription count changed.

## Dev 10.13 (kit 10.0.9, generator 10.11.0; not released): Chaos Randomizer

Asked: a third, independent randomizer: **anything can become anything**, with no compatibility
rules and no progression protection. OFF by default, its own key, saved, priority over the Enemy and
Boss Randomizers while ON. **Nothing of this has run in the game.** Seeds unchanged.

- `scripts/chaos.lua` (new, optional, **never in a player package**): **`BACKSPACE`** turns it on /
  off (`Ctrl+BACKSPACE`: what it changed here). Every spawner slot can become any enemy template seen
  on any planet of the save (`state.chaos_seen`) or learned by 10.12: regular, elite, flyer, turret,
  large, boss tier, story boss and unclassified, in both directions. Each slot gets its own seeded
  pick. Repeats are avoided until the pool is used up, and a slot never keeps its own template.
  No guards: no family / tier / planet rule, no timeouts, no retry limit, no story boss areas, no
  "not started" rule, no put-back, nothing that forces progression. Only learned friendly bots and
  mounts are left out (they are not enemies). Code integrity stays: live-instance check, read-back,
  game-used ids only, shared lists not written. `docs/CHAOS.md` explains the risks.
- Priority: while Chaos is ON the Enemy and Boss Randomizers change nothing and keep their own
  settings. Chaos OFF puts its slots back and they plan again (exactly their own picks).
- `16_rando_spawners.lua` (shared integration): priority clients with their own `assign`, clients
  with `guards = false` (their slots skip every safety net), census and restore hooks for clients,
  the record of writes pruned when nodes are gone. Enemy / Boss behaviour unchanged (tests/test_v1012.py
  passes unchanged).
- 10: settings `chaos_randomizer = false`, `key_chaos = "BACKSPACE"`, `chaos_cross_planet = true`; the
  status line; chaos is an optional kit file. Kit 10.0.9, banner `Randomizer dev 10.13`.
- `tools/build_public_release.py` holds `chaos.lua` back (`HELD_BACK`), and
  `release_tools/validate_release.py` rejects a package that contains it.
- Tests: tests/test_v1013.py (23), simulator only (nodes can belong to one planet now). 504 run,
  0 failures, 21 skipped. `TEST_REPORT_10.13.md`.

## Dev 10.12 (kit 10.0.8, generator 10.11.0; not released): Enemy Randomizer and Boss Randomizer

Asked: an Enemy Randomizer and a Boss Randomizer as two separate, independently switchable
features (`enemy.lua`, `boss.lua`), both OFF by default and switched in the game; randomized enemies
and bosses must still open doors, finish objectives and advance the story. **Nothing of this has run
in the game.** Seeds are unchanged (the generator is not touched): a 10.11 save continues.

New files (all optional, ENEMIES_AND_BOSSES.md):
- `scripts/16_rando_spawners.lua`: the layer both share. Reads the level's SpawnerScriptAction
  nodes (the game's combat encounter spawners), finds their Templates list by the DDL layout's
  signature (never a fixed offset), learns what each template is from the bot component of an actor
  the game spawned, and changes **only template ids**. The encounter's own node spawns, counts and
  completes the new enemies, so its doors, objectives, waves and story steps follow from the game's
  own logic, once, after the last enemy. Safety nets put an encounter back (and keep it original for
  the seed) when a replacement spawns nothing for 20 s, stays alive 180 s without a death, is another
  family than planned, or the checkpoint is loaded 3 times during it; story boss areas put every
  change back while you are there.
- `scripts/enemy.lua`: the **Enemy Randomizer** (`-` key; `Ctrl+-` shows what it changed here).
  Regular enemies (turret, flyer, swarmer, ground) become other regular enemies of the same family
  from the same planet's own encounters.
- `scripts/boss.lua`: the **Boss Randomizer** (`=` key; `Ctrl+=`). Boss-tier spawns (large bots and
  any spawned enemy with its own boss health bar) are permuted among the planet's boss-tier enemies
  of the same family: none is added or doubled. The eight story boss fights are left unchanged
  (boss-specific scripts and arenas; `RANDO_BOSS.STORY` lists them and why).

Settings (runtime only, 04 documents them): `enemy_randomizer = false`, `boss_randomizer = false`
(the start of a save that never used the keys), `key_enemies = "-"`, `key_bosses = "="`,
`spawner_runtime = true`. The switches are saved like planet shuffle's (`state.enemy_rando`,
`state.boss_rando`), kept over New Game, a choice before the companion's restore wins. No preset
turns them on.

Runtime changes elsewhere: 10 (`R.subscribe`, the frame call, the status line, New Game keeps the
switches and what was learned, the restore hook, the kit's optional files), 14 (each checkpoint is
passed on). Kit 10.0.8, banner `Randomizer dev 10.12`.

Tests: tests/test_v1012.py (32) against a new simulated encounter model (tests/sim/rivet_sim.lua:
spawner nodes laid out as the DDL says, reading their Templates at each spawn, counting their dead,
firing "all dead"). 481 run, 0 failures, 21 skipped. TEST_REPORT_10.12.md lists passed, failed and
untested cases.

## Dev 10.11 (kit 10.0.7, generator 10.11.0; not released): planet shuffle that starts each new planet at its intro

Asked: make planet shuffle actually work: when the player gets new Coordinates and goes to the new
planet, take them to that planet's intro so the first mission there starts; make sure players get
to Coordinates and first visits first, not revisits. **Nothing of this has run in the game.** Every
seed changes (generator 10.11.0, a new setting): start with New Game.

Why it did not work: the hub started a planet's story only AFTER the ship's planet-menu landing,
then warped on that planet to a landing pad or a learned checkpoint. The game had already played its
arrival without the story, and a pad is not where a first visit begins (Blizar's even sat on the
intact side, round 17 shows the game landing on the destroyed one). A planet whose Coordinates came
before what its first visit waits for (Viceron before Torren IV's Hurlshot) was offered as a
"revisit" with nothing to play, and revisits sat in the `]` list between first visits.

Runtime (15_rando_hub.lua, 03, 10):
- **Next visits made active between stories** (`hub_prime_open`): at the hub, after a finish, when
  Coordinates arrive and on the planet menu's accept, the next visit of every open planet you are not
  on is made active (available, then start; no hero swap, no travel), as the game itself does when a
  visit ends (round 17: MIS_SAV_01 and MIS_BLIZAR together at the end of Zurkie's first visit). Never
  while a story runs (v0.53's rule), never the hub planet or the prologue.
- **Planet-menu landing**: a story already active before the flight is left to the game's own arrival
  (nothing loaded); one started on landing loads the visit's **intro** on that planet. A first visit
  is always loaded at its intro while its story has not left its first step (`hub_planet_intro`).
  A first step still waiting a minute later is loaded once more at the intro (or its second point).
- **Intros** (03 `intros`, from the logs): Zurkie's CHK_ZURK_00_DEFAULT, Savali CHK_SAV_01_LANDING
  (then CHK_SAV_01_START), Blizar CHK_BLIZAR_B_LANDINGPAD_DESTROYED (then the intact pad), Torren IV
  CHK_MOL_START, Cordelion CHK_CORD_A_START, Ardolis CHK_ARD_START, Viceron CHK_ZORDOOM_START,
  Sargasso 2 CHK_SARG_02_MININGPLATFORM_LANDINGPAD, the finale CHK_MEGA_FINALE_START; Sargasso's first
  visit by its arrival scene's hash (C.OPENINGS, 2498464355), else the gel factory pad.
- **No revisit before a first visit** (`hub_blocked_home`): a planet whose first visit cannot be
  played yet is never a "revisit"; the planet menu sends you back with the reason ("needs the Hurlshot
  from the story on Torren IV"). Coordinates say what they open. `]` lists the start missions, then
  first visits, then revisits, then the finale.
- **The game's own trip to an open first visit is played** (`hub_follow_new`): Nefarious City's end
  takes you to Sargasso; with its Coordinates held that is its intro, so the hub carries on there
  instead of going back.
- Kit 10.0.7; banner `Randomizer dev 10.11 (kit 10.0.7)`.

Generator 10.11.0 (`coords_first_visit = true`, a new seed setting):
- No Coordinates and no gadget a location needs on a revisit (Zurkie's 2, Sargasso 2, Savali 2) or the
  finale: the way to the next planet never runs through a revisit.
- A planet's Coordinates only where its first visit can be played the moment they are found: every
  visit it waits for is done there (a story mission, its milestone and a side activity pay when their
  visit finishes; a Gold Bolt or armor pod is found during it). Nefarious City's story counts as done
  elsewhere (the ship's travel is off while it runs). So Viceron's are a reward of Torren IV's story.
  Those Coordinates are placed first. If a seed's settings leave no such place, the nearest fit is
  used and the seed says so (`coords_exceptions`, spoiler, warnings).
- Audit and spoiler updated.

Tests: tests/test_v1011.py (20). Changed where the rules changed: version strings, round 24's
fingerprint, the guard test (now with `hub_follow_new = false`), whole campaigns (also played with
the game's trip followed), the start's reach floor 4 -> 3 items (Zurkie's revisit holds no
progression any more), the catalog's Torren IV name (the simulator lists your game's CHK_MOL_START).
449 run, 0 failures, 21 skipped; big_batch 56,600 of 56,600 valid.

## Dev 10.1 (generator 10.1.0, data 5.1.0; kit stays 10.0.6, not released): Spybots, Lorbs, three weapons as items

Asked: Spybots and Lorbs were defined as locations but the generator never used them, so make them
hold items; put the Burst Pistol, Shatterbomb and RYNO 8 into the item pool. **Nothing of this has run
in the game.** Every seed changes (new generator and data versions): start with New Game.

- Data: 10 Spybots (`spybot:1`-`spybot:10`, any planet: counted in pickup order) and 12 Lorbs
  (`lorb:1`-`lorb:12`, Savali), `holds = "any"`. CraiggerBears stay unused.
- Generator: `collectibles = true` (new setting) puts them in the location pool. They are never in
  logic (no pickup event is bound), so they hold weapons, gadgets nothing needs, armor or currency,
  never Coordinates or a gadget a location needs. With `goldbolts_first` they share the leftover items
  with missions, side activities and armor sources (rank 2).
- Weapons: acquisition `reward` for the Burst Pistol, Shatterbomb and RYNO 8: always at a location,
  never in the 15 normal shop slots, never a random start weapon (`start_items` and `exclude` still
  apply). `12_rando_shop.lua` already closes any vendor slot whose weapon the seed gives at a
  location, so Shatterbomb's and RYNO 8's own slots now show the Burst Pistol.
- The Burst Pistol is still handed out by the game in the prologue, so its reward adds nothing new;
  it is kept off Gold Bolts and early-weapon spots when another place exists, and never counts as a
  weapon `weapon_logic` waits for.
- Audit: no reward-only weapon sold or started at random; no Coordinates at a Spybot or Lorb.
- Until `05_rando_bindings.lua` `collectible_events` binds the Spybot and Lorb pickup events, what
  those 22 locations hold is not handed over in the game (KNOWN_ISSUES.md).
- tests/test_v101.py (10); older tests updated where the rules changed. 429 run, 0 failures, 21
  skipped; big_batch 56,600 of 56,600 valid.

## 10.0.5 / Public Release v0.54 (2026-11-13): planet shuffle on 0, items given back, no stale guard

Reported (round 26, v0.53, tests/data/round26_rivet.log, seed pocket-pocket-zurkie-839, a restored
save): `[` (back to the hub) is useless; after trips with `]` / `Ctrl+]` the whole inventory was
gone; some levels do not work when warped to. Asked: a key to turn the planet randomizer off and on,
remembered. **Nothing of v0.54 has run in the game.**

Round 26, what the log shows:
- The game booted on Nefarious City (the restored state: Gold Bolts 3/25, hub 4/14, `in inventory
  15`), then the save continued on Viceron. No key was pressed (no `RANDO-KEY`), no planet menu was
  used, the hub launched nothing.
- Yet: `the game's own story took you to viceron - back to the hub`, `[ORDER KEPT]`, and the trip
  back was announced. `H.on_arrival`'s guard after a finished destination compared `H.frame` with
  `h.finished_at`, which was SAVED with the hub's state; frames start at 0 in every session, so a
  finish of an earlier session held the 2-minute guard far into the next one. Every load on another
  planet early in a session was undone.
- The Viceron load replayed one gadget and **no weapon**, against 15 items the randomizer counts as
  given: that save had lost them (the user's "lost all my inventory"). The cause is not in this log.
- The banner: `Randomizer 10. - seed ...` (`R.KIT_VERSION:sub(1, 3)`).
- The shop: `only 0 vendor weapon(s) in the array at +0x48` again, and once `ran past the 8 ms frame
  budget` at the id loop of `H.discover` (line 210).

Changes:
- 15: the guards use this session's frames only (`H.session.finished_frame`); `h.finished_at` is no
  longer written and is cleared on restore.
- 15: `[` (`H.key_return`) no longer warps home; it only cancels `H.return_at`. `Ctrl+[` twice is
  unchanged. Messages that offered `[` twice now point to `]` / `Ctrl+]` or the ship.
- 15: `0` (`key_shuffle`) toggles planet shuffle (`H.set_shuffle`). Off: `H.enabled()` is false (no
  arrival handling, no pending action, no auto return, no story ladder, hub keys answer "planet
  shuffle is off"), `14 T.active()` is false (no send-back), `H.take_back_world`. On: `apply_world`
  at the hub when nothing runs. Stored as `state.planet_shuffle_off` (saved by the companion, kept by
  `R.reset_for_new_game` and the test reset); a press before the companion's restore wins
  (`H.after_restore`). Destinations still finish and pay while it is off (no trip back).
- 15: `apply_world` records the travel byte as its own only when it was off before (`r.before ~=
  1`), and `H.on_arrival` drops the record at every planet change (a load sets the save's own
  values), so turning shuffle off never turns off the game's own travel.
- 09: `G.restore_inventory(why)`: every weapon and gadget with status confirmed / owned / failed is
  queued again with `restoring`; an answer adds it back ("Given back: ..."), no answer or "inventory
  changed, nothing new" keeps it owned quietly (no tries, the target is not questioned).
  `G.watch_inventory` / `G.check_inventory`: 420 game frames after the hub's own trip lands, a
  same-planet warp, or a load on another planet with nothing running, fewer reported weapons
  (WeaponAddedEvent since the planet change) than half of the weapons known as yours (at least 2)
  restores. `restore_inventory = false` turns the check off. `Ctrl+0` twice restores by hand.
- 10: `key_shuffle = "0"`, `restore_inventory = true`; RANDO-KEYS lists `planet shuffle 0`; banner
  `Randomizer v0.54 (kit 10.0.5)` (`R.RELEASE`).
- 12: the id loop yields every 256 bytes (was 512); a failed pointer layout's reason is kept in the
  log next to the inline one; the first slot object's bytes are logged once when no slot object
  holds a vendor weapon.
- Kit 10.0.5; generator stays 10.0.2 (seeds and fingerprints unchanged).
- Tests: tests/test_v054.py (22); 13 of them fail against v0.53's scripts. test_v051's way-home test
  calls `H.go_home` (the key no longer does).

## 10.0.4 / Public Release v0.53 (2026-11-13): the boss fight's shifts find planetary travel off

Reported (round 25, v0.52's first run, tests/data/round25_rivet.log, seed pocket-pocket-zurkie-839,
a restored save at nefcity_1): Nefarious City's boss fight sends Ratchet to Sargasso or Savali in
the middle of the level; with the randomizer Ratchet landed **with the ship**, on ground that was not
solid, fell and died, several times. **Nothing of v0.53 has run in the game.**

Round 25, what the log shows:
- The city's story ran (OBJ_NEFCITY_SKIDD_*, ROOFTOP_*, BAZAAR_RETURN, TOWERPATH_*) to
  CHK_NEFCITY_HEAVY_FIGHT; then the story's own rift: PlanetChangedEvent Savali,
  CHK_NEFCITY_HEAVYSHIFT_SAVALI, "arrived on savali during nefcity_1 - the story's own travel".
- Before it, on arriving in the city, the hub had run H.apply_world: `planetary travel: done (0x0 ->
  0x1)` and `level bits 0x0 - unlocking 1-10`. After every death the city loaded again (the load
  clears both, `0x0`), the hub turned the byte on again 180 frames later, and the next shift came:
  three shifts to Savali, each with the byte on.
- The hub also announced "Nefarious City: 2 destination(s) open" on every return.

Cause (inference): the travel byte is SetPlanetaryTravelAction's, all planetary travel on or off.
The game has it off during the city's story (Ratchet has no ship yet); with it on, the shift's
planet change was played as a ship arrival at a spot whose ground the shift does not load. The
level bits (UnlockLevelAction's mask) are also set by nothing in the game at that point.

Changes (15_rando_hub.lua):
- `H.running()`: the destination being played (current, not done).
- `H.apply_world(why)`: does nothing while a destination runs (`planetary travel and level bits
  left to the game while <id> runs`). It records what it turned on in this session
  (`H.session.world`: the byte, each level bit it set).
- `H.take_back_world(why)`: the byte off and the recorded level bits cleared; called by
  `H.launch_dest` for the hub's own story (`/`, `Ctrl+]`), which is played on the planet you are on
  without a load that would clear them. A New Game forgets the record.
- `H.finish`: when the hub's own story finishes on the hub planet, `apply_world` runs (the ship's
  menu works again); returning from elsewhere runs it through `at_hub` as before.
- `H.on_arrival`: back on the hub planet from another planet, with the hub's story running and no
  trip of ours: `back on <hub> from <planet> during <id> - the story's own travel`, no hub message.
- Kit 10.0.4; generator stays 10.0.2 (seeds and fingerprints unchanged).
- Tests: `tests/test_v053.py` (8): the round 25 evidence, the shift and the return, a reload, the
  finished story, the relaunch take-back, the settings. Against v0.52's 15_rando_hub.lua five of its
  six simulator tests fail. test_v100's hub-start test now expects the byte off while the story runs.

Not changed, still open from round 25: the shop (`only 0 vendor weapon(s) in the array at +0x48`,
its weapons given directly). Round 25 is a restored save, so the opening's name is still not in a log.

## 10.0.3 / Public Release v0.52 (2026-11-13): Nefarious City's story starts at its opening scene

Reported (round 24, v0.51's first run, tests/data/round24_rivet.log): the first Nefarious City
mission did not start. Asked for: warp to the city's opening cutscene, so the cutscene then the
gameplay play. **Nothing of v0.52 has run in the game.**

Round 24, what the log shows:
- The warp came after the parade handed Ratchet back, MIS_NEFCITY_01 went inactive -> available ->
  active, the warp landed at CHK_NEFCITY_START, and OBJ_NEFCITY_GO_TO_NEFCITY went to 1. It never
  went to 2: not after the 20 s reload, not after three presses of `/` (6 warps, all to
  CHK_NEFCITY_START). Bolts and Raritanium were picked up after the warp, so Ratchet could move
  (v0.51's walking fix held).
- Round 23 (the game's own order, lines 703-729): MIS_INTRO 2 -> 4; MIS_NEFCITY_01 0 -> 2 and
  MIS_NEFCITY_01_TRAINSTATION 0 -> 1 in the same frame; the rift to NefCity; checkpoint hash
  **3046787773**; only then CHK_NEFCITY_START. In round 24 hash 3046787773 never triggered, the
  train-station mission was never opened, and the prologue was written complete only after the
  story started. CHK_NEFCITY_START is where gameplay picks up after the arrival scene, not where the
  story begins.
- The name of hash 3046787773 is in no log: round 23 had no catalog, and in round 24 nothing
  triggered that checkpoint, so no RANDO-CHECKPOINT line names it. An offline search of 528 million
  name candidates found no plausible name.

Changes:
- 03: `C.OPENINGS.nefcity_1 = { hash = 3046787773, codes = { "NEFCITY", "NEF_" }, with = {
  "MIS_NEFCITY_01_TRAINSTATION" } }`. Not in the seed's hub plan: seeds and fingerprints are
  unchanged (round 24's seed is still 2a5550ece053).
- 14: `T.find_hash(hash, filters)` names a hash from `rivet.checkpoints()` lists; the checkpoint
  catalog also runs for every hub seed.
- 15, hub start (and `Ctrl+]` / `/` for the city's story): the prologue is written complete first
  (`hub_prologue_timing = "before"`; `"after"` is v0.51's order); the story is made available and
  started; inactive `with` missions are made available; then the warp goes to the opening, found by
  its hash (known names, then the codes, then up to `H.OPENING_WAIT` = 900 frames for the catalog).
  If the game does not list it, the warp goes to CHK_NEFCITY_START as in v0.51 and the city's
  catalog is logged.
- 15, watching: a story loaded at its opening gets `H.OPENING_STUCK_WAIT` = 3600 frames before one
  reload, at the opening again (20 s could cut a cutscene short). The opening is used only while the
  story's first mission has no step yet or waits at its GO_TO step; after that, `/` loads
  CHK_NEFCITY_START as before.
- 15, logging: `opening of nefcity_1: <name> (hash ...)`, `opening of nefcity_1 loaded: ...`,
  `with nefcity_1: ...`, and every objective of the current destination's missions
  (`RANDO-HUB objective ...`; RANDO-DISCOVER stops after `discovery_cap` lines of a kind).
- 10: `hub_prologue_timing` (`"before"` | `"after"`) and `hub_opening` (`true` | `false`). 04: both
  as commented lines; your values are unchanged.
- Kit 10.0.3 (every RANDO_FILES tag, R.KIT_VERSION, C.VERSION, TT.VERSION); generator G.VERSION stays
  10.0.2.
- Tests: `tests/test_v052.py` (15): the round 23/24 evidence read from the logs, the opening path, a
  control that reproduces round 24 with `hub_opening = false`, the fallbacks, the timings. The
  simulator's opening name (`CHK_NEFCITY_OPENING_SIMULATED`) is a stand-in. test_v100's
  `hub_game` keeps its old rule (the story moves on at CHK_NEFCITY_START) as the fallback model; the
  intended order change is updated in test_v100 and test_v051.

Not changed, still open from round 24: the shop (`only 0 vendor weapon(s) in the array at +0x48`,
ARSENAL_RESTORED's vendor config, and a frame-budget overrun at 12_rando_shop.lua:210, so its
weapons were given directly) and Glitch (never confirmed by the game).

## 10.0.2 / Public Release v0.51 (2026-11-13): the hub is Nefarious City

Asked for: the hub in Nefarious City; its story must work after the warp there; Ratchet must be
able to walk right after the warp (he could not in 10.0 / v0.5). Versioning from now on: a small
fix +0.01 (this one), a major update +0.5. **Nothing of v0.51 has run in the game.**

- 03: `HUB_PLANET = "nefarious_city"`, `HUB_CHECKPOINTS = { CHK_NEFCITY_START, CHK_NEFCITY_SHIP }`,
  `HUB_STORY = "nefcity_1"`, menu order `HUB_MENU`. `HUB_START` keeps 10.0's order, so placements
  are unchanged (test_v05 compares hub seeds with 10.0 field by field, apart from the hub plan's
  planet, checkpoints and each destination's kind and label).
- 15, start: the story is made active (hero, available, start), then the warp to CHK_NEFCITY_START
  (round 23's order). The prologue is written Complete Finished once on Nefarious City
  (`hub_prologue = "end"`, as kit 8.0 did in round 17), quietly: it pays, with no return trip.
- 15, when: `hub_trigger = "parade"` waits for OBJ_INTRO_GOING_DOWN to finish (round 23: the game
  answered nothing sent to the hero during it, and 10.0 warped right at its start) and for no
  *GOING_DOWN* / *CINE* / *CUTSCENE* objective for 120 frames; 1800 frames after the wrench it goes
  anyway.
- 15, home: START while the city's story is unfinished, SHIP after it. A warp home on the hub planet
  itself no longer waits for an arrival that never comes. No return trip when the game's own travel
  has already brought you to the hub.
- Simulator: the wrench starts GOING_DOWN; `S.parade_release()`; SIMULATED rule `S.hero_held`.
- Tests: `tests/test_v051.py` (15); test_v100 rewritten for the new hub. 356 run, 0 failures.

## 10.0 (2026-11-13): the hub, planet shuffle, spread rewards, shop split from rewards

Asked for: working planet shuffle (on by default), a hub start with the prologue / Battle Arena /
Nefarious City to choose from, better reward distribution, and no weapon both earnable and for sale.
Built on 9.0 (your 8.5.2 values stay the baseline). **Nothing of 10.0 has run in the game.**

### Round 23 (9.0, your log)
- The 9.0 story start worked in game: the parade, then Nefarious City, then Sargasso, then the planet
  menu to Zurkie's. Zurkie's first visit was played; it opened `MIS_BLIZAR` and `MIS_SAV_01`.
- Planet shuffle never did anything: `campaign planet_shuffle: not available yet (missing
  mission_control, travel)`. 9.0's director waits for the lab's "verified" lines, and those had never
  been written, although round 17 had already shown the mission writes working. So the game's own
  order ran.
- The shop ran past the 8 ms frame budget again (`12_rando_shop.lua:98/182`), so the vendor was
  never changed. With ARSENAL_RESTORED's vendor still selling its weapons, Fusion Grenade and
  Combuster were bought **and** given by the randomizer.
- Armor pods, Gold Bolts and missions paid mostly Bolts/Raritanium (`rewards 10/77`).
- New finding: `CheckpointHash` is the engine's CRC-32 of the checkpoint's name (29 names your game
  listed match hashes in rounds 13-23). Round 23 shows the game loading `CHK_NEFCITY_START`
  (2052464476) for Nefarious City's story. 8.x warped to `CHK_NEFCITY_SHIP` instead, and the story
  never left `OBJ_NEFCITY_GO_TO_NEFCITY` there.

### The hub and planet shuffle (`hub = true`, the default)
- `15_rando_hub.lua` (new, 10.0): New Game → Zurkie's at the parade's wrench (round 17's verified
  warp). The prologue is left **active** and is one of three start choices, with the Battle Arena
  (`MIS_ZURK_01_VISIT_01`) and Nefarious City. `]` / `Ctrl+]` choose and go.
- A launch confirms the hero, then runs the mission ladder (active / start / write "available" then
  start, as in round 17 / replay / explore). Then it warps to where the mission really starts:
  `CHK_NEFCITY_START`, `CHK_ZURK_00_DEFAULT`, the parade's own checkpoint, or a start learned from an
  earlier run. A story still at its "go to" step after 20 s is loaded once more **on the same planet**
  (8.4 went out to Zurkie's and back, and round 22 crashed right after that).
- Planet shuffle: every other destination opens with its planet's Coordinates (items of the seed,
  anywhere) and its dependencies. The solver's reach is a fixpoint over the visits, so any order you
  pick can be finished. A finished destination pays its locations and returns you to Zurkie's. The
  game's own follow-on travel (Nefarious City → Sargasso, the prologue → Nefarious City) is undone
  (`[ORDER KEPT]`; `hub_follow_story = true` plays along instead). Round 23 shows the prologue
  turning complete on Ardolis *before* the game rifts to Nefarious City, so the warp home waits for
  the new planet's first loaded checkpoint (or 15 s), not a fixed delay after the arrival event.
- The planet menu: a locked planet sends you back to Zurkie's; an open planet starts its next
  destination. Revisits are in the `]` list.
- `14_rando_travel.lua`: every triggered checkpoint is named (`RANDO-CHECKPOINT`). The engine hash is
  in Lua, and every catalog name is hashed.
- The director (`11`) stays inert for hub seeds. `hub = false` gives 9.0's story start, unchanged.

### Rewards spread (`distribution = "spread"`, the default)
- Progression (Coordinates, gadgets) goes anywhere in logic, with no late bias. `early_weapons` (2)
  weapons and one Coordinates go where the start can reach. Everything else is shared over Gold
  Bolts, story missions, side activities and armor pods in proportion. Gold Bolts may now give
  currency; the game's own Gold Bolt still counts. `"goldbolts_first"` is the 4.0-9.0 fill.
- Over 200 default seeds, every kind of location holds items in more than 30% of its slots, and
  armor pods hold weapons.

### Shop vs rewards (`shop_weapons = 8`)
- Each weapon has exactly one route. Ms. Zurkon sells `shop_weapons` different weapons; her other
  normal slots are closed (they show the Burst Pistol, which every save owns). ARSENAL_RESTORED's
  weapons are never sold. Any slot of the vendor (ARSENAL_RESTORED's, Challenge Mode's) that sells a
  weapon the seed gives elsewhere, or that another slot already sells, is closed too.
  `shop_close_slots = false` keeps those slots.
- Frame budget: hex is parsed with one `gsub` and a lookup table plus `string.byte` (no Lua loop per
  byte). Reads are 256 bytes, a slice yields after 2 ms, and a budget error halves the read size
  instead of counting as a failed try.
- With too few locations switched on, a leftover weapon starts with you instead of having no route
  (found by the batch with random settings).

### Seeds and files
- Generator 10.0.0, format 10, share code `RA10` (RA4-RA9 refused with the reason). New settings:
  `hub`, `distribution`, `shop_weapons`, `early_weapons`. A hub seed forces `planet_locks`,
  `travel_lock` and `campaign_mode = planet_shuffle`, with a note.
- The kit has 14 scripts again. `04_rando_settings.lua` is your file plus the 10.0 lines.
  `rando_give.dll` v6 is unchanged.

### Tests
- `tests/test_v100.py` (39 tests): an independent hub-seed verifier (sphere walk, routes, early
  rewards) over 600 preset seeds and 300 random-settings seeds; distribution and order statistics;
  audit mutations. Simulated: the start menu, each of the three starts, planet shuffle, the planet
  menu, learned starts, whole campaigns (with missing missions too), the shop's closed slots,
  parse speed, budget errors, round 23's real event stream (the hub starts at the wrench), and
  round 13 (it never starts).
- The older suites run with `harness.PRE10_SETTINGS` (no hub, Gold-Bolts-first, 15 shop weapons).
- `big_batch`: 56,600 / 56,600 seeds valid (BATCH_10.0.txt).

## 9.0 (2026-11-12): no hub; the story starts as in the game

Asked for: a version without the Zurkie's hub, starting with the prologue, then Nefarious City.
Built on your edited 8.5.2 scripts (01-06, 09), which are the baseline: your defaults in 02
(`planet_locks = true`, `campaign_mode = "planet_shuffle"`, `shop_prices = "weapon"`, Raritanium
120-1,000) and Punk/Reaver owned from the start are unchanged.

### Removed: the Zurkie's hub (8.0-8.5)
- `15_rando_hub.lua` is gone. A New Game is no longer taken to Zurkie's: the parade plays on, the
  game's own rifts take you to Nefarious City, and finishing its story takes you to Sargasso. The
  randomizer moves you nowhere, writes no mission state, sets no level bits or travel flag, and
  swaps no hero. Round 22's crash followed a warp to `CHK_NEFCITY_SHIP` with the story primed from
  Cordelion (the probable cause, not proven); 9.0 makes no warp of that kind.
- Presets `hub` and `hub_chaos` are retired: they become `balanced` and `chaos`, with a note. The
  seed is then identical to the replacement preset's.
- Seed settings `hub`, `hub_start_coordinates`, `hub_unlocks`, `hub_finale`, `hub_revisits` and
  in-game options `hub_*`, `key_hub`, `key_hub_return`, `story_on_arrival`,
  `story_prime_before_travel`, `story_reload_stuck`, `key_story` are retired. Each one still in a
  settings file is named in rivet.log (`... is gone in 9.0`) and ignored.
- The story-on-arrival starter, the hero checks and the story reload lived in the hub script and
  are gone with it. Test travel (`test_travel = true`) now only moves you.
- The kit check reports a leftover `15_rando_hub.lua` from an older kit (rivet.log and on screen).
  With a 9.0 seed that file does nothing (all of it waits for a hub plan), but it binds the old keys.

### The story's start is fixed in every mission order
- `03_rando_campaign.lua`: `C.STORY_START` = the leading visits the game itself travels to
  (`arrival = "story"`): `corson_intro > nefcity_1 > sargasso_1`. Every order of every mode
  (`planet_shuffle`, `mission_shuffle`, `full`, `chaos`) begins with them; only later visits move.
- `random_start` (a campaign beginning elsewhere) is retired; `full_campaign` and `campaign_chaos`
  keep their mission shuffle with the fixed start. No mode needs `new_game_init` any more.
- The generator's audit checks the start of every campaign order.

### Seeds
- Generator 9.0.0, seed format 9, share code `RA9`. 4.0-8.5 share codes are refused with the reason.
  The generator version is in the fingerprint, so every 9.0 seed is new: start it with New Game.
- The kit's `04_rando_settings.lua` is your 8.5.2 file without its hub lines, with
  `preset = "balanced"` (your G.DEFAULTS as they stand). Your commented values are kept.
- The spoiler's hub section is replaced by a STORY START line.

### Tools and tests
- `tools/build_data.py` reproduces your 8.5.2 `01_rando_data.lua` byte for byte (Punk and Reaver
  are `findable = "start"`; their sources stay as filler-only locations, as in your file). Before
  this, re-running it reverted your edit. `data/game_db.json` matches.
- `tests/test_v90.py` (new): no hub anywhere; retired presets and settings; every mode starts with
  the prologue, Nefarious City and Sargasso; your 9.0 and 8.5.2 settings files; a New Game played to
  Sargasso with no warp, flight, mission write or hero swap; a leftover hub script reported and
  inert; the planet menu still locks planets with levels.
- The tests now pin the settings they were written for (`tests/harness.py`, CLASSIC_TEST_SETTINGS:
  no Coordinates, the game's own order, Raritanium 20-150) instead of relying on the defaults, which
  you changed in 8.5.1. A pinned value never overrides the test's own settings or its preset.
- Removed: `test_hub.py`, `test_regression_v83.py`, `test_regression_v84.py` (9.0 changes seeds on
  purpose), and the hub's story/hero tests in test_v81-v85.

## 8.5 (2026-11-12): robustness pass on 8.4

No round 21 log yet, so nothing here comes from a new game report: every fix comes from reading the
8.4 code, and each has a test in `tests/test_v85.py` that fails on 8.4 and passes on 8.5. Seeds are
identical to 8.4 (`tests/test_regression_v84.py`), saves carry over, rando_give.dll is unchanged
(same bytes as 8.3/8.4). Everything 8.4 still needs to prove in your game (KNOWN_ISSUES.md 1) is
unchanged.

### rando_give.dll requests that were given up on
- **A mission call that timed out stayed in the helper's mailbox.** If the helper then ran it
  (e.g. after a hitch), a story start or state write happened that the hub had already counted
  as failed and handled another way. 8.5 takes the request back first (the same as items and
  currency already did on a load). If the helper answered at that moment, its answer is used.
- **A loading screen counted as a timeout for mission calls** (5 s). Now a call waits while the
  game is loading and the helper's pump is not running, up to 60 s (item deliveries already waited).
- **An item request that got no answer was left in the mailbox too.** A helper that recovered
  later could deliver it on top of the retry. Now it is taken back, and the retry is the only give.
- **A New Game** takes back an item or currency payment of the old run that is still in flight, so
  it never lands in the new run.

### The companion's late restore (round 20: it connected a minute after the game)
8.4 merged only some of this session's progress into the restored save.
- Bolts/Raritanium paid in this session but not yet given are now kept (they were dropped).
- An item the game confirmed in this session is no longer reset to "queued" by the older save. That
  reset could make it be sent again.
- Armor sources and finds, the shop's one-time gifts, gadgets, the hub's objective record and the
  armor baseline are kept as well.

### New Game
- The hub's record of the old run (destinations already reloaded, stories started, the "back to
  Zurkie's" timer) is cleared. Before, a destination reloaded in the old run could not be reloaded
  automatically in the new one.
- The delivery's weapon-type session state (seen types, a purchase in flight) is cleared.
- Delayed hub actions (next mission, back to Ratchet, the hero record) look at the state when they
  run, not the state from when they were scheduled. A restore in between could make them use the
  replaced state.

### Ms. Zurkon's shop
- **Shop-only weapons had no route** when rando_give.dll was missing entirely, stopped working
  during the session, or never found the vendor in memory. The script's own description promised a
  direct gift in those cases. 8.4 only gave them for an older helper. Now all of these give the
  seed's non-vendor shop weapons once, as before.

### Smaller fixes
- A planet-menu landing on an open planet (levels seeds) is now saved right away and filtered like
  every other landing (never a `TRANSITION_TO` point).
- The history in memory is capped at 400-500 entries. The save already kept the last 60, and
  rivet.log keeps everything.
- **Companion:** a save file the game refuses (another seed's content under this seed's name) is
  copied to `rando_<fingerprint>.lua.refused-<time>` before a fresh start. Before, the next saves
  replaced it and its `.bak`, so the progress in it was lost.

## 8.4 (2026-11-12): stabilization after round 20

Built from round 20's rivet.log (kit 8.3, v2.618 install). Generator unchanged (8.0.0): every seed
is the same as in 8.3 (same fingerprint, same items; `tests/test_regression_v83.py`), so your saved
progress carries over.

### Stories that did not start, and Viceron played as Ratchet
- **Cause.** The hub trusted the hero remembered in the save (`rivet`) while the game had Ratchet.
  Every swap was then skipped ("no swap needed") or refused (`already playing as that hero`), and
  the visits ran with the wrong hero. A story's first step ("go to <planet>") finished at once with
  the visit's own hero (Ardolis, Savali, Zurkie's 1 as Ratchet) and never with the other one
  (Torren IV and Viceron as Ratchet in round 20, Nefarious City as Rivet in round 17).
- **The hero is checked with the game.** `rivet.hero_play_as` answers `already playing as that hero`
  exactly when the hero is the one asked for, so 8.4 asks again after each swap until the game
  confirms (up to 15 s). A story is started only after that. One swap request at a time.
- **Four heroes were wrong in the registry** and are fixed, from the walkthroughs and your logs:
  Nefarious City 1 → Ratchet, Sargasso 2 → Rivet, Ardolis → Ratchet, Viceron → Rivet.
- **The story is started before the trip** (`story_prime_before_travel`): a hub trip, or a test
  travel warp, switches to the visit's hero and starts its story first, so the planet loads with the
  story running (round 20: Savali, active before the warp, finished "go to" on landing).
- **A story still at "go to" 20 s after its start is reloaded once** (`story_reload_stuck`): out to
  Zurkie's (or, for Zurkie's own visits, another open planet) and straight back. Round 20's Viceron
  moved on after its reload. The story key `/` reloads again on demand.
- **8.3's automatic restart of an active story is gone.** In round 20 it changed the state but never
  moved a story (Cordelion, Zurkie's 2). Ctrl+/ twice still restarts by hand.
- **Entry points.** Viceron `CHK_ZORDOOM_START`, Cordelion `CHK_CORD_A_START`, Ardolis
  `CHK_ARD_START` (all listed by your game). A planet's story start (`CHK_<code>_START`) now ranks
  first in the checkpoint catalog; `..._COMMAND_SHIP` no longer counts as a landing.
- **Test trips no longer teach the hub a landing.** Round 20's hub trip to Torren IV went to
  `CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP`, a mid-mission point a round 19 test trip had left as
  "where you last landed". Only the ship's planet menu is remembered now; older saves' entries move
  to test travel's own list.

### Weapons
- **"weapon type 1002 ... 1012 is weapon:burst_pistol".** A load equips your weapon and then replays
  every owned weapon; 8.3 took all of them for the Burst Pistol. Now only a purchase teaches a type
  (in either event order), one type per weapon, never from a load's replay, and wrong lessons in a
  save are dropped at load. A load's replay counts as a late delivery answer only when it holds
  exactly one new type.

### Ms. Zurkon's shop
- **"only 0 vendor weapon(s) in the array at +0x48"**, every try of rounds 18-20. The vendor's slot
  list is an array of pointers to slot objects (rivet's DDL: `List<VendorItemData?>`), not of slots.
  8.4 reads the slot objects through the pointers; the old layout is still tried first.

### ARSENAL_RESTORED
- **The game itself now says the mod is installed** (Mr. Zurkon's item config loaded). Round 20's
  companion answered after the 60 s wait, so the seed was made without the mod's weapons although
  rivet_hook had loaded it. With `seed = "random"` there is no timer at all: the companion answers
  the check before it sends the seed.

### Robustness
- **Kit check.** Every script carries its kit version; the first frame logs `RANDO-KIT all 14
  scripts are 8.4.0`, or names missing files and files from another kit (on screen too).
- **The campaign key is silent in a hub seed** (round 20: the old F12 key, also Steam's screenshot
  key, put "Campaign order is not available yet" on screen).
- **rando_give.dll** is unchanged (v6, the binary rounds 17-20 ran). Its build is now reproducible:
  `build.sh` pins the link time and rebuilds the shipped DLL byte for byte.
- **Settings.** New: `story_prime_before_travel`, `story_reload_stuck` (`story_restart_stuck` is
  retired; `false` there still switches the reload off). `test_travel` is now **off** in the kit's
  settings for a real playthrough.

### Tests
- 318 automated tests, 0 failures (17 skipped: PowerShell 7 and pre-8.3 git history unavailable on
  the build machine). New: `tests/test_v84.py` (31), `tests/test_regression_v83.py` (175 seeds in 7 presets against 8.3).
- 43,000 seeds valid (`BATCH_8.4.txt`). Strict-global audit of the scripts: no stray globals.

## Randomizer 8.3: the story starts where you land, and keyboard keys

8.3 is 8.2 plus two changes from your round 19 log. Your seed and progress carry over: the
generator is still 8.0.0. Nothing here changes a fingerprint. None of 8.3 has run in your game yet.

### Why the story didn't start (round 19)

1. **Test trips did nothing by design.** In 8.2, a test trip only reported the landing. The
   Viceron, Torren IV and Cordelion landings started nothing.
2. **Cordelion's story was already "active" but stuck.** `MIS_CORD_01_FIRST_VISIT` was active
   from an earlier session, so the hub left it alone (`already active`, line 628).

The round 17 log shows why an active story can sit still. Each story mission's first objective
is "go to <planet>":

- `MIS_ZURK_01_VISIT_01` was started while you were at Zurkie's. `OBJ_ZURK_01_GO_TO_ZURKONS`
  finished 2 seconds later, and the whole story played through the arena.
- `MIS_NEFCITY_01` was started from somewhere else. `OBJ_NEFCITY_GO_TO_NEFCITY` never finished,
  even after you got to Nefarious City.

So the "go to" step is checked once, when it starts, by the planet's own level. A story started
on another planet never moves.

### What 8.3 does

- **The story on arrival** (`story_on_arrival = true`). Landing on a planet starts that planet's
  first unfinished story, even if the story before it isn't finished. This covers test travel,
  the ship's planet menu and hub trips. The hub's order is ignored for this. The story is started
  through the same ladder as before: make it available (the v6 record write) if it is inactive,
  then the game's own start, then the replay call. Rivet's stories swap the hero to Rivet first.
  Zurkie's is still the hub: its story starts with the story key or the hub key.
- **Stuck stories are restarted** (`story_restart_stuck = true`). An active story whose last step
  is "go to <planet>", or with no step seen yet, is started again on its planet: available, then
  start. If the game refuses, the record goes back to active and the replay call is tried. A
  story you are in the middle of is left alone.
- **The randomizer remembers each mission's last step** (from `ObjectiveStateChangedEvent`). This
  is saved with your progress.
- **20 seconds after a start,** if the story is still at "go to", the screen tells you to press
  the story key.
- **The story key `/`** starts the story of the planet you are on. **Ctrl+/ twice** starts it again
  from its first step, even when it's running. That is written to the history.

### Keyboard keys

| Key | Does | Old key |
|---|---|---|
| `;` | status | F9 |
| `]` / Ctrl+`]` | next destination / go there | F6 |
| `[` twice / Ctrl+`[` twice | back to Zurkie's / finish this destination by hand | F5 |
| `.` / Ctrl+`.` | test travel: next planet / warp there | F7 |
| `,` / Ctrl+`,` | test travel: next landing point / fly there | F8 |
| `/` / Ctrl+`/` twice | start this planet's story / start it again | (new) |
| `'` | experimental mission order only | F12 |

- **Every key is a setting** in `04_rando_settings.lua`. A key name can be one character
  (`]`, `/`, `K`, `7`), `NUMPAD0`–`NUMPAD9`, `INSERT`, `DELETE`, `HOME`, `END`, `PAGEUP`,
  `PAGEDOWN`, or `F1`–`F24`.
- **The old F keys still work** while `legacy_f_keys = true`.
- **rivet.log lists the keys at start** (`RANDO-KEYS`) and logs every press (`RANDO-KEY`). If a
  key does nothing and has no `RANDO-KEY` line, the game didn't pass it on. Pick another key.
- **If rivet_hook's key numbers aren't Windows key codes,** the keys go back to the F keys, with
  F4 for the story key. A `RANDO-SETTINGS ... cannot be bound here` line says so. The check is
  `rivet.key("F6") == 0x75`.

### Also seen in round 19, not changed

- **rivet_hook said `game version mismatch, invalidating pointers`** (line 3). Round 18 didn't.
  Everything still worked: events, warps, flights, deliveries. If the game updated, keep an eye
  on it.
- **The companion answered late.** The seed was made before it answered, so ARSENAL_RESTORED
  counted as not installed. That gives `kit-bolt-kit-198` → `b25846f17df5`, not round 18's
  `4d170014c0c6`. The two have separate progress files. Start the companion before the game.
- **The shop:** ARSENAL_RESTORED replaces Ms. Zurkon's config (0 vendor weapons at +0x48), as in
  round 18.

### Tests
- 285 run, 0 failed, 17 skipped: 9 need PowerShell, and 8 need the 5.0/6.0 git history.
- New: `tests/test_v83.py` (23 tests) and `tests/data/round19_rivet.log`.

## Randomizer 8.2: test travel, and the round 18 checkpoint catalog fix

8.2 is 8.1 plus two things. Your seed carries over: same generator (8.0.0), same fingerprint
(`kit-bolt-kit-198` → `4d170014c0c6` with ARSENAL_RESTORED), same saved progress. None of 8.2 has
run in your game yet.

### New: test travel (docs/TEST_TRAVEL.md)

F7 picks any planet, F8 its landing point, Ctrl+F7 warps there, Ctrl+F8 flies there with the
ship. While `test_travel = true`, nothing sends you back: not the hub, not locked levels, not
the planet menu. It opens no Coordinates. It's a runtime option, so the seed doesn't change.

### Fixed: the checkpoint catalog never finished (round 18)

| In the log | Cause | 8.2 |
|---|---|---|
| 11 × `14_rando_travel.lua:115 / 140 / 141 / 197: ran past the 8 ms frame budget`, and no `checkpoint catalog:` line | every checkpoint name was compared with every planet's every code; every sort comparison scored both names again; 128 names a frame, sharing the 8 ms with the shop and armor | codes are a table lookup per name token; areas and scores are worked out once per name; a slice stops after 1.5 ms; the best landing point is a linear pick, not a sort |

A test checks that every checkpoint name in your logs (rounds 13-18) gets the same planet as in
8.1. Another fills the catalog with 2,100 extra names and checks that it completes.

### Seen in round 18, not changed in 8.2

- **Shop:** `only 0 vendor weapon(s) in the array at +0x48`. ARSENAL_RESTORED's .stage replaces
  `configs\vendor\ven_weapon_vendor.config` (round 18 line 260), so the vendor's list isn't where
  the shop script looks. After 5 tries the shop gave you the seed's extra shop weapons directly,
  as designed.
- **Armor:** `13_rando_armor.lua:117` and `:256` ran past the frame budget, once each.
- **Pixelizer** was sent 4 times with no answer from the game.
- **This save has the whole story done** (every destination mission reads `complete`). On this
  save, hub destinations finish as soon as you arrive. Test travel is the way to try the travel
  here.

### Files

- `scripts/16_rando_testtravel.lua` (new)
- `scripts/14_rando_travel.lua` (catalog; no send-back during test travel)
- `scripts/15_rando_hub.lua` (`H.check_levels`; no send-back, keeper or startup guard during test travel)
- `scripts/10_rando_runtime.lua` (settings `test_travel`, `key_test_travel`, `key_test_point`; F9 status; KIT 8.2.0)
- `scripts/04_rando_settings.lua` (test travel on, keys F7 / F8)
- `tests/test_v82.py` (15 tests), `tests/data/round18_rivet.log`

## Randomizer 8.1: fixes from your round 17 log

8.1 is 8.0 plus fixes for what your round 17 rivet.log showed. That log came from the install
that worked (the folder named Ratchet.and.Clank.Rift.Apart.v2.618). Your seed carries over: same
fingerprint, same plan, same saved progress. None of 8.1 has run in your game yet.

### What the log showed, and what changed

| In the log | Cause | 8.1 |
|---|---|---|
| `09_rando_real.lua:672: attempt to call a nil value (global 'u32_at')` on every planet change | the line called a local defined 120 lines below it | fixed; a test now checks every script for this kind of mistake |
| `travel to torren_iv impossible: no checkpoint known` (Cordelion too) | Torren IV and Cordelion have no checkpoint named LANDING / SHIP / DEFAULT, and Cordelion's tunnel is called KEDARO, not CORD | **checkpoint catalog** (below) |
| 440 × `12_rando_shop.lua: ran past the 8 ms frame budget`; the shop never changed | the vendor search read up to 16 KB of memory and scanned it in one frame; a failure was retried forever | the search runs a slice per frame (2 reads); it gives up after 5 failed tries and hands out the shop's extra weapons instead |
| levels `unlocked 0x0` after a reload (was `0x7FE`) | a save load resets the level mask; 8.0 only set it at Zurkie's | the level bits are put back on whichever planet you load on |
| `MIS_BLIZAR_01 / MIS_CORD_BOSS / MIS_ZURK_02 / MIS_SARG_02_REVISIT / MIS_MEGA_01_RIVET: not a mission in your game` | guessed names | replaced by names your game has: MIS_BLIZAR, MIS_CORD_01_FIRST_VISIT, MIS_ZURK_02B_VISIT_02B, MIS_SARG_02_REVISIT_SHIPS, MIS_MEGA_FINALE |
| Blizar and Savali chosen in the ship's menu sent you back to Zurkie's | no Coordinates for them yet (by design) | unchanged; the message names the reason |

### The checkpoint catalog (Torren IV, Cordelion and the rest)

`rivet.checkpoints()` lists the level's checkpoints with the **area** each one is in. Round 17
shows these areas: Zurkons, Sargasso (open world), Blizar_Intact, Blizar_Destroyed, Zordoom,
Megalopolis (open world), and interplanetary_space for the planet tunnels.

From about 10 seconds after the game starts, the randomizer fills a catalog. It runs one name
filter every 4 frames, and the last filter lists everything. Each checkpoint goes on a planet by
its area first and its name second. Planet tunnels (CHK_TRANSITION_TO_…) go on none. Each
checkpoint gets a score:

- landing pad 100, landing 90, ship 80, default 70, arrival 45, entrance 40, start 35;
- −60 for each of: cinematic, boss, finale, arena, challenge, return, escape, post-mission,
  teleporter, warp-back, tunnel.

The best one is where the hub warps. rivet.log prints the result once:

    RANDO-TRAVEL checkpoint catalog: corson_v 31=..., torren_iv N=CHK_..., cordelion N=CHK_..., ...

If a trip is asked before the catalog is complete, it waits ("looking for a landing point…"),
for 30 seconds at most.

If a planet still has no checkpoint, the hub says: *"no warp point known for X yet - fly there
from the ship's planet menu"*. Every planet is in that menu (the level bits). A menu landing on a
planet you hold Coordinates for starts its destination as before, and its landing checkpoint is
**remembered**, so the next F6 / Ctrl+F6 trip there works.

Not known yet: whether the catalog's choice for Torren IV and Cordelion is a sensible place to
land. The log line above shows what was chosen, and the menu fallback always works.

### ARSENAL_RESTORED, rivet_hook version

rivet_hook loads loose mods **only** from the paths listed under `[assets] paths` in rivet.toml.
The randomizer's 8.0 rivet.toml listed only `mods/default` (your log: *mod path mods/default does
not exist! skipping*), so a copied ARSENAL_RESTORED folder was never loaded. The companion also
only looked for the Overstrike install, so its weapons stayed out of the seed.

8.1:

- **rivet.toml** lists `mods/ARSENAL_RESTORED` (a folder with info.json) and
  `mods/ARSENAL_RESTORED.stage`. A path that isn't there is skipped, so nothing breaks without the
  mod.
- **companion\Install-ArsenalRestored.bat**: drag the mod's zip onto it. It:
  - copies the mod folder (the one holding info.json) or its .stage into `<game>\mods\ARSENAL_RESTORED`;
  - copies the mod's own .lua files into `<game>\scripts`, never over a randomizer file;
  - adds the path to rivet.toml (the old one is kept as rivet.toml.bak).
- **The companion** finds the rivet_hook version through rivet.toml. If the mod sits in mods\ but
  isn't listed, the companion says so.

The zip itself was not available to this build (Google Drive can't be reached from the build
machine). The installer handles the usual layouts, but it hasn't seen this one. If it says
"nothing copied", send the zip's file list.

### Tested here (offline, simulated game)

247 tests ran: 238 passed, 0 failed, 9 skipped (the PowerShell tests: no PowerShell on the build
machine). 16 of the tests are new in 8.1 (tests/test_v81.py).
The new tests cover:

- the catalog against the 70+ checkpoints your round 17 log listed, placing each on the right
  planet;
- simulated Torren IV and Cordelion trips;
- a trip waiting for the catalog;
- a remembered menu landing;
- level bits put back after a load;
- the shop search spanning frames with at most 2 reads each;
- a failing vendor stopping after 5 tries;
- the registry and the rivet.toml paths.

PowerShell changes (companion detection, installer) are **untested**.

