# Verified in actual gameplay

**8.0 has not run in your game yet, nor have 5.0, 6.0 and 7.0.** What 8.0's hub rests on from your
logs: the New Game objective sequence (rounds 14/15, replayed into hub seeds by
`tests/test_hub.py`), `CHK_ZURK_00_DEFAULT` as the planet menu's Zurkie's destination (round 14
line 171) and the mission state events (MIS_INTRO 2, Zurkie's cups 1). The rest is untested in
game (HUB.md, KNOWN_ISSUES.md).

**5.0, 6.0 and 7.0 have not run in your game yet.** Round 16 was the first run of 4.0 (three planets, seed
`kit-bolt-kit-198`, fingerprint c207a4c8437e).

## Round 16 (kit 4.0)

| What | Result | Evidence in rivet.log |
|---|---|---|
| Seed from the companion, New Game detected before the restore, start handed out | works | `RANDO-NEWGAME new game seen before the companion's restore`, `Randomizer start: Hoverboots, Map-O-Matic, ...` |
| Hoverboots, Map-O-Matic, Omniglove, Predator Launcher, Volcanic Eruptor delivered | works | `confirmed ... via native` |
| Gold Bolts pay one item each: Nefarious City 3, Nefarious City 2, Sargasso 2, Zurkon's 1 | works; Zurkon's 1 was matched by the current planet (a new name) | `RANDO-BOLT Zurkon's 1 -> goldbolt:07 (current planet scarstu ...)` |
| RYNO 8, Enforcer, Buzz Blades, Drillhound delivered | works | `confirmed weapon:ryno_8 ...` |
| **Blackhole Storm** | **never arrived**: sent as `wpn_nailgun`, the game took the message but added nothing (as in round 15). Fixed in 5.0: it is `wpn_warprifle` | `not confirmed after 2 direct tries: weapon:blackhole_storm` |
| Missions | MIS_INTRO paid Enforcer; MIS_NEFCITY_01, the Sargasso mission and Trudi paid **nothing** (4.0 had more locations than items). Fixed in 5.0: filler and armor items | `Randomizer: no item at Nefarious City: first story mission` |
| Vendor lock | took effect, and also blocked **ammo** (the hold time covers "a weapon (or ammo refill)"). Removed in 5.0 | `RANDO-VENDOR locked weapon purchases at ae5ce1e22662e244 VendorConfig`; your report |
| Armor baseline | 30 pieces owned before the seed, as in rounds 14 and 15 | `RANDO-ARMOR baseline: 30 armor piece(s)` |
| Config manager address | the same as rounds 14-15: `00007FF6C6ACBFE0` = exe + 0x52EBFE0 (5.0's helper finds it by rivet_hook's signature and logs it) | `[configs] config asset manager at 00007FF6C6ACBFE0` |

## Evidence 4.0 was built on (rounds 14/15)

Two pieces of round 14/15 evidence were put to new use in 4.0:

- **New Game is visible**: `ObjectiveStateChangedEvent MIS_INTRO / OBJ_INTRO_PARADE_START_CINE / 1`
  appears in round 14 (line 194) and round 15 (line 172), the two sessions where you started a
  new game, and in no save load (rounds 13-15). 4.0 starts the seed over on it.
- **Map-O-Matic can be granted**: round 15, `confirmed map_o_matic via native after 0 frames`,
  during the prologue. 4.0 gives it at the start of every seed.

**Round 14 (2026-11-11) was the first run of 2.0/3.0 code in your game** (kit 3.0, seed
`kit-bolt-kit-198`, preset standard). The 2.0 layer worked; the 3.0 campaign lab did not, for
reasons now understood (below). None of the campaign abilities (mission control, travel by
`level.fly`, new-game intro skip) has been seen working yet; CAMPAIGN.md has the tests that
settle them.

## Round 15 (kit 3.1)

| What | Result | Evidence |
|---|---|---|
| rando_give.dll v3 loads, the mission code of your exe matches byte for byte | works | `mission helper: ready (rando_give.dll v3, mission code matches this exe)` |
| Research-Campaign lists (the `""` fix) | works: 213 event classes, 860 checkpoints, 1216 regions, 361 configs | `summary.json` |
| 3.1's mission-table reader | **no manager**: the system 1 manager pointer is NULL in your game, so your game runs the second mission system. Nothing was called | `mission table not read: no mission manager yet`, Dump-GameCode `"manager": "0x0"` |
| Item delivery, banking, seed restore with the 3.1 files | works | `Banked ... (5 waiting)` |

## Round 14 (kit 3.0)

| What | Result | Evidence in rivet.log |
|---|---|---|
| In-game seed generation (random seed from the companion) | works | `RANDO-SEED ready kit-bolt-kit-198 a09bf08d1ae1 preset standard attempt 1` |
| Starting weapons into the real inventory through rando_give.dll | works: Predator Launcher at once, Volcanic Eruptor after one retry | `confirmed weapon:predator_launcher via native after 4 frames`, `confirmed weapon:volcanic_eruptor` |
| Already-owned weapons recognised (Bouncer, Burst Pistol) | works | `already in the game: weapon:bouncer (equipped)` |
| Armor baseline and armor finds as reward locations | works: 30 pieces owned before the seed ignored; 2 finds paid Gold Bolts | `RANDO-ARMOR baseline: 30`, `location armor_find:01` |
| Coordinates banking (Zurkie's rewards held, paid when found) | works | `Banked: 2 Gold Bolts - find the Coordinates for Scarstu ...` |
| Shop listing, test-mode keys F10/F11 | works | `Shop 1/4: Blackhole Storm ...` |
| 3.0 lab Ctrl+F12 scan | **0 nodes**: no Start/MakeAvailable mission nodes loaded on NefCity, Zurkie's, Corson V | `[LAB] 0 mission-action nodes loaded` |
| 3.0 lab Ctrl+F11 | **wrong branch**: the game reports its boot defaults once (intro running), not the loaded save, so the lab took every save for a new game | `no CompleteMissionAction node with a known field is loaded here` |
| Research-Campaign event/checkpoint/region/config lists | **empty**: the tool sent `""` as a filter; rivet_hook has no quotes | `summary.json`: `0 classes` |
| Research-Campaign code dump and script nodes | works: the mission handlers' code, which showed how the mission system really works (CAMPAIGN.md) | `game_code_dump.json` |

## Kits 1.x (rounds 1-13)

Everything below still applies, because 2.0 and later keep the same event handling and the
same delivery code. The 2.0 checklist is in TESTING.md, "Real-game test procedure".

Only what a rivet.log from your PC shows. Setup: RiftApart.exe 3.0630.1.0 (Steam),
rivet_hook 2.0.0, ARSENAL_RESTORED 5.4 through Overstrike.

## Seen working

| What | Round | Evidence in rivet.log |
|---|---|---|
| Scripts load, events subscribe (20/20), HUD messages, F7/F8/F9 keys (overlay on) | 5-13 | `RANDO-STATUS events subscribed 20/20`, `RANDO-NOTIFY ...` |
| MIS_INTRO completion pays its reward | 6 | phase-2 notes |
| GainGoldBoltEvent arrives (`BoltName = "Sargasso 2"`) | 6 | phase-2 notes |
| Real gadgets through the Nefarious City AddToInventoryAction node: Box Breaker, Hoverboots | 7-8 | `GadgetItemAddedEvent` with the item's type id, kept in the save |
| Real weapons through that node (Bombardier, Glove of Doom, Negatron Collider) | 8 | per kit 1.3 notes |
| rando_give.dll loads through `[renderdoc] dll_path`, checks the exe, and its hook runs | 12-13 | `direct delivery: helper at 7FEF00000000: ready` |
| Planet completion during real play: MIS_SARG_01_CLANKPUZZLE paid +4 Gold Bolts | 12 | phase-2 notes |
| Shop purchase (Predator Launcher) | 12 | phase-2 notes |
| Companion restore after a game start | 13 | `RANDO-SAVE restored: [TEST] Gold Bolts 0 ...` (line 44) |
| **Direct delivery, hero target:** Predator Launcher (restored) | 13 | line 70: `confirmed weapon:predator_launcher via native` + `WeaponAddedEvent` |
| **Headhunter** | 13 | line 227 |
| **Warmonger** | 13 | line 239 |
| **Schrodinger (restored)** | 13 | line 285 |
| Already-owned weapon recognised (Topiary Sprinkler) | 13 | line 232 |
| Test mode F10/F11, shop buy of Coordinates, sold-out shop | 13 | lines 216-420 |
| Arriving on a planet unlocks it (NefCity, Zurkon = Scarstu) | 13 | `RANDO-PLANET Zurkon scarstu unlocked` |

## Seen failing (fixed in kit 1.4, not yet re-tested in game)

| What | Round | Fix |
|---|---|---|
| The game did not answer for Executor. Kit 1.3 then blamed the target, tried the groups, and switched direct delivery off for the session. Mr. Zurkon was never sent, and "it arrives on Nefarious City" was shown while on Nefarious City | 13 | A target that has worked stays in use. The item waits and is retried. Two different unanswered items are needed before the target is questioned. If no target answers, delivery pauses only until the next planet. The hint text matches where you are |

## Not yet seen in game

- Everything new in 3.2: asking the game (system 2) for mission states, rando_give.dll v4's start/complete/replay, the director with them, the new lab.
- Everything new in 2.0:
  - in-game seed generation and random seeds
  - Coordinates banking
  - second story missions
  - armor finds through `rivet.vanity_owns`
  - the shop with confirmation
  - the 2.0 companion
- Everything new in kit 1.4: the retry and pause behaviour, the settings file, the shop texts, and the F9 waiting list.
- Gadgets through rando_give.dll.
- Executor and Mr. Zurkon arriving.
- Gold Bolt pickups during real play, apart from the event itself.
- Side-location rewards. Kit 1.3 could not pay them at all. Kit 1.4 pays them with their planet.
