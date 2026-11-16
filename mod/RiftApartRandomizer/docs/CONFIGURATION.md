# Configuration (10.0)

## scripts\04_rando_settings.lua

`seed` and `preset` choose the seed. Each randomization option is listed there commented out,
so remove `--` to set one. Changing the seed or any randomization option makes a **different
seed** with its own progress file; start it with New Game. Keys and in-game options can change at
any time. A wrong value is reported in rivet.log (`RANDO-SETTINGS ...`) and the preset's value is
used.

These are fixed: every Gold Bolt gives one item; Hoverboots and the Map-O-Matic are in the start;
every weapon has exactly one route (a shop slot, the start or a reward location, WEAPONS.md); the
solver proves every seed can be finished.

## 10.0: the hub, distribution, shop

| Seed setting | Default | |
|---|---|---|
| `hub` | `true` | New Game → Zurkie's Battleplex; choose the Prologue, the Battle Arena or Nefarious City; Coordinates open the rest (HUB.md). `false`: 9.0's story start |
| `distribution` | `"spread"` | items over Gold Bolts, story missions, side activities and armor pods; `"goldbolts_first"`: every Gold Bolt an item first (4.0-9.0) |
| `shop_weapons` | `8` | 0-15 different weapons Ms. Zurkon sells; her other normal slots are closed and those weapons are rewards |
| `early_weapons` | `2` | 0-6 weapons where the start alone can reach (with `weapon_logic = "none"`) |
| `coords_first_visit` | `true` | dev 10.11: Coordinates (and gadgets a location needs) are never on a revisit or the finale, and a planet's Coordinates are only where its first visit can be played the moment you find them (Viceron's: a reward of Torren IV's story). `false`: 10.1's placement |

A hub seed always has `planet_locks = true`, `travel_lock = true` and `campaign_mode = "planet_shuffle"`;
other values are noted in rivet.log and ignored. `start_coordinates` does not apply.

| In-game option | Default | |
|---|---|---|
| `hub_runtime` | `true` | `false`: no hub actions at all |
| `hub_trigger` | `"wrench"` | when New Game goes to Zurkie's; `"cinematic"`: at once |
| `hub_force_missions` | `true` | an inactive story mission is made available, then started |
| `hub_replay` | `true` | if starting fails, try the game's replay call |
| `hub_levels` / `hub_travel_flag` | `"all"` / `true` | level bits 1-10 and planetary travel on (round 17); v0.53: only while no destination runs (round 25) |
| `hub_fly` | `true` | to a landing pad, fly when a ship answers |
| `hub_auto_return` / `hub_return_delay` | `true` / `12` | back to Zurkie's after a finished destination |
| `hub_hero_swap` | `true` | the destination's hero is set first |
| `hub_follow_story` | `false` | `true`: when the game's own story takes you to an open destination, play it |
| `hub_follow_new` | `true` | dev 10.11: when the game's own story takes you to a planet whose **first visit** is open (its Coordinates held), play it there (the game just played its arrival) instead of going back |
| `hub_prime_open` | `true` | dev 10.11: between stories, the next visit of every open planet you are not on is made active (as the game does when a visit ends), so the ship's flight lands at its intro |
| `hub_planet_intro` | `true` | dev 10.11: a first visit is loaded at its intro (03 `intros`, `C.OPENINGS`) while its story has not left its first step. `false`: 10.0's start / landing order |
| `hub_blocked_home` | `true` | dev 10.11: landing on a planet whose first visit waits for another visit sends you back with the reason (never a revisit). `false`: you stay and explore |
| `key_hub` / `key_hub_return` / `key_story` | `]` / `[` / `/` | legacy F6 / F5 / F4; v0.54: `[` only cancels the automatic return |
| `key_shuffle` | `0` | v0.54: planet shuffle off / on (saved in the randomizer state); Ctrl+0 twice gives your items back |
| `restore_inventory` | `true` | v0.54: give your items back when a hub trip or a load reports fewer than half of your weapons |
| `shop_close_slots` | `true` | closed slots show the Burst Pistol; `false`: their own weapon |

## Presets

| Preset | Name | What it changes from the defaults |
|---|---|---|
| `balanced` | Balanced | **the kit's 04 file (9.0).** Nothing: your defaults (02's G.DEFAULTS since 8.5.1): every item system, Coordinates as items (a planet's mission rewards wait for them; travel is free), mission order `planet_shuffle` (played in the game's own order until verified), prices by weapon, Raritanium 120-1,000 |
| `chaos` | Chaos | locked levels with the fewest open planets; 1 starting weapon, no starting gadget; random prices (25-300%); Bolts 500-40,000 and Raritanium 10-2,000 per reward (budgets 350,000 / 10,000), half and half, not scaled by the story |
| `full` | Full Randomizer | Coordinates are items too: a planet's mission rewards wait for its Coordinates (travel stays free); Bolts up to 15,000, Raritanium up to 250 (budgets 180,000 / 3,000) |
| `campaign` | Campaign Randomizer | **locked levels** (LEVELS.md): flying to a planet needs its Coordinates; the story's own planets plus the next one open at the start |
| `everything` | Everything Randomized | locked levels (story planets only at the start), random prices (50-200%), 2,500 Bolts and 25 Raritanium at the start, Bolts up to 20,000 and Raritanium up to 400 (budgets 250,000 / 5,000) |

Older names still work: `standard`, `extended`, `armor` and `classic` are `balanced`, and
`coordinates` is close to `full`. The experimental mission-order presets are `planet_shuffle`,
`mission_shuffle` (6.0's `campaign`), `full_campaign` and `campaign_chaos` (LEVELS.md,
CAMPAIGN.md); in 9.0 every one starts with the prologue, Nefarious City and Sargasso.
`python tools/rando.py presets` prints this list.

**9.0: the hub is gone.** `hub` and `hub_chaos` become `balanced` and `chaos` (with a note); the
seed settings `hub`, `hub_start_coordinates`, `hub_unlocks`, `hub_finale`, `hub_revisits` and
`random_start` are ignored and named in rivet.log.

## Toggles

| Setting | Default | |
|---|---|---|
| `weapons` | true | the weapon pool (the vendor's 15, Pixelizer, Bouncer, plus restored weapons) is spread over the shop's 15 slots, the start and reward locations. false: the vendor sells as usual |
| `restored_weapons` | `"auto"` | ARSENAL_RESTORED's 9 weapons join the pool. `"auto"`: when the game has the mod's Mr. Zurkon item config loaded (8.4) or the companion finds the mod installed (ARSENAL_RESTORED.md). `true`: always, **only with the mod installed**. `false`: never. (6.0 name: `include_arsenal_restored`) |
| `gadgets` | true | Box Breaker, Omniglove, Glitch |
| `armor` | true | the 27 findable armor pieces (helmets, chests, boots, each its own item) are rewards; every armor source is a location (ARMOR.md). Without armor there are too few items for 25 Gold Bolts, so `false` is turned back on with a warning |
| `levels` | false | **locked levels**: each planet's travel needs its Coordinates (LEVELS.md). Sets `planet_locks` and `travel_lock` |
| `mission_order` | `"vanilla"` | experimental reordered visits: `planet_shuffle`, `mission_shuffle`, `full`, `chaos` (played in the game's own order until mission control is verified). (6.0 name: `campaign_mode`) |
| `shop` | `"shuffle"` | `"shuffle"`: her 15 slots sell the seed's weapons (SHOP.md). `"vanilla"`: her own weapons |
| `bolts` | true | Bolts rewards at locations without an item |
| `raritanium` | true | Raritanium rewards at locations without an item |
| `planet_locks` | false | Coordinates are items. With `travel_lock = false` (6.0's behaviour) a planet's mission rewards wait for them; travel is free |
| `travel_lock` | false | with `planet_locks`: flying to a planet without its Coordinates sends you back |
| `omega_weapons` | true (dev kit) | dev 10.15, Challenge Mode: the 20 Omega versions are rewards of their own (`omega:<weapon>`), on locations that would give currency; the rest of the seed stays the same. An Omega found first also gives its weapon; the weapon found later never undoes it (OMEGA.md) |
| `omega_runtime` | true | dev 10.15 (17_rando_omega.lua): false = Omega rewards are only recorded, the game's flag is never written |
| `omega_flag_offset` | -1 | dev 10.15, developers: the Omega flag's byte offset from the weapon's item id in its record; -1 = learned from two Omega purchases (OMEGA.md) |

## Enemies and bosses (dev 10.12; runtime only, the seed does not change)

| Setting | Default | |
|---|---|---|
| `enemy_randomizer` | true (dev kit) | the Enemy Randomizer's start for a save that never used its key |
| `boss_randomizer` | true (dev kit) | the Boss Randomizer's start for a save that never used its key |
| `key_enemies` | `"-"` | Enemy Randomizer on/off in the game (Ctrl: what it changed here) |
| `key_bosses` | `"="` | Boss Randomizer on/off in the game |
| `spawner_runtime` | true | false: neither changes anything |

| `chaos_randomizer` | false | dev 10.13: the Chaos Randomizer's start for a save that never used its key (NO protection, CHAOS.md) |
| `key_chaos` | `"BACKSPACE"` | Chaos Randomizer on/off (Ctrl: what it changed here) |
| `chaos_cross_planet` | true | Chaos's pool includes templates seen on every planet (false: this planet's only) |

The dev kit's 04_rando_settings.lua starts Omega, Enemy and Boss Randomizers ON. The in-game keys
still switch Enemy and Boss independently, and the save remembers your choice across New Game.
Omega is a seed option: changing it makes a new seed. CHAOS remains OFF and is separate; while Chaos
is ON the Enemy and Boss Randomizers pause. See ENEMIES_AND_BOSSES.md, OMEGA.md and CHAOS.md.

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
| `collectibles` | true | dev 10.1: the 10 Spybots and 12 Lorbs give rewards (never in logic; they pay once their pickup event is bound) |

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
and says so: armor on, fewer starting gadgets then weapons (8.5.2), Coordinates on, weapon logic
lower, one more planet open at the start, Coordinates/levels off. A seed that can't fill all 25 Gold Bolts even then is refused, with the
reason.

## In-game options (change any time)

| Setting | Default | |
|---|---|---|
| `key_status` | `;` | status: Gold Bolts n/25, rewards, planets open, deliveries waiting. **Ctrl+; twice** (locked levels): open the planet you were last sent back from |
| `key_campaign` | `'` | experimental mission order only (logs a line and does nothing in the game's own order) |
| `legacy_f_keys` | true | the old F7, F8, F9 and F12 keys work as well |
| `test_travel` | false | **8.4: off in the kit.** true: `.` / `,` go to any planet for testing (TEST_TRAVEL.md) |
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
  - 5.0: `include_hidden_weapons`, `experimental_pickups`, `experimental_collectibles`;
  - 9.0 (the hub's): `hub_runtime`, `hub_trigger`, `hub_intro`, `hub_force_missions`, `hub_replay`,
    `hub_levels`, `hub_travel_flag`, `hub_fly`, `hub_auto_return`, `hub_return_delay`,
    `hub_hero_swap`, `key_hub`, `key_hub_return`, `story_on_arrival`, `story_prime_before_travel`,
    `story_reload_stuck`, `story_restart_stuck`, `key_story`.

## Sharing a seed

The spoiler log's first lines contain a **share code**, e.g.
`RA9|lombax-ryno|chaos|bolts_max=20000`. Someone else gets the same seed with the same seed text,
preset and options, or in one step with `python tools/rando.py share "RA9|..."`. 4.0-8.5 codes are
refused, because the same text gives a different 9.0 seed.

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
