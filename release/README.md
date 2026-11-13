# Ratchet Rift Apart Randomizer: Public Release v0.5 (beta)

A randomizer for **Ratchet & Clank: Rift Apart** on PC (Steam). Every playthrough is a new seed:
weapons, gadgets, armor and planet Coordinates are shuffled over Gold Bolts, story missions, side
activities, armor pods, your starting kit and Ms. Zurkon's shop. Planets open in a different order
each run, and a solver checks that every seed can be finished.

| | |
|---|---|
| Release | Public Release **v0.5** (randomizer build 10.0.0) |
| Game | Ratchet & Clank: Rift Apart, **Steam**, game version **v3.630.1.0** |
| OS | Windows 10 or 11, 64-bit |
| Needs | **rivet_hook 2.0.1** (free, separate download) and Windows PowerShell (built into Windows) |
| Status | **Beta.** See "Before you play" below |

## Before you play

This is an early public release. Be clear about what that means:

- The randomizer's systems were developed and tested over many rounds on one PC. Seed generation,
  weapon and armor delivery, Gold Bolt rewards, the shop, the warp to Zurkie's and the mission-state
  writes have each been seen working in the game.
- **The current hub mode (start at Zurkie's, choose your first planet) has not yet finished a full
  playthrough in the game.** Some parts of it have only been tested offline, against a simulator.
- It has **not yet been tested on a second PC**. Everything that ties it to one computer has been
  removed, and the package was checked as a clean install, but other-PC reports are what this beta
  is for.
- **Back up your saves and play on a spare save slot.** See INSTALLATION.md, step 1.

## What it does

- **Start at the hub.** Start a New Game. Once Ratchet picks up his wrench in the parade, you're
  taken to **Zurkie's Battleplex**. Pick your first destination there: the Prologue, the Battle Arena
  or Nefarious City.
- **Planet shuffle.** Every other planet opens when you find its **Coordinates**. Coordinates can be
  behind any Gold Bolt, story mission, side activity or armor pod. Finish a destination and you're
  brought back to Zurkie's to choose the next one.
- **Randomized starting kit.** You always get the **Hoverboots** and the **Map-O-Matic**, plus
  random weapons and a random gadget (2 and 1 by default).
- **One location, one reward.** Each Gold Bolt, story mission, side activity and armor pod gives
  exactly one reward: an item (weapon, gadget, armor piece or Coordinates) or, when the seed has no
  item left for it, Bolts or Raritanium. Gold Bolts are still real Gold Bolts. The randomizer
  never charges several Gold Bolts for one item.
- **Armor is in the pool.** 21 findable armor pieces are rewards.
- **One route per weapon.** Each weapon is either for sale, in your starting kit or a reward,
  never two of these. By default Ms. Zurkon sells 8 different weapons, and her other slots are
  closed.
- **Spoiler log** for every seed (optional reading), and a **companion window** that saves
  randomizer progress.
- **Optional:** if you have the ARSENAL_RESTORED mod installed, its 9 weapons join the pool
  automatically.

The full player guide, with keys, settings and presets, is in `docs/PLAYER_GUIDE.md`.

## Quick install

1. Back up `Documents\Ratchet & Clank - Rift Apart`.
2. Install **rivet_hook 2.0.1** in the game folder and run the game once.
3. Copy **everything inside this package's `GAME_FOLDER`** into the game folder, the one that holds
   `RiftApart.exe`.
4. Start `rando_companion\Start-Companion.bat`, then the game, then **New Game** on a spare slot.

The step-by-step version, with updating and uninstalling, is in **INSTALLATION.md**.

## Files in this package

| Path | What it is |
|---|---|
| `GAME_FOLDER\` | Everything that goes into the game folder (see INSTALLATION.md) |
| `GAME_FOLDER\scripts\` | The randomizer: 14 Lua scripts that rivet_hook runs |
| `GAME_FOLDER\rando_give.dll` | Small native helper that puts rewards into your inventory (source in `source\`) |
| `GAME_FOLDER\rivet.toml` | rivet_hook settings the randomizer needs |
| `GAME_FOLDER\rando_companion\` | The companion (PowerShell) and the optional ARSENAL_RESTORED installer |
| `docs\PLAYER_GUIDE.md` | How a run works, keys, settings, presets |
| `source\rando_give\` | Complete source of `rando_give.dll`, which builds to the same bytes |
| `INSTALLATION.md`, `TROUBLESHOOTING.md`, `COMPATIBILITY.md`, `CHANGELOG.md`, `CREDITS_AND_LICENSES.md`, `LICENSE.txt` | What they say |
| `SHA256SUMS.txt` | Checksums of every file in this package |

## Safety and privacy

- No network access, telemetry, ads or background processes. The companion runs only while its
  window is open.
- No administrator rights needed. The game's own files and your game saves are not modified.
- `rando_give.dll` changes the running game's memory, and only while the game runs. Before it
  changes anything, it checks every byte it relies on. On any other game version it does nothing.
  COMPATIBILITY.md lists exactly what each part reads and writes.

Not affiliated with or endorsed by Sony Interactive Entertainment, Insomniac Games or Nixxes
Software. "Ratchet & Clank" and "Ratchet & Clank: Rift Apart" are trademarks of Sony Interactive
Entertainment LLC. No game assets are included.
