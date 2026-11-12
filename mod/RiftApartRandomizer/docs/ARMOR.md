# Armor (5.0, unchanged in 6.0 and 7.0)

## What you see

- **Armor pieces are rewards.** A Gold Bolt or a mission can give "Q-Force chest". It goes into
  your armor through the game's own armor code (the same calls the game's "give armor" script
  action makes), so it shows in the armor menu, counts for set bonuses, and is saved like any
  piece you found.
- **Armor sources give the seed's item instead of their piece.** When a pocket dimension's armor
  pod, a Zurkie's challenge or the Lorb monk would hand you a piece, you get the item the spoiler
  lists for that source: "Armor pod (Robot Pirate helmet): Thumper". It can be a weapon, a
  gadget, another armor piece, Bolts or Raritanium.
- Each source pays once. If the game runs the same source again (a replay), you get its own piece.
- Pieces you owned before the seed started (the 30 of the Deluxe Edition and free sets on PC)
  never count.

## How it works

`rando_give.dll` v5 replaces the handler of `VanityGiveBundleAction` (RVA 0x880720, checked
byte for byte against your exe; identical in your round 14 and round 15 code dumps). The new
handler makes exactly the same three calls (resolve the hero, find its VanityInventoryManager,
GiveBundle) and fires the same output plug, except for a piece Lua listed in the helper's
mailbox. For a listed piece nothing is given, the "success" plug fires (so the level script goes
on), the entry is removed, and the event goes into a ring. `13_rando_armor.lua` keeps the list
equal to the seed's armor sources that are not collected yet, reads the ring, and collects the
source's location.

**Fallback.** If the helper is older than v5, its hook is not installed, or a source uses some
other path, the piece arrives as usual. Every few seconds the script asks the game which pieces
you own (`rivet.vanity_owns`); a new piece the randomizer did not give collects its source then
("found by polling"). You keep that piece as well.

## The 8 sets (27 pieces)

From the guides (IGN, GameSpot, PowerPyx, Push Square): 8 sets, 24 pieces, from pocket
dimensions, Zurkie's challenges and the Lorb monk on Savali. In the game files they are these
folders of `configs/hero/vanity/vanitybundles/`:

| Set | Folder | Sources hold |
|---|---|---|
| Galactic Ranger | `galactic ranger` | any item |
| Robot Pirate | `pirate` | any item |
| Carbonox Advanced | `carbonox_armor` | any item |
| Lombax Praetorian | `lombax_armor` | any item |
| Q-Force | `qforce_armor` | any item |
| Captain Starshield | `starshield_armor` | any item |
| Robot Disguise, Wasteland Gear | two of `punk_armor`, `reaver_armor`, `warmachine_armor` | filler only |

Which two of the last three folders are Robot Disguise and Wasteland Gear is not in the game
files, so the randomizer names those pieces by folder ("Punk helmet"), and their sources only
hold Bolts or Raritanium: the folder the game never hands out costs nothing. All 27 pieces are
rewards either way. When your round 17 log shows which folders the game gives, the names and
the filler-only rule can be fixed (`RANDO-ARMOR source <name> intercepted`).

The 10 sets owned from the start on PC (Android, Imperial, Rebel, Holoflux, Quest, Marauder,
Commando, Clank, the default outfit, the Carbonox pre-order set) are not randomized. The demo
outfit is not a set you can own.

## Settings

| Setting | Default | |
|---|---|---|
| `armor` | true | armor pieces are rewards and armor sources are locations. Without armor the 25 Gold Bolts cannot all be filled (the vendor's weapons stay in the shop), so `false` is turned back on with a warning |
| `armor_intercept` | true | in-game switch: `false` lets every source give its own piece (its location still pays, through the ring or polling) |

## What rivet.log shows

- `RANDO-ARMOR helper: armor give verified, armor sources on` at the start.
- `intercepting 27 armor source(s)`, then one fewer for each source collected.
- `RANDO-ARMOR source <piece> intercepted source:<id>` when a source pays its item.
- `found by polling` when a piece arrived another way.
