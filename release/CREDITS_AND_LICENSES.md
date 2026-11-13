# Credits and licenses: Ratchet Rift Apart Randomizer v0.54

## This mod

**Author: MegaRay.** The randomizer's own files are released under the **MIT License**
(`LICENSE.txt`, Copyright (c) 2026 MegaRay):

- the 14 Lua scripts;
- the companion and installer scripts (`.ps1`, `.bat`);
- `rivet.toml`;
- `rando_give.dll` and its source;
- the documentation.

The MIT License lets anyone use, change and redistribute these files, as long as they keep the
copyright and license notice.

**AI disclosure.** Most of the code (Lua scripts, companion scripts, `rando_give.dll` source) and
the documentation were generated with Anthropic's Claude, under MegaRay's direction. The research,
design decisions and in-game testing were done by MegaRay. No AI-generated game assets, images,
voices or audio are included.

## Required, not included

| Project | Author | License | Relationship |
|---|---|---|---|
| **rivet_hook**: https://codeberg.org/neptuwunium/rivet_hook (releases: https://github.com/neptuwunium/rivet_hook/releases) | neptuwunium | EUPL-1.2 | The mod loader the randomizer runs on. It runs the randomizer's Lua scripts through its scripting API, loads `rando_give.dll`, and provides the pipe bridge the companion uses. **Not bundled:** players download it from its official page, under its own license. No rivet_hook code is included in this package |

About `rando_give.dll` and rivet_hook: the DLL doesn't link to or contain rivet_hook code. To find the
game's config asset manager, it searches for the same 26-byte pattern of the game's own machine code
that rivet_hook searches for, and reads the manager's layout as rivet_hook's source documents it
(rivet_hook `src/signature.hpp`, `src/configs.cpp`). Credit for that finding goes to neptuwunium.

## Optional, not included

| Project | Notes |
|---|---|
| **ARSENAL_RESTORED** | A separate mod by its own author. The randomizer only detects it (by one asset id) and adds its weapons to the pool. None of its files are included. Get it from its own page and follow its permissions |
| **Overstrike**, by Tkachov | Mod manager for `.stage` mods. Only needed for the Overstrike version of ARSENAL_RESTORED |

## Research and data sources (no code or files included)

- **rivet** (neptuwunium, EUPL-1.2, https://codeberg.org/neptuwunium/rivet): engine type
  definitions and format documentation, used during research.
- **Overstrike** (Tkachov) and **Ripped Apart** (chaoticgd): archive format, asset-id hashing and
  asset lists, used during research.
- **Factual game data from public guides:**
  - normal weapon prices, from the gamepressure.com Rift Apart guide (used for the default
    `shop_prices = "weapon"`);
  - the mission order, from public walkthroughs (gamepressure, thegamer) and a public gear guide
    (vulkk).
  These sources were used as factual references only. No text from them is included.
- **Identifiers from the game:** item, mission and checkpoint names and asset ids come from the
  game's own asset list. Short byte sequences of `RiftApart.exe`'s machine code are embedded in
  `rando_give.dll`, only so it can confirm the exact game version before it does anything. No
  game files, models, textures, audio or text are included.

## Game

Ratchet & Clank: Rift Apart © Sony Interactive Entertainment LLC. Developed by Insomniac Games;
PC version by Nixxes Software. This is an unofficial fan modification, not affiliated with or
endorsed by any of them. You need your own copy of the game.

## Permissions for this mod

- Under the MIT License you may use, change and share this mod, including modified versions,
  as long as you keep the copyright and license notice.
- A request, not a condition: please link to the official mod page rather than re-uploading the
  unchanged package. That way players get updates and the bug-report thread.
