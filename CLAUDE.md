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

Current version: v0.70 (kit 10.0.35), the public beta, built from branch `release-v0.70` (= v0.62-DEV14 released).
The dev line is `fix/v0.62-dev5` (merged into `main`). Player ZIP SHA-256: see `DEVELOPMENT_LOG.md` (v0.70 entry).
Not yet verified in the real game: see `release/KNOWN_ISSUES.md` and `mod/RiftApartRandomizer/docs/KNOWN_ISSUES.md`.
