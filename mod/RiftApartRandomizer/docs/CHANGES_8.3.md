# Randomizer 8.3: the story starts where you land, and keyboard keys

8.3 is 8.2 plus two changes from your round 19 log. Your seed and progress carry over: the
generator is still 8.0.0. Nothing here changes a fingerprint. None of 8.3 has run in your game yet.

## Why the story didn't start (round 19)

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

## What 8.3 does

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

## Keyboard keys

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

## Also seen in round 19, not changed

- **rivet_hook said `game version mismatch, invalidating pointers`** (line 3). Round 18 didn't.
  Everything still worked: events, warps, flights, deliveries. If the game updated, keep an eye
  on it.
- **The companion answered late.** The seed was made before it answered, so ARSENAL_RESTORED
  counted as not installed. That gives `kit-bolt-kit-198` → `b25846f17df5`, not round 18's
  `4d170014c0c6`. The two have separate progress files. Start the companion before the game.
- **The shop:** ARSENAL_RESTORED replaces Ms. Zurkon's config (0 vendor weapons at +0x48), as in
  round 18.

## Tests
- 285 run, 0 failed, 17 skipped: 9 need PowerShell, and 8 need the 5.0/6.0 git history.
- New: `tests/test_v83.py` (23 tests) and `tests/data/round19_rivet.log`.
