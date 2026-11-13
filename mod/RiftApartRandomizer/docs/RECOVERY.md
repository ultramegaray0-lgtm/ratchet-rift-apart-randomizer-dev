# Recovery: back to the original game

The randomizer never changes the game's own files (archives, toc, exe) or your game saves'
format. It adds files next to the game, and while it runs it adds items to the inventory of the
save you play.

## Remove the randomizer (keep rivet_hook)

1. Close the game and the companion window.
2. From `<game>\scripts` delete every `*_rando_*.lua`: `01_rando_data.lua`,
   `02_rando_generator.lua`, `03_rando_campaign.lua`, `04_rando_settings.lua`,
   `05_rando_bindings.lua`, `06_rando_capabilities.lua`, `09_rando_real.lua`,
   `10_rando_runtime.lua`, `11_rando_campaign.lua`, and `00_rando_seed.lua`,
   `07_rando_*.lua`, `08_rando_*.lua` if present.
3. Delete `<game>\rando_give.dll`.
4. In `<game>\rivet.toml` set `[renderdoc] enabled = false` (or put back your own rivet.toml).

The game now runs with rivet_hook only.

## Remove rivet_hook too

Delete `hid.dll`, `rivet_hook.dll`, `rivet.toml`, `rivet.log` and the `scripts` folder from the
game folder. Steam's **Verify integrity of game files** then confirms that the game is original.
ARSENAL_RESTORED is installed through Overstrike and is separate: uninstall it there if you want.

## Your game save

Weapons and gadgets the randomizer added are now part of that save, like items bought from a vendor. To go
back to the state before the randomizer, restore the copy of
`Documents\Ratchet & Clank - Rift Apart` you made before installing (INSTALL.txt, "BEFORE YOU
START"). Close the game first.

## Randomizer progress only

- **Start the seed over:** start a New Game: the randomizer starts the seed's progress over by itself and keeps the previous run as `rando_<fingerprint>.runN.lua`. To throw progress away without a new game: close the game, then delete `companion\randomizer_saves\rando_<fingerprint>.lua` (the fingerprint is in the spoiler log's name and in rivet.log `RANDO-SEED ready`). In test mode you can instead press Ctrl+F10 twice in the game.
- **A New Game reset you did not want** (it should only happen when the prologue starts): close the game, copy `rando_<fingerprint>.runN.lua` (the highest N) over `rando_<fingerprint>.lua`, start again. To switch the reset off: `new_game_reset = false`.
- **The vendor:** the randomizer only changes which weapon each slot sells, in memory. To see the usual order, set `shop_runtime = false` and reload the level. Nothing about the vendor is saved; the next level load restores the game's values.
- **Armor pods:** if a pod should give you its own piece instead, set `armor_intercept = false` and reload the scripts (Pause); its location still pays.
- **A new random seed:** start the companion with `-NewRandomSeed`, or delete `randomizer_saves\random_seed.txt`.
- **Go back to 1.4:** see MIGRATION.md (your 1.4 progress file is untouched).
- **A save got damaged:** the companion uses `rando_<fingerprint>.lua.bak` automatically. If both are damaged, it says so and does not overwrite them. Fix or delete the file, then restart the companion.

## The campaign (3.0)

- **Turn the campaign off for a seed:** set `campaign_mode = "vanilla"` (a different seed, start it on a new save), or delete `06_rando_capabilities.lua`'s verified lines (put back the kit's file). Then the director does nothing, and the game's own order plays.
- **A lab experiment (test mode) changed a save's story:** that is why the tests run on a spare slot. Restore your save backup or delete that slot. The randomizer only borrows a node's field for 45 frames and puts it back. It never writes save files.
- **F12 took you somewhere without its story:** a warp moves the save's checkpoint. Use the planet menu to fly back, or load the autosave from before F12. Send rivet.log (`RANDO-CAMPAIGN` lines).

## Something is stuck

- **Rewards keep "waiting":** press F9. Rewards waiting for the game are retried on every planet load. If rivet.log shows `direct delivery off: refused this exe`, your RiftApart.exe is not 3.0630.1.0 (a game update). The DLL then does nothing at all, by design.
- **The game crashes at start after an update:** remove `rando_give.dll`, or set `[renderdoc] enabled = false`. The DLL checks every byte it uses and should refuse a changed exe, but an update can also move rivet_hook's own hooks.
