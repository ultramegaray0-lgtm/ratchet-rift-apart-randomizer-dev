# v0.76-DEV4 integration status

This branch now contains the self-contained v0.76-DEV4 all-planet builder package copied from the uploaded development patch.

## Integrated files

- `tools/stage_enemies/stage_allgame.py` — game-wide zone scan, planning, streaming .stage build, check/install/uninstall.
- `knowledge.py`, `rcra.py`, and `fakegame.py` — compatibility knowledge, zone parser/writer, synthetic-game fixtures.
- `stage_check_log.py` — manifest-aware runtime log checker.
- `scripts/18_rando_stage_enemies.lua` — scale 2.0.0 runtime diagnostics.
- Tests, launchers, evidence, and technical documentation.
- `BASELINE_COVERAGE_REPORT.md` — the uploaded 2026-11-25 baseline report.

## Honest baseline

The uploaded all-game run found 935 enemy spawners and changed 170 (18%) across 38 zones on 7 planets. It also counted 638 Template-adapter nodes that the current builder does not modify. There were 447 zones it could not decode. These are known coverage gaps, not successful replacements.

## Safety and scope

The builder reads game data without modifying it during scan/build/check. Install backs up replaced files; uninstall restores the newest backup. The normal replacement pool is restricted to enemy kinds already present in each zone. It does not yet inject foreign-planet actors or rewrite Template-adapter nodes.

Do not describe this as a 100% replacement build. A complete scan of the user's local game installation is still required to generate the actual .stage. The real Ardolis zone is required for the bundled end-to-end test; game data is intentionally not stored in this repository.

## Next engineering phase

1. Run CI for syntax and Lua scale tests.
2. Use a fresh local all-planet inventory to classify every unhandled enemy-owned adapter and every undecodable zone.
3. Add adapter-specific writers only where the zone structure and runtime ownership semantics are evidenced.
4. Keep experimental changes in a separate profile with byte-level checks and automatic rollback.
5. Re-run the complete game scan and report changed / eligible / unresolved totals per planet.
