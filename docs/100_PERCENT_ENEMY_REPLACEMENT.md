# 100% Enemy Replacement — aggressive development plan

Status: implementation branch opened; source-package audit in progress.

## Goal

Build the most aggressive practical enemy replacement build for Rift Apart: every reachable, enemy-owned encounter spawner that can be safely or experimentally rewritten should receive a replacement. Do not stop at the current 170/935 direct enemy spawners.

“100%” is the target for eligible enemy spawners in reachable game content, not a claim that every actor in every asset—including civilians, bosses, scripted allies, props, and unused archive zones—must be replaced.

## Baseline from v0.76-DEV4 coverage report

- 32,300 zone assets in the game's DAG.
- 9,046 zones scanned; 8,599 decoded; 447 not decodable.
- 109 zones hold spawner factories.
- 1,324 spawner factories total; 935 currently classified as enemy spawners.
- 170 changed across 38 zones and 7 planets (18% of the 935).
- 638 other spawner nodes use a Template adapter and are not yet handled.
- 23,254 zone assets were not in the TOC scan.
- Current .stage output is 6.4 MB across 38 zone members.
- Four changes have direct in-game confirmation; the coverage report records 79 proven, 54 kin, and 33 shared-seen changes.

## Workstreams

### 1. Expand spawner discovery
- Enumerate every spawner node shape, not only SunsetSpawnerFactory / Templates.
- Add adapters for the 638 Template nodes and identify any additional node families.
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

## Current source gap

The uploaded `RandoEnemies_POC_v0.76-DEV4.zip` contains a POC report, a 1.0.1 diff, a one-zone stage output, manifests, candidate data, and verification scripts. It does **not** include the full `tools/stage_enemies/stage_enemies.py`, `zone.py`, `knowledge.py`, or the complete source tree needed to apply the diff and rebuild the all-planet generator.

Required next upload: the complete v0.76-DEV4 working source folder or a ZIP containing the full `tools/stage_enemies/` directory, the associated Lua scripts, and the exact build command/config. Do not upload only the POC output ZIP again.
