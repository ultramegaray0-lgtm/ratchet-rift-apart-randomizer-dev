# V4.2 Campaign Progression Safe

## Why this build exists

The V4 total-coverage build used `--profile v4 --force-all-enemies`. That profile explicitly bypasses faction/movement and spawn-point compatibility checks and also enables exact `SpawnerScriptAction Template` adapters. It patched mission-story zones throughout the campaign. The V4.1 verdict gate only excluded known `NO SPAWN` / `ORIGINAL SPAWNED` spawners; it did not prove that the remaining replacements preserve every story encounter's completion wiring.

The uploaded test log also showed that F10 was bound twice: the story-mission test mode and enemy emergency rescue. V4.2 moves enemy emergency rescue to **F12**, leaving F10 for the test tools.

## V4.2 policy

- Every zone whose path contains `/storymission/` is skipped entirely. The builder does not write any of its script variables into the new stage.
- Uses the existing `safe` factory planner, not `v4` or `--force-all-enemies`.
- Keeps only local, single-owner factory variables that pass the existing faction/movement-pair and spawn-point checks.
- Does not use the `SpawnerScriptAction Template` node adapters (those are only enabled by profiles `v3` and `v4`).
- Does not use cross-planet actor references or forced foreign templates.
- Retains the ordinary runtime randomizer for eligible non-story zones.
- Emergency recovery is **F12**. It restores future spawner templates; it does not kill live enemies, complete objectives, or force doors open.

This is deliberately a controlled campaign-safety build, not a claim of 100% enemy replacement. The immediate goal is to determine whether storymission zone edits were responsible for the campaign blocker while keeping supported non-story encounters randomized.

## Build and install

Run `BUILD_V4_2_CAMPAIGN_SAFE.bat` from this folder and provide the game folder containing `RiftApart.exe`, `toc`, and `dag`. The launcher builds from the installed game's own archives, runs the independent byte-level check, then asks before installing. Existing files are backed up by the installer.

After installing, reload the current checkpoint so the mission graph and its spawner state are recreated from the new native story zones. Do not continue the already-stuck encounter and expect a template restore to repair its existing runtime state.

## Acceptance criteria

1. The early story encounter spawns native enemies and completes its objective/door normally.
2. A later non-story encounter still shows supported randomized enemies.
3. F12 disables further runtime replacements and restores changed runtime spawners.
4. The full campaign has no story progression blocker.

Only the first two can be established by the next focused in-game test. A complete campaign run is still required before calling the build campaign-verified.
