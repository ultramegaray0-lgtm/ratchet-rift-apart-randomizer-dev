# Rift Apart Randomizer 10.0 (development project)

**Dev 10.20 (kit 10.0.15):** the Enemy / Boss / Chaos Randomizers DO NOT WORK in the game yet (no census has
ever read a spawner node). 10.19's premise was refuted by the next log; 10.20 fixes two diagnostics and adds
the read-only `dev(spawnprobe).lua` to find where an encounter's Templates live. `docs/KNOWN_ISSUES.md` 0l,
`docs/TESTING.md` 2-dev7.

**Dev 10.19 (kit 10.0.14; refuted in the game):** a spawner node keeps its enemy list in a separate Spawner component (handle at
node +0x60, seen in your log's dumps); the randomizers now read and change that component's list.
Simulator-tested only; `docs/KNOWN_ISSUES.md` 0k.

**Dev 10.18 (kit 10.0.13):** the spawner's Prius is reached through `ddlPriusData` by hand (rivet gives none
for script nodes), templates are learned from their template actors, and each changed fight logs whether the
change took effect. Simulator-tested only; `docs/KNOWN_ISSUES.md` 0j, `docs/ENEMIES_AND_BOSSES.md` section 6.

**Dev 10.17 (kit 10.0.12):** the Enemy, Boss and Chaos Randomizers read each spawner's Prius (in your game
the old instance read failed on every node, so nothing was ever changed). Simulator-tested only;
`docs/KNOWN_ISSUES.md` 0i, `docs/ENEMIES_AND_BOSSES.md` section 6.

**Dev 10.15 (kit 10.0.11):** **Omega weapons** (Challenge Mode): `omega_weapons = true` adds the 20 Omega
versions as rewards of their own; an Omega found first also gives its weapon, the weapon found later never
undoes it. The game's Omega flag is set by `scripts/17_rando_omega.lua` (developer kit only) once it has
learned where your game keeps it. `mod/RiftApartRandomizer/docs/OMEGA.md`, `docs/TEST_REPORT_10.15.md`. Not run
in the game yet. Built on 10.13: the 10.14 patch is not in this repository.

Dev 10.13 (kit 10.0.9): the **Chaos Randomizer** (`scripts/chaos.lua`, `BACKSPACE` key, OFF by
default): any enemy or boss can become any other, from any planet, with **no protection** (a run may
become impossible). While ON it takes priority over the Enemy and Boss Randomizers, which keep their own
settings and resume when it is OFF. Never in a player package. `mod/RiftApartRandomizer/docs/CHAOS.md`,
`docs/TEST_REPORT_10.13.md`. Not run in the game yet.

Dev 10.12 (kit 10.0.8): an **Enemy Randomizer** (`scripts/enemy.lua`, `-` key)
and a **Boss Randomizer** (`scripts/boss.lua`, `=` key), separate, OFF by default, saved per save. They
change only the enemy templates of the game's own encounter spawners, so the encounter itself still
completes, opens its doors and advances the story; story bosses are never changed. Shared layer:
`scripts/16_rando_spawners.lua`. Not run in the game yet: `mod/RiftApartRandomizer/docs/ENEMIES_AND_BOSSES.md`,
`docs/TEST_REPORT_10.12.md`.

Dev 10.11 (kit 10.0.7): planet shuffle starts every new planet at its intro
(open planets' next visits are made active between stories, as the game does; a landing that starts
the story loads the visit's intro), and Coordinates always open a first visit (never on a revisit;
Viceron's come from Torren IV's story). See `mod/RiftApartRandomizer/docs/CHANGELOG.md`.

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
