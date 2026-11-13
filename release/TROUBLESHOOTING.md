# Troubleshooting: Ratchet Rift Apart Randomizer v0.54

Most answers are in `rivet.log`, in the game folder. Open it in Notepad and search for `RANDO-`.

| Log tag | What it covers |
|---|---|
| `RANDO-KIT` | Whether all 14 scripts are present and from the same version |
| `RANDO-SEED` | The seed, and whether ARSENAL_RESTORED was found |
| `RANDO-HUB` | Every hub step: destinations, mission starts, trips |
| `RANDO-REAL` | Item deliveries and the helper DLL |
| `RANDO-SAVE` | The connection to the companion |
| `RANDO-ERROR` | Anything that went wrong |

## Nothing happens: no seed, no start items, no warp to Nefarious City

1. **Is rivet_hook loading?** `rivet.log` should exist and be updated each time you start the game.
   If it isn't, rivet_hook isn't installed: check that `hid.dll` and `rivet_hook.dll` are next to
   `RiftApart.exe`. If the game crashes at start, use rivet_hook's `hid_win10.dll`, renamed to
   `hid.dll`.
2. **Are scripts enabled?** In `rivet.toml`, `[scripts]` must have `enabled = true` and
   `path = "scripts"`. rivet_hook turns scripts off by default, so use the randomizer's
   `rivet.toml`.
3. **Are the scripts in the right place?** They belong in `<game folder>\scripts\`, not in
   `<game folder>\GAME_FOLDER\scripts\` or in a nested folder from the zip.
4. Search `rivet.log` for `RANDO-KIT`.

## `RANDO-KIT` says a file is missing or from another version

The `scripts` folder mixes versions. Delete every `*_rando_*.lua` file in it, then copy the 14
files from this package's `GAME_FOLDER\scripts` again. Leftovers from older test builds
(`07_rando_testmode.lua`, `08_rando_probe.lua`, `00_rando_seed.lua`) must go too.

## "rando_give.dll ... refused this exe (nothing patched)" or "rando_give.dll is not loaded"

- **refused this exe:** your game version isn't the one the helper was built for (Steam
  v3.630.1.0). The helper then does nothing at all, by design. Updates are usually needed after a
  game patch. Seeds still generate, and anything that can be delivered another way still is, but
  rewards that need the helper won't arrive. Check that Steam has the game fully updated. On another
  store's version (Epic Games), the helper isn't supported.
- **not loaded:** `rando_give.dll` must be next to `RiftApart.exe`, and `rivet.toml` needs
  `[renderdoc] enabled = true` and `dll_path = "rando_give.dll"`. This is the only setting rivet_hook
  has for loading an extra DLL. Nothing of RenderDoc is used.

## Antivirus or Windows SmartScreen warns about `rando_give.dll`

The helper hooks one function in the running game, the same way most game mod loaders do, and
some antivirus programs flag that pattern. Its complete source is in `source\rando_give\`, and
it builds to exactly the shipped file (SHA-256 in `SHA256SUMS.txt`). It has no network, file or
registry code (COMPATIBILITY.md lists everything it imports). If you'd rather not run it, set
`[renderdoc] enabled = false` in `rivet.toml`. The randomizer then can't put rewards into your
inventory directly, so most rewards won't arrive.

## The companion window says "waiting for the game / randomizer scripts"

That's normal until the game has started and the scripts have loaded. It keeps trying. If it
never connects:

- `rivet.toml` needs `[bridge] enabled = true` and `pipe_name = "rivet_hook"`.
- Start the game normally, not as administrator. The companion and the game must run as the same
  Windows user.

## The companion window closes at once, or PowerShell refuses to run it

- `Start-Companion.bat` starts PowerShell with `-ExecutionPolicy Bypass` for this one script only,
  without changing any system setting. If your PC's policy is set by an administrator or company
  (Group Policy), that can still block it. Ask the PC's administrator, or play without the
  companion (progress won't be saved).
- If Windows marks the files as downloaded from the internet, right-click
  `RandoCompanion.ps1` → Properties → tick **Unblock** → OK. Do the same for `Install-ArsenalRestored.ps1`.
- "Access to the path ... is denied": the companion saves into `rando_companion\randomizer_saves`
  next to itself. Your Windows user must be able to write in the game folder. Steam's folders
  normally allow that. Don't run the companion as administrator to get around it: then it can't
  talk to the game.

## The screen says "start the companion" or "the companion is not running"

- **"start the companion (seed = random)":** with the default random seed, no seed is made until
  the companion connects. Start `rando_companion\Start-Companion.bat`. Start it before New Game,
  so your starting items arrive during the parade.
- **"the companion is not running - progress will NOT be saved":** you use a fixed seed and the
  companion isn't connected. Start it and keep its window open. It connects within a few seconds.

## A destination's story won't start

The hub logs each step as `RANDO-HUB`. In order, try:

1. Wait 20 seconds. If the story is stuck at its first "go to ..." step, the hub reloads that spot
   once by itself.
2. Press `/` to start the story of the planet you're on.
3. Press `[` twice to go back to Nefarious City, then choose the destination again.
4. Press `Ctrl+[` twice to finish the destination by hand. Its rewards are paid and the next
   planets open, so the run can always continue.

If this happens, please report it on the mod page with your `rivet.log` (see below).

## I was sent back to Nefarious City

You landed on a planet whose Coordinates you don't have yet, or the game's own story tried to move
you on. That's intended: choose your next destination with `]`.

## The warp to Nefarious City doesn't come right at the wrench

That's intended (v0.51). Picking up the wrench starts a short scripted part of the parade. The
randomizer waits until it is over and Ratchet can walk again (a few seconds), so the warp doesn't
cut it off. In `rivet.log` the warp follows the line `the parade handed Ratchet back`. If the
parade never reports that part as finished, the warp goes 30 seconds after the wrench anyway.

## Nefarious City's story doesn't start (it stays at "go to Nefarious City")

v0.52 is meant to fix this (v0.51 had it). The city is now loaded at its opening scene, the spot
the game itself loads after the prologue, instead of `CHK_NEFCITY_START`. In `rivet.log`:

- `opening of nefcity_1: <name> (hash 3046787773, ...)`: the opening was found and the warp went
  there. `opening of nefcity_1 loaded` follows when the city loads.
- `objective MIS_NEFCITY_01 OBJ_NEFCITY_GO_TO_NEFCITY 2`: the story left its first step.
- `hash 3046787773 is not among the checkpoints your game lists`: the opening wasn't found, so the
  city was loaded at `CHK_NEFCITY_START` as in v0.51. The next line lists the city's checkpoints.

If the story still waits after about a minute, the opening is loaded once more. Press `/` to load
it again yourself, or `Ctrl+[` twice to count the city's story as finished by hand. Either way,
please send your `rivet.log`.

## Ratchet lands with the ship and falls to his death in Nefarious City's boss fight

v0.53 fixes this (v0.52 had it). The boss fight's rifts to Savali or Sargasso were played as ship
landings because the randomizer had turned the ship's planetary travel on. While a story runs it
now leaves that to the game. Load your save; the fight's checkpoint works as it is. In `rivet.log`
you should see `planetary travel and level bits left to the game while nefcity_1 runs` and, after
each rift back, `back on nefarious_city from savali during nefcity_1`. If Ratchet still comes down
with the ship, please send your `rivet.log`.

## A level sends me back to Nefarious City, or "doesn't work" after a warp

v0.54 fixes one cause (v0.53 had it). When you continued a save on another planet, the randomizer
could mistake that load for the game's own story travel and send you back to Nefarious City. That
came from a timer the randomizer saved in a previous session. In `rivet.log` you now see
`arrived on <planet> (a load) - nothing changed` instead of `the game's own story took you to`.

If a level still misbehaves, press `0` to switch **planet shuffle** off. The game then handles
travel, levels and stories its own way: nothing is undone, nothing warps you, no planet sends you
back. Items stay randomized. If the level works with it off, please send your `rivet.log`. Press `0`
again to switch it back on; the choice is remembered with your randomizer progress.

## My weapons and gadgets are gone after a trip

After the randomizer's own trips (`Ctrl+]`, the ship's menu landing it starts a story from) and
when a save loads on another planet, it compares the game's weapon list with the weapons it gave
you. If fewer than half are there, it sends everything it knows you own again: lost items come back
("Given back: ..."), items you still have stay as they are. Press `Ctrl+0` twice to do this by hand
at any time, for example in a save that lost them before v0.54. In `rivet.log` these lines start
with `RANDO-RESTORE`. Weapons you bought yourself come back too once the randomizer has seen them
(bought or equipped); Bolts, Raritanium and armor aren't sent again. What empties the inventory is
not known yet; please send your `rivet.log` if it happens.

## Ratchet can't move after the warp

v0.51 and later are meant to prevent this. If it still happens:

1. Press `/` to load the story of the planet you're on again.
2. Send your `rivet.log` (see below). The lines with `RANDO-HUB` around the warp show when it went
   and which part of the parade was running.

## A reward said it was given, but it's not in my inventory

Look for `RANDO-REAL` lines. Deliveries are retried. Glitch is never confirmed by the game, so it is
retried and then counted as given. If an item is missing after a reload, see the next point.

## I loaded an older save and now items are missing

Loading an older game save doesn't undo randomizer progress. The randomizer still counts items
as given that the older save doesn't have. Press `Ctrl+0` twice to have them sent again (v0.54), or
play forward from your latest save. To start the seed over, choose New Game.

## The shop shows its normal weapons

When the shop can't be changed in memory, Ms. Zurkon sells her usual weapons. The weapons the seed
put in the shop but she doesn't sell are then given to you directly, once (said on screen and in
`rivet.log` as `RANDO-SHOP`).

## Starting over

- **Same seed, new run:** New Game. The previous run's progress is kept as a `.runN` file.
- **New random seed:** close everything, delete
  `rando_companion\randomizer_saves\random_seed.txt`, start again, then New Game.
- **Clean slate:** delete `rando_companion\randomizer_saves`. This deletes all randomizer progress
  and spoilers. Game saves are not affected.

## Reporting a problem

On the mod page, please include:

- the release version (v0.54) and your game version (right-click `RiftApart.exe` → Properties →
  Details → File version; v3.630.1.0 shows as 3.0630.1.0);
- the `rivet.log` from the game folder, uploaded as a file;
- the companion window's text, if it shows an error;
- what you did just before the problem.

`rivet.log` contains your game folder's path, which can include your Windows user name. Edit
that out before you post the log if you prefer.
