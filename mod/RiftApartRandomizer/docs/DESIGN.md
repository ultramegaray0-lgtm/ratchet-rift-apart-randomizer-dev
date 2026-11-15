# How the Randomizer works (7.0)

> **9.0:** 8.0-8.5's hub layer (15_rando_hub.lua) is removed; the design below is the whole randomizer again. RESEARCH_8.0.md keeps the hub's research.

## The rules of 7.0

1. **One Gold Bolt = one item.** Each of the game's 25 Gold Bolts holds exactly one item that the
   randomizer can really hand over: a weapon, a gadget, an armor piece or Coordinates. Picking the
   Gold Bolt up gives that item at once. No Gold Bolt holds currency or nothing.
2. **One weapon pool, one route per weapon** (WEAPONS.md, SHOP.md). The pool is the vendor's 15,
   Pixelizer and Bouncer, plus ARSENAL_RESTORED's 9 when the mod is installed. It is split per
   seed: 15 weapons go into Ms. Zurkon's 15 slots (each keeps its unlock point and, in 7.0, gets
   the seed's price), then the start, then reward locations. No weapon is sold and also a reward.
   Shatterbomb and RYNO 8 keep their own slots; cut configs are never placed.
3. **Hoverboots and the Map-O-Matic always start.** The rest of the start is random (2 weapons
   and 1 gadget by default), plus any `start_items` and start currency.
4. **Every item has one route.** A shop slot, the start, or one location.
5. **New Game starts the seed over.** Loading a save never does.
6. **Armor is randomized** (ARMOR.md): the 27 findable pieces are items, and every armor source
   is a location.
7. **Nothing gives nothing.** A location that is not a Gold Bolt and holds no item gives Bolts or
   Raritanium, each location its own amount from the ranges, scaled by the story and kept within
   a budget per currency (7.0).
8. **Locked levels** (7.0, `levels`): each planet's travel needs its Coordinates; the story's own
   planets are open from the start; the game's own travel is never blocked (LEVELS.md).

## The constraint everything follows

The planet menu, missions and story overlays follow the save's mission state. In your game
(round 15) every mission action takes the "system 2" branch, where the game's own actions can
start a mission only after the game itself has opened it, and nothing makes a mission available.
So **the story runs in the game's own order**, and the randomizer randomizes what you get, not
where the story goes:

- the 25 Gold Bolts, story missions, side activities and armor sources give the seed's items;
- the starting inventory is random (plus the two fixed gadgets);
- 7.0 locked levels: Coordinates lock each planet's **travel** (the story waits for them, and the
  solver proves they are always findable in time); or, with `planet_locks` alone, each planet's
  mission rewards;
- a progression solver proves the seed can be completed with the game's order.

The 3.x campaign layer (reordering the 14 planet visits) is still in the kit. It stays off until
mission control is verified in your game (CAMPAIGN.md); until then campaign presets play the
game's order with the seed's rewards, which is also proven finishable.

## Pieces

| Piece | File | Runs |
|---|---|---|
| Game database: items, locations, planets | `scripts/01_rando_data.lua` (built by `tools/build_data.py` from your dag and the 1.x model) | game + offline |
| Generator, solver, spoiler | `scripts/02_rando_generator.lua` | game + offline (`tools/rando.py`) |
| Campaign registry, order generation, campaign reach for the solver | `scripts/03_rando_campaign.lua` | game + offline |
| Capabilities verified in your game | `scripts/06_rando_capabilities.lua` (written by `tools/build_capabilities.py`) | game |
| Delivery into the real inventory | `scripts/09_rando_real.lua` + `rando_give.dll` | game |
| Runtime: triggers, Gold Bolts, New Game, finale, saving | `scripts/10_rando_runtime.lua` | game |
| Shop: the seed's slot map in the vendor config, compensation | `scripts/12_rando_shop.lua` | game |
| Armor sources and armor rewards | `scripts/13_rando_armor.lua` | game |
| Locked levels: the planet menu, the warp back, the escape hatch | `scripts/14_rando_travel.lua` | game |
| Weapon registry | `data/weapon_registry.json`, `docs/WEAPONS.md` (built by `tools/build_data.py`) | offline |
| Campaign director, mission research, lab | `scripts/11_rando_campaign.lua` | game |
| Saving, random-seed memory, spoiler file, previous runs, the ARSENAL_RESTORED check | `companion/RandoCompanion.ps1` | Windows |

## Items

| Category | Count | How it reaches you |
|---|---|---|
| Weapons | pool of 17 (the vendor's 15, Pixelizer, Bouncer) + 9 ARSENAL_RESTORED when enabled: 15 sold in the shop, the rest start or rewards. Shatterbomb and RYNO 8 in their own slots, Burst Pistol from the game's start, 11 cut configs never placed | shop: the vendor config; start and rewards: `rando_give.dll` → the game's own AddToInventory message |
| Gadgets | Hoverboots + Map-O-Matic (always start), Box Breaker, Omniglove, Glitch (randomized); the game's own kit (Swingshot, Helipack, Grind Boots, Rift Tether) is left alone | same |
| Coordinates | 10, with `levels` / `planet_locks` (the story's own planets start open) | randomizer key: opens the planet's travel (levels) or its mission rewards |
| Armor | 27 findable pieces (30 owned from the start on PC are left alone) | `rando_give.dll` v5 → the game's own GiveBundle (what VanityGiveBundleAction calls) |
| Currency | Bolts, Raritanium, any number of times, each its own amount (7.0) | `rando_give.dll` → AddToInventory with the currency item and a count (at most 100,000 per request) |
| Story abilities | 6 | given by the story only; the logic treats them as unavailable |

Without ARSENAL_RESTORED and with the defaults the reward pool has 29 items: 2 gadgets and 27
armor pieces (the 17 weapons fill the 15 shop slots and the 2 starting weapons; 1 gadget starts).
With the mod installed 9 more weapons are rewards; with levels, 7 Coordinates (10 minus the open
planets). Gold Bolts take weapons and gadgets first, then armor; the rest go to first story
missions, then other locations; everything else gives Bolts or Raritanium. If settings leave fewer than
25 grantable items, the generator turns armor back on, then Coordinates (they are items too). If
that is still not enough it refuses the settings and says why.

## Locations

| Kind | Count | Trigger | Default |
|---|---|---|---|
| Gold Bolts | 25 | GainGoldBoltEvent (seen in your game) | always on, one item each |
| First story mission of a planet | 10 | MissionStateChangedEvent (seen in your game) | on |
| Side activities | 6 | a bound mission name, otherwise paid with the planet | on |
| Second story mission | 9 | counting distinct missions | on (`story_milestones`) |
| Armor sources | 27 (9 take filler only, ARMOR.md) | the helper's armor-action ring; `rivet.vanity_owns` polling as fallback | on (`armor`) |
| Spybots / Lorbs (dev 10.1) | 10 + 12 | an event class you bind (none bound yet: out of logic) | on (`collectibles`) |
| CraiggerBears | 3 | an event class you bind | off |

There are more locations than items. Gold Bolts are filled first, then every planet's first
story mission, then the other missions, side activities and armor sources at random; what is
left gives Bolts or Raritanium.

### Which Gold Bolt is which

The game names a Gold Bolt like `"Sargasso 2"`. The runtime matches it to one of that planet's
Gold Bolt locations, preferring one whose requirements you meet. If the name is not known, the
planet you are on is used. If the data's split of Gold Bolts per planet ever disagrees with the
game, any Gold Bolt location still unclaimed pays. Every physical Gold Bolt you pick up gives one
item until all 25 are given. Each name counts once, also after a reload.

## Logic

The solver plays the seed sphere by sphere: what can be collected with what the previous spheres gave.

- **Story progress is free** without levels: every planet is reached eventually, because the game drives it.
- **Levels (7.0).** The 14 visits are walked in the game's own order; a visit needs its planet's Coordinates (and its gadgets and abilities), a location needs its visit reached and its planet open, Gold Bolts included.
- **Gold Bolts pay at once** with `planet_locks` alone.
- **Coordinates** (`planet_locks`). A planet's mission rewards pay only once you hold its Coordinates. Until then they are banked, never lost.
- **Gadgets.** A location needing the Omniglove counts only the randomizer's copy. Hoverboots are always owned from the start.
- **Abilities and unknown triggers.** Locations needing a story ability, or whose trigger isn't proven (armor, collectibles), are out of logic. They hold only non-progression items (a Gold Bolt of that kind still holds one weapon or gadget).
- **Weapon logic** (`light` / `standard`). The rewards of later planets need a minimum number of randomizer weapons, so weapons arrive early.

## Generation

1. **Normalize the settings.** 7.0 names (`levels`, `restored_weapons`, `mission_order`) and 6.0's filler settings are translated. Out-of-range or unknown values fall back to the preset's, with a warning; a min above its max is swapped. Retired settings are named as such. The fingerprint is a hash of `RA7`, the generator version, data version, seed text and settings.
2. **Start.** Hoverboots and Map-O-Matic, the open planets' Coordinates, `start_items`, then the random weapons and gadget; the shop's 15 slots and their prices (their own random stream).
3. **Count.** There must be at least 25 grantable items left, one per Gold Bolt.
4. **Assumed fill of the progression items.** Each item goes to a location reachable with everything not yet placed. When the remaining grantable items are exactly what the free Gold Bolts need, the item must go to a Gold Bolt.
5. **Gold Bolts.** Every Gold Bolt still empty gets one grantable item.
6. **The rest.** Remaining items go to first story missions, then at random to the other missions, side activities and armor sources (never to the 9 filler-only sources). Every location left gets Bolts or Raritanium with its own amount (their own random stream; the budget pass scales them down if needed).
7. **Verify** with the solver and audit: every Gold Bolt holds one grantable item, Hoverboots and Map-O-Matic start, no item has two routes, nothing sits behind itself (Coordinates never on their own planet), every amount in range, every total within budget. A reordered mission order is also solved in the game's own order. If anything fails, run another deterministic attempt. If settings leave too little room, the weapon logic is lowered or more planets open at the start, written to the warnings and the spoiler log.

**Determinism.** A 64-bit xoshiro256** generator seeded by FNV-1a. Every table walk is over sorted keys, so separate Lua states and processes give byte-identical seeds. The tests check this.

## Runtime state and saving

- The state of a seed: locations collected and paid, Gold Bolt names seen, items given, delivery status, run number.
- The companion saves it after every change (`randomizer_saves\rando_<fingerprint>.lua`, with `.bak`) and restores it after a game start or script reload. Restoring never hands anything out twice.
- **New Game.** The game reports `MIS_INTRO / OBJ_INTRO_PARADE_START_CINE / 1` only when a new game starts (rounds 14 and 15). Loading a save only shows the boot default `OBJ_INTRO_PROLOGUE / 1` (rounds 13-15). On a new game the run number goes up, progress starts over and the start is handed out again. The companion keeps the old run as `rando_<fingerprint>.run<N>.lua`. If the prologue starts before the companion has answered, the restored run is started over as soon as it arrives.
- **Without the companion** (fixed seed only), the randomizer plays after 60 seconds anyway and says that progress is not saved.
- **Shop.** `12_rando_shop.lua` rewrites the Item field (and, once the Price field is found by the slots' own prices, the price) of the vendor's weapon slots in memory every time the vendor config loads (SHOP.md).
- **Levels.** `14_rando_travel.lua` remembers the last planet-menu choice; a landing that follows it on a locked planet is undone with a warp after 3 seconds; anything else is never blocked (LEVELS.md). What it learned (landing checkpoints, sent-back count) is saved with the rest.
- **Armor sources.** `13_rando_armor.lua` keeps the helper's interception list equal to the open armor sources and pays a source when the helper reports it (ARMOR.md).
- **Currency.** Filler payouts wait in their own queue (saved), sent after any waiting item, one request each, never sent twice once the game took it.
- **Finale.** `MIS_MEGA_FINALE` (or any Megalopolis mission named FINAL...) completing shows "campaign complete" with the Gold Bolt count.
