# Test report: dev 10.15 (kit 10.0.11) - Omega weapons

Built on a Linux machine without the game. **No in-game test was performed.** Every runtime result
below is from the simulator (tests/sim/rivet_sim.lua), whose inventory layout is invented for the test.

## Automated

`python run_tests.py`: **536 run, 0 failures, 0 errors, 21 skipped** (the skips are the same as
before: 9 need PowerShell 7, 12 need old git commits). New: tests/test_v1015.py, 32 tests.

| Area | Tests | Result |
|---|---|---|
| Data: 20 Omega items, the weapon's own id, never a real item, none for ARSENAL_RESTORED / cut weapons; build_data reproduces 01 byte for byte | 2 | pass |
| Generator off: 60 seeds (5 presets, hub / goldbolts_first / weapons off) have the same fingerprint and spoiler as the 10.13 commit `376a887` from git | 1 | pass |
| Generator on: 90 seeds pass the audit; each Omega once; never Gold Bolt, shop, random start; the rest of the seed is the off seed's | 2 | pass |
| start_items / exclude with `omega:` keys; spoiler section; an Omega key with the setting off is ignored with a note | 1 | pass |
| Audit catches an Omega on a Gold Bolt and an Omega placed with the setting off | 1 | pass |
| Weapon -> Omega (no second send), Omega -> weapon (nothing sent, kept), Omega with neither owned (prerequisite), both at once, repeated rewards, all 20 weapons both orders | 6 | pass |
| A byte that is not 0/1 is never written; `omega_runtime = false`; without 17 the tier is still kept; kit check and status | 4 | pass |
| Learning: two purchases teach the byte (one with a Raritanium upgrade in the same visit); one purchase never does; a byte every record holds as 1 never counts; buying a new weapon teaches nothing; kept over a New Game | 5 | pass |
| Save / load; a save that lost the flag gets it again; the late-restore merge keeps "applied"; loads move the records; the inventory restore (worst case: a resend clears the flag) and a New Game+ Omega are set again | 6 | pass |
| A seed's locations pay their Omegas; an Omega in start_items | 2 | pass |
| 17 held back from player packages; release/ untouched since 10.13 | 2 | pass |

Static: every script compiles under Lua 5.4 (lupa); the strict-globals audit (RANDO_STRICT_GLOBALS) over
test_v1015 reports no new global besides `RANDO_OMEGA` (allowed, like `RANDO_HUB`).

## Not possible here

- Anything in the real game: the inventory component, the records' layout, whether an Omega purchase
  reports `PurchaseWeaponEvent`, whether the game honours and saves a flag written from outside.
- The companion's PowerShell tests (no pwsh on the build machine).
- `tools/big_batch.py` was not re-run: with `omega_weapons` off the generator's output is unchanged
  (tested against git above).
