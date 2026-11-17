# Known issues (Randomizer 10.0)

9.0 has passed every automated test, but it has **not run in your game yet**. Everything below
comes from your logs of rounds 13-22, from the code, or from the simulator. Each item says which.
Use this page to tell a known issue from a new one.

## 0n. Since dev 10.22 (kit 10.0.16): still NO enemy is randomized in the game

- NOT FIXED. Your dev 10.21 log (tests/data/round32_rivet.log): dev(spawnproof) v1 never armed ("0
  regular-enemy template(s) learned" every time). REASON (real bytes): the arena's enemy nodes have no Template
  variable; they spawn through a "Factories" variable (a SunsetSpawnerFactory node), cached at Spawner +0x48.
  All Template nodes on Zurkon spawned rift portals. v1 also lost work to the 8 ms frame budget.
- dev(spawnproof) v2 swaps Factories (and Templates); TESTING.md 2-dev9. Unproven in the game.

## 0m. Since dev 10.21 (kit 10.0.16): still NO enemy is randomized in the game

- NOT FIXED. No in-game replacement has happened yet; 0l still holds.
- LEAD (your dev 10.20 log): spawner nodes take their template from a script VARIABLE ("Template", actors)
  and report spawns in "LastSpawn". dev(spawnproof).lua tests it with ONE replacement on Zurkon; it needs
  the developer rando_give.dll v7 (rando_give_source/dev_build). TESTING.md 2-dev8.
- FIXED (developer files): dev(spawnprobe) lost PlanetChanged / Checkpoint events to rivet_hook's limit of
  64 event callbacks; developer files now listen through 16_rando_spawners.
- OPEN: rivet.script_nodes may return a short list when the frame budget runs out (the census listed 0
  nodes on Zurkon five times in your last log).

## 0l. Since dev 10.20 (kit 10.0.15): Enemy / Boss / Chaos Randomizers DO NOT WORK in the game

- NOT FIXED. Your rivet.log of 2026-11-17 with dev 10.19 (tests/data/round30_rivet.log): 17 censuses, every
  one "0 spawner node(s) read, 0 template(s)". Nothing was ever changed; the three switches have nothing to
  act on. This is true of every version since 10.12 (no census has read a node in any of your logs).
- PROVED by that log: node +0x60 is the handle of the node's Spawner component (6 of 6 dumped pairs; the
  SpawnerStoppedEvent carries the same handle). Neither the node nor its Spawner component keeps a Prius
  (ddlPriusData 0 in both). So 0k below was wrong to call 10.19 a fix: the Spawner component does not carry
  the Templates list where 10.19 looked.
- UNKNOWN: where a running encounter's Templates list is in memory. Not guessed again: dev(spawnprobe).lua
  (developer file, read-only) collects it in one play session. TESTING.md "2-dev7".
- FIXED (diagnostics only): dumps were cut at 1024 characters a line (rivet_hook's log buffer); zero-filled
  memory was reported as "factory-only spawner (no Templates)".

## 0k. Since dev 10.19 (kit 10.0.14): the node's Spawner component

- WRONG (see 0l): 10.19's premise was refuted by the next log; nothing was fixed.
- "FIXED" as written then (your rivet.log of 2026-11-17, dev 10.18): still nothing randomized. Its dumps show the node keeps
  no Prius; it keeps the handle of its Spawner component at +0x60. 10.19 reads that component's Prius.
  ENEMIES_AND_BOSSES.md section 6. Simulator only (modelled on the dumps).
- FIXED: a node stopped by the frame budget is read again (the census was restarted from scratch).
- OFF: the level-wide Spawner component scan (it ran past the frame budget every time).
- OPEN (needs the game): the Spawner component on the node's own actor (else
  `spawner component of ... not found` lists what is there); `verify ... TOOK EFFECT`.

## 0j. Since dev 10.18 (kit 10.0.13): the Prius reached by hand

- FIXED (your rivet.log of 2026-11-17, dev 10.17): still nothing randomized. Every node "no Prius and the
  instance is only 128 bytes": rivet_hook gives no `prius` for script actions. 10.18 follows
  `ddlPriusData` -> holder -> data itself (then pointers in the node, then a bounded deep search), and
  learns templates from their template actors. ENEMIES_AND_BOSSES.md section 6. Simulator only.
- FIXED: a census still running when the level changed could publish the old level's nodes.
- FIXED: a spawner that spawned before the census read the level (at the load) counted as idle and could
  be changed mid-fight; it now counts as started (Enemy / Boss leave it alone; Chaos still changes it).
- CHANGED: Chaos uses another planet's template only where its template actor is loaded (CHAOS.md).
- LIMIT (by design): enemies a level spawns the moment it loads are there before any script can read the
  level, so their first wave keeps its enemies; later waves, later fights and the next loads change.
- OPEN (needs the game): `verify ... TOOK EFFECT` on a changed fight (the engine reading Templates at each
  spawn). Not touched: the vendor array, RANDO-OMEGA inventory, the old `16_rando_testtravel.lua` in your
  scripts folder (delete it).

## 0i. Since dev 10.17 (kit 10.0.12): the spawner census reads the Prius

- FIXED (your rivet.log of 2026-11-17): the Enemy, Boss and Chaos Randomizers changed nothing. Every
  census read 0 spawner nodes ("cannot read the node"): the fields are in the node's Prius, not in its
  small instance. 10.17 reads the Prius (`layout prius +0x8` in the census line). Simulator only.
- FIXED: a census stopped by rivet_hook's 8 ms frame budget (that log: `16_rando_spawners.lua:542/437`)
  was dropped until the next checkpoint or planet; it now starts again (up to 5 times).
- NEW (fallback): a spawn whose event has no sender is matched to its node by its SpawnLocation.
- OPEN (needs the game): whether a Templates write in the Prius changes what the node spawns (the node
  may copy its Prius when it starts; then only nodes not started yet change, which is what is written);
  the bot class names `rivet.components` returns for spawned enemies.
- Ms. Zurkon's vendor (`only 0 vendor weapon(s) in the array at +0x48`) and `RANDO-OMEGA inventory not
  found` in the same log are separate issues, not touched here.

## 0h. Since dev 10.15 (kit 10.0.11): Omega weapons

`omega_weapons` is off by default; nothing below matters while it is off. Nothing has run in the game
(OMEGA.md section 5).
- **The game's Omega flag is only written by `17_rando_omega.lua`, and only after it has learned its
  place** from two Omega purchases at Ms. Zurkon (Challenge Mode) or `omega_flag_offset`. Until then an
  Omega reward gives its weapon and is recorded as pending.
- **The inventory component's class name is a guess** (`ItemInventory`, then three others). If none
  answers, rivet.log says `RANDO-OMEGA inventory not found` and nothing is written.
- **If an Omega purchase reports no `PurchaseWeaponEvent`**, nothing is learned.
- Ms. Zurkon's own Omega upgrades stay for sale in Challenge Mode (their price fields are not located).
- 6 of the 20 Omega names are assumed (no guide lists them by name).
- Not in a player package (held back by the release builder).

## 0g. Since dev 10.13 (kit 10.0.9): Chaos Randomizer

OFF by default. **By design it can make a run impossible** (CHAOS.md): encounters that never finish,
unbeatable bosses and broken story steps are expected while it is on, not bugs. To recover:
BACKSPACE (Chaos OFF), then load the last checkpoint.
- **Templates from other planets** (`chaos_cross_planet`, on by default) may not be loaded where they
  are used. What the game does then has never been seen: nothing, a wrong spawn, or a crash.
- **BACKSPACE** has not been tried in the game as a rivet_hook key. If the game uses it or never
  passes it on, set another `key_chaos` in 04.
- Spawner-driven non-combat scripts (Clank puzzles) can break until their templates are learned as
  friendly.
- Not in a player package (held back by the release builder).

## 0f. Since dev 10.12 (kit 10.0.8): Enemy and Boss Randomizer

Both are OFF by default; nothing below matters while they are off. Nothing of them has run in your
game (ENEMIES_AND_BOSSES.md, TEST_REPORT_10.12.md).

- **The Templates list's place in memory comes from the DDL**, checked by a signature at run time. If
  your game lays it out differently, every node is `skipped` in rivet.log and nothing is changed.
- **Learning needs `rivet.component` to answer for spawned actors** with the DDL's bot classes
  (`GameBotShooter`, `GameBotMeleeFlier`, ...). If it does not, nothing is learned and nothing changes.
- **A fresh save changes nothing on a planet until its enemy types were seen once.** Learned types
  are saved and kept over New Game.
- **Story bosses are never randomized** (their fights are scripted for that boss); their areas put
  every change back while you are there (checkpoint names with BOSS / FINALE / HEAVY_FIGHT / CHASE;
  a boss area named otherwise is not recognised, the other safety nets still apply).
- **Only spawner-node encounters change.** Enemies placed in the level, actor spawners, proximity and
  crowd spawners keep theirs.
- **Difficulty can rise or fall** within a family (a weak ground bot can become a strong one).
- **Enemies stuck in geometry** are not detected directly: an encounter whose enemies live 180 s
  without a death is put back (load the last checkpoint to get its original enemies).
- **Classes the DDL does not explain** (`PoolShark`, `MrFunGuy`, `Telepathipus`, mounts, hazards) are
  never used or replaced.

## 0e. Since dev 10.11 (kit 10.0.7)

- **Making a visit active before you fly there is new for the hub.** The game does it itself at the
  end of a visit (round 17: Savali and Blizar together, round 16: Zurkie's), but never for as many
  planets at once as a late run has open. If the ship's menu or a planet behaves oddly with several
  stories active, `hub_prime_open = false` in 04 turns it off (a landing then starts the story and
  loads the visit's intro, which is the other path). `RANDO-HUB prime ...` lines show every call.
- **Intro checkpoints are partly inferred.** Seen in your logs as the game's own landing with the
  visit active: Zurkie's (CHK_ZURK_00_DEFAULT), Savali (CHK_SAV_01_LANDING), Blizar
  (CHK_BLIZAR_B_LANDINGPAD_DESTROYED, the destroyed pad: 10.0 used the intact one). Ran from a
  warp: Ardolis (CHK_ARD_START). Only listed by your game: Torren IV (CHK_MOL_START), Cordelion
  (CHK_CORD_A_START), Viceron (CHK_ZORDOOM_START), the finale. Sargasso's arrival scene is a hash
  (2498464355) looked up at run time; without its name the gel factory pad is used. A first step
  still waiting a minute after the landing is loaded once more at the visit's intro (or its second
  point).
- **A primed visit may still land at a plain pad.** Whether the mission start the hub makes sets the
  game's per-planet landing (as its own story scripts do) is unknown; if it does not, the stuck-step
  reload above loads the intro.
- **Following the game's own trip to Sargasso** (after Nefarious City's story, when you hold its
  Coordinates) is new; `hub_follow_new = false` restores the trip back.
- **Viceron's Coordinates are always a reward of Torren IV's story** (the only place where its first
  visit can be played at once). `coords_first_visit = false` gives 10.1's placement back.

## 0d. Since v0.54 (10.0.5)

- **What empties the inventory is not known.** Round 26 shows the result (a save on Viceron with no
  weapon), not the cause. The give-back only covers items the randomizer knows as yours (given, or
  seen bought / equipped / reported); Bolts, Raritanium and armor are not sent again.
- **The automatic check needs the load's weapon replay.** A trip or load whose replay reports
  fewer than half of your known weapons sends everything again; owned items then cost a second or
  so each in the mailbox and stay owned (`still in your inventory`). If a load replays only part of
  what you own, this happens without need; it is harmless.
- **Planet shuffle off is a plain switch.** It does not undo anything the hub did before (a story it
  started stays started). Destinations still finish and pay while it is off, without the trip back.
- **The shop** still finds no slot ("only 0 vendor weapon(s) in the array at +0x48", rounds 18-26);
  v0.54 logs the pointer layout's own reason and, once, a slot object's bytes for round 27.

## 0c. Since v0.53 (10.0.4)

- **The cause of round 25's ship landings is an inference.** The travel byte is the only thing about
  ship travel the randomizer changes, and the game has it off during the city's story. If Ratchet
  still lands with the ship in the boss fight's shifts, the log line `planetary travel and level
  bits left to the game while nefcity_1 runs` shows the hub did not turn it on.
- **The ship's planet menu is not opened by the hub while a story runs.** The byte and the level
  bits go on at the hub when nothing is running (as before), and when the city's story finishes.
- **Other stories' rifts** (later visits) run with whatever the byte was when they were launched
  from the hub; only the hub's own story takes it back first. No such report yet.

## 0b. Since v0.52 (10.0.3)

- **The city's opening checkpoint has no name in any log.** It is found by its hash among the names
  `rivet.checkpoints()` lists. If your game does not list it, the hub falls back to
  CHK_NEFCITY_START (v0.51, where round 24's story never moved on) and logs the city's checkpoints.
- **Whether a warp to the opening plays the arrival scene** is untested. Round 23 shows only that the
  game loads it first after the prologue. If it does not, `objective MIS_NEFCITY_01 ...` lines and the
  `opening of nefcity_1 loaded` line show how far it got.
- **Writing the prologue complete on Corson V** (before the warp) is new. v0.51 and kit 8.0 wrote
  it after the warp. `hub_prologue_timing = "after"` restores that.
- From round 24, unchanged: the shop could not be changed (ARSENAL_RESTORED's vendor config, and a
  frame-budget overrun), so its weapons were given directly; Glitch is never confirmed.

## 0a. Since 10.0

- **Nothing of the 10.0 hub has run in the game.** The steps it uses were seen working in round 17
  (the warp to Zurkie's, the mission writes and starts, the travel flag and level bits). Three things
  are new and untested: Nefarious City loaded at `CHK_NEFCITY_START`, the prologue resumed at the
  parade's checkpoint, and the warp back to Zurkie's after the game's own follow-on travel.
- **Starts are only known for three destinations** (Nefarious City, Zurkie's first visit, the
  prologue). The others warp to their landing pad, or fly there when a ship answers. The first
  checkpoint their story triggers is learned for the next run. If a story waits at its "go to" step,
  it is loaded once more; after that, `/` or `Ctrl+[` twice.
- **Heroes.** Round 20 showed every hero swap failing under 8.3; 8.4's confirmation check has never
  appeared in a log. A destination started as the wrong hero may stall at its first step.
- **Spybots and Lorbs hold rewards that do not pay yet (dev 10.1).** The 10 Spybots and 12 Lorbs
  are reward locations (`collectibles = true`, the default), but their pickup event has never appeared
  in any log, so nothing completes them in the game until `05_rando_bindings.lua`
  `collectible_events` binds it. They are never in logic, so a seed never needs them, but the weapons,
  gadgets and armor placed there are not handed over until then. `collectibles = false` keeps them
  out.
- **The Burst Pistol reward adds nothing new (dev 10.1).** It is an item of the pool now, but the game
  still hands one out in the prologue and no hook removes items. The generator keeps it off Gold Bolts
  and early-weapon spots when it can.
- **The randomizer gives no Gold Bolts.** There is no verified way to add a real one, and a fake one
  is exactly what you asked to avoid. So Gold Bolts are neither rewards nor shop replacements.
  `configs/pickup/pup_gold_bolt_item.config` exists in your game's files; whether granting it counts
  as a real Gold Bolt is untested.
- **Shop replacements are closed slots, not gadgets or armor.** The vendor sells weapon items only.
  Putting a gadget or armor id into a weapon slot was judged too risky to try blind. Gadgets and
  armor are rewards at locations instead.
- **Armor pods hold weapons, armor and gadgets, but not Coordinates.** Their planets are not known
  (polling finds a piece after the fact, sometimes on the next planet), so the solver cannot rely on
  them.
- **Closed slots and the frame-budget fix are untested.** If the vendor still cannot be changed, it
  sells its usual weapons, some of which are rewards in your seed (said on screen).
- **The prologue stays active** while you play other destinations. If loading a save ever drops you
  back into the parade, that is the reason: `[` twice returns to Zurkie's.

## 0. Since 9.0

- **No hub.** A New Game plays the prologue, then Nefarious City, then Sargasso (the game's own
  travel). The randomizer moves you nowhere. 8.0-8.5's hub items in section 1 below (heroes,
  priming, reloads, hub trips) no longer apply; they are kept for the record.
- **A leftover `15_rando_hub.lua`** from an older kit is reported at start (`RANDO-KIT ... delete`).
  With a 9.0 seed it does nothing, but it binds the old hub keys. Delete it.
- **The mission order in the spoiler** (your default `planet_shuffle`) is not followed in the game:
  your game cannot open a mission out of order (CAMPAIGN.md). The game's own order is played, and
  every seed is proven finishable in it.
- **Punk and Reaver armor sources** (your 8.5.2 data) are still 6 filler-only locations. Their
  pieces are owned from the start, so those locations probably never pay (offline: they are not
  intercepted, and the start-owned pieces are in the armor baseline). Their currency counts toward
  the Bolts/Raritanium budgets.
- **Raritanium with your defaults** (min 120, budget 2,000): when more than 16 rewards are Raritanium,
  every one gives 120 (the spoiler's NOTES say so).

## 1. From 8.4/8.5, with the hub (kept for the record; 9.0 has no hub)

1. **Whether the hero fix starts every story.** The rule "a story's first step needs the visit's
   own hero" fits all seven clean cases in rounds 17 and 20 (CHANGELOG.md). It is an inference, not
   game code. If a story still waits at "go to <planet>" with the right hero, 8.4 reloads it once.
   If it still waits after that, press `/` (reload again) or `[` twice and come back. Send the
   rivet.log lines `hero:`, `prime`, `story still waiting`, `reload:`.
2. **Starting a story before the trip.** In round 20 a story that was already active when you
   travelled (Savali) finished its first step on landing. 8.4 now does this on purpose for hub
   trips and test-travel warps. No story has yet been started on purpose from another planet.
   `story_prime_before_travel = false` switches it off: the story then starts after landing, as in 8.3.
3. **The reload trip** (out to Zurkie's and back) uses the same warps as a hub trip, which work.
   It has never been used for a stuck story. `story_reload_stuck = false` switches it off.
4. **New entry points.** `CHK_ZORDOOM_START` (Viceron) and `CHK_CORD_A_START` (Cordelion) are names
   your game listed, but nobody has warped there yet. `CHK_ARD_START` (Ardolis) worked in round 20.
   Torren IV still has no known story start: the catalog picks one.
5. **Viceron's broken lighting (round 20).** It happened after a warp to
   `CHK_ZORDOOM_LANDING_COMBAT`, a mid-mission point, as Ratchet, with the story not yet running.
   The cause is not proven. 8.4 changes all three (story start point, Rivet, story started first).
   rivet_hook's docs say a planet's story overlays load from the save's mission state, which fits.
   If the lighting is still wrong, say where you landed (`travel:` line).
6. **The shop's new layout.** Reading the slot list as an array of pointers matches the game's data
   definition and explains rounds 18-20's "only 0 vendor weapons". It has only run in the
   simulator. If it fails, the old fallback still gives you the seed's non-vendor shop weapons once.
   `RANDO-SHOP vendor ... slot objects by pointer` in rivet.log means it worked. The Price field
   search and the slot map writes have never run in your game.
7. **ARSENAL_RESTORED detected in game.** This depends on Mr. Zurkon's item config being loaded when
   the game starts. If it isn't, the companion still decides as before. `RANDO-SEED
   ARSENAL_RESTORED is installed (the game has ...)` means the in-game check found it.

## 2. Known limitations (by design or engine)

- **The parade.** A new save always starts in the parade (9.0: it plays to its end as in the game).
- **Travel can only be undone after landing, not blocked before.**
- **Whole visits move, never single missions.** The randomizer can't reorder or skip objectives
  inside a mission.
- **A mission inside a visit may swap the hero itself** (Zurkie's 1: Ratchet, then Rivet in the
  arena). 8.4 only sets the hero before a story starts, or while its first step waits. It never
  sets it in the middle of a story.
- **Story abilities come from the story itself** (Phantom Dash, Hurlshot, ...). In the game's own
  order they always come before they are needed.
- **ARSENAL_RESTORED's vendor** sells the mod's weapons in its own slots. Those slots are not moved.
  A seed with the mod may also give one of those weapons as a reward. You then own it, and the
  vendor shows it as owned.
- **Armor you already owned** before a seed started can pay its source location when the randomizer
  sees it (round 18, a finished save). On a New Game this cannot happen.
- **Progress made while the companion is closed is not saved.**
- **The last ~2 seconds before the game closes.** The companion saves every 2 s. If the game closes
  (or crashes) right after a reward, the save can be one step behind: a Bolts/Raritanium payment
  sent in that moment can come again on the next start, and a location collected in that moment
  can be forgotten (its reward came, but the randomizer counts the location as not found). Close the game from its menu
  and give the companion a moment; its window shows "saved (version ...)" after each change.
- **Loading an older game save does not undo randomizer progress.** Items the randomizer gave after
  that game save are gone from the game's inventory, but the randomizer still counts them as given
  and does not send them again. A load only replays part of what you own, so the randomizer can't
  safely tell a lost item from an owned one. Play forward from your latest save in a seed.

## 3. Still open from earlier rounds

- **Glitch deliveries** are never confirmed by an event (round 16 onwards). The delivery is retried,
  then counted as given.
- **Currency amounts.** In round 20, "currency sent: 3000 / 8250 Bolts" was logged. Whether the game
  added exactly that amount has not been checked.
- **"rivet_hook: game version mismatch, invalidating pointers"** (rounds 19-20) is rivet_hook's own
  message. Everything that uses rivet_hook still worked. rando_give.dll checks the game's bytes
  itself (0x7 = all paths matched).
- **The PowerShell companion** is checked by hand only. PowerShell 7 could not run on the build
  machine, so its 9 tests were skipped (8.5 changes one branch of it: a refused save is kept aside).

## 4. Fixed in 8.5 (see CHANGELOG.md; found in the code, none reported from a game yet)

- A mission call that timed out could still run later; a loading screen counted as a timeout.
- An item or currency request with no answer, or in flight at a New Game, could run later.
- The companion's late restore dropped this session's currency, could re-send a confirmed item, and
  lost armor sources, shop gifts and the hub's objective record.
- A New Game kept the hub's record of the old run (no automatic reload of a destination reloaded there).
- Shop-only weapons had no route without a working rando_give.dll, or when the vendor was never found.
- A planet-menu landing (levels seeds) was saved late and not filtered.
- A save the game refused was overwritten by the companion.

## 5. Fixed in 8.4 (see CHANGELOG.md)

- Stories that did not start, and Viceron as Ratchet: the save's hero was trusted, and 4
  registry heroes were wrong.
- 8.3's automatic restart, which never moved a story.
- A hub trip to a test trip's mid-mission checkpoint (Torren IV).
- "weapon type 1002 ... 1012 is weapon:burst_pistol".
- The shop's "only 0 vendor weapons" (rounds 18-20).
- ARSENAL_RESTORED treated as not installed because the companion answered late.
- The campaign message from the F12 key in a hub seed.
