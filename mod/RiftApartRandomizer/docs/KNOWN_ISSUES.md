# Known bugs and limitations (Randomizer 8.0 / 8.1)

**8.1 (CHANGES_8.1.md)** fixes the round 17 findings: the planet-change error (u32_at), "no
checkpoint known" for Torren IV and Cordelion (checkpoint catalog, with the ship's planet menu as
the fallback, which is remembered), the shop's 8 ms frame-budget errors (sliced search), the level
bits lost on a save load, and five mission names your game lacks. Still open after round 17:
Glitch deliveries are not confirmed by an event; rivet.configs("Mission") lists nothing; whether
the catalog's warp points on Torren IV and Cordelion are good places to land is unknown until you
try them (rivet.log line "checkpoint catalog").

8.0 is an experimental build. It has been tested offline only (TESTING.md). This page lists what
is known or expected to go wrong, so you can tell a known issue from a new one.

## Expected in your first session (unknown until then)

1. **The warp from the parade.** rivet_hook's checkpoint warp loads another planet's region
   (rivet_hook docs; earlier rounds warped onto unreached planets). It has never been used from the
   parade. If it doesn't land, the hub retries other Zurkie's checkpoints, then opens your
   Coordinates where you are ("could not reach Zurkie's").
2. **The prologue's state write.** `hub_intro = "force"` writes Complete Finished into MIS_INTRO's
   saved record. Possible outcomes:
   - no visible effect;
   - the game moves on to Nefarious City's story (the hub undoes travel for 2 minutes after the
     start);
   - something breaks in the parade's leftovers.

   `hub_intro = "leave"` turns it off.
3. **Destination stories may not start.** System 2 has no make-available. 8.0's write of
   "Available" is an experiment, and so is replay. Expect explore mode on most destinations until
   the log shows what works. Ctrl+F5 twice finishes a destination.
4. **A started story may misbehave.** A mission started out of its order may expect things an
   earlier mission set up: a planet state, a ship, a cutscene, Clank or Kit. Possible results: a
   stuck objective, a missing door, a wrong cutscene. Back out with F5 twice. The destination stays
   open.
5. **Hero swaps.** `rivet.hero_play_as` is the game's own swap, but a swap during a planet's arrival
   has not been tried. A Rivet visit with Ratchet (or the other way round) may break that visit's
   scripts. Use `hub_hero_swap = false` to test without it.
6. **The ship at Zurkie's.** After a warp, Ratchet's ship may not be at Zurkie's. Then the planet
   menu isn't reachable and Ctrl+F6 warps instead of flying. Both reach the destination.
7. **The level bits.** What bits 1-10 mean is unknown. With `hub_levels = "all"`, the ship's menu
   may list every planet. A planet without Coordinates sends you back. `"off"` leaves them alone.
8. **Landing checkpoints.** Five planets have a known landing checkpoint
   (`CHK_NEFCITY_SHIP`, `CHK_SAV_01_LANDING`, `CHK_BLIZAR_A_LANDINGPAD`, Zurkie's two). The others
   are found with `rivet.checkpoints()` by name code, landing pads first. A wrong pick lands you
   somewhere odd on the right planet. The research lines list every LANDING checkpoint, for the
   next version.
9. **The finale's checkpoint** is searched by `MEGA` / `MALINON` / `CORSON`. It may land on a parade
   checkpoint instead of the final battle's area.

## Known limitations (by design or engine)

- The game itself always starts a new save in the parade. The hub leaves it as soon as Ratchet has
  his wrench; changing the start as data is not possible yet (RESEARCH_8.0.md, section 6).
- Travel can't be blocked before landing, only undone after.
- 8.0 moves whole visits, never single missions inside a visit.
- The 3.x mission-order presets (`planet_shuffle`, ...) and 7.0's level locks don't apply to a hub
  seed. They are switched off with a note in the spoiler.
- In a hub seed, story abilities (Phantom Dash, Hurlshot, ...) come only from the story itself.
  If the Nefarious City or Torren IV story never runs, Viceron's own story may need them. Viceron
  still opens in order, and explore mode always works.
- The randomizer can't reorder or skip objectives inside a mission.
- Progress made while the companion is closed is not saved (as in 7.0).

## Carried over from 7.0 (still open)

- The vendor's Price field search, the shop's slot map, currency counts as amounts, armor sources
  through the game's armor code, and the ARSENAL_RESTORED toc check have still not run in your game
  (7.0's round 17 checklist).
- The PowerShell companion's new code is checked by hand only: PowerShell 7 couldn't run on the
  build machine.

## Bugs found and fixed while building 8.0

- **A stale "current planet" after the companion's restore (7.0 too).** Until the next planet
  change, the randomizer's current planet was the one stored in the save, not the one you were on.
  Now this session's planet wins, for every seed.
- **A hub destination left from the menu kept counting as "in progress"** at Zurkie's. It now stays
  open, and Ctrl+F5 at the hub does nothing.
- **Keys during a loading screen** could warp from rivet_hook's render-thread fallback. Hub keys now
  wait until the game has loaded.
