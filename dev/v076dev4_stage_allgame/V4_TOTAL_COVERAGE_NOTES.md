# Enemy Randomizer V4 — total-coverage attempt

Status: **engineering branch; offline tests and the user's local-game build are still required. This is not yet a verified 100% in-game replacement.**

## V4 priority

V4 prioritizes getting replacement enemy choices in place before the game spawns its first wave, including after checkpoint/death retries. Loading time and runtime scan cost are secondary to coverage.

### 1. Preload resident enemy templates during loading

The V3 runtime only called the global template loader after `scene_ready()` and a live hero. That was too late to help the first post-retry wave.

V4 changes the independent global-template frame callback so it continues during menus, loading screens and checkpoint reloads. It:
- requests the generated all-planet enemy asset catalog before scene readiness;
- creates at most one resident template actor per frame, keeping each callback small;
- keeps retrying native asset-load / template-create failures (up to 9,999 attempts) with increasing frame delays, so a slow loading phase does not silently abandon a template;
- logs `GLOBAL PRELOAD: ready N/total | pending N | failed N` as the pool changes;
- continues preloading even when the Enemy Randomizer switch is OFF, so the pool is ready if the player turns it on later.

The runtime scan budget is raised to 3 ms per frame (within the hook's shared 8 ms frame budget), with 4,096-node/queue/group ceilings, 32 group members, 9,999 budget restarts and 9,999 late-template probes. This deliberately spends more frame time and allows long-running scans rather than silently dropping a large zone.

The preload requires the custom global-registry Rivet Hook that exposes `rivet.template_actor`. The V4 source ZIP contains the hook patch source, not a prebuilt native DLL; keep the working V3 global-registry hook installed. If the log says `GLOBAL PRELOAD BLOCKED`, the native hook is missing and the preload is not active.

This is a priority preload, **not an engine loading-screen lock**. The current Lua/Rivet API exposes asynchronous asset loading but no safe way to pause the game's own scene transition until every native asset has loaded. V4 does not pretend otherwise; the patched `.stage` data is what gives the game randomized factory choices before the first wave.

### 2. Patch spawner data before the game reads it

The V4 builder writes the `.stage` file against the user's actual game archives. The game therefore reads the randomized factory Template variable from the patched zone data on initial load and on a retry that reloads that zone. Runtime discovery is fallback for spawners the stage build did not own.

The V4 profile combines:
- forced foreign enemy templates for structurally valid, single-owner, classifiable regular-enemy `SunsetSpawnerFactory` variables;
- exact `SpawnerScriptAction` `Template` adapters where the node has one unambiguous local Template variable and the planner can preserve a local unchanged anchor;
- the runtime factory, node Template and node Template-group adapters;
- a first scene-ready runtime scan (zero-frame delay) and more frequent streaming-zone rescans.

### 3. Maximum-coverage policy

The V4 factory planner deliberately bypasses faction/movement compatibility and spawn-point compatibility when choosing a foreign regular-enemy replacement. The V4 node Template planner also bypasses family-pair compatibility while retaining its structural/local-reference and anchor requirements.

This is intentionally unsafe. A replacement can be too large, too small, unable to reach the player, unable to die, or otherwise incompatible with the encounter. A changed fight can softlock. The user explicitly prioritized replacement coverage over safety and load time; the build labels every such factory change `FORCED-TEST-V4-UNSAFE`.

The V4 runtime retry limit is raised to 9999 so checkpoint retries do not permanently disable a changed runtime encounter after five deaths. It does not override structural write validation or make an invalid actor safe.

### 4. Known failed-spawner protection (V4.1)

The bundled 2026-11-26 verdict set contains **31 `NO SPAWN` results** (including multiple factories in Ardolis first visit and the Ardolis pirate-king ship). V4.1 leaves those exact spawner variables native instead of trying a different replacement for the same spawner. This is deliberately more conservative than V4: a recorded no-spawn result is treated as a property of the spawner/encounter until new in-game evidence proves otherwise. The five `WORKED` verdicts remain eligible for evidence-guided selection; `NOT REACHED` is not treated as a failure.

### 5. Campaign recovery key (V4.1)

Press **F10** at any point to enter Emergency Safe Mode for the rest of the current game session.

- Turns the Enemy Randomizer OFF and restores its live runtime edits.
- Scans the current level's manifest-owned `.stage` spawners and writes their original template UID/handle back when the original actor is available.
- Keeps scanning newly loaded zones/checkpoints in recovery-only mode and restores their manifest-owned variables before any runtime replacement can run.
- Stops further global enemy-template preloading for the session.
- Does **not** delete enemies already spawned, force an encounter output, or open a door by bypassing the game's objective logic. If a wave is already stuck, press F10, wait for the restore message, then reload the last checkpoint so the game respawns the native enemies.

If an original template UID cannot be resolved in the current level, the log reports `EMERGENCY RESTORE UNAVAILABLE`; use the builder's `safe` fallback build or uninstall the stage patch before continuing. F10 is intentionally a one-way session safety latch; restart the game to return to normal randomization.

### 6. What V4 does not yet claim

The word “total” describes the aggressive spawner coverage attempt, not all actors in the game. These categories remain outside the current proven replacement mechanism:
- story bosses and phase-driven boss encounters;
- NPCs, civilians, friendlies, mounts, vehicles, hazards, props and pickups;
- enemies placed directly in a zone with no supported spawner variable;
- split children, projectiles and enemies created internally by another actor;
- direct spawn calls not represented by the supported factory / node variables;
- ambiguous or malformed variables, and shared factory variables that cannot be safely identified as a single-owner factory;
- zones the game archive scanner cannot decode or that are not reachable from the current game install.

V4 expands the global asset list to every unambiguous, classifiable regular-enemy actor asset found in the scanned game archive, including enemy assets that were previously only used as placed actors. Story bosses and non-enemies remain excluded. This broadens the replacement pool; it does not prove every actor asset is valid as a live spawner template. Assets the native hook cannot create remain listed as preload failures and are not counted as ready.

### 7. Build and install

Run `BUILD_V4_TOTAL_COVERAGE.bat` from this directory. It:
1. scans the actual game archive;
2. builds V4 with `--profile v4 --force-all-enemies --rate 1.0`;
3. builds the global resident enemy asset catalog and the hybrid node inventory;
4. runs the independent byte-level `.stage` check;
5. installs only after the check passes, backing up replaced files.

The launcher uses `--no-safe` because the ordinary “safe” fallback is not the selected V4 experiment. Keep the automatic backup; use the builder's uninstall route to restore it.

### 8. Acceptance gate

After install, the first test should be one ordinary encounter followed by one deliberate death/checkpoint retry. Confirm:
- `GLOBAL PRELOAD` advances while the loading screen/menu is visible;
- the same spawner produces the same selected replacement after retry;
- first-wave enemies are replaced, not merely later waves;
- replaced enemies can be killed and encounters, doors and mission progression complete.

Then play every planet and run `CHECK_MY_LOG.bat`. A V4 build report counts patched variables, not successful spawns. The log must classify each reached spawn as replacement or original, and any remaining gaps must be fed into the next patch.

**Do not call this 100% complete until the user's logs show every eligible, reached enemy spawn replaced and the full campaign completes without a progression blocker.**
