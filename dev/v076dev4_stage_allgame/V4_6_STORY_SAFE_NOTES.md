# V4.6 Story-Safe Campaign Patch

## Why this patch exists

The supplied `rivet(9).log` shows the Nefarious City story encounter was not protected by the previous V4.5 build:

- The V4.5 launcher explicitly built with storymission zones included.
- The generated stage manifest changed nine enemy spawners in `levels/i29/overlay/storymission/mis_nefcity_01/i29_nefcity_01_gp_combat.zone`.
- The runtime variable route also changed enemy spawners while `MIS_INTRO` was active.
- V repeatedly queried `MIS_INTRO` and the game returned that its mission record was already complete. The previous tracker kept a stale mission target and therefore did not address the live encounter.
- F11 is an emergency restore switch. It turns off future enemy replacement and restores loaded spawner variables; it does not synthesize a mission objective or encounter completion signal.

The stage builder already had a `--exclude-storymission` option, but V4.5 did not use it.

## V4.6 changes

1. **All storymission overlay zones are excluded from the generated `.stage` patch.** The builder still applies the V4 maximum-coverage profile to eligible non-story zones.
2. **Runtime enemy replacement pauses while a story mission is active.** The tracker listens to both mission-state changes and start/end devstats events, so it can clear a mission when the game ends it.
3. **Existing runtime changes are put back** when the story-mission guard becomes active.
4. **V no longer falls back to an old completed mission** after the live mission ledger has cleared it. A completed mission record is reported as completed, not as encounter progress.
5. **F11 labels are corrected** consistently. F11 remains a restore/safe-mode key, not a mission-completion command.

## Build and install

Run `BUILD_V4_6_STORY_SAFE.bat`, select the same game folder, and allow the builder to scan, build, and independently check the output. Install the resulting build when prompted.

The generated manifest/report should contain no zones under `levels/.../storymission/...`. Non-story zones remain eligible for the experimental V4 maximum-coverage randomizer.

For an encounter that was already altered before installing this patch, load the last checkpoint after installing so the game respawns the encounter using its native spawners. The patch cannot retroactively repair enemies already spawned or invent a missing story signal.

## Validation status and limits

- Source-level changes committed to this branch.
- The builder's `--exclude-storymission` option is already implemented in `stage_allgame.py`; V4.6 now passes it.
- No game executable or save is available in this environment, so this is **not** an in-game verified fix.
- The V4 maximum-coverage profile remains experimental for non-story zones. This patch specifically removes enemy randomization from storymission overlays to protect campaign progression.
