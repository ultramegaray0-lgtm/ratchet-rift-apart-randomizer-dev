# Research

## Campaign research (3.1): how the game runs its missions

CAMPAIGN.md has the full background and the three in-game tests. In short:

1. `companion\research\Research-Campaign.bat` (read-only, about 3 minutes, on any planet) collects:
   - event classes and their fields;
   - the level's checkpoints and regions (story overlays);
   - mission configs;
   - every loaded node of 37 mission/travel/reward script actions, with details;
   - the randomizer's own mission log and node scan;
   - the game code of the mission actions (`Dump-GameCode.ps1 -Extended`);
   - rivet.log and rivet.toml;
   - optionally the dag (`-NoDag` to skip) and your saves (`-NoSaves` to skip).

   Everything goes into one `campaign_research_<date>.zip`.
2. The lab (test mode, a spare save):
   - Ctrl+F12 reads the mission table (read-only) and checks it against the game's own state
     function;
   - Ctrl+F11 makes the next locked visit available, starts it and flies there. During a new
     game's intro (state 3), it finishes the intro instead.
3. Tools:
   - `tools/build_capabilities.py rivet.log` writes `06_rando_capabilities.lua` (only `RANDO-LAB VERIFIED` lines count);
   - `tools/build_campaign_registry.py <zip>` writes `07_rando_campaign_registry.lua` (the mission names your game reports);
   - `tools/analyze_dump.py` disassembles the dumped handlers.

Round 14's dump is how 3.1 found the mission manager: `tools/analyze_dump.py` on
`game_code_dump.json` shows the handlers of the mission actions. 3.1's dump also copies the
mission manager's vtable and the functions behind `+0x120` (start) and `+0x1E0`.

## Adding armor (and more) as real rewards (2.0)


Weapons and gadgets reach your inventory because the code of the game's `AddToInventoryAction`
was read and checked byte for byte. `rando_give.dll` repeats exactly that call, and only if
every byte matches. Armor, currency and upgrades need the same for their own actions. The
names are known from your exe's RTTI:

- `VanityGiveBundleAction`, `VanityGiveSetAction` (armor)
- `AddCurrencyAction` (bolts / Raritanium)
- `SetWeaponLevelAction`
- `UnlockLevelAction`, `SetPlanetaryTravelAction` (planets)
- `CollectibleCollectAction`

Their code has not been read yet, because this project has no copy of RiftApart.exe.

## What to do (5 minutes, read-only)

1. Start the game with the randomizer installed, and load into any planet.
2. Run `companion\research\Dump-GameCode.bat`.
3. Send back `companion\research\game_code_dump.json`.

The tool only reads memory through rivet_hook's bridge (`mem.read`). It changes nothing and does
not touch files outside its folder. It needs rando_give.dll loaded, because the DLL tells it
where the exe sits in memory.

## What happens with it

`tools/analyze_dump.py` disassembles each action's handler: which game functions it calls, which
global message ids it uses, and which node fields hold the item. The tests check this on the
known AddToInventoryAction handler, which correctly recovers:

- SendMessage at RVA 0x1B7B850
- GetPlayerActors
- message id 0x60315B8
- the Target plug hash
- the item field +0x60

With the armor handler decoded the same way, rando_give.dll gets a second request kind, also
checked byte for byte. Armor rewards can then be switched from "tracked" to real.

## 7.0: level actions decoded from the round 15 dump

`tools/analyze_dump.py tests/data/round15_game_code_dump.json --action UnlockLevelAction` and the
dumped targets show:

- `UnlockLevelAction` (handler RVA `0x89DA00`) reads a level number (1-10) from a float plug and
  calls `0x89C1E0`, which sets (`0x549CFE88` in) or clears (`0xB71F5BBE`) bit *n* of a 32-bit mask
  at a global object's `+0x30`, then fires a plug.
- `IsLevelUnlockedAction` (handler `0x89DC60`) tests that bit (`0x89C140`: `bt eax, edx`).

Neither touches the mission manager (`0x68EA390`) or the story overlays. So "levels" there are a
small separate feature, not the planets' story, and unlocking them cannot reorder the campaign.
`SetPlanetaryTravelAction` (`0x607500`) reads one bool plug (`0x12BDF60`) and stores it in a
single global byte (RVA `0x5FFD3C0`): planetary travel on or off as a whole, not per planet. It
could switch the whole planet menu off, which would block the story too, so 7.0 does not use it.
The ship's planet-menu travel is observed through `PlanetMenuAcceptEvent`
(DestinationCheckpointName, InterplanetaryCheckpointName) and cannot be vetoed, which is why 7.0's
locked levels warp you back after landing (LEVELS.md).
