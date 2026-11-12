# Test travel (8.2)

Test travel takes you to any planet, whatever Coordinates you hold. It is there to try out the
travel itself: which landing points work, what the warp and the ship's flight do on each planet,
and what the planet menu shows.

It is **off** in the 8.5 kit's `04_rando_settings.lua` (a real playthrough); set it to true to use it:

```lua
test_travel = true,          -- false for a real run
key_test_travel = ".",       -- 8.3 (was F7; the old F keys still work with legacy_f_keys)
key_test_point = ",",        -- 8.3 (was F8)
```

It is a runtime option. It does not change the seed, its fingerprint or its spoiler, so you can
turn it on and off at any time (edit the file, then press Pause to reload the scripts).

## Keys

| Key | What it does |
|---|---|
| **.** | Next planet. All 10 are listed, in story order, starting after the one you are on. The screen shows the planet, its landing point, and where that point came from |
| **,** | Next landing point on that planet |
| **Ctrl+.** | Warp there. This is rivet_hook's checkpoint warp, the one the game's level scripts use |
| **Ctrl+,** | Fly there with the ship. This needs the ship's planet menu nearby, for example on a landing pad. Round 17: Zurkie's → `CHK_NEFCITY_SHIP` worked |

The landing points of a planet are listed best first:

1. the hub's own entry points (8.4: a destination's story start first);
2. where you last landed there with the ship's planet menu;
3. where a test trip last went (8.4: never used by the hub's own trips);
4. the ones seen in your logs;
5. up to 12 from the checkpoint catalog, which lists every checkpoint `rivet.checkpoints()`
   names, places each on its planet and scores it (landing pads first, cinematics, bosses and
   tunnels last).

The catalog starts about 10 seconds after the game loads. If a planet shows "no landing point
known yet", wait a few seconds and press `.` again.

## While it is on

- **A test trip starts the planet's story (8.3).** With `story_on_arrival`, landing starts that
  planet's first unfinished story, even if the story before it isn't finished (docs/CHANGELOG.md).
  8.4: a warp (Ctrl+.) switches to that story's hero and starts the story before it leaves.
  A test trip opens no Coordinates and pays nothing by itself. Gold Bolts, armor pods and the rest pay
  as usual. Zurkie's is still the hub's own arrival: Ratchet again, the level bits, and the hub key `]`.
- **Nothing sends you back.** The ship's planet menu takes you to any planet. Neither the hub
  nor locked levels warp you away, and the hub's Corson V keeper and startup guard stay still.
- **The level bits** (the planet menu's list) are put back after a load, as the hub does.
- **A landing is remembered** as that planet's landing point for later trips, test or hub.
- **Every trip is logged.** It goes into the randomizer history as `[TEST TRAVEL]` and into
  rivet.log as `RANDO-TEST` lines. The status line (`;`) says `TEST TRAVEL on`.

## What to look for in rivet.log

- `RANDO-TEST selected <planet> <checkpoint> (k/n, <source>)`: what `.` / `,` chose.
- `RANDO-TEST warp to <checkpoint> ...` or `fly to ...`, then `arrived on <planet> by warp at ...`.
  A trip that doesn't land within 3 minutes is reported and forgotten.
- `RANDO-TEST warp to X for Y failed: ...`: that landing point refused. Press `,` and try the
  next one.
- `RANDO-TRAVEL checkpoint catalog: ...`: one line when the catalog is complete. It never
  appeared in round 18; 8.2 fixes that.

## Warnings

- Warping into the middle of a story section the save hasn't reached can leave the level in an
  odd state. The usual 8.x rule applies: play on a spare save.
- A warp moves the save's current checkpoint with you.
