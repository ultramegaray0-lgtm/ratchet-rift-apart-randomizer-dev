# Rift Apart Randomizer 8.3 (development project)

8.3 = 8.2 + the story starts where you land, keyboard keys: `mod/RiftApartRandomizer/docs/CHANGES_8.3.md`.
8.2 = 8.1 + test travel and the round 18 catalog fix: `mod/RiftApartRandomizer/docs/CHANGES_8.2.md`.
8.1 = 8.0 + the round 17 fixes: `mod/RiftApartRandomizer/docs/CHANGES_8.1.md`.

| Path | What it holds |
|---|---|
| `mod/RiftApartRandomizer/` | The install-ready folder. Start with its `INSTALL.txt`. Its `docs/` covers levels, weapons, shop and prices, armor, ARSENAL_RESTORED, design, configuration and presets, New Game, limitations, testing (report and round 17 checklist), compatibility, recovery and migration |
| `mod/RiftApartRandomizer/docs/COMPLETION_REPORT.md` | **Start here for 8.0**: the Zurkie's hub, its status in four categories (verified automatically / not verified in game / investigated but unsuccessful / unknown), files |
| `mod/RiftApartRandomizer/docs/HUB.md`, `RESEARCH_8.0.md`, `KNOWN_ISSUES.md` | 8.0: the player's guide to the hub, the technical research report, known bugs and limitations |
| `mod/RiftApartRandomizer/scripts/15_rando_hub.lua` | 8.0 hub runtime: New Game at Zurkie's, Coordinates, travel, the mission ladder, the return |
| `data/` | The game database (`game_db.json`), the weapon registry (`weapon_registry.json`) and their real sources (your dag's item ids, the 1.x model) |
| `tools/build_data.py` | Builds `scripts/01_rando_data.lua`, `data/weapon_registry.json` and `docs/WEAPONS.md` from `data/sources` (7.0: vanilla prices, planet checkpoints, the ARSENAL_RESTORED marker) |
| `tools/rando.py` | Offline generator and spoiler generator, presets (`hub` included), share codes and batch validation (runs the shipped Lua through lupa) |
| `tools/big_batch.py` | Release validation: 43,000 seeds (9,000 hub) through the audit, the independent item verifier, the campaign and game-order replays and the independent hub verifier |
| `tools/build_capabilities.py` | Turns the lab's rivet.log (`RANDO-LAB VERIFIED`) into `scripts/06_rando_capabilities.lua` |
| `tools/build_campaign_registry.py` | Turns a `campaign_research_*.zip` into `scripts/07_rando_campaign_registry.lua` |
| `tools/analyze_dump.py` | Decodes `companion/research` dumps |
| `tools/summarize_log.py` | Summarizes a rivet.log |
| `mod/RiftApartRandomizer/rando_give_source/` | `rando_give.dll` v6 source (portable core + Windows layer), `build.sh` |
| `tests/` | Weapon registry; generator with independent verifiers and mutation tests; regression against 5.0 and 6.0 (from git); runtime against a simulated game (levels and the warp back, prices, currency, restored-weapons check, shop slots, armor, a New Game to finale on level-locked seeds); your real logs replayed (rounds 13-16); the DLL core; companion (PowerShell 7); tools |
| `run_tests.py` | Runs everything and writes `TEST_RESULTS.txt` |
| `DEVELOPMENT_LOG.md` | History, findings and handoff |

Quick start for development: `pip install lupa capstone`, `python run_tests.py`,
`python tools/rando.py generate --seed test --preset hub --out out/` (spoiler log, seed
file and settings), `python tools/big_batch.py`.
