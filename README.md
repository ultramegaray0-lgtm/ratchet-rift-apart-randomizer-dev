# Rift Apart Randomizer 10.0 (development project)

10.0 = the Zurkie's hub with mission selection (the prologue, the Battle Arena, Nefarious City),
planet shuffle through Coordinates (on by default), rewards spread over every kind of location, and
the shop split from the rewards. `hub = false` keeps 9.0's story start. Player guide:
`mod/RiftApartRandomizer/docs/HUB.md`. `mod/RiftApartRandomizer/docs/CHANGELOG.md` (8.1-10.0),
`docs/VERIFICATION_REPORT.md` (what is verified, and how), `docs/KNOWN_ISSUES.md`, `docs/TESTING.md`.

| Path | What it holds |
|---|---|
| `mod/RiftApartRandomizer/` | The install-ready folder. Start with its `INSTALL.txt`, then `docs/PLAYING.md`. Its `docs/` covers levels, weapons, shop and prices, armor, ARSENAL_RESTORED, design, configuration and presets, New Game, limitations, testing (report and round 23 checklist), compatibility, recovery and migration |
| `mod/RiftApartRandomizer/docs/VERIFICATION_REPORT.md` | **Start here for 10.0**: every feature in four categories (automated tests / static inspection / game execution / not verified) |
| `mod/RiftApartRandomizer/docs/RESEARCH_8.0.md`, `KNOWN_ISSUES.md` | 8.0's mission-system research (the hub it designed is removed in 9.0; the findings stand), known bugs and limitations |
| `data/` | The game database (`game_db.json`), the weapon registry (`weapon_registry.json`) and their real sources (your dag's item ids, the 1.x model) |
| `tools/build_data.py` | Builds `scripts/01_rando_data.lua`, `data/weapon_registry.json` and `docs/WEAPONS.md` from `data/sources` (7.0: vanilla prices, planet checkpoints, the ARSENAL_RESTORED marker; 9.0: reproduces your 8.5.2 data byte for byte) |
| `tools/rando.py` | Offline generator and spoiler generator, presets, share codes (RA10) and batch validation (runs the shipped Lua through lupa) |
| `tools/big_batch.py` | Release validation: 56,600 seeds. 19,600 hub seeds (your 04 file, every preset, random settings) through the audit and `test_v100.verify_hub_seed`; 37,000 pre-10.0-mode seeds through the item verifier, the campaign and game-order replays and 9.0's story-start check |
| `tools/build_capabilities.py` | Turns the lab's rivet.log (`RANDO-LAB VERIFIED`) into `scripts/06_rando_capabilities.lua` |
| `tools/build_campaign_registry.py` | Turns a `campaign_research_*.zip` into `scripts/07_rando_campaign_registry.lua` |
| `tools/analyze_dump.py` | Decodes `companion/research` dumps |
| `tools/summarize_log.py` | Summarizes a rivet.log |
| `mod/RiftApartRandomizer/rando_give_source/` | `rando_give.dll` v6 source (portable core + Windows layer), `build.sh` |
| `tests/` | Weapon registry; generator with independent verifiers and mutation tests; regression against 5.0 and 6.0 (from git); runtime against a simulated game (levels and the warp back, prices, currency, restored-weapons check, shop slots, armor, a New Game to finale on level-locked seeds); your real logs replayed (rounds 13-20); 8.4: weapon types, the shop's pointer layout, the kit check (`test_v84.py`); 8.5: mailbox take-back, late restore, New Game resets, shop routes (`test_v85.py`); 9.0's story start, now `hub = false` (`test_v90.py`); **10.0: hub seeds verified independently, the three starts, planet shuffle, whole campaigns, closed shop slots, round 23 replayed (`test_v100.py`)**; the DLL core; companion (PowerShell 7); tools. `story_helpers.py`: an ordinary 9.0 game for the travel tests |
| `run_tests.py` | Runs everything and writes `TEST_RESULTS.txt` |
| `DEVELOPMENT_LOG.md` | History, findings and handoff |

Quick start for development: `pip install lupa capstone`, `python run_tests.py`,
`python tools/rando.py generate --seed test --preset balanced --out out/` (spoiler log, seed
file and settings), `python tools/big_batch.py`.
