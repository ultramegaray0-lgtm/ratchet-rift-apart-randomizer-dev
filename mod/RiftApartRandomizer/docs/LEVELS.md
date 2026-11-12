# Levels and the campaign in 7.0

> **8.0:** the `hub` preset (the new default) plays the campaign from Zurkie's Battleplex instead: HUB.md. This page describes 7.0's level locks, which the 7.0 presets still use.

**Short version.** 7.0 randomizes **which planets you can travel to, and when**. Each planet's
travel is locked behind its **Coordinates**, which are items hidden in the seed (Gold Bolts,
missions, armor pods...). The **story's mission order stays the game's own**. Your game cannot
open a mission out of order, so a seed that claimed to reorder missions would not work, and 7.0
doesn't claim that. This page explains what was investigated, what 7.0 does instead, and why it
can't softlock.

Turn it on with the `campaign`, `chaos` or `everything` preset, or with `levels = true`.

## What was investigated

| Question | Finding | Source |
|---|---|---|
| Can the randomizer load a mission or a planet's story directly? | No. The whole game is one level (`i29`) of regions; a planet's story content is in overlay regions that load from the save's **mission state** | game (earlier rounds: a warp onto an unreached planet loads it without its story) |
| Can it open (make available) a mission out of order? | **No.** Your game runs mission "system 2" (round 15). There, `MakeMissionAvailableAction` does nothing at all; start works only on a mission the game has opened (state 1) | exe code (round 15 dump, all five mission actions) |
| Does `UnlockLevelAction` unlock planets? | No. It sets or clears a bit (levels 1-10) in a mask at a global's `+0x30`; `IsLevelUnlockedAction` reads it. It has nothing to do with mission state or overlays | exe code (round 15 dump, RVA `0x89DA00`, `0x89C1E0`, `0x89C140`), decoded for 7.0 |
| Can the planet menu lock single planets? | No. `SetPlanetaryTravelAction` stores one bool in one global byte: all travel on or off, which would block the story too | exe code (round 15 dump, RVA `0x607500`), decoded for 7.0 |
| Is there a hub level? | No separate one. The ship's **planet menu** is the game's own hub: every interplanetary trip you choose goes through it (`PlanetMenuAcceptEvent` with the destination checkpoint) | game (round 14 line 171, round 16 line 390) |
| Which travel does the game do by itself? | The parade's rifts (Corson V, Torren, Ardolis, Nefarious City), rift jumps inside missions (Nefarious City, Savali, Nefarious City), and the story's own move from Nefarious City to Sargasso when `MIS_NEFCITY_01` completes: none of them uses the planet menu | game (round 16 lines 200-221, 310-344) |
| Can travel be stopped? | No. rivet_hook events cannot be vetoed and the menu event's strings are read-only. A trip can only be undone after landing, with rivet_hook's `warp` | rivet_hook 2.0.1 source |

So a hub world that sends you to any planet's story in any order can't be built on this game.
What follows is the closest version that works reliably.

## What 7.0 does: the planet menu is the hub

1. **Start.** You start on the parade as usual. The planets the game itself takes you to (Corson
   V, Nefarious City, Sargasso) are open. With `start_coordinates = "first_two"` (the `campaign`
   preset), the next planet in the story (Zurkie's) is open too; with `random_extra`, a random
   later one.
2. **Pick an open planet.** In the ship's planet menu, any open planet can be visited: for its
   story mission when the story is there, or for its Gold Bolts, side activities and armor pods.
3. **Complete things, get rewards.** Missions, Gold Bolts, side activities and armor pods give
   the seed's items, Bolts and Raritanium.
4. **Coordinates unlock the next destinations.** When a reward is a planet's Coordinates, "you can
   fly to X now" appears, and X is open from then on.
5. **A locked planet sends you back.** If you choose a planet without its Coordinates, you land,
   "no Coordinates for X yet - back to Y" appears, and after 3 seconds rivet_hook's warp takes you
   back to the checkpoint you last landed on at the planet you came from.

The story still decides **which mission is next**. When the story needs a planet whose
Coordinates you don't have, you find them on the planets that are already open: Gold Bolts,
second story missions, side activities and armor pods. That's where each seed's level order
comes from. The spoiler log's LEVELS section lists the planets in the order their Coordinates
can be reached.

## Why it can't softlock

- **The solver plays the seed in the game's own order** (`03_rando_campaign.lua` `C.reach`). Each
  visit needs its planet's Coordinates; each location on a planet needs that planet's
  Coordinates, and the visit it belongs to. A seed is accepted only when every visit can be
  reached, and every in-logic location too (`accessibility = "full"`).
- **Two independent re-implementations** in Python (`tests/test_generator.py` `verify`,
  `tests/test_campaign.py` `verify_campaign`) replay every seed in the release batch visit by
  visit. The generator's own audit also checks that no Coordinates sit on their own planet (Gold
  Bolts included) and that the story's own planets are open from the start.
- **The game's own travel is never blocked.** Only an arrival that follows a planet-menu choice
  (within 3 minutes) is checked. The parade, rifts, story moves, loading a save and the warp back
  itself are not. If the game takes you to a locked planet, its rewards pay as usual.
- **Fallbacks, said on screen and in rivet.log (`RANDO-TRAVEL`):**
  - no checkpoint known for the planet you came from, or the warp fails: you stay, and that
    planet's mission rewards wait for its Coordinates (6.0's banked rule) instead;
  - `levels_runtime = false` in 04_rando_settings.lua: same, for every planet (no warps);
  - **Ctrl+F9 twice** opens the planet you were last sent back from. Its Coordinates are given and
    recorded as `[OPENED BY HAND]` in the history. The solver makes this unnecessary; it's there in
    case the game's story differs from the model somewhere.

## Where the warp goes

In this order:
1. the checkpoint where you last landed on that planet through the planet menu (learned while you
   play, saved by the companion);
2. a checkpoint seen in your logs (`CHK_NEFCITY_SHIP`, `CHK_ZURK_00_DEFAULT`,
   `CHK_ZURK_LANDING_SHIP`, `CHK_SAV_01_LANDING`, `CHK_BLIZAR_A_LANDINGPAD`);
3. `rivet.checkpoints()`, searched by the planet's name codes, landing pads first.

The warp moves the save's checkpoint to that planet, which is where you came from anyway.

## The mission order presets (experimental, unchanged since 3.2)

`planet_shuffle`, `mission_shuffle`, `full_campaign` and `campaign_chaos` still generate reordered
visit orders. They need verified mission control, which your game's system 2 can't provide
(CAMPAIGN.md). Until then they play in the game's own order. **New in 7.0:** every such seed is
also proven finishable in the game's own order, during placement and again at the end (6.0
checked this only in tests). The spoiler log's MISSION ORDER section says so.

## Untested in the game

Everything on this page has been tested against the simulated game only. TESTING.md lists the
checks for your next session:
- the landing and warp timing;
- whether the warp checkpoint names exist;
- that a story travel never triggers a warp.

The events used (`PlanetMenuAcceptEvent`, `PlanetChangedEvent`) are taken from your real logs.
