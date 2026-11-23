# Installation: Rift Apart Randomizer v0.75 LITE

About 5 minutes. Nothing to run but the game.

## 1. Back up your saves

1. Close the game.
2. Press `Win+R`, paste `%USERPROFILE%\Documents\Ratchet & Clank - Rift Apart` and press Enter.
3. Copy that whole folder somewhere safe.

The randomizer never changes your save files, but the game saves normally while you play. Use a
save slot you don't need.

## 2. Find the game folder

In Steam, right-click **Ratchet & Clank: Rift Apart** → **Manage** → **Browse local files**. The
folder that opens contains `RiftApart.exe`. These steps call it **the game folder**.

## 3. Install rivet_hook (required)

rivet_hook is the mod loader that runs the randomizer's scripts. It is made by another author and
is not included. Follow its own instructions. In short:

1. Download rivet_hook 2.0.1 from https://github.com/neptuwunium/rivet_hook/releases and extract it.
2. Copy `hid.dll` and `rivet_hook.dll` into the game folder. If the game crashes at start, use
   `hid_win10.dll` instead, renamed to `hid.dll`.
3. Start the game once, reach the main menu, then quit.

## 4. Install Lite

1. Open this download's `GAME_FOLDER` folder.
2. Copy **everything inside it** (`scripts` and `rivet.toml`) into the game folder.
3. When Windows asks about replacing `rivet.toml`:
   - **No other rivet_hook mods:** choose **Replace**.
   - **Other rivet_hook mods:** back up your `rivet.toml` first, replace it, then copy your own
     entries back.

The game folder then contains:

```
<game folder>\
    RiftApart.exe
    hid.dll, rivet_hook.dll             (rivet_hook)
    rivet.toml                          (randomizer Lite)
    scripts\                            (randomizer Lite: 13 files, 01_rando_data.lua ... 15_rando_hub.lua)
```

`scripts\15_rando_hub.lua` is optional: delete it and you are never taken back to Nefarious City
after a planet (rewards still arrive whenever you are there).

## 5. Check that it runs

1. Start the game, choose **New Game** on a spare save slot.
2. A few seconds in, the screen says `Randomizer Lite: seed rift-lite-test`.
3. If nothing appears: open `rivet.log` in the game folder and search for `RANDO-KIT`. It must say
   `RANDO-KIT release v0.75 (kit 10.0.39)` and `all 12 required scripts are 10.0.39`. If a line
   says the scripts folder mixes versions, delete every `*_rando_*.lua` in `scripts` and copy the
   download's files again.

## Uninstall

Delete the 13 randomizer files in `scripts` and the randomizer's `rivet.toml`. Your saves are not
touched.
