# Rift Apart Randomizer 9.0 (development project)

9.0 = your edited 8.5.2 scripts without the Zurkie's hub: a New Game plays the prologue, then
Nefarious City, then Sargasso, as in the game. `mod/RiftApartRandomizer/docs/CHANGELOG.md` (8.1-9.0),
`docs/VERIFICATION_REPORT.md` (what is verified, and how), `docs/KNOWN_ISSUES.md`, `docs/TESTING.md`.

| Path | What it holds |
|---|---|
| `mod/RiftApartRandomizer/` | The install-ready folder. Start with its `INSTALL.txt`, then `docs/PLAYING.md`. Its `docs/` covers levels, weapons, shop and prices, armor, ARSENAL_RESTORED, design, configuration and presets, New Game, limitations, testing (report and round 23 checklist), compatibility, recovery and migration |
| `mod/RiftApartRandomizer/docs/VERIFICATION_REPORT.md` | **Start here for 9.0**: every feature in four categories (automated tests / static inspection / game execution / not verified) |
| `mod/RiftApartRandomizer/docs/RESEARCH_8.0.md`, `KNOWN_ISSUES.md` | 8.0's mission-system research (the hub it designed is removed in 9.0; the findings stand), known bugs and limitations |
| `data/` | The game database (`game_db.json`), the weapon registry (`weapon_registry.json`) and their real sources (your dag's item ids, the 1.x model) |
| `tools/build_data.py` | Builds `scripts/01_rando_data.lua`, `data/weapon_registry.json` and `docs/WEAPONS.md` from `data/sources` (7.0: vanilla prices, planet checkpoints, the ARSENAL_RESTORED marker; 9.0: reproduces your 8.5.2 data byte for byte) |
| `tools/rando.py` | Offline generator and spoiler generator, presets, share codes (RA9) and batch validation (runs the shipped Lua through lupa) |
| `tools/big_batch.py` | Release validation: 41,000 seeds (7,000 from your kit 04 file and the retired hub presets) through the audit, the independent item verifier, the campaign and game-order replays and 9.0's story-start check |
| `tools/build_capabilities.py` | Turns the lab's rivet.log (`RANDO-LAB VERIFIED`) into `scripts/06_rando_capabilities.lua` |
| `tools/build_campaign_registry.py` | Turns a `campaign_research_*.zip` into `scripts/07_rando_campaign_registry.lua` |
| `tools/analyze_dump.py` | Decodes `companion/research` dumps |
| `tools/summarize_log.py` | Summarizes a rivet.log |
| `mod/RiftApartRandomizer/rando_give_source/` | `rando_give.dll` v6 source (portable core + Windows layer), `build.sh` |
| `tests/` | Weapon registry; generator with independent verifiers and mutation tests; regression against 5.0 and 6.0 (from git); runtime against a simulated game (levels and the warp back, prices, currency, restored-weapons check, shop slots, armor, a New Game to finale on level-locked seeds); your real logs replayed (rounds 13-20); 8.4: weapon types, the shop's pointer layout, the kit check (`test_v84.py`); 8.5: mailbox take-back, late restore, New Game resets, shop routes (`test_v85.py`); **9.0: no hub, the story's fixed start, your settings files, a leftover hub script (`test_v90.py`)**; the DLL core; companion (PowerShell 7); tools. `story_helpers.py`: an ordinary 9.0 game for the travel tests |
| `run_tests.py` | Runs everything and writes `TEST_RESULTS.txt` |
| `DEVELOPMENT_LOG.md` | History, findings and handoff |

Quick start for development: `pip install lupa capstone`, `python run_tests.py`,
`python tools/rando.py generate --seed test --preset hub --out out/` (spoiler log, seed
file and settings), `python tools/big_batch.py`.
