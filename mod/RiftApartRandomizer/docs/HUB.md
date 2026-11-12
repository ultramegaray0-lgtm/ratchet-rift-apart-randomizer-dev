# Zurkie's Battleplex hub (Randomizer 8.0, experimental)

**8.0 has not run in your game yet.** Your first session is its first test. Bugs and broken saves
are expected, so play on a spare save slot and keep your backups.

## What happens

1. **NEW GAME.** The parade starts as always (the game itself always starts there). Once Ratchet
   picks up his wrench, the randomizer takes him straight to **Zurkie's Battleplex**. The HUD says:
   - `Randomizer: to Zurkie's Battleplex - the randomized campaign starts there`;
   - then `Zurkie's Battleplex: Coordinates for X and Y`.
2. **Two Coordinates** are open at once, on two different planets chosen by the seed. Your starting
   inventory (Hoverboots, Map-O-Matic, the seed's weapons and gadget) arrives as in 7.0.
3. **Pick a destination.** F6 shows what you can play now ("Destination 1/3 - Savali: Village
   attack... (ratchet)"). **Ctrl+F6** goes there: the ship's own flight when a ship is near,
   otherwise a warp. The ship's planet menu also works, but a planet without Coordinates sends you
   back to Zurkie's.
4. **Play it.** On arrival, the randomizer asks the game about that visit's story and tries to start
   it (see "Story or explore" below). Rivet's visits switch you to Rivet.
5. **Finish it.** When the visit's last mission completes:
   - the destination's rewards are paid (its story missions and side activities);
   - the next Coordinates of the seed open;
   - after 12 seconds you are taken back to Zurkie's (F5 cancels).

   Gold Bolts and armor pods pay the moment you find them, as always.
6. **Back at Zurkie's**, `New Coordinates: ...` appears. Pick the next destination.
7. **The finale** (Corson V) opens when every other destination is finished.

Zurkie's own two visits (Francois, meeting Ratchet) are destinations too. You play them at the hub,
without travelling.

## Story or explore

For each destination, the randomizer tries, in order:

| Step | What it is | Known to work in your game? |
|---|---|---|
| the story is already active | nothing to do | n/a |
| start an **available** mission | the game's own `StartMissionAction` call, byte-checked | the call's code matches your exe; never run in game |
| make an **inactive** mission available, then start it | writes "Available" into the mission's saved state (`rando_give.dll` v6) | **unknown: the 8.0 experiment** |
| replay it | the game's own `ReplayMissionAction` call | unknown |
| **explore** | the planet is yours to explore; its Gold Bolts, armor pods and side activities pay as always | always works |

In explore mode the HUD says so. **Ctrl+F5 twice** finishes the destination by hand: its rewards
are paid and the next Coordinates open. It's recorded in the history and in rivet.log
(`[FINISHED BY HAND]`). This is what keeps the campaign going whatever the game does.

## Keys

| Key | What it does |
|---|---|
| F6 | next open destination (repeat to cycle) |
| Ctrl+F6 | go to the destination shown. Before the hub has started (an older save, or the warp failed): go to Zurkie's and start the hub |
| F5, twice | back to Zurkie's (an unfinished destination stays open) |
| F5 during the 12-second countdown | stay where you are |
| Ctrl+F5, twice | finish the current destination by hand |
| F9 | status (`hub n/13 done`); Ctrl+F9 is unchanged (levels seeds only) |

Change the keys with `key_hub` and `key_hub_return` in `04_rando_settings.lua`.

## Settings

| Setting (04_rando_settings.lua) | Default | What it does |
|---|---|---|
| `preset = "hub"` | **default in 8.0** | a hub seed with balanced items. `hub_chaos`: the hub with chaos' currency and prices. Any 7.0 preset is still there and plays like 7.0 |
| `hub_start_coordinates` | 2 | Coordinates open at the start (2 to 4, all different planets) |
| `hub_unlocks` | 1 | Coordinates each finished destination opens (1 to 3) |
| `hub_finale` | `"all"` | `"half"`: the finale opens after half of the destinations |
| `hub_revisits` | true | second visits (Zurkie's 2, Sargasso 2, Savali 2) are destinations |
| `hub_runtime` | true | false: a hub seed does nothing hub-specific (for testing the rest) |
| `hub_trigger` | `"wrench"` | when to leave the parade: `"wrench"`, `"control"` (first control), `"cinematic"` (at once) |
| `hub_intro` | `"force"` | `"force"`: mark the skipped prologue complete in the save. `"leave"`: leave it active |
| `hub_force_missions` | true | the "make available" step above |
| `hub_replay` | true | the replay step above |
| `hub_levels` | `"all"` | sets every level bit (1-10) at Zurkie's, in case the ship's menu reads them. `"off"`: don't touch |
| `hub_travel_flag` | true | turns planetary travel on at Zurkie's |
| `hub_fly` | true | leave Zurkie's with the ship's flight when a ship answers |
| `hub_auto_return` | true | a finished destination takes you back to Zurkie's |
| `hub_return_delay` | 12 | seconds before that |
| `hub_hero_swap` | true | Rivet's destinations switch to Rivet, Zurkie's back to Ratchet |

The first five change the seed (new progress, New Game). The others can change any time.

## Saving and loading

- The randomizer's hub progress (open Coordinates, finished destinations) is saved by the companion
  with the rest. Keep its window open.
- A save made at Zurkie's or on a destination loads there. A destination you were playing carries
  on: the randomizer asks the game where its story is.
- If a load ever puts you back in the parade, the randomizer takes you to Zurkie's again.
- Starting another New Game with the same seed starts it over (run 2, 3, ...), at Zurkie's again.

## If it goes wrong

| What you see | What to do |
|---|---|
| Still in the parade after the wrench | wait a minute (it retries); then Ctrl+F6. rivet.log: `RANDO-HUB warp to Zurkie's` |
| "could not reach Zurkie's" | your Coordinates are open anyway: Ctrl+F6 travels from anywhere |
| A destination says "explore" | explore, then Ctrl+F5 twice |
| A story starts but breaks (no objective, stuck) | F5 twice back to Zurkie's, then Ctrl+F6 to the same destination: it asks the game again. Or finish it by hand |
| The game takes you somewhere else right after the start | the randomizer brings you back (`right after the hub started`) |
| Everything is wrong | `hub_runtime = false` plays the seed without the hub, like 7.0 (start a New Game) |

## What to send after your first session

- `rivet.log` (next to RiftApart.exe).
- The companion's save and spoiler (`companion\randomizer_saves`).
- What you saw at each step: the parade → Zurkie's; the Coordinates message; F6/Ctrl+F6; the
  first destination's story (did a mission start? objectives? cutscenes?); the return; a save and
  load; the ship's planet menu at Zurkie's (which planets does it show?).

`python tools/summarize_log.py rivet.log` lists every `RANDO-HUB` line. The research lines alone
(mission states, level bits, checkpoint names) are enough to plan the next version.
