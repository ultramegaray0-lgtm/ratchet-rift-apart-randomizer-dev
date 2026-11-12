# Starting a new game with Randomizer 8.0

8.0 seeds differ from 7.0 seeds even with the same seed text, so 8.0 needs a **New Game**. Your
7.0 progress files stay in `companion\randomizer_saves` and are never touched.

## With the hub (preset `hub`, the 8.0 default)

1. Start `companion\Start-Companion.bat`, then the game. **New Game** on a spare slot.
2. The parade starts. "Randomizer: new game - seed ... starts over" and your start items appear.
3. Pick up the wrench. "Randomizer: to Zurkie's Battleplex" appears, then a fade, and you are at
   Zurkie's: "Zurkie's Battleplex: Coordinates for X and Y".
4. F6 chooses a destination, Ctrl+F6 goes there. Finish it (or, in explore mode, Ctrl+F5 twice).
   You come back to Zurkie's with new Coordinates. HUB.md has everything else.

The rest of this page is the 7.0 walkthrough, which still applies to the 7.0 presets.

## Once

1. Back up `Documents\Ratchet & Clank Rift Apart`.
2. Install the kit (INSTALL.txt): 13 scripts, `rivet.toml`, `rando_give.dll` (v6), the
   `companion` folder.
3. In `<game>\scripts\04_rando_settings.lua` choose:
   - `preset`: `hub` (8.0 default), `hub_chaos`, `balanced`, `chaos`, `full`, `campaign` or
     `everything` (CONFIGURATION.md);
   - `seed`: `"random"`, or any text you want to share or replay.

   Leave `restored_weapons = "auto"`. If ARSENAL_RESTORED is installed, its weapons are in the
   seed.

## Every new seed

1. Start `companion\Start-Companion.bat`, then the game. In the companion window, wait for:
   - `ARSENAL_RESTORED is installed: ...` or `... is not installed ...` (only with
     `restored_weapons = "auto"`);
   - `new random seed: ...` or `continuing random seed: ...` (with `seed = "random"`);
   - `spoiler log written to ...`.
2. In the game's main menu choose **New Game** (any difficulty) in an empty or spare slot.
3. During the parade the HUD shows:
   - `Randomizer: new game - seed <seed> starts over (run N)`;
   - `Randomizer start: Hoverboots, Map-O-Matic, <weapons>, <gadget>[, Bolts, Raritanium]`.

   The items arrive in your inventory within a few seconds, a little later if the parade is in
   a cinematic.
4. Play. Every Gold Bolt says `Gold Bolt n/25: <item>`. Missions, side activities and armor pods
   say what they gave. F9 shows the status at any time.

## With locked levels (`campaign`, `chaos`, `everything`, or `levels = true`)

- Corson V, Nefarious City and Sargasso are open from the start (the story takes you there).
  `campaign` also opens Zurkie's.
- Watch for `Coordinates: <planet> - you can fly to <planet> now`.
- Choosing a planet without its Coordinates in the ship's menu lands you there, says
  `no Coordinates for <planet> yet - back to <planet>`, and 3 seconds later takes you back.
- When the story wants a planet you can't reach yet, look for its Coordinates on the open planets:
  - Gold Bolts;
  - second story missions;
  - Zurkie's cups;
  - side activities;
  - armor pods.

  The spoiler's LEVELS section lists where each one is.
- Stuck anyway? **Ctrl+F9 twice** opens the planet you were last sent back from. It's recorded in
  the history; report it with rivet.log, because the solver should have made it unnecessary.

## Saving, loading, restarting

- Save and load as usual. The randomizer's own progress is saved by the companion (keep its
  window open) and restored when the game or the scripts restart.
- Starting another New Game with the same seed starts the seed over (run 2, 3, ...). The previous
  run's file is kept as `rando_<fingerprint>.runN.lua`.
- A different seed: change `seed` (or start the companion with `-NewRandomSeed`), then New Game.
