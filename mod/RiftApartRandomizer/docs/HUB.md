# Zurkie's Battleplex hub (Randomizer 8.5)

The hub preset (`preset = "hub"`, the default) turns the campaign into a hub: Zurkie's Battleplex is
home, and each planet visit of the story is a **destination** you open with Coordinates.

8.4 and 8.5 have not run in your game yet. The hub's travel, state writes, deliveries and hero swaps have
all worked in rounds 17-20. Play on a spare save slot and keep backups.

## What happens

1. **NEW GAME.** The parade starts as always. Once Ratchet picks up his wrench, the randomizer takes
   him to **Zurkie's Battleplex** (`Randomizer: to Zurkie's Battleplex ...`), then shows
   `Zurkie's Battleplex: Coordinates for X and Y`.
2. **Two Coordinates** are open at once, on two different planets chosen by the seed. Your starting
   inventory arrives: Hoverboots, Map-O-Matic, and the seed's weapons and gadget.
3. **Pick a destination.** `]` shows what you can play now, for example `Destination 1/3 - Savali:
   Village attack... (ratchet)`. **Ctrl+]** goes there:
   - 8.4 first switches to that visit's **hero** and **starts its story**, then travels (the ship's
     flight when a ship is near, otherwise a warp);
   - the ship's planet menu also works, but a planet without Coordinates sends you back to Zurkie's.
4. **Play it.** The story is running when you land. If it isn't (an older save, the planet menu),
   the randomizer starts it then (see "Story or explore").
5. **Finish it.** When the visit's last mission completes:
   - its rewards are paid;
   - the next Coordinates of the seed open;
   - after 12 seconds you are taken back to Zurkie's (`[` cancels).

   Gold Bolts and armor pods pay the moment you find them.
6. **Back at Zurkie's** (as Ratchet), `New Coordinates: ...` appears. Pick the next destination.
7. **The finale** (Corson V) opens when every other destination is finished.

Zurkie's own two visits (Francois, meeting Ratchet) are destinations too. You play them at the hub.

## The hero of each visit

| Ratchet | Rivet |
|---|---|
| Nefarious City, Zurkie's 1, Savali 1 and 2, Cordelion, Ardolis, the finale | Sargasso 1 and 2, Blizar Prime, Torren IV, Zurkie's 2, Viceron |

The hero is checked with the game (`hero: rivet confirmed` in rivet.log), never taken from the
save. A visit's first step ("go to <planet>") only finishes with its own hero. That is why
Torren IV and Viceron stalled in round 20, played as Ratchet.

## Story or explore

For each destination, after its hero is confirmed, the randomizer tries in order:

| Step | What it is | In your game |
|---|---|---|
| the story is already active | left to the game | yes |
| start an **available** mission | the game's own start call | yes (round 17) |
| make an **inactive** mission available, then start it | writes "Available" into the mission's saved state (`rando_give.dll` v6) | yes (round 17: Zurkie's 1 played to the end) |
| replay it | the game's own replay call | unknown |
| **explore** | the planet is yours; its Gold Bolts, armor pods and side activities pay | always |

**A story still at "go to <planet>" 20 s after its start is reloaded once.** You go out to Zurkie's
(or, for Zurkie's own visits, another open planet) and straight back. The HUD says so. Round 20's
Viceron moved on after a reload. Press `/` to reload again.

**Ctrl+[ twice** finishes the destination by hand: its rewards are paid and the next Coordinates
open (`[FINISHED BY HAND]` in the history). This keeps the campaign going whatever the game does.

## Keys

| Key | What it does |
|---|---|
| `]` | next open destination (repeat to cycle) |
| Ctrl+`]` | go to the destination shown. Before the hub has started: go to Zurkie's and start the hub |
| `[` twice | back to Zurkie's (an unfinished destination stays open) |
| `[` during the 12-second countdown | stay where you are |
| Ctrl+`[` twice | finish the current destination by hand |
| `/` | start (or reload) the story of the planet you are on |
| Ctrl+`/` twice | restart that story (experimental) |
| `;` | status (`hub n/13 done`) |

With `legacy_f_keys = true` (default) the old keys also work: F6, F5, F4, F9. Change keys in
`04_rando_settings.lua` (`key_hub`, `key_hub_return`, `key_story`, `key_status`).

## Settings

| Setting (04_rando_settings.lua) | Default | What it does |
|---|---|---|
| `preset = "hub"` | default | a hub seed with balanced items. `hub_chaos`: the hub with chaos' currency and prices |
| `hub_start_coordinates` | 2 | Coordinates open at the start (2 to 4) |
| `hub_unlocks` | 1 | Coordinates each finished destination opens (1 to 3) |
| `hub_finale` | `"all"` | `"half"`: the finale opens after half of the destinations |
| `hub_revisits` | true | second visits (Zurkie's 2, Sargasso 2, Savali 2) are destinations |
| `hub_hero_swap` | true | each visit is played as its own hero; Ratchet at Zurkie's |
| `story_prime_before_travel` | true | hero and story first, then the trip |
| `story_reload_stuck` | true | the reload above |
| `story_on_arrival` | true | landing on a planet any way starts its story |
| `hub_force_missions`, `hub_replay` | true | the ladder's steps above |
| `hub_auto_return`, `hub_return_delay` | true, 12 | back to Zurkie's after a finished destination |

The first four change the seed (new progress, New Game). The others can change any time.

## Saving and loading

- Hub progress (open Coordinates, finished destinations) is saved by the companion. Keep its window
  open.
- A save made at Zurkie's or on a destination loads there, and a destination you were playing
  carries on.
- A New Game with the same seed starts it over (run 2, 3, ...).

## If it goes wrong

| What you see | What to do |
|---|---|
| Still in the parade after the wrench | wait a minute (it retries), then Ctrl+`]` |
| A destination says "explore" | explore, then Ctrl+`[` twice |
| "the story still waits at its first step" | `/` reloads it again; or `[` twice and come back |
| "could not switch to rivet" | the hero swap was refused; the story may wait; send rivet.log |
| "the scripts folder mixes kits" | copy every file of the kit's `scripts` folder again (INSTALL.txt) |
| Everything is wrong | `hub_runtime = false` plays the seed without the hub (New Game) |

## What to send after a session

- `rivet.log` (next to RiftApart.exe) and the companion's `randomizer_saves` folder.
- What you saw, per destination: the hero, whether the story started, where you landed.

`python tools/summarize_log.py rivet.log` lists every `RANDO-HUB` line.
