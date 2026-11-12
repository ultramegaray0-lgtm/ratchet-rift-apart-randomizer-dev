# Changelog

Newest first. 8.4 is a stabilization release: no new features, the same seeds as 8.3.

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
- 315 automated tests, 0 failures (17 skipped: PowerShell 7 and pre-8.3 git history unavailable on
  the build machine). New: `tests/test_v84.py` (28), `tests/test_regression_v83.py` (175 seeds in 7 presets against 8.3).
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

