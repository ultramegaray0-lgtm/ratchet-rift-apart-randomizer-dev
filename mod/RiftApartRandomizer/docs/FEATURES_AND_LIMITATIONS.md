# Features and limitations (Randomizer 8.0)

Each line says how it is known to work:

- **game**: seen working in your game, in a rivet.log you sent (rounds 1-16).
- **your logs**: built from, and replayed against, the events your game sent in rounds 13-16.
- **offline**: the real code passes automated tests (the generator directly; runtime code against
  the simulated game).
- **untested in game**: built and tested offline only.

Round 16 ran 4.0 in your game. 5.0, 6.0 and 7.0 have not run in the game yet.

## The 8.0 requirements (Zurkie's hub, experimental)

| Requirement | 8.0 | Evidence |
|---|---|---|
| New Game starts at Zurkie's | the parade's wrench triggers a checkpoint warp to `CHK_ZURK_00_DEFAULT`; the prologue is written complete; a parade on a later load is undone | trigger: **your logs** (rounds 14-16 replayed); warp and write: **untested in game** |
| Two randomized Coordinates at once | from the seed, two different planets, each playable first; saved | offline: 9,000 hub seeds + the independent verifier |
| Actual randomized destinations | hub travel (ship flight or warp) to any open destination; the mission ladder starts its story or falls back to explore | **untested in game**; explore and finishing by hand always work |
| Battleplex as the hub | finish → rewards → next Coordinates → back to Zurkie's | offline (simulated campaigns to the finale) |
| Every destination reachable, no repeats, finale last | the hub plan, checked over every order a player could choose | offline |
| 7.0 systems kept | weapons, restored weapons, armor, gadgets, Bolts, Raritanium, shop, spoiler, seeds, start | offline (the 7.0 suites unchanged and passing) |

What can't be done, and why: RESEARCH_8.0.md and KNOWN_ISSUES.md.

## The 7.0 requirements

| Requirement | 7.0 | Evidence |
|---|---|---|
| One randomizer, everything together | 12 scripts + rivet.toml + rando_give.dll + companion; weapons, restored weapons, armor, levels, Bolts and Raritanium in one seed | offline: 34,000-seed release batch |
| Unified reward pool | weapons (registry), 27 armor pieces, gadgets, Coordinates, Bolts and Raritanium amounts | offline |
| Restored weapons | ARSENAL_RESTORED's 9 in the pool when the companion finds the mod (`restored_weapons = "auto"`) | Predator Launcher, Volcanic Eruptor, Schrodinger delivered in **game** (rounds 13-16, mod installed); the toc check is **untested in game** |
| Armor, each piece independent | 27 items (9 sets x helmet / chest / boots) | offline. Armor through the game's armor code: **untested in game** |
| Bolts in thousands / tens of thousands | per reward 1,000-10,000 by default (up to 100,000), scaled by the story, budget per seed | offline. Amounts in game: **untested** |
| Raritanium in hundreds / thousands | configurable up to 5,000 per reward; the default is 20-150 so upgrades aren't trivial (`chaos`: 10-2,000) | offline |
| Configurable ranges, no trivial economy | min/max, budget, Bolts share, scaling (CONFIGURATION.md) | offline: every amount in range, every total within its budget, on every batch seed |
| Randomized levels | **locked levels**: each planet's travel needs its Coordinates; the solver proves the story's next planet is always reachable | offline. The warp back: **untested in game** |
| Randomized mission order | **not possible** in your game (below). Experimental presets reorder visits but play in the game's order, which every such seed is proven against | your logs + offline |
| Hub world | the ship's planet menu is the hub (LEVELS.md); no separate hub level exists | your logs |
| Mission completion detection | `MissionStateChangedEvent` 3/4, `MissionCompleteEvent`, planet fallbacks, finale | **game** (rounds 13-16) |
| Correct unlocks, nothing permanently locked, no softlock | the solver + two independent replays; the story's own travel never blocked; bank fallback; Ctrl+F9 escape hatch | offline |
| Reward on every location | items, or Bolts / Raritanium | offline |
| No duplicate progression item, no unobtainable weapon, nothing on an unreachable location | audit + independent verifier, every seed | offline |
| Ms. Zurkon uses the registry | 15 slots sell the seed's pool weapons (restored ones too); ammo and upgrades untouched | offline; vendor screen **untested in game** |
| Configurable prices | `shop_prices` vanilla / weapon / percent / random; written only where the game's own prices are found in memory | offline (simulated vendor); **untested in game** |
| Never sell a weapon that can't be used | cut configs never placed; restored weapons only with the mod | offline + **game** (registry evidence) |
| Starting inventory | Hoverboots + Map-O-Matic always; random weapons and gadget; `start_items`; start currency | **game** (Hoverboots, Map-O-Matic delivered); start currency **untested in game** |
| Presets and toggles | Balanced, Chaos, Full, Campaign, Everything; toggles for weapons, restored weapons, armor, levels, mission order, Bolts, Raritanium, shop, start | offline |
| Seed validation | complete assignment, campaign, weapon pool, armor, currency, spoiler log; audit + independent verifiers; mutation tests show the checkers catch broken seeds | offline: 34,000 seeds, 0 invalid |

## What can't be done, and what 7.0 does instead

| Asked for | Why not | Instead |
|---|---|---|
| **Randomized mission order / mission destinations** | Your game runs mission "system 2" (round 15), where nothing but the game's own scripts opens a mission (`MakeMissionAvailableAction` does nothing). Story content loads from mission state, and `UnlockLevelAction` only flips a 10-bit mask unrelated to missions (decoded for 7.0) | Locked levels: the order in which planets become reachable is the seed's; the story's mission order is the game's (LEVELS.md) |
| **A separate hub level** | The game is one level of regions; there is nothing to load as a hub | The ship's planet menu, with locked destinations |
| **Stopping a flight before it happens** | rivet_hook events cannot be vetoed | The warp back after landing (3 s) |
| **ARSENAL_RESTORED bundled inside the mod** | Its assets were not available, and re-shipping them needs the author's permission | Auto-detected when installed (ARSENAL_RESTORED.md) |
| **Removing items the story gives** (Burst Pistol, story gadgets) | No hook removes items | Never rewards, so nothing is wasted on them |
| **Story abilities as rewards** (Phantom Dash, Hurlshot, Speetle, Trudi, MagBoots, Wallrun) | No item config | The logic treats them as the story's |
| **Weapon upgrades / other pickups as rewards** | Their effect when given by config is untested | Not placed |
| **Spybots, Lorbs, CraiggerBears as locations** | Their pickup events are not bound yet | Not locations (no phantom rewards) |

## Known limits

1. **Gold Bolt names.** Only `"Sargasso 2"`, `"Nefarious City 2/3"` and `"Zurkon's 1"` have been
   seen in game. Others are matched by planet name, then the planet you are on. Every physical Gold
   Bolt still gives one item; which spoiler line it is may differ, never the count.
2. **Items during the prologue parade** may arrive a little later (retried).
3. **Pixelizer and Bouncer** in a normal game are sold in the seed's slots: untested in game.
4. **One playthrough per seed at a time.** Use a different seed per save slot.
5. **Without the companion** progress is not saved, and `restored_weapons = "auto"` means "not
   installed" (both said on screen).
6. **Locked levels** rely on the landing checkpoint of the planet you came from. Five are known
   from your logs; others are learned as you land or searched with `rivet.checkpoints()`. With
   none, that planet's rewards wait for its Coordinates instead (said on screen).

## Softlocks

The randomizer never removes items and never changes mission state. Every item it gives is in
addition to the game's own, and the shop keeps every slot's unlock point. With locked levels the
story can wait for Coordinates, and that is exactly what the solver and the two independent
replays check for every seed: the Coordinates the story needs next are always reachable on planets
already open. The game's own travel is never blocked. The escape hatch (Ctrl+F9) and
`levels_runtime = false` exist in case the game's story differs from the model.
