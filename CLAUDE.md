## ACTIVE ENEMY RANDOMIZER WORKING BASE — READ FIRST

For **Enemy Randomizer work only**, the authoritative highest-coverage baseline is the existing branch:

- Branch: `work/v4-total-enemy-coverage`
- Direct link: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/tree/work/v4-total-enemy-coverage
- V4 notes: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/blob/work/v4-total-enemy-coverage/dev/v076dev4_stage_allgame/V4_TOTAL_COVERAGE_NOTES.md
- V4 builder: https://github.com/ultramegaray0-lgtm/ratchet-rift-apart-randomizer-dev/blob/work/v4-total-enemy-coverage/dev/v076dev4_stage_allgame/BUILD_V4_TOTAL_COVERAGE.bat

**This branch is the selected working base, ahead of V4.6 for enemy-coverage scope. Do not start new enemy-randomizer work from `main`, V4.6, or another older enemy branch.** First fetch the repository, check out/pull `work/v4-total-enemy-coverage`, and inspect its current HEAD and working tree. Continue development on this same branch unless the user explicitly changes the target. Do not reset, force-push, overwrite, or discard its work. Do not merge this experimental branch into `main` or the player release without explicit authorization.

The branch is intentionally an aggressive maximum-coverage experiment: it combines pre-load/global enemy-template work, retry-persistent runtime discovery, forced foreign regular-enemy factory replacements, and exact `SpawnerScriptAction` Template adapters. It is the best selected baseline for the user's goal of maximizing randomized enemies—not a verified 100% in-game result. Its own notes explicitly warn that bypassing faction/movement/spawn-point compatibility can cause softlocks, and that bosses, NPCs, non-spawner actors, unsupported/undecodable zones, and other categories are not proven covered. Never describe it as complete or safe without new evidence.

Before changing it:
1. Read `dev/v076dev4_stage_allgame/V4_TOTAL_COVERAGE_NOTES.md`, `IMPLEMENTATION_STATUS.md`, and the latest coverage/evidence reports on that branch.
2. Inspect the branch's latest commit and working-tree state; preserve all existing work.
3. Build on V4's actual code and evidence. Do not silently substitute V4.6's safer/narrower behavior or revert to V3.
4. Keep offline/static validation distinct from real-game validation. A patched variable is not proof of a replacement spawn; a replacement spawn is not proof that the encounter or campaign progresses.
5. Record exactly what changed, tests run, known gaps, and in-game evidence in the branch documentation.

This instruction is an enemy-randomizer-specific override to the general workflow below. The general `main` workflow still applies to unrelated randomizer work.

# Ratchet & Clank: Rift Apart Randomizer — development repository

This is the **private development source of truth**. The public player repository
(`RatchetRA`) only receives release builds made from here.

## Rules (always)

- This repository must stay **private**. Never change its visibility, never create releases,
  forks, mirrors or public links for it, and never copy developer files into the public repo.
- Never commit personal data: Windows user folders (`X:\Users\<name>\...`), real names, emails,
  tokens or keys. Before every push run `bash tools/privacy_scan.sh` and check every hit.
  New `rivet.log` files from the player's PC must have the `game = ...` path replaced with
  `<GAME_FOLDER>\RiftApart.exe` before they go into `tests/data/`.
- No original game files or assets. The two `tests/data/*_game_code_dump.json` files are short
  byte excerpts used by one test; do not add more game data than a test needs.
- Do not rewrite or force-push history. Commit meaningful changes with descriptive messages.

## Session workflow

1. `git pull` (or clone) and read `DEVELOPMENT_LOG.md` (history, findings, handoff) and
   `README.md` (layout).
2. Work on `main`. Old version branches (`v8.3` … `release-v0.54`) are kept for history.
3. `pip install lupa capstone` then `python run_tests.py` (writes `TEST_RESULTS.txt`;
   PowerShell 7 tests skip without `pwsh`).
4. Update `DEVELOPMENT_LOG.md` with what changed and what is verified in the real game vs only in
   the simulator.
5. Commit, run the privacy scan, push to `main`.

## Layout in brief

- `mod/RiftApartRandomizer/` — the install-ready kit: `scripts/` (18 kit Lua scripts: 12 required, 6 optional - 15_rando_hub, 16_rando_spawners, enemy, boss, chaos and 17_rando_omega (both dev only: held back from player packages);
  nothing else since dev 10.30), `dev_scripts/` (the `dev(name).lua` developer diagnostics, which never ship),
  `rando_give.dll` + `rando_give_source/`,
  `companion/` (PowerShell companion and research tools), `rivet.toml`, `docs/`.
- `release/` — player-facing docs for the public ZIP; `tools/build_public_release.py` builds it;
  `release_tools/validate_release.py` validates it.
- `data/`, `tools/` — game database, generators and analysis tools.
- `tests/` — simulator-based test suite (`tests/sim/rivet_sim.lua`), real-log replays.

Current version: v0.75 (kit 10.0.39), the public beta (= v0.71-DEV9 released), on `main` and branch `release-v0.75`.
Two packages: the full player ZIP (`tools/build_public_release.py`, docs in `release/`) and the Lite ZIP for NexusMods
(`tools/build_lite_release.py`, `release_lite/`: Lua scripts only, no DLL, no companion). SHA-256: RatchetRA's RELEASE_NOTES.md.
Not yet verified in the real game: see `release/KNOWN_ISSUES.md` and `mod/RiftApartRandomizer/docs/KNOWN_ISSUES.md`.
