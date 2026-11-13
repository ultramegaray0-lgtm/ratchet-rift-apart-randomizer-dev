# Changelog

Newest first. 8.4 and 8.5 are stabilization releases: no new features, the same seeds as 8.3.

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

