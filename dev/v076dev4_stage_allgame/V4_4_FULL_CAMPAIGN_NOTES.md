# V4.4 Full Campaign Experimental

## Purpose

V4.4 returns to maximum campaign coverage after the V4.2 diagnostic branch. It includes zones under `levels/.../storymission/...`; it does not pass `--exclude-storymission`.

## Build profile

The launcher runs:

```powershell
py -3 -I tools/stage_enemies/stage_allgame.py build --game "GAME" --out "BUILD" --seed "RiftApart-Enemy-V4.4-FullCampaign" --profile v4 --force-all-enemies --rate 1.0
```

The V4 planner:
- Uses the global scanned actor catalogue as the replacement pool, including globally unique enemy template UIDs from other zones.
- Attempts every structurally identifiable, classifiable regular-enemy factory at a 100% selection rate. V4.4 excludes same-kind candidates even when they have a different UID, preventing no-visible-change swaps such as hover → hover or shooter → shooter found in Copy5.log.
- Bypasses faction/movement and spawn-point compatibility checks. This is deliberately unsafe and may create enemies that fail to spawn, cannot be killed, or do not work with a particular encounter.
- Includes V3/V4 exact `SpawnerScriptAction Template` adapters where the existing planner can identify them.
- Still refuses ambiguous or shared-owner template variables, non-regular/boss-tier/unclassified actors, and references it cannot safely decode. Therefore this is not a literal 100% replacement of every enemy actor in the game.
- Emits a conservative `safe/` fallback build as well as the main V4 output. The launcher installs the main V4 build only after the byte-level check passes.

## Story progression and V key status

The V key is included in V4.4 as a **guarded mission-cleanup assist**, not a full active-encounter bypass.

- V queries the active story mission tracked by the spawner layer.
- If the game reports state 3 (Complete Cleaning), V calls the game's own CompleteMissionAction and verifies state 4.
- If the game reports state 2 (Active), V refuses to fake deaths or skip the encounter. The actual encounter-completion signal is not exposed by the current hook, so V cannot yet force a stuck active combat gate.
- F11 is enemy emergency recovery. It replaces the previous F12 binding, which collided with the legacy campaign key in the supplied log.

The V code has been added but has not been validated in-game. Do not treat it as a proven encounter bypass.

## New campaign test

1. Back up the current save separately.
2. Run `BUILD_V4_4_FULL_CAMPAIGN.bat` and point it to the game folder containing `RiftApart.exe`, `toc`, and `dag`.
3. Review the generated `COVERAGE_REPORT.md` and `inventory.csv`; the report is the actual coverage result, not the "100% rate" setting.
4. Install only after the independent `check` passes.
5. Start a **new campaign** so story mission graphs and spawner state are initialized from the new stage. Do not reuse a save already stuck in an encounter.
6. At each first encounter on a planet, note: original enemy, replacement enemy, whether it spawns, whether it can be killed, and whether the encounter completes/door opens.
7. If story progression stalls, record the encounter name and collect `rivet.log`. F11 is emergency recovery only; reload the last checkpoint after using it if necessary.

## Acceptance criteria

- Builder completes and independent byte-level check passes.
- Coverage report shows storymission zones were scanned/planned and lists every refusal.
- Randomized replacements spawn and are killable.
- Story encounters advance naturally without objective/door softlocks.
- A full new-campaign run is required before calling V4.4 campaign-verified.


## V4.4 follow-up: hotkeys and story-gate honesty

- V is now bound and checks the currently active story mission tracked by the spawner layer.
- If the game reports mission state 3 (Complete Cleaning), V asks the game's own mission system to finish cleanup and verifies the returned state is 4.
- If the mission is still active (state 2), V reports that it cannot bypass the encounter. It does not kill actors, forge death events, or mark objectives complete.
- F11 is now enemy emergency recovery. This avoids the F12 collision with the legacy campaign key observed in rivet - Copy5.log.
- The Copy5 log's initial global template pool of 0 was transient: later in that same log it reached 26 resident templates. The same log contained same-kind substitutions (for example, hover → hover), which V4.4 now filters out. The .stage summary for that session still recorded zero spawns from patched .stage spawners on the visited level; the runtime route separately recorded replacements. Do not interpret 277 manifest changes as 277 successful in-game replacements.
- The V path is code-added but not yet validated in-game. A true active-encounter force-complete still requires identifying the game's encounter-specific completion signal.


## V4.4 follow-up: controls and installer cleanup

- V checks the currently active story mission. It can finish mission cleanup only when the game reports state 3; it does not bypass an active encounter (state 2).
- F11 is enemy emergency recovery, avoiding the F12 collision with the legacy campaign key observed in rivet - Copy5.log.
- The installer backs up and removes obsolete scripts/dev(debug).lua; uninstall restores it from the generated backup.
