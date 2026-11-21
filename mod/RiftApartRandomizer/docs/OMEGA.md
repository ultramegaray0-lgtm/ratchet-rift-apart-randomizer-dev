# Omega weapons (dev 10.15, kit 10.0.24)

Challenge Mode (New Game+) sells an **Omega** version of every weapon: it raises the weapon's level
cap from 5 to 10 and opens new upgrade nodes. The private dev kit now sets `omega_weapons = true` by default, so the seed has the 20 Omega
versions as **rewards of their own** (`omega:<weapon>`), next to the weapons themselves.

**Nothing of this has run in the game.** The generator, the ownership logic and the save are tested
offline; setting the game's Omega flag is tested only against the simulator, whose memory layout is
invented. `17_rando_omega.lua` is therefore held back from player packages.

## 1. How the game handles Omega weapons (research)

From the game's own type data (neptuwunium/rivet's DDL dump) and your dag:

| Finding | Where |
|---|---|
| There is **no Omega item**: none of the 919 item ids in your dag is an Omega config | `data/sources/dag_item_ids.json` |
| An Omega weapon is the weapon you own with the bool **`WeaponItemPrius.Omega`** set (hash `0x534A51FB`) | `Types/WeaponItemPrius.cs` |
| The record also holds the weapon's 64-bit item config id (`ItemPrius.ItemConfigHash`), XP, ammo and mods | `Types/ItemPrius.cs`, `WeaponItemPrius.cs` |
| The game sets it only through Ms. Zurkon: `VendorItemData.OmegaPrice`, `OmegaRequiredCardBonus` (a Holocard set), `OmegaOnly` | `Types/VendorItemData.cs` |
| Omega names and descriptions belong to the weapon's item config | `Types/WeaponItemConfig.cs` |
| The save knows `IsChallengeMode` and `FirstOmegaWeaponPurchased` | `Types/GameCampaignSave.cs` |
| No script action sets the flag (no give-Omega node exists) | the whole type list |

So:
- `AddToInventoryAction` (the randomizer's only way to give a weapon) can never give an Omega;
- giving the normal weapon never makes it Omega, and an Omega is never a second copy of the weapon;
- whether giving a weapon you already own touches its Omega flag is **not known** (the randomizer
  assumes the worst and checks, section 4).

Guides (vulkk, ludo.guide) list the Omega versions by their level-5 names (Omega Blast Pistol, Omega
Drillpack, Omega Blackhole Vortex ...). 14 of the 20 are listed by name; the other 6 (Shatterbomb,
Enforcer, Topiary Sprinkler, Void Repulser, Warmonger, Pixelizer) are assumed from "every weapon has
one". The 9 ARSENAL_RESTORED weapons and the cut weapons get no Omega item.

## 2. The item pool (generator, `omega_weapons`)

- Off (set `omega_weapons = false`): **every seed is exactly the 10.13 seed** (same fingerprint, same spoiler).
- On (the dev-kit default): the same seed - the same items in the same places, the same shop and start - plus the 20 Omega
  versions on locations that would otherwise give Bolts or Raritanium (their own random stream). The
  seed's fingerprint changes (its saves and share code are its own).
- Each Omega is placed once: never on a Gold Bolt, never in the shop, never as a random start weapon,
  never needed by the logic. `start_items = "omega:enforcer"` starts with one; `exclude =
  "omega:ryno_8"` leaves one out. Too few locations: the rest are left out, and the spoiler says so.
- The spoiler has an OMEGA VERSIONS section: each one's in-game name and where it is.

## 3. Ownership: weapon and Omega are separate rewards, the tier only goes up

Per weapon the randomizer keeps a tier: 0 not owned, 1 the weapon (`state.weapons`), 2 Omega
(`state.omega`). Each reward is recorded under its own key (`state.inventory["weapon:x"]`,
`state.inventory["omega:x"]`).

| What happens | Result |
|---|---|
| The weapon, then its Omega | The Omega upgrades the weapon you have. The weapon is **not sent again** |
| The Omega first, the weapon not owned | The weapon is given first (the Omega's prerequisite, `state.omega_prereq`); the reward recorded is the Omega; then its flag is set |
| The Omega first, then the weapon | The weapon reward is recorded; **nothing is sent**; the Omega stays ("you have its Omega version already (kept)") |
| Both in the same moment | One send of the weapon, then the flag |
| The same reward again (restore, replay) | Recorded once, nothing sent |
| Save / load | `omega`, `omega_prereq` are saved; a late companion restore keeps the furthest status (applied over pending) |
| A New Game (a new run of the seed) | The run's tiers start over. What was learned about your game (section 4) is kept |
| New Game+ (Challenge Mode) | Weapons the game carried over as Omega are seen and protected like the randomizer's own |

Without `17_rando_omega.lua` all of this still holds; only the game's flag is not written ("recorded").

## 4. Setting the flag in the game (`17_rando_omega.lua`, developer kit only)

Nothing is written at an offset that was not seen in your game:

1. **The record.** The hero's inventory component (`rivet.component(hero, "ItemInventory")`, then
   `ItemInventoryPrius`, `GridInventory`, `GridInventoryPrius`) is searched for an array of records
   holding the weapons' item ids - the search the shop already makes for the vendor's slots.
2. **The flag's byte is learned from the game.** When you enter a vendor, every weapon record is read.
   When you buy an **Omega** there (`PurchaseWeaponEvent` for a weapon you already owned), the bytes of
   that record that went 0 -> 1 are the candidates; a byte counts only if every other record holds it
   as 0 or 1 and at least one as 0. **Two Omega purchases of different weapons** must agree on exactly
   one byte (a Raritanium upgrade in the same visit can add candidates, never remove the real one).
   Then rivet.log says `RANDO-OMEGA LEARNED: the Omega flag is the byte at +0x..` and the HUD says so.
   A developer can skip this with `omega_flag_offset = <n>` in 04 once the offset is known.
3. **Writing.** Only for a weapon the game has confirmed in your inventory: the record's id is read
   again, the byte must read 0 or 1, `01` is written and read back. A byte holding anything else is
   never written (3 failures: that weapon is left alone for this load).
4. **Keeping.** After every load and every 10 s each Omega the randomizer gave, and each one the game
   showed as Omega, is read again; a cleared flag is set again (`RANDO-OMEGA kept ...`). So the
   inventory restore (Ctrl+0 twice), or a reward of the normal weapon, can never leave it non-Omega.
5. `omega_runtime = false`: nothing is ever written.

Until step 2 has happened an Omega reward says "recorded - set once the randomizer has found your
game's Omega flag" and waits; it is set the moment the byte is known.

## 5. Not known (needs the game) - TESTING.md 2-dev5

- Which component class name rivet_hook answers to for the hero's inventory, and whether the records
  hold the item config id as `ItemPrius` declares (`RANDO-OMEGA inventory: N weapon record(s)` or
  `inventory not found: ...` with the component's first bytes).
- Whether an Omega purchase reports `PurchaseWeaponEvent` (if not, nothing is learned and nothing is
  ever written - set `omega_flag_offset` from a byte dump instead).
- Whether the game honours the flag set from outside (level cap 10, the Omega name, the upgrade nodes),
  and whether it saves it.
- Whether an Omega outside Challenge Mode does anything (the setting is meant for Challenge Mode).
- Ms. Zurkon still sells Omega upgrades in Challenge Mode as usual (the slot fields `OmegaPrice` /
  `OmegaOnly` have not been located in memory, so they are not changed). Buying one there is the game's
  own route; a later Omega reward for that weapon is then simply recorded.


## 6. v0.61-DEV3 live-log correction (2026-11-21)

The current `rivet(3).log` does **not** identify the Omega flag or prove any successful Omega write:

- `rivet.components` was called with values from `GadgetItemAddedEvent.ItemHandle`,
  `InventoryHandle` and `WeaponLevelUpEvent.ItemHandle`. The game replied that these
  handles have no readable component list or are past the end of the scene. They are not
  valid scene-actor handles for this API.
- `rivet.find_component("WeaponItem")` fails because **WeaponItem is not a registered live
  component class**. `WeaponItemPrius` in the DDL dump is a DDL data type; that does not make
  `"WeaponItem"` a component class name.
- The log contains 37 `weapons not found` messages, zero `LEARNED` messages and zero confirmed
  `SET` / read-back results. Base-weapon purchase messages are not evidence that an Omega
  upgrade was purchased or that its flag changed.
- The DEV4 diagnostic ZIP's README described it as read-only, but its Lua still had code paths
  calling `rivet.set_field` and `rivet.write`. Treat that file as **not hard-disabled**. Do not
  run it as a diagnostic-only build until those paths are gated off.

The rivet_hook API documents `rivet.hero()` as the player's actor handle and
`rivet.components(handle)` as the way to list that actor's actual live component class names.
The next safe discovery step is therefore to enumerate components on the **hero handle**, not
on the event's item handles and not by guessing a DDL type name.

A read-only probe has been added at
`mod/RiftApartRandomizer/dev_scripts/dev(omega_inventory_probe).lua`. Copy it into the active
`GAME_FOLDER/scripts/` directory for one run, launch into live gameplay with the hero present,
then inspect `RANDO-OMEGA-PROBE` lines in `rivet.log`. It logs the hero's component class list
and metadata / first Prius bytes for component names containing item, inventory, weapon, equip
or loadout. It has no `rivet.write` or `rivet.set_field` call.

**No Omega runtime fix is claimed yet.** A component class and a record layout must be identified
from the live game before the flag can be safely read, much less written. The Omega memory
layout in the simulator is invented, not in-game evidence.


## 10.0.24 follow-up: hero component discovery

The runtime now falls back to one read-only enumeration of the live hero's component classes when
none of ItemInventory, ItemInventoryPrius, GridInventory, or GridInventoryPrius exists. It logs the
full class list and metadata / first Prius bytes for item, inventory, weapon, equipment, and loadout
candidates. A candidate is **not** automatically accepted as the inventory, and no memory is written
by this diagnostic. Omega flag discovery and actual Omega writes remain unverified and disabled
until the real inventory record and Omega byte are identified in-game.
