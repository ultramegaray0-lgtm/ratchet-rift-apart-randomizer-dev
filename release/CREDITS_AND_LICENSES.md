# Credits and licenses: Ratchet Rift Apart Randomizer v0.5

## This mod

The randomizer's own files are released under the **MIT License** (`LICENSE.txt`):

- the 14 Lua scripts;
- the companion and installer scripts (`.ps1`, `.bat`);
- `rivet.toml`;
- `rando_give.dll` and its source;
- the documentation.

Development was AI-assisted: most of the code and documentation was written with Anthropic's Claude,
directed, reviewed and tested in the game by the mod author. NEXUS_PAGE_DESCRIPTION.md has the
NexusMods disclosure.

## Required, not included

| Project | Author | License | Used for |
|---|---|---|---|
| **rivet_hook**: https://codeberg.org/neptuwunium/rivet_hook (releases: https://github.com/neptuwunium/rivet_hook/releases) | neptuwunium | EUPL-1.2 | Runs the randomizer's Lua scripts, loads `rando_give.dll`, and provides the pipe bridge the companion uses. Not bundled: download it from its official page |

`rando_give.dll` contains no rivet_hook code. To find the game's config asset manager, it uses the
same byte pattern that rivet_hook uses for that purpose; that pattern is credited here.

## Optional, not included

| Project | Notes |
|---|---|
| **ARSENAL_RESTORED** | A separate mod by its own author. The randomizer only detects it and adds its weapons to the pool; none of its files are included. Get it from its own page and follow its permissions |
| **Overstrike**, by Tkachov | Mod manager for `.stage` mods. Only needed for the Overstrike version of ARSENAL_RESTORED |

## Research and data sources

- **rivet** (neptuwunium, EUPL-1.2, https://codeberg.org/neptuwunium/rivet): the engine type
  definitions and format documentation, used during research. No rivet code is included.
- **Overstrike** and **Ripped Apart** (chaoticgd): the archive format, the asset-id hashing and the
  asset lists, used during research. No code from them is included.
- Normal weapon prices, used for the default `shop_prices = "weapon"`, were taken from the
  gamepressure.com Rift Apart guide (as factual price data).
- Item, mission and checkpoint identifiers come from the game's own asset list. They are
  identifiers only: no game files, models, textures, audio or text are included.

## Game

Ratchet & Clank: Rift Apart © Sony Interactive Entertainment LLC. Developed by Insomniac Games;
PC version by Nixxes Software. This is an unofficial fan modification, not affiliated with or
endorsed by any of them. You need your own copy of the game.

## Permissions for this mod

- You may use it and change it for yourself, and share your changes, under the MIT License.
- When you share it, please link to the official mod page rather than re-uploading the package.
  That way players get updates and the bug-report thread.
