# Global resident enemy-template experiment

This branch replaces the V2.2 foreign-template-UID experiment with a runtime asset registry.

## Architecture

1. stage_allgame.py scans all available zones and writes 15_rando_global_enemy_assets.lua from every classifiable regular enemy actor asset already used by a native factory or SpawnerScriptAction template. Paths are deduplicated; ambiguous path/name combinations and non-regular/boss assets are excluded.
2. The custom Rivet Hook API rivet.template_actor(path, uid, create) requests the actor asset through the game's native LoadActorAsset path. With create=false, it only requests/polls the asset. With create=true, it creates a resident actor through the same native SpawnActorFromAsset function used by the hook's rift portals.
3. The native helper assigns a stable high-bit synthetic UID, marks the source actor as ActorFlag::Template, clears active/update and zone/level-unload flags, and sets zoneIndex=-1. It returns the actor handle and flags for read-back validation.
4. 16_rando_spawners.lua classifies each resident source and adds it to the current level's template pool. It creates at most one actor per frame to avoid exhausting Rivet Hook's 8 ms Lua budget.
5. The original SpawnerScriptAction remains responsible for the actual combat spawn, death tracking, encounter counts, and progression. Only its Templates selection is changed.

This is intentionally not the old V2.2 method: the builder must not write foreign source-zone UIDs into target .stage files.

## Build and install

### 1. Build the custom Rivet Hook

Run the GitHub Actions workflow "Build Global Enemy Registry Hook" on this branch. Download the rivet-hook-global-enemy-templates artifact from the completed run. Back up the existing hook files before replacing them with the artifact files.

The workflow builds a pinned upstream Rivet Hook source revision and applies patch_rivet_hook.py. The custom API is not present in an unmodified Rivet Hook release.

V3 diagnostic native build: [GitHub Actions run 45761496419](https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/actions/runs/45761496419) — all configure, compile, collect, and upload steps passed. Artifact: [rivet-hook-global-enemy-templates (7.37 MB)](https://api.github.com/repos/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/actions/artifacts/15089833146/zip). This build adds separate native diagnostics for exceptions, null actor returns, and unreadable actor pointers, including asset ID/status/path.

### 2. Build the local game-specific catalog

For V3.0, run `dev/v076dev4_stage_allgame/BUILD_V3_0_MAX_COVERAGE.bat` against the installed game folder. It builds a local-zone factory + exact node Template stage, a factory-only safe fallback, and a synchronized full runtime script bundle. Do not pass `--force-all-enemies` or `--cross-planet`; those recreate the unverified foreign-UID approach that caused the V2.2 failures.

From the repository root in PowerShell (replace the game path with the installed game folder):

```powershell
py -3 .\dev\v076dev4_stage_allgame\tools\stage_enemies\stage_allgame.py build --game "E:\Path\To\Ratchet.and.Clank.Rift.Apart Modded" --out ".\builds\V3_0" --profile v3 --rate 1.0
py -3 .\dev\v076dev4_stage_allgame\tools\stage_enemies\stage_allgame.py check --game "E:\Path\To\Ratchet.and.Clank.Rift.Apart Modded" --build ".\builds\V3_0"
```

The output should contain:
- RandoEnemies.stage
- 15_rando_global_enemy_assets.lua
- 16_rando_spawners.lua
- 18_rando_stage_manifest.lua
- 18_rando_stage_enemies.lua
- COVERAGE_REPORT.md

Run the builder's install command to install the stage and Lua files. It backs up files it replaces.

### 3. Verify the new runtime registry

On launch, rivet.log should report:
- GLOBAL TEMPLATE REGISTRY: requesting ... actor asset(s)
- GLOBAL TEMPLATE READY ... for accepted templates
- any GLOBAL TEMPLATE REJECTED / GLOBAL TEMPLATE FAILED entries with a reason

The status API also reports global_templates.

## Hybrid all-spawner coverage

The V3 all-planet `.stage` builder edits SunsetSpawnerFactory `Templates` variables and exact `SpawnerScriptAction` `Template` adapters. It supports a shared variable only when every owner is a distinct, uniquely-keyed spawner with exactly one Template plug. Other node/group adapters remain on the runtime route.

- `.stage` owns only the factory `Templates` keys listed in a V3 manifest; unmodified factory keys remain eligible for the runtime route. Older `max`/`all` manifests retain their conservative all-factory write guard.
- Runtime `Template` and group adapters remain enabled, using the global resident-template pool where the native
  asset path can create a resident template. Manifest-listed node Template keys are excluded from runtime writes; a shared variable is listed under every owner key and patched only once.
- The stage monitor observes only the adapter type and spawner keys listed in its manifest, so runtime-only spawns are not
  misreported as `.stage` replacements.
- The complete V3 runtime bundle uses kit version `10.0.50` plus the separate `STAGE_LUA = 1.1.0` handshake. Both checks must match.

For the V3 local-only build, run `dev/v076dev4_stage_allgame/BUILD_V3_0_MAX_COVERAGE.bat`. It builds a V3 hybrid profile and a factory-only safe fallback, runs the independent `.stage` checker, and deliberately does **not** use `--cross-planet`. The older `BUILD_HYBRID_MAX_COVERAGE.bat` is marked legacy experimental profile-all and is not the V3 release path.

This hybrid is the current highest-coverage route without writing foreign-zone actor UIDs into `.stage` files or letting
two systems write the same Script Vars variable. The V3 log checker expands shared-owner changes into per-owner verdicts, so a WORKED result can pin the same replacement safely on the next build. It is not yet a proven 100% result: the native global registry previously
created 14 of 25 catalog templates, and the node-adapter path still requires in-game verification.

## Safety and known unknowns

- The actor-asset load and spawn calls are native engine paths already used by Rivet Hook; the new helper compiles against the pinned hook source.
- The key unproven runtime behavior is whether SpawnerScriptAction accepts a zone-less actor with a synthetic high-bit UID and Template flag as a source template. Compilation cannot prove this.
- If that works, the original encounter system still performs the combat spawn. If it does not, the script rejects the template or the game may refuse that replacement; do not assume the method is game-verified until the first in-game log confirms it.
- The catalog only includes regular enemy actors that the scanner can classify. It intentionally excludes boss-tier and ambiguous assets.
- The randomizer's existing compatibility setting still governs which global templates can replace a given spawner. enemy_compat = max is the broadest mode and retains the project's existing combat-watch behavior.
