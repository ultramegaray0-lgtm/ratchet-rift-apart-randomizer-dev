# Ratchet & Clank: Rift Apart Randomizer v0.55

A randomizer for the PC version of Ratchet & Clank: Rift Apart. Weapons, gadgets, armor and
planet Coordinates are shuffled across Gold Bolts, story missions, side activities, armor pods
and Ms. Zurkon's shop. Every seed is checked by a solver before you play, so it can always be
finished.

This is an unofficial fan mod. It is a beta: please report problems.

## What you need

- Ratchet & Clank: Rift Apart on Steam, version 3.630.1.0, on Windows 10 or 11 (64-bit).
- rivet_hook 2.0.1 (2.0.0 also works). It is **required** and **not included**: download it from
  https://github.com/neptuwunium/rivet_hook/releases.
- Windows PowerShell (already part of Windows).

Install steps: **INSTALLATION.md**.

## Playing

1. Start `rando_companion\Start-Companion.bat` and keep its window open. It saves your randomizer
   progress and picks your random seed.
2. Start the game and choose **New Game** on a spare save slot.
3. The screen shows your seed, then your starting items. Play the game: Gold Bolts, story
   missions, side activities and armor pods now give the seed's items.
4. **Coordinates** are items too. Rewards on a planet you don't hold Coordinates for are kept
   until you find them.

### Planet shuffle (off by default)

Press **0** in the game to turn planet shuffle on or off. Your choice is saved.

- **Off:** the game's normal story order, with randomized items.
- **On:** Nefarious City becomes your hub. Planets open when you find their Coordinates, and you
  play them in any order with the ship's planet menu. When a planet's story is done, you are
  taken back to Nefarious City. Turn it on during the opening parade of a New Game. If you turn it
  on later, it starts with your next New Game.

**Ctrl+0 twice** sends your randomizer items again if some went missing.

The randomizer uses no other keys.

## Settings

Open `scripts\04_rando_settings.lua` in the game folder with Notepad. Each option has a short note.
The main ones:

| Setting | What it does |
|---|---|
| `seed` | `"random"` (default) or any text for a fixed seed you can share |
| `preset` | `balanced` (default), `full`, `chaos` or `everything` |
| `distribution` | `"goldbolts_first"`: every Gold Bolt gives an item. `"spread"`: items go anywhere |
| `shop_weapons` | how many weapons Ms. Zurkon sells (0-15) |
| `start_weapons`, `start_gadgets` | what you start with |
| `exclude` | items to leave out |

Changing the seed or an option makes a new seed: start it with New Game.

## Your progress and spoilers

- Progress: `rando_companion\randomizer_saves\`.
- Your random seed: `rando_companion\randomizer_saves\random_seed.txt`. Delete it for a new one.
- Spoiler log: `rando_companion\randomizer_saves\spoilers\` (only open it if you want spoilers).
- New Game starts the seed over.

## Optional: ARSENAL_RESTORED

If the ARSENAL_RESTORED mod is installed, its 9 weapons join the item pool automatically.
It is not needed.

## Help

See **TROUBLESHOOTING.md**. When you report a problem, include the mod version (v0.55), your game
version and `rivet.log` from the game folder. Remove your Windows user name from any path in it
first.

Credits and licenses: **CREDITS_AND_LICENSES.md**.
