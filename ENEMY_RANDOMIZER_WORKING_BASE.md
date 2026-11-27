# Enemy Randomizer Working Base — Claude Handoff

**Selected baseline: `work/v4-total-enemy-coverage`. This is the branch to continue from.**

- Repository: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev
- Selected branch: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/tree/work/v4-total-enemy-coverage
- V4 engineering notes: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/blob/work/v4-total-enemy-coverage/dev/v076dev4_stage_allgame/V4_TOTAL_COVERAGE_NOTES.md
- V4 launcher: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/blob/work/v4-total-enemy-coverage/dev/v076dev4_stage_allgame/BUILD_V4_TOTAL_COVERAGE.bat

## Instruction

Continue enemy-randomizer development from `work/v4-total-enemy-coverage`. The user has selected this as the strongest enemy-coverage baseline, including over V4.6. Do not begin from `main`, V4.6, or an older branch; do not replace this baseline with the safer/narrower V4.6 approach. Pull and inspect the latest branch state before editing, then commit further work to this same branch. Preserve existing work and history. Do not merge it into `main` or a player release unless explicitly asked.

## Why this is the selected baseline

V4 combines:
- global enemy-template preloading intended to begin during loading/menu phases;
- persistent retries for template creation and runtime discovery;
- all-planet enemy asset catalog and resident-template work;
- forced foreign regular-enemy replacements for structurally eligible factory templates;
- exact `SpawnerScriptAction` local Template adapters;
- aggressive coverage settings that intentionally relax faction, movement, family-pair, and spawn-point compatibility constraints.

## Important honesty / safety boundary

This is the **highest-coverage selected experiment**, not proof of 100% enemy replacement and not a validated release. The V4 notes explicitly state that unsafe substitutions can softlock encounters. Bosses, NPCs, friendlies, non-spawner actors, direct/internal spawns, unsupported or undecodable zones, ambiguous variables, and other categories remain outside proven coverage. The native hook artifact and local game archive scan/build may also be required. Do not claim success from stage patch counts alone.

The next engineering work should maximize real eligible enemy replacement while retaining exact diagnostics, reversible stage changes, independent byte checks, and explicit separation between offline tests and real in-game evidence. Any claimed improvement must identify the evidence that supports it. Preserve progression where possible, but do not silently drop V4's coverage objective.

## Required first steps

1. Check out and pull `work/v4-total-enemy-coverage`.
2. Read `dev/v076dev4_stage_allgame/V4_TOTAL_COVERAGE_NOTES.md`, `dev/v076dev4_stage_allgame/IMPLEMENTATION_STATUS.md`, and current coverage/evidence files.
3. Inspect the latest commit, current changes, tests, and CI before modifying anything.
4. Continue from this branch and update its documentation with each meaningful change.
