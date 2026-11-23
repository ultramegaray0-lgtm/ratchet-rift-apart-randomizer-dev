# Omega weapons (dev 10.15, kit 10.0.24)

Challenge Mode (New Game+) sells an **Omega** version of every weapon: it raises the weapon's level
cap from 5 to 10 and opens new upgrade nodes. The private dev kit now sets `omega_weapons = true` by default, so the seed has the 20 Omega
versions as **rewards of their own** (`omega:<weapon>`), next to the weapons themselves.

**Verified in the game (round52, DEV11):** the weapon records are found, the Omega byte is +0x88 from the
weapon's item id in a GameWeaponItem component, the randomizer's write takes effect, and six Omega purchases at
Ms. Zurkon turned that same byte on. (Older text below: "Nothing of this has run in the game.") The generator, the ownership logic and the save are tested
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


## v0.62-DEV5 (kit 10.0.25): the live components, start_omega, a developer compare

- Round45 listed the live hero's item components: GameInventoryManager (8552 bytes), HeroWeaponManagerLocal (2080),
  GameEquipManager (872), VanityInventoryManager (17640). `O.CLASSES_LIVE` searches the first three (after the four
  old names) for the same proof as before: an array whose elements hold the weapons' 64-bit item ids. The search reads
  the whole component (at most `O.MAX_HEADER` = 0x2200 bytes) in a job, never in one frame.
- When records are found, each one's first 0x180 bytes are logged once (`RANDO-OMEGA record <weapon> ...`): a save that
  already owns an Omega weapon shows its byte as 01 where the others hold 00.
- `start_omega = 1` (dev settings): every new game starts with one random Omega version, its weapon given first. The
  reward waits ("recorded") until the flag's byte is known; then it is set at once.
- Learning the byte: two Omega purchases at Ms. Zurkon (Challenge Mode), as before, OR dev(debug).lua: NUMPAD1 reads
  every record, make ONE weapon Omega (buy it), NUMPAD2 lists the bytes that went 0 -> 1, Ctrl+NUMPAD2 takes a single
  candidate as this save's flag. Or set `omega_flag_offset` in 04 once the byte is known.
- Still not seen in the game: whether one of these components holds the records, and whether the game honours a flag
  set from outside (levels 6-10, the Omega name).


## v0.62-DEV6 (kit 10.0.26): why round46's purchases taught nothing, and what changed

See CHANGELOG "v0.62-DEV6". In short: wrong components searched (the inventories are found by handle now, through the
hero's own component list), the wrong purchase event (Omega = VendorPurchaseEvent alone), a "before" read that was never
taken (EnteredVendorEvent does not come; the read is taken when the records are found and refreshed), and a search that
overran the frame budget. To teach the byte: buy Omegas of two different weapons, a few seconds apart, and look for
"RANDO-OMEGA LEARNED". If rivet.log still says "inventory not found", send it: it now lists every hero component
("hero components: ...", 12 per line) and each searched candidate with its handle.


## v0.62-DEV8 (kit 10.0.28): round48 - the walk was stopped by the frame budget

DEV7 ran in the game, but the hero's component walk was killed 19 times by rivet_hook's 8 ms budget and never finished.
The search now runs only in frames with room (`O.FRAME_ROOM`), in 1.5 ms slices (`O.SLICE_SECONDS`), and the walk resumes
where it stopped (`O.wstate`). Omega weapons are sold only in Challenge Mode: teaching the byte needs a Challenge Mode
save. The learned byte is stored in state and used in later games, including normal ones.


## v0.62-DEV9 (kit 10.0.29): round49 - inventories by handle through the SceneManager

DEV8's walk finished in the game (141 components), but the inventories that InventoryChangedEvent names on the hero
are not in the hero's component list. They are now resolved by handle through the SceneManager (rando_give.dll v7,
`O.resolve`), searched first, and arrays of u32 item handles are read as well (`O.records_handles`). The first few items
GadgetItemAddedEvent names are logged with their class and first bytes (`O.probe_item`) to learn the item layout.


## v0.62-DEV10 (kit 10.0.30): round50 - no learning: the game's own type data

Round50 confirmed the DEV9 handle lookup in the game but the search was starved and cut by a level change. DEV10
stops searching inventories: the weapon records are the scene's components whose class carries the WeaponItemPrius
type (`O.ddl_find`, through `SceneManager.componentLookups`), and the Omega byte's place is read from that type's live
field table (`O.weapon_layout`: ItemConfigHash +48, Omega +184 in rivet's DDL dump, +0x88 from the id). So **no
Challenge Mode purchase is needed**: `O.offset()` answers "the game's type data" as soon as the census has read the
type, and Omega rewards are written once the weapon is confirmed. Writes need the live field table and a record owned
by the hero's actor. A purchase now only confirms the byte. `omega_flag_offset` still overrides; learning
(`state.omega_cal`) is only the fallback when the type-data route finds nothing.


## v0.62-DEV11 (kit 10.0.31): round51 - GameWeaponItem, fields in the instance

The DEV10 census ran in the game and found 33 `GameWeaponItem` (and 4 `GameMeleeWeaponItem`) components, whose class
prius is plain ItemPrius; items keep no prius holder. Weapon items are now taken by class name, the weapon id is found in
the instance, and the Omega byte (+0x88 from the id, WeaponItemPrius's own order) is trusted only if the neighbouring
fields check out in (nearly) every weapon record: ItemCount 1, sane ammo floats, a sane Test list, Omega 0/1.


## v0.62-DEV12 (kit 10.0.32): round52 - verified

Omega works in the game. The randomizer's Omega Ricochet was applied, and six purchases at Ms. Zurkon confirmed the
byte. Fixed: the game's own Omegas are forgotten at each load, so another save never inherits them. The status line
counts the seed's Omega rewards.
Item pool: `omega_weapons` is ON by default now (G.DEFAULTS), and Omega versions never go to Spybots / Lorbs (their
pickup events are not bound yet). A seed made with the old default needs `omega_weapons = false` to stay the same.


## DEV13 (kit 10.0.33): round53 corrections

- **SelectedCell is not a sanity field.** Weapons with upgrades read 118-216 at id +112; the "< 64" rule made every
  round53 census untrusted. The trust check is now ItemCount +8 = 1, ammo floats +20/+24, Test list +120, Omega +136
  = 0/1 (>= 90% of the records, at least 3).
- **Two sets on the hero.** GameEquipInventory holds the weapons you own; GameOverrideInventory holds copies (ItemCount
  0 except during some arena challenges). Only GameEquipInventory (else the hero's actor) is written.
- **Checkpoint loads rebuild item components.** A census or record set from before a `CheckpointTriggeredEvent` with
  `Loaded=true` is dropped.
- **Carried-over weapons.** A trusted record with ItemCount 1 and XP > 0 counts as owned: the Omega is set without a
  prerequisite send.


## v0.71-DEV2 (kit 10.0.37): an empty record is never written; early Omega for the test

round54 wrote the Omega flag of Negatron Collider (a start gift) onto a record the game did not hold:

| | slot (+12) | XP (+16) | ammo (+24) |
|---|---|---|---|
| Pixelizer, given in Zurkon (event 1005) | 1005 | 317740 | 16 / 16 |
| Negatron Collider, given in the intro (event 1002) | **5015** | 0 | 0 / 0 |

The game numbers the weapons the hero owns from 1001 (the WeaponType of `WeaponAddedEvent`); every other record keeps
5000 + n. `O.empty_slot` (slot >= 5000, XP 0, ammo 0) is now checked before any write and any "applied". A weapon whose
record stays empty after the game said "added" is sent again after 900 frames (`RANDO_REAL.regive`, at most twice per load).
The likely cause (not proven): what the randomizer hands over during the Nefarious City intro does not survive the intro.

Test settings (dev defaults): `omega_early = true` (generator: the Omega versions go on the first locations the start can
reach, never on Gold Bolts / Spybots / Lorbs) and `omega_test = 6` (runtime: weapon rewards arrive as their Omega version
until 6 Omega weapons are held). The spoiler still lists weapon:x for a reward that `omega_test` turns into Omega.
