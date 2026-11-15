# The shop in 7.0

## What you see

Ms. Zurkon's weapon vendor works as usual (bolts, ammo, upgrades), but her 15 normal weapon
slots sell **this seed's weapons** at **this seed's prices**. Each slot keeps the point in the
story where it appears and unlocks; the weapon in it and (7.0) its price change. From a spoiler log:

```
prices: what the weapon sold costs in the normal game
the slot of Drillhound             sells Pixelizer                  10000 Bolts
the slot of Enforcer               sells Blackhole Storm            35000 Bolts
```

The seed's weapon pool has 17 weapons: the vendor's own 15 plus Pixelizer and Bouncer (which a
normal game sells only in Challenge Mode). Per seed, 15 of them go into the slots and the rest
to the start (2 by default) or, when more weapons are in the pool (ARSENAL_RESTORED), to reward
locations. So:

- every weapon in the pool has **exactly one** route: one slot, the start, or one location;
- no weapon is sold and also a reward; no slot sells the same weapon as another;
- usually no slot sells its own weapon (the order is reshuffled until it is a derangement);
- dev 10.1: Shatterbomb, RYNO 8 and the Burst Pistol are rewards at locations; the vendor slots
  Shatterbomb and RYNO 8 have in the normal game are closed (they show the Burst Pistol you own);
  ammo and upgrades are never touched.

Because every slot keeps its unlock point, you can buy as many weapons at each point of the
story as in the normal game, whatever the order.

## How it works

The vendor's stock is the config `VendorConfig.ItemDatas`, an array of `VendorItemData { Item,
Price, MissionShow, MissionUnlock, UnlockedInChallengeMode, OmegaPrice, OmegaOnly, IsAmmo }`
(game type data). `12_rando_shop.lua`:

1. lists the loaded vendor configs (`rivet.configs("VendorConfig")`),
2. asks `rando_give.dll` v5 where each one is in memory (the helper finds the config manager
   with rivet_hook's own signature and only reads it),
3. looks in the config's first 0x100 bytes for an array `{ pointer, count, capacity }` whose
   elements contain the item ids of registry weapons (64-bit ids from your game's dag: they do
   not appear by chance). The spacing of the matches gives the element size, their common
   position the Item field,
4. for every slot in the seed's map (`slot of X -> sells Y`), writes Y's id into the slot that
   holds X, reads it back, and marks the config by changing `UpgradeCellYOffset` by 1/16 of a
   pixel. Slots not in the map (Shatterbomb, RYNO 8, Burst Pistol, ammo, and anything another
   mod added) are left alone.

Configs reload with their level, which drops both the changes and the mark, so the map is
applied again after every load.

## Prices (7.0)

`shop_prices` decides what each of the 15 slots costs (CONFIGURATION.md): `"weapon"` (default: a
slot costs what its new weapon costs in the normal game, so a strong weapon in an early slot is not
cheap), `"percent"`, `"random"`, or `"vanilla"` (her own prices). The prices come from the guides
(gamepressure's weapon list): Enforcer 1,250, Mr. Fungi 3,000, Topiary Sprinkler 4,000, Negatron
Collider 5,000, Ricochet 6,500, Lightning Rod 8,000, Drillhound 10,000, Void Repulser 17,500, Cold
Snap 20,000, Glove of Doom 22,500, Bombardier 25,000, Buzz Blades 27,500, Warmonger 30,000,
Blackhole Storm 35,000, Headhunter 40,000 (all 15: 255,250 Bolts); Shatterbomb 1,250.

Where the Price field is in memory has not been seen in your game, so it is **found, not assumed**:
after the weapons are written, every slot's element is searched for that slot's own normal price,
as a 32-bit integer or float. Only a position where at least 3 slots hold their own price, and no
slot holds a different value, is used. Then each slot's new price is written there, in the same
encoding, and read back. If the guide prices don't match what your game holds, nothing is written
and her prices stay as usual (`RANDO-SHOP vendor ... prices left as they are - ...`). The weapons
are still shuffled either way.

## When the shop cannot be changed

The seed never strands a weapon. If the map cannot be applied, every weapon the seed put in the
shop that the normal vendor does not sell (Pixelizer and Bouncer, plus ARSENAL_RESTORED's when
that is on) is **given to you directly**, once, saved by the companion, with the message
"Shop: ..." on screen. That happens when:

- `shop_runtime = false`;
- rivet_hook has no config API, or the helper is older than v5 (after about 2 minutes);
- the array is not found after several tries;
- some slots of the map are missing from the vendor (only those slots' weapons are given).

The vendor's own 15 weapons are then still for sale in their usual slots.

## Settings

| Setting | Default | |
|---|---|---|
| `shop` | `"shuffle"` | `"vanilla"`: the vendor's slots are left alone; Pixelizer and Bouncer go to the start or reward locations instead |
| `shop_prices` | `"weapon"` | vanilla / weapon / percent / random (above) |
| `shop_price_percent`, `shop_price_max_percent` | 100 / 150 | percent and random |
| `shop_runtime` | true | in-game switch for step 4 and the prices; off = the compensation above |

## What rivet.log shows

- `RANDO-SHOP helper: config manager at 00007FF6C6ACBFE0 (exe +0x52EBFE0, rivet_hook's signature matched 1x)`
- `RANDO-SHOP vendor <id> at <address>: 15 weapon slots, 15 changed (element 0x.. bytes, Item at +0x.., array of N at +0x..)`
  followed by `drillhound->pixelizer ...` and `(kept)` for slots outside the map,
- `RANDO-SHOP vendor <id>: Price at +0x.. (u32, 15 slots held their own price): enforcer=35000 ...`
  (7.0) or `prices left as they are - <why>`,
- `also sells <weapon> in a slot of its own` (another mod or Challenge Mode),
- or why it was left alone and what was given instead (`Shop: ...`).

If the log says the slots were changed but the vendor screen still shows the usual weapons, the
vendor copies its stock somewhere else when a level loads. If the screen shows one weapon and
buying gives another, the slot keeps a second reference. Either way, send that rivet.log and set
`shop_runtime = false` meanwhile (the seed stays the same; Pixelizer and Bouncer are given).
