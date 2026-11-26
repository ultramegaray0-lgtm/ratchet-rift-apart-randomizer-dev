# 100% Enemy Replacement — aggressive development plan

Status: V3.0 engineering alpha.3 on `work/global-runtime-enemy-registry`; offline CI passes, while real-game validation remains a separate release gate.

## Goal

Build the most aggressive practical enemy replacement build for Rift Apart: every reachable, enemy-owned encounter spawner that can be safely or experimentally rewritten should receive a replacement. Do not stop at the current 170/935 direct enemy spawners.

“100%” is the target for eligible enemy spawners in reachable game content, not a claim that every actor in every asset—including civilians, bosses, scripted allies, props, and unused archive zones—must be replaced.

## Baseline from v0.76-DEV4 coverage report

- 32,300 zone assets in the game's DAG.
- 9,046 zones scanned; 8,599 decoded; 447 not decodable.
- 109 zones hold spawner factories.
- 1,324 spawner factories total; 935 currently classified as enemy spawners.
- 170 changed across 38 zones and 7 planets (18% of the 935).
- 638 other nodes were found with Template adapters; V3 now plans exact `SpawnerScriptAction` nodes, while generic nodes and group adapters remain subject to separate runtime/eligibility rules. The 638 count is a census, not 638 confirmed enemy spawners.
- 23,254 zone assets were not in the TOC scan.
- Current .stage output is 6.4 MB across 38 zone members.
- Four changes have direct in-game confirmation; the coverage report records 79 proven, 54 kin, and 33 shared-seen changes.

## Workstreams

### 1. Expand spawner discovery
- Enumerate every spawner node shape, not only SunsetSpawnerFactory / Templates.
- Finish exact `SpawnerScriptAction` coverage, including safe shared Template variables; identify remaining node/group adapter families from the census and runtime logs.
- Resolve script-variable references, actor-group references, handles, local UID/index pairs, and shared owners.
- Distinguish one-shot factories from reusable/multi-wave factories and patch before first spawn where possible.
- Build a complete per-zone inventory with explicit reasons for every skipped node.

### 2. Expand zone coverage
- Diagnose the 447 undecodable zones by failure category: malformed/unsupported section, missing dependency, legacy format, bounds issue, or unsupported schema.
- Extend the decoder only when structure is evidenced; never guess offsets or silently accept malformed data.
- Investigate zones outside the TOC separately and determine which are reachable/loaded in actual play.
- Prioritize all reachable planets, hubs, arenas, challenge rooms, side areas, and scripted combat spaces.

### 3. Aggressive replacement pools
- Add a permissive experimental mode that tries every known enemy template, including unverified family pairings.
- Keep a conservative compatibility mode as fallback.
- Score candidates by actor validity, movement/locomotion, faction, size, spawn-point support, and known runtime evidence.
- When evidence is missing, mark the assignment EXPERIMENTAL rather than excluding it.
- Never silently substitute a civilian, pickup, vehicle, boss, ally, or progression actor as an ordinary enemy.

### 4. Spawn-point and actor compatibility
- Expand beyond the current volume/clue-native spawn-point evidence.
- Resolve external spawn-point references where possible; retain unresolved cases in the experimental manifest.
- Permit cross-family movement/size mismatches only in the explicit experimental tier.
- Keep every replacement paired with a reversible original reference.

### 5. Build integrity and reversibility
- Preserve original zone bytes and write only validated reference fields unless a new format has been independently established.
- Verify both UID and index references, ownership, and uniqueness.
- Generate per-zone byte diffs, manifests, hashes, and a rollback package.
- Reject corrupt outputs; isolate a bad zone rather than losing the whole build.

### 6. Runtime observability
- Emit one result per patched spawner: armed, original, replacement, failed, never reached, or unknown.
- Track spawned replacement counts and original-spawn counts per zone/planet.
- Separate frame-budget warnings from actual replacement failures.
- Do not count a patch as successful merely because it was written to the .stage file.

## Acceptance target

The release report must show:
1. Total reachable enemy spawners discovered.
2. Number patched, by spawner type, planet, and confidence tier.
3. Number skipped, with an exact reason for each.
4. Number of undecodable/reachable zones remaining.
5. Independent structural verification of every output zone.
6. Runtime evidence where available, clearly separated from offline-only claims.

The headline target is 100% of eligible reachable enemy spawners attempted in experimental mode. The report must still disclose any that could not be decoded, resolved, or reached.

## V3.0 implementation status

The branch now contains the all-planet builder, native global-template hook patch, global resident-template registry, synchronized runtime script bundle, and an offline planner for exact `SpawnerScriptAction` Template variables. The planner patches a shared variable only when every owner is a distinct, uniquely-keyed spawner with exactly one Template plug; it patches that variable once and records every owner key.

The V3 profile combines factory and node Template adapter changes in one `.stage`, with adapter-aware runtime monitoring and independent byte-level verification. Alpha.2's expanded 19-test offline suite passed in [GitHub Actions run 45761701002](https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/actions/runs/45761701002), including safe shared-owner grouping and exact WORKED-verdict pins; the real-zone fixture was skipped because game data is not committed. Unlisted factory, node, and group adapters remain eligible for the runtime route. It deliberately does not write foreign-zone actor UIDs into `.stage` or directly spawn combat enemies.

Build with `dev/v076dev4_stage_allgame/BUILD_V3_0_MAX_COVERAGE.bat`. Read `dev/v076dev4_stage_allgame/V3.0_ALPHA_NOTES.md` before treating the build as a release.

Important remaining gaps:
- 447 zones in the baseline scan were not decodable; the current user's game must be scanned again.
- The previous global native asset test created 14 of 25 resident templates; 11 still failed in `SpawnActorFromAsset`.
- The V3 node-adapter planner only attempts exact `SpawnerScriptAction` nodes with a singular local Template plug and either one owner or a fully verified all-spawner shared-owner group. It does not claim all 638 census entries are eligible.
- The new build has not yet been proven in-game to preserve every wave, death counter, door, and progression trigger.

V3.0 acceptance requires both offline CI/byte checks and a real in-game log showing replacement spawns, deaths, and completed encounters. A 100% attempted build is not the same as 100% successful in-game replacements.
