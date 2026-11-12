# Moving from 8.3 to 8.4

**No new seed needed.** 8.4 gives the same seeds as 8.3 (same fingerprint), so progress carries
over; a New Game is still the best way to play a full run.

1. Delete every old randomizer `.lua` file from `<game>\scripts`, then copy the **14** new ones
   (every one changed: each now carries its kit version, checked at start as `RANDO-KIT`).
2. `rando_give.dll` is unchanged (v6). Replace `rivet.toml` and the `companion` folder anyway.
3. Use the kit's `04_rando_settings.lua`: it has `story_prime_before_travel`, `story_reload_stuck`
   and `test_travel = false`. 8.3's `story_restart_stuck` is retired (rivet.log names it).
4. Saved 8.3 state is cleaned up on load: wrong weapon-type lessons are dropped, and landings
   remembered from test trips move to test travel's own list.

What changed for you: see CHANGELOG.md.

# Moving from 7.0 to 8.0

**Start a NEW GAME for an 8.0 seed** (on a spare slot: 8.0 is experimental and may break saves).
Generator 8.0 gives different seeds for the same text (share codes start with `RA8`; `RA4`-`RA7`
are refused). Your 7.0 progress files stay in `companion\randomizer_saves` untouched.

1. Delete every old randomizer `.lua` file from `<game>\scripts`, then copy the **13** new ones
   (`15_rando_hub.lua` is new).
2. **Replace `rando_give.dll`** next to RiftApart.exe: 8.0 needs v6 (the hub's mission and level
   requests). v6 does everything v5 did. Replace the `companion` folder too (version text only).
3. Use the kit's `04_rando_settings.lua`: its preset is now `hub`. If you keep your 7.0 file, add
   `preset = "hub"` for the hub; every 7.0 preset still works and plays like 7.0.
4. The hub's keys are F6 and F5 (HUB.md). Change them with `key_hub` / `key_hub_return` if they
   clash with something.

What changed for you: see CHANGELOG.md and HUB.md.

# Moving from 6.0 to 7.0

**Start a NEW GAME for a 7.0 seed.** Currency amounts, prices and levels changed the seed format,
so the same seed text gives a different seed (share codes start with `RA7`; `RA4`-`RA6` codes are
refused). Your 6.0 progress files stay in `companion\randomizer_saves` untouched.

1. Delete every old randomizer `.lua` file from `<game>\scripts`, then copy the **12** new ones
   (`14_rando_travel.lua` is new).
2. `rando_give.dll` is unchanged (v5). Replace `rivet.toml` (unchanged, harmless) and the
   `companion` folder (it now checks for ARSENAL_RESTORED).
3. Use the kit's `04_rando_settings.lua`. If you keep your 6.0 file:
   - `filler`, `filler_bolts`, `filler_raritanium` are converted (`bolts_min = bolts_max =
     filler_bolts`, ...);
   - `include_arsenal_restored`, `campaign_mode` still work (7.0 names: `restored_weapons`,
     `mission_order`);
   - preset `standard` is `balanced`; preset `campaign` now means **locked levels** (6.0's
     `campaign` is `mission_shuffle`);
   - new options (currency ranges, prices, levels, `start_items`) use their defaults.
4. ARSENAL_RESTORED: leave `restored_weapons = "auto"`; keep the mod installed for its weapons.

What changed for you: see CHANGELOG.md.

# Moving from 5.0 to 6.0

**Start a NEW GAME for a 6.0 seed.** The weapon pool, the shop and the seed format changed, so
the same seed text gives a different seed (share codes start with `RA6`; `RA4` and `RA5` codes
are refused). A 5.0 seed file is not loaded; your 5.0 progress files stay in
`companion\randomizer_saves` untouched and can be deleted.

1. Delete every old randomizer `.lua` file from `<game>\scripts` (also `00_rando_seed.lua` and
   `07_rando_testmode.lua` if present), then copy the **11** new ones. Same file names as 5.0.
2. `rando_give.dll` is unchanged (v5); copying it again does no harm. Replace `rivet.toml` and
   the `companion` folder.
3. Use the kit's `04_rando_settings.lua`. Removed: `include_hidden_weapons`,
   `experimental_pickups`, `experimental_collectibles` (if you keep your old file they are
   ignored and named in rivet.log). Changed defaults: `include_arsenal_restored = false`,
   `weapon_logic = "none"`. Preset `classic` is now the same as `standard`.
4. ARSENAL_RESTORED is no longer needed. You can leave it installed or remove it in Overstrike
   (ARSENAL_RESTORED.md). If you keep it and want its weapons in the pool, set
   `include_arsenal_restored = true`.

What changed for you:
- Ms. Zurkon's 15 slots sell the seed's weapons, including Pixelizer and Bouncer; the rest of
  the pool is in your start. Every weapon has exactly one route;
- no cut or hidden weapon and no untested pickup is ever a reward;
- if the shop cannot be changed, the weapons only it would sell are given to you;
- without ARSENAL_RESTORED most story missions give Bolts / Raritanium (the items run out after
  the Gold Bolts: FEATURES_AND_LIMITATIONS.md).

# Moving from 4.0 to 5.0

**Start a NEW GAME for a 5.0 seed.** The data and the generator changed (weapon configs, shop,
armor, filler), so the same seed text gives a different seed (share codes start with `RA5`).
Your 4.0 progress files stay in `companion\randomizer_saves` untouched.

1. Delete every old randomizer `.lua` file from `<game>\scripts`, then copy the **11** new ones
   (two are new: `12_rando_shop.lua`, `13_rando_armor.lua`).
2. Replace **`rando_give.dll` (now v5)** next to RiftApart.exe. The armor and shop features need
   it; with the old v4 they fall back (armor by polling, shop left alone) and rivet.log says so.
3. Replace `rivet.toml` and the `companion` folder.
4. Use the kit's `04_rando_settings.lua` (4.0's `armor_rewards`, `armor_finds`,
   `lock_vendor_weapons` are gone; if you keep your old file they are ignored and named in
   rivet.log).

What changed for you:
- the Blackhole Storm arrives (4.0 sent a cut weapon's config);
- the vendor works again (ammo too) and sells its weapons in shuffled slots;
- armor pieces are rewards, and armor pods give random items;
- missions, side activities and pods with no item give Bolts or Raritanium.

# Moving from 3.x to 4.0

**Start a NEW GAME for a 4.0 seed.** 4.0 changes the generator (one item per Gold Bolt, no
shop), so the same seed text gives a different seed with a new fingerprint. Your 3.x progress
files stay in `companion\randomizer_saves` and are not touched.

1. Delete every old randomizer `.lua` file from `<game>\scripts`, then copy the 9 new ones.
2. Replace `rivet.toml` and the `companion` folder. `rando_give.dll` is unchanged (v4); copying
   it again does no harm.
3. In `04_rando_settings.lua`: 3.x shop and economy options (`shop_slots`, `economy`,
   `key_shop_next`, ...) are gone. If you keep your old file, they are ignored and named in
   rivet.log. The kit's new file lists what exists now.

What changed for you:
- every Gold Bolt gives one item at once; there is no shop, no F7/F8, no Gold Bolt prices;
- Hoverboots and Map-O-Matic are always in the start, plus random weapons and a gadget;
- New Game starts the seed over by itself (the previous run is kept as `rando_<fp>.runN.lua`);
- the vendor does not sell weapons;
- `planet_locks` (Coordinates) is off by default (preset `coordinates` turns it on), and it never
  holds back a Gold Bolt's item.

# Moving from 3.0/3.1 to 3.2 (earlier)

**No new save needed** (the generator is unchanged, 3.0.0). Replace the 9 files in
`<game>\scripts`, the `companion` folder, and **`rando_give.dll` (now v4)**. 3.2 talks to the
mission system your game actually runs (CAMPAIGN.md); 3.1's reader of the other one is gone.

# Moving from 3.0 to 3.1 (earlier)

**No new save needed.** The generator is unchanged (version 3.0.0), so the same seed text and
settings give the same seed and fingerprint, and the companion restores your 3.0 progress.

1. Replace all files of `<game>\scripts` that 3.0 installed with the 3.1 ones (same 9 names).
2. **Replace `rando_give.dll`** next to RiftApart.exe with the 3.1 one (v3). Item delivery is the
   same code; v3 adds the game's own mission calls, which stay unused until the tests in
   CAMPAIGN.md verify them.
3. The companion and its research tools: replace the `companion` folder.

What changed: the campaign lab and director (CAMPAIGN.md), F12/Ctrl+F12/Ctrl+F11 meanings
in test mode, the research tool's lists, and four registry mission names your game reported.

# Moving from 2.0 to 3.0

**Start a new game save for a 3.0 seed.** 3.0 adds two settings (`campaign_mode`,
`random_start`), so even a 2.0 seed text with the same preset gives a **different seed** (new
fingerprint, different placements). A campaign seed also tracks your place in the campaign
order, and that only makes sense from the start of the story.

Your 2.0 run is not lost:

- Your **game save** is untouched.
- Your **2.0 progress** stays in `companion\randomizer_saves\rando_<fingerprint>.lua`. 3.0 never opens a file of another fingerprint. To continue the 2.0 run, keep the 2.0 scripts.
- Items 2.0 put into your inventory stay in that save.

## Steps

1. Back up `Documents\Ratchet & Clank Rift Apart`.
2. In `<game>\scripts`, delete all randomizer `.lua` files (`00_` to `11_` `*rando*`).
3. Copy the 3.0 `scripts` folder contents (9 files: `01`-`06` and `09`-`11`, see INSTALL.txt). `rando_give.dll` is unchanged. The 3.0 companion replaces the 2.0 one, and its save format is the same.
4. Choose a seed and preset in `04_rando_settings.lua`, start the companion, then **New Game** in a free slot.

## What changed for you

| 2.0 | 3.0 |
|---|---|
| The campaign always ran in the game's order | `campaign_mode` and 4 campaign presets: the order of the 14 planet visits is randomized and proven finishable (in the game: after the capability tests, CAMPAIGN.md) |
| Starting Coordinates: the first planets | in campaign seeds, the first planets *of the campaign order* |
| Weapon logic by planet number | weapon logic by position in the campaign |
| F9 status | also shows `campaign n/14: <visit>` or why the campaign is not active |
| — | **F12**: go to the next visit of the campaign (when active) |
| — | `companion\research\Research-Campaign.bat` (read-only) and the lab keys in test mode (Ctrl+F12 scan, Ctrl+F11 experiment) |
| Gold Bolt test key F11 | Ctrl+F11 is the lab experiment. Plain F11 still gives a test Gold Bolt |

# Moving from 1.4 to 2.0 (earlier)


**A fresh game save is required for a 2.0 seed.** Rewards come from story missions as they
finish, and a save that is far into the story won't send those events again. 2.0 seeds are
also different seeds, so 1.x progress (Gold Bolts, purchases) can't carry over.

Your 1.4 run is not lost:

- Your **game save** is untouched. Keep it.
- Your **1.4 randomizer progress** stays in the old companion's `randomizer_saves\rando_d6c9b213073c.lua`. To continue that run, keep the 1.4 kit's scripts installed.
- Items 1.4 put into your inventory stay in that game save.

## Steps

1. Back up `Documents\Ratchet & Clank Rift Apart`.
2. In `<game>\scripts`, delete all randomizer `.lua` files (`00_`, `04_`-`10_` from 1.x).
3. Install 2.0 (INSTALL.txt). Copy the 2.0 companion to its own folder. It refuses 1.x scripts with a clear message.
4. In the game, start a **New Game** in a free save slot, then play.

## What changed for you

| 1.4 | 2.0 |
|---|---|
| One fixed seed, `lombax-ryno-2026` | any seed text, or random; generated in the game; spoiler log |
| Planet completion, Gold Bolts, side rewards | adds second story missions, armor finds and sets, optional collectibles |
| Coordinates were only announced | Coordinates unlock a planet's rewards (banked until found) |
| Shop could contain anything | shop holds only items placed nowhere else; confirmation; owned items hidden |
| F8 buys | F8 twice buys |
| `08_rando_probe.lua` and friends in scripts | moved to `extras\dev_tools` |
