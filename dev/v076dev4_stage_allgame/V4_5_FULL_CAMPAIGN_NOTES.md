# V4.5 Full Campaign Experimental

## Purpose

V4.5 returns to maximum campaign coverage after the V4.2 diagnostic branch. It includes zones under `levels/.../storymission/...`; it does not pass `--exclude-storymission`.

## Build profile

The launcher runs:

```powershell
py -3 -I tools/stage_enemies/stage_allgame.py build --game "GAME" --out "BUILD" --seed "RiftApart-Enemy-V4.5-FullCampaign" --profile v4 --force-all-enemies --rate 1.0
```

The V4 planner:
- Uses the global scanned actor catalogue as the replacement pool, including globally unique enemy template UIDs from other zones.
- Attempts every structurally identifiable, classifiable regular-enemy factory at a 100% selection rate. V4.5 excludes same-kind candidates even when they have a different UID, preventing no-visible-change swaps such as hover → hover or shooter → shooter found in Copy5.log.
- Bypasses faction/movement and spawn-point compatibility checks. This is deliberately unsafe and may create enemies that fail to spawn, cannot be killed, or do not work with a particular encounter.
- Includes V3/V4 exact `SpawnerScriptAction Template` adapters where the existing planner can identify them.
- Still refuses ambiguous or shared-owner template variables, non-regular/boss-tier/unclassified actors, and references it cannot safely decode. Therefore this is not a literal 100% replacement of every enemy actor in the game.
- Emits a conservative `safe/` fallback build as well as the main V4 output. The launcher installs the main V4 build only after the byte-level check passes.

## Story progression and V key status

The V key is included in V4.5 as a **guarded mission-cleanup assist**, not a full active-encounter bypass.

- V queries the active story mission tracked by the spawner layer.
- If the game reports state 3 (Complete Cleaning), V calls the game's own CompleteMissionAction and verifies state 4.
- If the game reports state 2 (Active), V refuses to fake deaths or skip the encounter. The actual encounter-completion signal is not exposed by the current hook, so V cannot yet force a stuck active combat gate.
- F11 is enemy emergency recovery. It replaces the previous F12 binding, which collided with the legacy campaign key in the supplied log.

The V code has been added but has not been validated in-game. Do not treat it as a proven encounter bypass.

## New campaign test

1. Back up the current save separately.
2. Run `BUILD_V4_5_FULL_CAMPAIGN.bat` and point it to the game folder containing `RiftApart.exe`, `toc`, and `dag`.
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
- A full new-campaign run is required before calling V4.5 campaign-verified.


## V4.5 follow-up: hotkeys and story-gate honesty

- V is now bound and checks the currently active story mission tracked by the spawner layer.
- If the game reports mission state 3 (Complete Cleaning), V asks the game's own mission system to finish cleanup and verifies the returned state is 4.
- If the mission is still active (state 2), V reports that it cannot bypass the encounter. It does not kill actors, forge death events, or mark objectives complete.
- F11 is now enemy emergency recovery. This avoids the F12 collision with the legacy campaign key observed in rivet - Copy5.log.
- The Copy5 log's initial global template pool of 0 was transient: later in that same log it reached 26 resident templates. The same log contained same-kind substitutions (for example, hover → hover), which V4.5 now filters out. The .stage summary for that session still recorded zero spawns from patched .stage spawners on the visited level; the runtime route separately recorded replacements. Do not interpret 277 manifest changes as 277 successful in-game replacements.
- The V path is code-added but not yet validated in-game. A true active-encounter force-complete still requires identifying the game's encounter-specific completion signal.


## V4.5 follow-up: controls and installer cleanup

- V checks the currently active story mission. It can finish mission cleanup only when the game reports state 3; it does not bypass an active encounter (state 2).
- F11 is enemy emergency recovery, avoiding the F12 collision with the legacy campaign key observed in rivet - Copy5.log.
- The installer backs up and removes obsolete scripts/dev(debug).lua; uninstall restores it from the generated backup.


## V4.5 investigation: why V never found the mission

The supplied `rivet(8).log` proves the V4.4 mission lookup was broken before it even reached the mission-state action:

- The log records 35 V key callbacks. Each one reports `SP.V.mission is unavailable`.
- `16_rando_spawners.lua` wrapped `RANDO.on_mission_state`, but the actual `MissionStateChangedEvent` path in `11_rando_campaign.lua` calls `RANDO_CAMPAIGN_RT.on_mission(name, state, previous)`. The old wrapper was attached to the wrong callback and never received the event.
- The old filter also explicitly discarded `MIS_INTRO`, even though this log records `MIS_INTRO` entering state 2 (active). V4.5 now hooks the actual campaign callback and no longer filters out `MIS_INTRO`. It still excludes the unrelated `MIS_RYNO_PLANS` side mission and cup missions.
- V also has a fallback that selects the newest state-2 mission from the campaign runtime's own event ledger if the spawner tracker has not yet seen it.

## V4.5 active-state recovery behavior

- V queries the selected mission through the game's mission helper.
- If it is already in state 3, V invokes the game's `CompleteMissionAction` and verifies state 4.
- If it is in state 2, V attempts the helper's v6 `set_state` operation to request state 3, then queries the live mission again. It invokes `CompleteMissionAction` only if that live query confirms state 3.
- If the helper lacks the v6 capability, or the live query remains state 2, V reports failure and logs the exact reason. It does not claim to have fired a spawner's `OnNumDeadTrigger`, opened a door, or started a wave.
- This is a guarded mission-state recovery attempt, not yet a proven encounter-node completion signal. The game-side encounter output is still not exposed by the currently verified hooks. Do not call it fully fixed until the in-game test shows the objective/door/wave actually advances.

## What the supplied log says about enemy replacement and progression

- The global template pool eventually reached 26 resident templates (21 walker, 5 flyer); the early spawn exceptions were transient, not a permanent preload failure.
- The three logged `.stage` summaries each report zero spawns from `.stage`-related spawners in the tested session. The manifest's 277 edits therefore did not translate into observed `.stage` enemy spawns in that run.
- The runtime route did work later: one NefCity summary records 13 enemy spawns, 9 replaced (69%), with all three verified replacement pairs' spawned bots dying (9 deaths). Four spawns were not tied to a spawner and were not replaced.
- Another earlier summary recorded 7 original despite a change and 2 spawned before the randomizer read their spawner. This is a timing/coverage gap, not proof that all enemies were randomized.
- The log includes `EndMissionDevstatsEvent` for `MIS_INTRO`, `MIS_NEFCITY_01`, and `MIS_RYNO_PLANS`, but it does not include subsequent `MissionStateChangedEvent` completion states for those missions. V4.5 adds mission-event tracking so the next log can show the queried mission and the actual response.

## V4.5 acceptance test

1. Run `BUILD_V4_5_FULL_CAMPAIGN.bat`; keep the generated coverage report and manifest.
2. Install after the independent stage check passes, then start a fresh campaign/checkpoint.
3. At a stuck story gate, press V once. The log must now show `V` selecting a named mission, followed by a query result. Repeated `SP.V.mission is unavailable` means the hotfix did not load.
4. If the state is 2, inspect whether the v6 state override is available and whether the follow-up live query reaches state 3. If it does, V will request cleanup to state 4.
5. The real acceptance criterion remains the game visibly advancing the current encounter: door opens, objective changes, or next wave starts. A mission record changing alone is not sufficient evidence.
