# Configuration (8.0)

## scripts\04_rando_settings.lua

`seed` and `preset` choose the seed. Each randomization option is listed there commented out,
so remove `--` to set one. Changing the seed or any randomization option makes a **different
seed** with its own progress file; start it with New Game. Keys and in-game options can change at
any time. A wrong value is reported in rivet.log (`RANDO-SETTINGS ...`) and the preset's value is
used.

These are fixed: every Gold Bolt gives one item; Hoverboots and the Map-O-Matic are in the start;
every weapon has exactly one route (a shop slot, the start or a reward location, WEAPONS.md); the
solver proves every seed can be finished.

## Presets

| Preset | Name | What it changes from the defaults |
|---|---|---|
| `hub` | Zurkie's Hub | **8.0, the default in `04_rando_settings.lua`, experimental** (HUB.md): New Game starts at Zurkie's Battleplex with two random Coordinates; every finished destination opens the next ones. Items as `balanced` |
| `hub_chaos` | Zurkie's Hub (chaos) | the hub, with chaos' currency, prices and start (no locked levels: the hub has its own) |
| `balanced` | Balanced | nothing: every item system, the game's own level order, moderate currency, prices by weapon |
| `chaos` | Chaos | locked levels with the fewest open planets; 1 starting weapon, no starting gadget; random prices (25-300%); Bolts 500-40,000 and Raritanium 10-2,000 per reward (budgets 350,000 / 10,000), half and half, not scaled by the story |
| `full` | Full Randomizer | Coordinates are items too: a planet's mission rewards wait for its Coordinates (travel stays free); Bolts up to 15,000, Raritanium up to 250 (budgets 180,000 / 3,000) |
| `campaign` | Campaign Randomizer | **locked levels** (LEVELS.md): flying to a planet needs its Coordinates; the story's own planets plus the next one open at the start |
| `everything` | Everything Randomized | locked levels (story planets only at the start), random prices (50-200%), 2,500 Bolts and 25 Raritanium at the start, Bolts up to 20,000 and Raritanium up to 400 (budgets 250,000 / 5,000) |

Older names still work: `standard`, `extended`, `armor` and `classic` are `balanced`, and
`coordinates` is close to `full`. The experimental mission-order presets are `planet_shuffle`,
`mission_shuffle` (6.0's `campaign`), `full_campaign` and `campaign_chaos` (LEVELS.md,
CAMPAIGN.md). `python tools/rando.py presets` prints this list.

## The hub (8.0)

Seed settings, only used when `hub = true` (the hub presets). They change the seed.

| Setting | Default | |
|---|---|---|
| `hub` | false (true in the hub presets) | Zurkie's Battleplex hub (HUB.md). Turns `levels` / `planet_locks` / `travel_lock`, `mission_order` and `random_start` off, with a note in the spoiler |
| `hub_start_coordinates` | 2 | Coordinates open at the start: 2 to 4, all different planets, each playable first |
| `hub_unlocks` | 1 | Coordinates each finished destination opens: 1 to 3 |
| `hub_finale` | `"all"` | `"half"`: the finale opens after half of the destinations |
| `hub_revisits` | true | false: second visits (Zurkie's 2, Sargasso 2, Savali 2) are not destinations |

In-game options (change any time): `hub_runtime`, `hub_trigger`, `hub_intro`, `hub_force_missions`,
`hub_replay`, `hub_levels`, `hub_travel_flag`, `hub_fly`, `hub_auto_return`, `hub_return_delay`,
`hub_hero_swap`, `key_hub` (F6) and `key_hub_return` (F5). HUB.md, "Settings", explains each one.

## Toggles

| Setting | Default | |
|---|---|---|
| `weapons` | true | the weapon pool (the vendor's 15, Pixelizer, Bouncer, plus restored weapons) is spread over the shop's 15 slots, the start and reward locations. false: the vendor sells as usual |
| `restored_weapons` | `"auto"` | ARSENAL_RESTORED's 9 weapons join the pool. `"auto"`: when the companion finds the mod installed (ARSENAL_RESTORED.md). `true`: always, **only with the mod installed**. `false`: never. (6.0 name: `include_arsenal_restored`) |
| `gadgets` | true | Box Breaker, Omniglove, Glitch |
| `armor` | true | the 27 findable armor pieces (helmets, chests, boots, each its own item) are rewards; every armor source is a location (ARMOR.md). Without armor there are too few items for 25 Gold Bolts, so `false` is turned back on with a warning |
| `levels` | false | **locked levels**: each planet's travel needs its Coordinates (LEVELS.md). Sets `planet_locks` and `travel_lock` |
| `mission_order` | `"vanilla"` | experimental reordered visits: `planet_shuffle`, `mission_shuffle`, `full`, `chaos` (played in the game's own order until mission control is verified). (6.0 name: `campaign_mode`) |
| `shop` | `"shuffle"` | `"shuffle"`: her 15 slots sell the seed's weapons (SHOP.md). `"vanilla"`: her own weapons |
| `bolts` | true | Bolts rewards at locations without an item |
| `raritanium` | true | Raritanium rewards at locations without an item |
| `planet_locks` | false | Coordinates are items. With `travel_lock = false` (6.0's behaviour) a planet's mission rewards wait for them; travel is free |
| `travel_lock` | false | with `planet_locks`: flying to a planet without its Coordinates sends you back |

## Currency

Every location that isn't a Gold Bolt and holds no item gives Bolts or Raritanium. Each location
gets its own amount, decided by the seed (the spoiler lists them).

| Setting | Default | Range | |
|---|---|---|---|
| `bolts_min`, `bolts_max` | 1,000 / 10,000 | 100-100,000 | Bolts per reward, rounded to 250 (50 under 1,000) |
| `raritanium_min`, `raritanium_max` | 20 / 150 | 1-5,000 | Raritanium per reward, rounded to 5 (1 under 50) |
| `bolts_budget` | 150,000 | 0-5,000,000 | the most all Bolts rewards give together; 0 = no limit |
| `raritanium_budget` | 2,000 | 0-500,000 | the most all Raritanium rewards give together; 0 = no limit |
| `bolts_percent` | 60 | 0-100 | with both on: the share of currency rewards that are Bolts |
| `currency_scaling` | true | | amounts grow with the planet's place in the story (first planet near the minimum, last near the maximum; armor pods in the middle). false: any amount in the range anywhere |

**Why these defaults.** The 15 shop weapons cost 255,250 Bolts in the normal game, so the default
budget (150,000) pays for about 60% of them over a whole playthrough; the rest is up to you. One
Raritanium reward of 20-150 is worth roughly 7-50 mini-boss drops (+3 each), so it's noticeable
without maxing your weapons. For "hundreds and thousands" of Raritanium, raise `raritanium_max`
(and the budget): the `chaos` preset goes up to 2,000 per reward. When the amounts drawn add up to
more than the budget, every reward is scaled down toward its minimum, and the spoiler's NOTES say
by how much. A minimum, multiplied by the number of rewards, that is already above the budget wins
over the budget (said in NOTES too).

## Shop prices

| Setting | Default | |
|---|---|---|
| `shop_prices` | `"weapon"` | `"vanilla"`: the game's prices. `"weapon"`: a slot costs what the weapon it now sells costs in the normal game (Headhunter 40,000 wherever it is). `"percent"`: every slot costs `shop_price_percent` % of its normal price. `"random"`: each slot a random % between `shop_price_percent` and `shop_price_max_percent` |
| `shop_price_percent` | 100 | 0-500 |
| `shop_price_max_percent` | 150 | 0-500 (random only) |

Prices are rounded to 50 Bolts. Pixelizer and Bouncer (1 Bolt in Challenge Mode) take the slot's
own price under `"weapon"`. Shatterbomb and RYNO 8 keep theirs. New prices are written only once
the shop script finds the vendor's own prices in memory (SHOP.md); otherwise her prices stay as
usual, which rivet.log says.

## Where rewards are

The 25 Gold Bolts, the first story mission of each planet and (with `armor`) the 27 armor sources
always are.

| Setting | Default | |
|---|---|---|
| `story_milestones` | true | the second story mission of each planet |
| `side_locations` | true | Zurkie's cups, Trudi, Blizar chef, Ardolis |

## Start

| Setting | Default | |
|---|---|---|
| `start_weapons` | 2 | random starting weapons (0-4). The shop's 15 slots take their weapons first, so without restored weapons at most 2; a higher value is lowered with a warning. The Burst Pistol is always there too (the game gives it) |
| `start_gadgets` | 1 | random starting gadgets besides Hoverboots and Map-O-Matic (0-2) |
| `start_items` | `""` | items you always start with, e.g. `"weapon:enforcer,glitch,armor:pirate_head"` (keys in WEAPONS.md / ARMOR.md / `data/game_db.json`). An item the seed doesn't randomize, or a weapon the shop's slots need, is ignored with a warning |
| `start_bolts`, `start_raritanium` | 0 | currency handed out with the start (0-100,000 / 0-5,000) |
| `start_coordinates` | `"first_two"` | with Coordinates: `start_only`, `first_two`, `random_extra`. With locked levels the story's own planets (Corson V, Nefarious City, Sargasso) are always open; `first_two` adds the next one (Zurkie's), `random_extra` a random later one |

## Logic

| Setting | Default | |
|---|---|---|
| `weapon_logic` | `"none"` | `none` / `light` / `standard`: weapons needed before later planets' rewards. Lowered automatically, with a warning, when the locations can't carry it |
| `accessibility` | `"full"` | full: every in-logic location reachable. beatable: progression items and planets only |
| `exclude` | `""` | item keys never randomized, e.g. `"weapon:enforcer,glitch"`. An excluded vendor weapon stays in its own slot; excluded Coordinates are owned from the start. Hoverboots and the Map-O-Matic can't be excluded |

When the settings leave too few places for everything, the generator relaxes them in this order
and says so: armor on, Coordinates on, weapon logic lower, one more planet open at the start,
Coordinates/levels off. A seed that can't fill all 25 Gold Bolts even then is refused, with the
reason.

## In-game options (change any time)

| Setting | Default | |
|---|---|---|
| `key_status` | F9 | status: Gold Bolts n/25, rewards, planets open, deliveries waiting. **Ctrl+F9 twice** (locked levels): open the planet you were last sent back from |
| `key_campaign` | F12 | experimental mission order only |
| `real_items`, `real_weapons` | true | put rewards into your real inventory |
| `armor_intercept` | true | armor sources give the seed's item instead of their own piece |
| `shop_runtime` | true | write the seed's weapons and prices into the vendor. false (or when that fails): the weapons only the shop would sell are given to you once |
| `levels_runtime` | true | locked levels: send you back from a locked planet. false: you stay, and its rewards wait for its Coordinates |
| `new_game_reset` | true | New Game starts the seed's progress over (the previous run's file is kept) |
| `discovery` | true | logs the events the randomizer hears (useful for bug reports) |
| `log_notifications` | true | HUD messages also go to rivet.log |

**Changed or removed.**
- 6.0's `filler` (`mixed` / `bolts` / `raritanium` / `none`), `filler_bolts` and
  `filler_raritanium` still work: they're converted to `bolts`, `raritanium` and their
  `_min` / `_max` (rivet.log says so).
- These options from earlier versions no longer exist. If they're still in your file, they're
  ignored and named in rivet.log:
  - 3.x: `key_shop_next`, `key_shop_buy`, `shop_slots`, `economy`, `luxury_slots`,
    `completion_gold_*`, `start_gold`, `gold_bolt_locations`;
  - 4.0: `armor_rewards`, `armor_finds`, `lock_vendor_weapons`;
  - 5.0: `include_hidden_weapons`, `experimental_pickups`, `experimental_collectibles`.

## Sharing a seed

The spoiler log's first lines contain a **share code**, e.g.
`RA7|lombax-ryno|chaos|bolts_max=20000`. Someone else gets the same seed with the same seed text,
preset and options, or in one step with `python tools/rando.py share "RA7|..."`. 4.0-6.0 codes are
refused, because the same text gives a different 7.0 seed.

## Spoiler generator (offline, optional: Python 3.9+ and `pip install lupa`)

```
python tools/rando.py generate --seed "my seed" --preset campaign --set bolts_max=20000
python tools/rando.py random --preset everything
python tools/rando.py share "RA7|my seed|campaign|"
python tools/rando.py presets
python tools/rando.py batch --count 5000 --random-settings 500
python tools/rando.py settings
```

`generate` writes `spoiler.txt`, `seed.json`, `settings.lua` and `00_rando_seed.lua`. Put the last
one in `<game>\scripts` to play exactly that pre-made seed; it then takes priority over
04_rando_settings.lua. The companion also writes every seed's spoiler log in the game
(`companion\randomizer_saves\spoilers`).

## rivet.toml, companion

`[scripts]` on, `[bridge]` on (companion), `[renderdoc] dll_path = "rando_give.dll"` (the
inventory helper), `[overlay]` on. Companion parameters: `-SaveDir`, `-PipeName`, `-IntervalMs`,
`-NewRandomSeed`, `-GameDir` (the folder of RiftApart.exe, for the ARSENAL_RESTORED check when the
game isn't running yet).
