# Player guide: Ratchet Rift Apart Randomizer v0.51

## How a run goes

1. **Start the companion, then the game.** Run `rando_companion\Start-Companion.bat` and leave its
   window open, then start the game.
2. **New Game.** The parade on Corson V starts as usual; every new save starts there. The screen
   shows your seed and your starting items, which arrive in your inventory over the next few
   seconds.
3. **The hub: Nefarious City.** When Ratchet has his wrench and the parade lets him walk again (a
   few seconds later), you're taken to **Nefarious City**. Its story starts right there, from where
   the game itself starts it. The prologue counts as done, and its reward is paid. `]` (next) and
   `Ctrl+]` (go) list what is open:
   - **Nefarious City:** the city's story (already running after the warp).
   - **Battle Arena:** Zurkie's first visit.
4. **Planet shuffle.** Every other planet opens when you hold its **Coordinates**. Coordinates are
   rewards like any other, so they can be anywhere. A destination also waits for the visits it
   depends on in the story (Sargasso's second visit comes after its first, for example). The finale
   opens last.
5. **Finishing a destination** pays its rewards and lists what's newly open. 12 seconds later
   you're back in Nefarious City. Press `[` once to cancel that return and stay. If the game's own
   story tries to carry you to the next planet (to Sargasso after the city's story, for example),
   you're brought back to Nefarious City instead, so you always choose.
6. **The ship's planet menu works too.** Landing on a planet whose Coordinates you don't have sends
   you back to Nefarious City. Landing on an open planet starts its next destination.
7. **Revisits.** Once a planet's destinations are done, it appears in the `]` list as "revisit":
   go there for Gold Bolts, armor and side activities.
8. **Saving and loading are normal.** The companion saves the randomizer's own progress separately
   (every ~2 seconds when something changes).

## Keys

| Key | What it does |
|---|---|
| `]` | Show the next destination |
| `Ctrl+]` | Go to it |
| `[` twice | Back to Nefarious City (once: cancel an automatic return) |
| `Ctrl+[` twice | Finish the current destination by hand, if its story will not start |
| `/` | Start the story of the planet you're on |
| `;` | Status: Gold Bolts, rewards, Coordinates, deliveries still on the way |
| `Pause` | Reload the scripts (rivet_hook) |
| `F3` | rivet_hook's overlay window |

The old F keys also work (`F6` = `]`, `F5` = `[`, `F4` = `/`). To change any key, edit
`scripts\04_rando_settings.lua` (`key_hub`, `key_hub_return`, `key_story`, `key_status`).

## What is randomized

| | |
|---|---|
| **Starting kit** | Always the Hoverboots and the Map-O-Matic. Plus 2 random weapons and 1 random gadget by default; a seed short of items may start with fewer. Plus Coordinates for the three start planets (Corson V, Nefarious City and Zurkie's). You also keep the game's own fixed start (Burst Pistol). |
| **Reward locations** | 25 Gold Bolts, the story missions, side activities (Zurkie's cups, Trudi, the Blizar chef, Ardolis) and armor pods. Each gives exactly **one** reward. **Every Gold Bolt gives an item**, never currency. |
| **Items** | Weapons, gadgets (Box Breaker, Omniglove, Glitch), 21 armor pieces, planet Coordinates. With ARSENAL_RESTORED, also its 9 weapons. |
| **Currency** | A story mission, side activity or armor pod the seed has no item left for gives Bolts (1,000-10,000) or Raritanium (120-1,000). Gold Bolts never do. |
| **Shop** | Ms. Zurkon sells 8 different weapons from the pool, at that weapon's normal price. Her other slots are closed: they show the Burst Pistol, which you already own. |
| **Weapons** | Each weapon has exactly one route: the shop, your start or a reward location, never two. |

**Gold Bolts stay real.** Picking one up counts in the game as always (including for the game's own
Gold Bolt extras). The randomizer adds that location's reward. It never adds Gold Bolt prices.

**Every seed can be finished.** Before you get a seed, a solver walks every order you could play in
and checks that nothing you need is ever locked behind itself.

## Settings (`scripts\04_rando_settings.lua`)

Open the file in Notepad. Lines starting with `--` are switched off; remove the `--` to use one.
**Changing the seed or any option that changes the seed makes a new seed. Start it with New Game.**
Keys and in-game options can change at any time. A wrong value is reported in `rivet.log`
(`RANDO-SETTINGS`), and the default is used instead.

| Setting | Default | |
|---|---|---|
| `seed` | `"random"` | Any text, for example `"lombax-ryno-2026"`. `"random"` lets the companion pick one and remember it |
| `preset` | `"balanced"` | `balanced`, `chaos`, `full`, `campaign` or `everything` (below) |
| `hub` | `true` | `false`: no hub; the story starts the game's own way (prologue → Nefarious City → Sargasso) with randomized rewards |
| `distribution` | `"goldbolts_first"` | Every Gold Bolt holds exactly one item. `"spread"` (10.0's default) shares items over all kinds of location instead, so some Gold Bolts give currency |
| `shop_weapons` | `8` | 0-15 weapons for sale. The rest become rewards |
| `early_weapons` | `2` | 0-6 weapons placed where your starting kit can reach (Gold Bolts there first), plus one Coordinates. With very tight settings it is lowered automatically, with a note in the spoiler |
| `start_weapons` / `start_gadgets` | `2` / `1` | Random starting weapons (0-4) and gadgets (0-2) |
| `armor` | `true` | Armor pieces as rewards |
| `restored_weapons` | `"auto"` | ARSENAL_RESTORED's weapons: `"auto"` when the mod is found; `false` never |
| `exclude` | `""` | Items to leave out, for example `"weapon:ryno_8"` |
| `test_travel` | `false` | A testing aid that lets you go anywhere. Leave it off for a real run |
| `hub_trigger` | `"parade"` | When the new game goes to Nefarious City: once the parade lets Ratchet walk again after the wrench. `"wrench"`: at the wrench itself (v0.5's timing) |
| `hub_prologue` | `"end"` | `"end"`: the prologue counts as done once you're in Nefarious City. `"keep"`: it stays open, to continue later from the `]` list |
| `hub_start_story` | `true` | The first warp starts Nefarious City's story. `false`: just go there |

### Presets

| Preset | In short |
|---|---|
| `balanced` | The default: everything above |
| `chaos` | Bigger currency swings, random shop prices, a smaller starting kit |
| `full` | Like balanced, with a little more currency |
| `campaign` | Like balanced; locked travel is the focus (the hub always uses it) |
| `everything` | Random shop prices, starting Bolts and Raritanium, more currency |

## Your progress

- Randomizer progress (which locations you've collected, what was given) is saved by the companion
  in `rando_companion\randomizer_saves\rando_<id>.lua`, with a `.bak` of the previous save.
- **Keep the companion open while you play.** With the default `seed = "random"`, no seed is made
  until the companion connects (the screen says "start the companion"). With a fixed seed, the
  randomizer runs without it, but its progress isn't saved, and the screen warns you about that.
- **New Game starts the seed over.** The previous run's file is kept as `rando_<id>.runN.lua`.
- **Play forward from your latest save.** Loading an older game save doesn't undo randomizer
  progress (see TROUBLESHOOTING.md).
- **Quit from the game's menu,** then give the companion a second. A crash in the 2 seconds after a
  reward can repeat a currency payment, or forget that location.
