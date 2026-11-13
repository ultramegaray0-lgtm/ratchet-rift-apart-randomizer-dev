# Compatibility: Ratchet Rift Apart Randomizer v0.54

## Supported

| | Supported | How this was established |
|---|---|---|
| Game | **Ratchet & Clank: Rift Apart, Steam, v3.630.1.0** (`RiftApart.exe` file version 3.0630.1.0, the Steam patch of 9 July 2026) | `rando_give.dll` checks every byte of the game code it relies on, and does nothing on any difference. Those checks passed on the developer's install of this version |
| Operating system | **Windows 10 / 11, 64-bit** | the target platform. The development builds ran on one Windows PC; **this release (v0.54) has not yet run on Windows** |
| Mod loader | **rivet_hook 2.0.1** (2.0.0 also works) | used in the developer's test rounds. The randomizer needs its Lua scripting, overlay, pipe bridge and `config_set`, all added in 2.0.0 |
| PowerShell | Windows PowerShell 5.1 (built into Windows) or PowerShell 7 | the companion uses only commands available in 5.1 (checked statically); its automated tests ran under PowerShell 7.4 in earlier builds |
| Game install location | any folder, any drive, paths with spaces or `&` | nothing in the package uses a fixed path; everything is found relative to `RiftApart.exe` or the companion's own folder |
| Windows user | any user name; no administrator rights | nothing uses user-folder paths |

## Not supported or not tested

| | Status |
|---|---|
| Other game versions (older or future patches) | **Not supported.** The helper DLL switches itself off ("refused this exe"), so seeds generate but rewards that need it don't arrive. A game update needs a randomizer update, and usually a rivet_hook update |
| Epic Games Store version | **Untested.** Its executable may differ from Steam's. The helper then switches itself off |
| Steam Deck / Linux (Proton) | **Untested.** rivet_hook's `hid.dll` proxy needs a Wine DLL override, and the companion needs PowerShell. Not supported for now |
| Mod managers (Vortex, Overstrike, ...) | **Not supported.** Install by hand as described in INSTALLATION.md. Overstrike is still fine for *other* `.stage` mods |
| Two randomizer versions at once | Never. Delete old `*_rando_*.lua` files before installing |
| A second PC | **Not yet tested.** This beta is the first public test |

## Other mods

| Mod | |
|---|---|
| **ARSENAL_RESTORED** (Overstrike or rivet_hook version) | Supported and optional. Its 9 weapons join the reward pool when it's found. They're never sold in Ms. Zurkon's shop, and the slots its vendor adds for them are closed |
| Other rivet_hook asset mods | Fine. Keep their entries in `rivet.toml` under `[assets] paths` |
| Other rivet_hook Lua scripts | Should coexist. They run side by side in `scripts\`. Not tested together |
| Overstrike `.stage` mods that only change looks (skins, textures) | Should be fine. Not tested |
| Mods that change weapons, the vendor, item configs or missions | May conflict. A changed vendor can leave some shop slots unchanged; those weapons are then given to you directly |

## What each part reads and writes

| Part | Reads | Writes | Network | Admin |
|---|---|---|---|---|
| `scripts\*.lua` (run by rivet_hook) | game memory, through rivet_hook's API | game memory, through rivet_hook's API (inventory, mission state, travel flags, the vendor's slots); `rivet.log` through rivet_hook | none (rivet_hook's Lua has no file or network access) | no |
| `rando_give.dll` (loaded by rivet_hook) | `RiftApart.exe` code in memory (byte checks) | game memory only: one 14-byte hook on the game's script pump, one replaced armor-reward handler (only if its 0x72 bytes match exactly), one 4 KiB mailbox page. Once per frame it carries out at most one request the scripts left in the mailbox (give an item or armor piece, query, start or complete a mission, set a mission's saved state, the level mask or the travel flag), inside an exception handler. Nothing on disk | none | no |
| `rando_companion\RandoCompanion.ps1` | `rivet.toml` and `mods\` (to find ARSENAL_RESTORED); the game's `toc` file, read-only, searched for one asset id; the local pipe `\\.\pipe\rivet_hook` | `rando_companion\randomizer_saves\` only (progress, `.bak` copies, `random_seed.txt`, spoilers) | none (a local named pipe on this PC only) | no |
| `rando_companion\Install-ArsenalRestored.ps1` (only if you run it) | the ARSENAL_RESTORED zip, folder or `.stage` you give it | `mods\ARSENAL_RESTORED` (replaced if present), the mod's `.lua` files into `scripts\`, `rivet.toml` (old copy kept as `rivet.toml.bak`), a temporary folder in `%TEMP%` that it deletes afterwards | none | no |

**`rando_give.dll` imports** (the complete list): from `kernel32.dll` `CloseHandle`,
`CreateToolhelp32Snapshot`, `FlushInstructionCache`, `GetCurrentProcess`, `GetCurrentProcessId`,
`GetCurrentThreadId`, `GetModuleHandleA`, `GetModuleHandleExA`, `GetThreadContext`, `OpenThread`,
`ResumeThread`, `SetThreadContext`, `SuspendThread`, `Thread32First`, `Thread32Next`,
`VirtualAlloc`, `VirtualProtect`; from `ntdll.dll` `__C_specific_handler`. There's no file, registry,
network or process-launch function. It needs no C runtime.

**The game's files and your game saves are never changed.** rivet_hook loads everything from loose
files at run time; there is no archive or `toc` rewrite. Removing the files (INSTALLATION.md,
"Uninstalling") returns the game to normal.
