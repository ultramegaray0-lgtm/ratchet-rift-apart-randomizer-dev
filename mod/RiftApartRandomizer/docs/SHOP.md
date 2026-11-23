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


## v0.62-DEV5: why the dev kit uses shop = "vanilla"

Every round from 17 to 45 logged "only 0 vendor weapon(s) in the array at +0x48" (inline and pointer layouts both
tried) and then "Ms. Zurkon could not be changed". With shop = "shuffle" the seed still made some of her weapons
rewards (Gold Bolts, missions), and she kept selling them: the same weapon could be bought AND found. The dev settings
now use shop = "vanilla": she sells her usual weapons and none of them is ever placed as a reward, so every weapon has
exactly one route. "shuffle" stays available for when the slot array is found.

For that, 12_rando_shop.lua logs once per vendor config and session what rivet.config() answers (field names, types,
the first entry of any list): `RANDO-SHOP PROBE vendor config <id> VendorConfig fields: ...`. If ItemDatas shows up as
a list of entries with an Item field, rivet.config_set may reach the slots by path without any memory offset.

## v0.71-DEV1: the slots as config pointers

`rivet.config()` cannot list `ItemDatas`: rivet_hook's `ddl::values_of()` skips arrays of structs, so the DEV5
probe only ever showed the nine plain numbers. The search therefore also treats an 8-byte field as a weapon when it
equals the address of that weapon's loaded `*_item.config` (asked from `rando_give.dll`, kind 7, after every load).
The dev settings use `shop = "shuffle"` again. What `rivet.log` shows:

- `RANDO-SHOP weapon configs in memory: N of M weapons asked for`
- `RANDO-SHOP vendor <id> at <addr>: 15 weapon slots, 15 changed (..., Item at +0x.. as a config pointer, ...)`, or
- `RANDO-SHOP EVIDENCE ...` (once): the config's first bytes, its arrays' first bytes and some looked-up addresses.
  Send that log: it shows what the slots hold.

If the vendor screen still shows her usual weapons after "changed", the vendor copies its stock when a level loads;
if it shows one weapon and buying gives another, something else names the item too. `shop = "vanilla"` (or
`shop_runtime = false`) goes back to her usual weapons.

## v0.71-DEV3: shop bonus (2 weapons, 2 Omega, 2 gadgets, 2 armor)

Root cause of the old failure: the item id in each vendor element is a u64 at element +20, which is only 4-byte
aligned. The search stepped 8 bytes, so it never matched. It now steps 4 bytes and takes the element size from the
vtable repeats.

shop_bonus = true adds six locations (shop:armor_1/2, shop:gadget_1/2, shop:omega_1/2). Their items come from other
locations (never one the logic needs; Gold Bolts only with distribution = "spread"). Buying a shop weapon slot pays
its bonus ("Shop bonus: ..."). The spoiler has a SHOP BONUS block. shop_bonus = false leaves seeds unchanged.
Only 3 randomizable gadgets exist, so you may get 1 gadget bonus, not 2.

## v0.71-DEV5: why no bonus was ever paid, and the shop items

Round 57 (rivet.log of DEV4): the 28 slot writes held (VERIFY 28 of 28) and Ms. Zurkon sold the seed's weapons, but every
purchase logged "not a weapon of this kit's registry: no bonus checked". PurchaseWeaponEvent names a weapon WEAPON_MRFUNGI
while its config is wpn_mrfunguy_item.config; the old lookup built "wpn_" .. name .. "_item.config" and missed it.
`H.weapon_of_purchase(name, config)` now matches the event's WeaponConfig (a double: id rounded to 2048, so within 4096)
and then the name with everything but letters and digits dropped, against the config name, the key and the display name.

The field dump, the unknown-entry list and the prices used to run in the frame of the slot writes and were killed by the
8 ms budget (a budget error inside a pcall is swallowed; the prices line is the one that was logged). They run in the next
frames now, from the copy of the array read before the seed was written (no memory reads), and each price write is
checked against the slot first. `RANDO-SHOP EVIDENCE field +0x..` lists, per 4-byte word of the element, the entries that
differ from the most common value: that is where Price, MissionShow, MissionUnlock, OmegaPrice, OmegaOnly and IsAmmo are.

Four entries of the vendor (index 4, 8, 31, 32 in round 57) are none of the registry's weapons (one is the Dimensionator).
They are left alone; `EVIDENCE N entries sell something this kit's registry does not know` gives their ids.

shop_show_items (04_rando_settings.lua): "notify" (default) = bonuses ride on the weapon bought, announced; "try" = EXPERIMENT,
each gadget / armor bonus is also written into a closed slot by its own item id (the closed slots nearest to the open
ones), the vendor screen may not accept a non-weapon; the purchase event of such a slot carries the item's id and pays
the item (H.hosted); "off" = nothing announced. Omega bonuses are not hosted: an Omega is a weapon's own flag.

## v0.71-DEV9: a bonus on a weapon you already own

Her screen shows a weapon you already own as owned, and nothing can be bought in that slot (that is how the closed slots work).
So a bonus riding on a weapon you hold could never be paid - round 61's save held every weapon of the seed's shop. Now, once the
weapon a bonus slot sells reads as yours in two looks ~5 s apart, the bonus is given directly ("Ms. Zurkon: you already have the
Enforcer - Box Breaker is yours"). Yours = the randomizer confirmed it, the game showed it (equipped, bought), the shop gave it
directly, or your weapon records hold it (17_rando_omega.lua, `RANDO-OMEGA held: ...`). A purchase always pays first, never twice.
`shop_pay_owned = false` waits for a purchase as before. rivet.log: `RANDO-SHOP OWNED ...`.

## v0.71-DEV8: written once, even when a try is cut off

Round 60: the first write to Ms. Zurkon's slots was cut off by rivet_hook's 8 ms frame budget, and the next try read the
weapons it had written as the slots' own and shuffled them again (only 4 of 8 weapons were for sale). Every slot write is now
remembered for the session (address, the slot's own weapon, the value written) before it is made, so a later try finds the
same slots and writes the same stock; prices likewise. A slot of the seed's shop that this vendor lacks sells its weapon - and
its bonus - in one of the vendor's closed slots (rivet.log: `RANDO-SHOP ... REROUTE`); only with no closed slot left is the
weapon given directly. Closed slots still show the Burst Pistol you own; `shop_weapons` (0-15) sets how many weapons she sells.
