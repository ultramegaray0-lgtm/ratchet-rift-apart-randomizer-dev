# Playing Randomizer 9.0

9.0 has no Zurkie's hub. A run is the game's own story with randomized rewards:

1. **Start.** `companion\Start-Companion.bat`, then the game. **New Game** on a spare slot.
2. **The prologue.** The parade on Corson V plays as usual. The HUD says
   `Randomizer: new game - seed ... starts over`, then `Randomizer start: Hoverboots, Map-O-Matic, ...`.
   Your start items arrive in the inventory over the next seconds.
3. **Nefarious City, then Sargasso.** The parade's rifts take you to Nefarious City, and finishing its
   story takes you to Sargasso, both by the game itself. The randomizer never moves you, starts no
   mission and swaps no hero (8.0-8.5's hub did all three).
4. **After that.** Fly with the ship's planet menu as the story opens planets.
   - With the `balanced` preset (the kit's 04 file: your defaults), travel is free. Coordinates are
     items: a planet's **mission** rewards wait until you find its Coordinates. Gold Bolts always pay
     at once.
   - With locked levels (`campaign`, `chaos`, `everything`), flying to a planet without its
     Coordinates sends you back. The story's own planets (Corson V, Nefarious City, Sargasso) are
     always open. LEVELS.md has the details.
5. **Rewards.** Every Gold Bolt gives one item at once. Story missions, side activities and armor
   pods give theirs; a location without an item gives Bolts or Raritanium. Ms. Zurkon sells the
   seed's weapons (SHOP.md).

## Keys

| Key | |
|---|---|
| `;` | status: Gold Bolts n/25, rewards, Coordinates, deliveries waiting |
| `Ctrl+;` twice | locked levels: open the planet you were last sent back from (recorded in the history) |
| `'` | experimental mission order only (logs a line and does nothing in the game's own order) |
| `.` `,` | test travel, only with `test_travel = true` (TEST_TRAVEL.md) |

The old F keys (F7, F8, F9, F12) work too while `legacy_f_keys = true`. `]`, `[` and `/` were hub
keys and do nothing in 9.0.

## The mission order setting

Your default `campaign_mode = "planet_shuffle"` writes a shuffled planet order into the spoiler. Your
game cannot open a mission out of order (CAMPAIGN.md), so until mission control is verified the game's
own order is played, and every seed is proven finishable in that order. In 9.0 every shuffled order
also starts with the prologue, Nefarious City and Sargasso.

## If it goes wrong

- rivet.log: `RANDO-KIT` (the kit), `RANDO-SEED` (the seed), `RANDO-REAL` (deliveries),
  `RANDO-TRAVEL` (locked levels), `RANDO-ERROR`.
- `RANDO-KIT ... delete from the scripts folder: 15_rando_hub.lua`: an older kit's hub script is
  still there. Delete it. With a 9.0 seed it does nothing, but it binds the old hub keys.
- KNOWN_ISSUES.md and RECOVERY.md.
