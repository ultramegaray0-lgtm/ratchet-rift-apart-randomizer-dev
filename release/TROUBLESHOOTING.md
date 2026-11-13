# Troubleshooting: Ratchet Rift Apart Randomizer v0.5

Most answers are in `rivet.log`, in the game folder. Open it in Notepad and search for `RANDO-`.

| Log tag | What it covers |
|---|---|
| `RANDO-KIT` | Whether all 14 scripts are present and from the same version |
| `RANDO-SEED` | The seed, and whether ARSENAL_RESTORED was found |
| `RANDO-HUB` | Every hub step: destinations, mission starts, trips |
| `RANDO-REAL` | Item deliveries and the helper DLL |
| `RANDO-SAVE` | The connection to the companion |
| `RANDO-ERROR` | Anything that went wrong |

## Nothing happens: no seed, no start items, no warp to Zurkie's

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
3. Press `[` twice to go back to Zurkie's, then choose the destination again.
4. Press `Ctrl+[` twice to finish the destination by hand. Its rewards are paid and the next
   planets open, so the run can always continue.

If this happens, please report it on the mod page with your `rivet.log` (see below).

## I was sent back to Zurkie's

You landed on a planet whose Coordinates you don't have yet, or the game's own story tried to move
you on. That's intended: choose your next destination with `]`.

## A reward said it was given, but it's not in my inventory

Look for `RANDO-REAL` lines. Deliveries are retried. Glitch is never confirmed by the game, so it is
retried and then counted as given. If an item is missing after a reload, see the next point.

## I loaded an older save and now items are missing

Loading an older game save doesn't undo randomizer progress. The randomizer still counts items
as given that the older save doesn't have. Play forward from your latest save. To start the seed
over, choose New Game.

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

- the release version (v0.5) and your game version (right-click `RiftApart.exe` → Properties →
  Details → File version; v3.630.1.0 shows as 3.0630.1.0);
- the `rivet.log` from the game folder, uploaded as a file;
- the companion window's text, if it shows an error;
- what you did just before the problem.

`rivet.log` contains your game folder's path, which can include your Windows user name. Edit
that out before you post the log if you prefer.
