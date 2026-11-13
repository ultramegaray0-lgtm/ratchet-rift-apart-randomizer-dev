# Changelog: Ratchet Rift Apart Randomizer

## Public Release v0.52 (beta), 2026-11-13. Randomizer build 10.0.3

A small fix. **It has not been run in the game yet** (see README).

**Nefarious City's story starts again**
- In v0.51 the city's story never got past "go to Nefarious City". The warp landed at
  `CHK_NEFCITY_START`, but the game starts the city's story one step earlier, with the arrival scene
  it loads straight after the prologue. v0.52 copies the game's order:
  1. the prologue is marked complete first;
  2. the city's story starts, and its train-station mission opens with it, as in the game;
  3. the city loads at that **opening scene**, so the cutscene plays and then the gameplay.
- The opening's name isn't known in advance. The randomizer finds it by its checkpoint number among
  the names your game lists. If your game doesn't list it, the city loads at `CHK_NEFCITY_START` as
  before, and `rivet.log` lists the city's checkpoints.
- The opening scene gets about a minute before it is loaded once more, so the cutscene isn't cut
  short. While the story waits at its first step, `/` loads the opening again.
- `rivet.log` now logs every step of the city's story (`RANDO-HUB objective ...`).
- New in-game options, both optional: `hub_opening` (`true`; `false` = v0.51's load point) and
  `hub_prologue_timing` (`"before"`; `"after"` = v0.51's order).

**Unchanged**
- Seeds are the same as v0.51 (generator 10.0.2), so a v0.51 seed keeps its fingerprint and its
  progress. Start a New Game to try the new start. `rivet.log` shows
  `RANDO-KIT all 14 scripts are 10.0.3`.
- `rando_give.dll`, `rivet.toml` and the companion are unchanged.

## Public Release v0.51 (beta), 2026-11-13. Randomizer build 10.0.2

A small update. **It has not been run on Windows 11 or in the game yet** (see README).

**The hub is Nefarious City**
- A new game now goes to **Nefarious City** instead of Zurkie's Battleplex, and finishing a
  destination brings you back there. Messages and the spoiler log name it.
- **The city's story starts with that warp.** The story mission is made active first, then the city
  loads at the checkpoint where the game itself starts the city's story (`CHK_NEFCITY_START`). That
  is the order the game uses after the prologue. If the story still waits at its first step after 20
  seconds, that spot is loaded once more.
- The way home is that story start while the city's story is unfinished, and the ship's landing pad
  (`CHK_NEFCITY_SHIP`) afterwards.
- The Battle Arena (Zurkie's) is open from the start, as before, now as an ordinary destination.

**Ratchet can walk right after the warp**
- v0.5 warped at the moment Ratchet picked up his wrench. That moment starts a short scripted part
  of the parade (`OBJ_INTRO_GOING_DOWN`), during which the game ignores the player. The warp cut it
  off, and the prologue stayed active. v0.51 waits until that part is over and no parade cutscene
  is running (a few seconds), then warps. If the parade never reports it as over, it warps 30
  seconds after the wrench anyway.
- Once you're in Nefarious City, the prologue is written as complete and its reward is paid, as
  the game has it before the city. In-game option `hub_prologue = "keep"` leaves it open instead.
- New in-game options, all optional: `hub_trigger` (`"parade"` default, `"wrench"` = v0.5's
  timing), `hub_prologue` (`"end"` / `"keep"`), `hub_start_story` (`true`).

**Unchanged**
- Item placement is unchanged: apart from the hub's name and checkpoints, seeds are identical to
  10.0's, field for field. Every Gold Bolt still gives exactly one item.
- Build 10.0.2 is a new generator version, so v0.51 seeds are new seeds: start them with New Game.
  `rivet.log` shows `RANDO-KIT all 14 scripts are 10.0.2`.
- `rando_give.dll` and `rivet.toml` are byte-identical to v0.5.

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
  Nefarious City. (v0.51: the hub is Nefarious City.)
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
