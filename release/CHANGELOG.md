# Changelog: Ratchet Rift Apart Randomizer

## Public Release v0.5 (beta), 2026-11-13. Randomizer build 10.0.1

The first public release. It is build 10.0, plus one gameplay correction and the packaging for
other PCs. **This release has not been run on Windows 11 or in the game yet** (see README).

**Gameplay: every Gold Bolt gives exactly one item**
- The shipped settings now use `distribution = "goldbolts_first"`. Every one of the 25 Gold Bolts
  holds exactly one item (weapon, gadget, armor piece or Coordinates), never Bolts or Raritanium.
  In 10.0's `spread` fill, about a third of Gold Bolts gave currency.
- 10.0's early game is kept. Hub seeds still get `early_weapons` (2) weapon rewards and one
  Coordinates where the starting kit can reach. Gold Bolts there are used first, so they still
  hold items. If settings are too tight for that (for example armor off with `early_weapons = 6`),
  `early_weapons` is lowered automatically, with a note in the spoiler, instead of the seed failing.
- Nothing else changes. Seeds with `distribution = "spread"`, and all non-hub seeds, are
  identical to 10.0, apart from the new version number in their fingerprint.
- Generator and kit version 10.0.1. v0.5 seeds are new seeds, so start them with New Game.
  `rivet.log` shows `RANDO-KIT all 14 scripts are 10.0.1`.
- The settings file, one log message and two spoiler-log lines pointed to development documents
  that aren't in this package. They now point to `docs\PLAYER_GUIDE.md` and TROUBLESHOOTING.md.

**Packaging for other PCs**
- New player documentation: README, INSTALLATION (install, update, uninstall, save backup),
  TROUBLESHOOTING, COMPATIBILITY, CREDITS_AND_LICENSES, and a player guide.
- One `GAME_FOLDER` to copy into the game folder. The companion now ships as `rando_companion\`,
  where its scripts expect it.
- Development material is left out of the package: test mode, research and dump tools, developer
  probes, test results and development logs.
- The save-backup instructions now name the game's real save folder,
  `Documents\Ratchet & Clank - Rift Apart`. The earlier text left out the " - ".
- `Install-ArsenalRestored.bat` now uses Windows line endings.
- The companion's window title and one error message named the old version 9.0. They now name
  10.0 and this kit's scripts.
- `rando_give.dll` is unchanged. It is rebuilt from the included source as part of the release check,
  and the result is byte for byte the shipped file.

**What the randomizer does (build 10.0.1)**
- Zurkie's Battleplex hub: after the parade's wrench, choose the Prologue, the Battle Arena or
  Nefarious City.
- Planet shuffle through Coordinates, on by default. Finishing a destination brings you back to
  the hub.
- Every Gold Bolt gives exactly one item. Story missions, side activities and armor pods give one
  reward each.
- Randomized starting kit, always with the Hoverboots and the Map-O-Matic.
- Armor in the reward pool.
- One route per weapon: sold, in the starting kit or a reward, never two of these.
- A solver checks that every seed can be finished.
- Optional ARSENAL_RESTORED weapons.
- A companion for saving progress, random seeds and spoiler logs.

## Private development builds (summary)

The randomizer was developed privately through builds 1.x to 10.0 (2026), with in-game test
rounds 6-23 on one PC. The main steps:

- **4.0:** one item per Gold Bolt; Hoverboots and Map-O-Matic in the start.
- **5.0:** armor rewards; shop shuffle.
- **6.0:** one route per weapon.
- **7.0:** locked levels and Coordinates; currency rewards.
- **8.x:** first Zurkie's hub, mission-state control and robustness fixes.
- **9.0:** story start without the hub.
- **10.0:** the hub returns, with planet shuffle on by default, spread rewards and closed shop slots.
