# Compatibility

| Part | Requirement | Checked how |
|---|---|---|
| Game | Ratchet & Clank: Rift Apart, Steam, `RiftApart.exe` 3.0630.1.0 | `rando_give.dll` compares every byte it relies on and does nothing at all on any difference ("refused this exe" in rivet.log) |
| rivet_hook | 2.0.0 or 2.0.1 (hid.dll proxy) | both used in your game (2.0.0 in round 13). Uses `on_event`, `notify`, `read`/`write`, `script_nodes`, `component`, `signal`, `hash`, `vanity_owns`, `time_scale` (optional), `configs`/`config`/`config_set` (shop; added in rivet_hook 2.0.0, Sep 2026), `fly`/`warp` (3.0 campaign), bridge `script.exec` and `mem.read` |
| rivet.toml | `[overlay] enabled`, `[scripts] enabled`, `[bridge] enabled`, `[renderdoc] dll_path = "rando_give.dll"` | the kit's rivet.toml |
| ARSENAL_RESTORED | optional (7.0) | `restored_weapons = "auto"`: its 9 weapons join the pool when the companion finds it installed; not installed, they stay out. Its own vendor slots are left alone (ARSENAL_RESTORED.md) |
| Other Overstrike mods | fine, unless they change item configs the randomizer uses. A mod that changes the vendor's stock may leave some slots unchanged; their weapons are then given to you directly (nothing is lost) | not tested |
| Companion | Windows PowerShell 5.1 (built in) or PowerShell 7 | tests run under PowerShell 7.4 |
| Offline tool (optional) | Python 3.9+ and `pip install lupa` | |
| Saves | any slot; a **New Game** for every new 7.0 seed (6.0 progress cannot be continued). One seed per save slot | |
| rando_give.dll | v5 (unchanged since 5.0): items as v2; mission calls as v4; armor give, armor-source interception and config lookup only when every byte of that code matches RiftApart.exe 3.0630.1.0 | v4 still delivers weapons and gadgets, but cannot give armor rewards; armor sources then fall back to polling and the shop weapons the vendor does not sell are given to you (rivet.log says so). Use v5 |
| Game updates | an exe update stops the DLL (by design) and may break rivet_hook. Wait for updates of both | |

Never load two randomizer versions at once. Delete old scripts before installing.
