# Installation: Ratchet Rift Apart Randomizer v0.54

Time needed: about 10 minutes. You don't need any programming tools.

## What you need

| | Version | Where |
|---|---|---|
| Ratchet & Clank: Rift Apart | Steam, **v3.630.1.0** (the current Steam version) | Steam |
| rivet_hook | **2.0.1** (2.0.0 also works) | https://github.com/neptuwunium/rivet_hook/releases, source at https://codeberg.org/neptuwunium/rivet_hook |
| Windows PowerShell | 5.1, built into Windows 10/11 (PowerShell 7 also works) | already installed |
| ARSENAL_RESTORED | optional | its own mod page |

rivet_hook is not included in this package. It is another author's mod loader, released under its
own license. Download it from its official page.

## Step 1: back up your saves

1. Close the game.
2. Press `Win+R`, paste `%USERPROFILE%\Documents\Ratchet & Clank - Rift Apart` and press Enter.
3. Copy that whole folder somewhere safe, for example to your Desktop.

Steam Cloud also syncs these saves. The randomizer never writes to them, but the game saves
normally while you play. **Use a save slot you don't need.**

## Step 2: find the game folder

In Steam: right-click **Ratchet & Clank: Rift Apart** → **Manage** → **Browse local files**. The
folder that opens holds `RiftApart.exe`. These instructions call it **the game folder**. It can be
on any drive, and its path can contain spaces.

## Step 3: install rivet_hook

Follow rivet_hook's own instructions. In short:

1. Download the release zip from rivet_hook's latest release (2.0.1) and extract it.
2. Copy `hid.dll` and `rivet_hook.dll` into the game folder. If the game crashes at start, use
   `hid_win10.dll` instead, renamed to `hid.dll`.
3. Create a folder named `mods` in the game folder.
4. Start the game once. When you reach the main menu, quit. rivet_hook has now written its
   `rivet.toml`.

## Step 4: install the randomizer

1. Open this package's `GAME_FOLDER` folder.
2. Select **everything inside it** (`scripts`, `rando_companion`, `rando_give.dll`, `rivet.toml`)
   and copy it into the game folder.
3. Windows asks about replacing `rivet.toml`:
   - **If you use no other rivet_hook mods:** choose **Replace**.
   - **If you do use other rivet_hook mods:** first copy your `rivet.toml` somewhere safe, then
     replace it. Afterwards, copy your own entries back into `paths` under `[assets]`. The
     randomizer needs these settings, all of which are in its `rivet.toml`:
     `[overlay] enabled = true`, `[scripts] enabled = true` and `path = "scripts"`,
     `[bridge] enabled = true`, `[renderdoc] enabled = true` and `dll_path = "rando_give.dll"`.

When you're done, the game folder looks like this. Lines marked `<- randomizer` are this
package's files:

```
<game folder>\
    RiftApart.exe
    hid.dll, rivet_hook.dll          (rivet_hook)
    mods\                            (rivet_hook)
    rivet.toml                       <- randomizer
    rando_give.dll                   <- randomizer
    scripts\                         <- randomizer: 01_rando_data.lua ... 16_rando_testtravel.lua (14 files)
    rando_companion\                 <- randomizer: Start-Companion.bat, RandoCompanion.ps1,
                                                    Install-ArsenalRestored.bat / .ps1
```

## Step 5: optional, ARSENAL_RESTORED

You don't need it. If you have it:

- **Overstrike version:** keep it installed through Overstrike. Nothing else to do.
- **rivet_hook version:** drag its downloaded zip onto `rando_companion\Install-ArsenalRestored.bat`.
  It copies the mod into `mods\ARSENAL_RESTORED`, copies the mod's own `.lua` files into `scripts`,
  and adds the mod to `rivet.toml`. The old `rivet.toml` is kept as `rivet.toml.bak`. Running it
  again replaces any earlier `mods\ARSENAL_RESTORED` folder.

With the default setting `restored_weapons = "auto"`, the mod's 9 weapons join the pool when the
companion finds the mod.

## Step 6: start a randomized playthrough

1. Double-click `rando_companion\Start-Companion.bat`. A console window opens. **It's required
   with the default random seed, so keep it open while you play:** it saves your randomizer progress, picks and remembers your random seed, and
   writes the spoiler log.
2. Start the game from Steam.
3. Choose **New Game** on a spare slot. The parade starts as usual. The screen shows the seed,
   then your starting items.
4. When Ratchet has his wrench and can walk again (a few seconds later), you're taken to
   **Nefarious City**, the hub, and its story starts. Press `]` to cycle through the destinations
   and `Ctrl+]` to go.

`docs/PLAYER_GUIDE.md` covers the rest of a run.

**Check the install (optional).** Open `rivet.log` in the game folder and search for
`RANDO-KIT all 14 scripts are 10.0.5`. If you see `RANDO-ERROR` instead, see TROUBLESHOOTING.md.

### Your seed

- By default (`seed = "random"`), the companion picks a random seed on the first run and remembers
  it in `rando_companion\randomizer_saves\random_seed.txt`.
- **New random seed:** close the game, delete `random_seed.txt`, then start the companion and the
  game again and choose New Game.
- **A seed of your own** (for races, or to share): open `scripts\04_rando_settings.lua` in Notepad
  and change `seed = "random"` to, for example, `seed = "lombax-ryno-2026"`. Then start a New Game.
- **Spoiler log:** `rando_companion\randomizer_saves\spoilers\`. Open it only if you want spoilers.

## Updating to a newer version

1. Close the game and the companion window.
2. Back up your saves (step 1).
3. In the game folder's `scripts` folder, **delete every `*_rando_*.lua` file**. Leave other mods'
   scripts alone.
4. If you changed `scripts\04_rando_settings.lua`, keep a copy of it first. Copy your values into
   the new version's file; don't replace the new file with the old one.
5. Copy the new `GAME_FOLDER` contents into the game folder, as in step 4 of the install.
6. Keep `rando_companion\randomizer_saves`. It holds your progress and spoilers. A new randomizer
   build usually means new seeds, so start a New Game unless the changelog says otherwise.

## Uninstalling

The randomizer only adds files. To remove it:

1. Close the game and the companion window.
2. Delete these from the game folder:
   - `scripts\01_rando_data.lua` through `scripts\16_rando_testtravel.lua`: the 14 files listed in
     this package's `GAME_FOLDER\scripts`. Delete the whole `scripts` folder only if no other
     mod uses it.
   - `rando_give.dll`
   - `rando_companion\`. This deletes your randomizer progress and spoilers. Keep
     `rando_companion\randomizer_saves` if you want them.
   - `rivet.toml`. If you saved your own copy before installing, put it back. Otherwise
     rivet_hook writes a new default one on its next start.
3. If you used `Install-ArsenalRestored.bat`, remove `mods\ARSENAL_RESTORED` (or
   `mods\ARSENAL_RESTORED.stage`) and its `.lua` files from `scripts` as well, if you no longer
   want that mod.
4. To remove rivet_hook too, delete `hid.dll`, `rivet_hook.dll`, `rivet.toml`, `rivet.log` and the
   `mods` folder.

The game's own files were never changed, so nothing needs to be restored. If you want to be sure,
use Steam → Properties → Installed Files → **Verify integrity of game files** (this doesn't
remove added files).

**Your game saves:** saves made during a randomized run stay randomized. The items you received
are in that save. To go back to your old saves, restore the backup from step 1.
