# Development log: Rift Apart randomizer

Earlier rounds (1-12) are summarised in the claude.ai project docs
`RiftApart_Randomizer_phase1.md` and `RiftApart_Randomizer_phase2.md`. The generator and solver
live in the `rcra_randomizer` repository, which was not available in this session.

## 2026-11-10: round 13 log → kit 1.4

### Investigated
- The round-13 `rivet.log` (kit 15 / 1.3, rivet_hook 2.0.0, test mode on, a save with 3 planets done). `tools/summarize_log.py` gives:
  - Four weapons confirmed through rando_give.dll with the hero target: Predator Launcher, Headhunter, Warmonger, Schrodinger.
  - The Executor was sent 4 times with no answer. Direct delivery was then switched off.
  - Mr. Zurkon (bought afterwards) was never sent.
  - The hint "it arrives on Nefarious City" was shown while on Nefarious City, and no route-1 node was found there.
- Every script of kit 15. The DLL source and the shipped DLL (rebuilt with clang/lld: byte-identical apart from the link timestamp).
- rivet_hook 2.0.1 source (GitHub mirror) for exact API behaviour:
  - `time_scale()` raises during loads.
  - `script.exec` answers are capped at 4095 characters.
  - Callbacks are switched off after `error_limit` errors.
  - Event string fields are read-only.
  - The ship's travel is driven by checkpoint names.
- The dag-derived item id table against the seed:
  - Every id matches its config path.
  - Mr. Zurkon's id is not in the game's dag; it comes from ARSENAL_RESTORED's added assets, per the phase-1 research.
  - The gadget type ids match the hashes your game reported.

### Bugs found and root causes
1. **One silent item switched direct delivery off for the session (critical, seen in game).** `finish()` treated "no answer for this item" as "this target is wrong", even for a target that had just delivered four items. It moved on to the groups, and with all of them silent it called `native_disable`, which is permanent. Every later reward, Mr. Zurkon included, was stuck.
2. **An already-owned weapon looked like "no reaction" (found by the simulator).** The game answers in the same pump that takes the request, so `InventoryChangedEvent` arrives before the script sees the hand-over. The check compared against the hand-over frame. During calibration, an owned item therefore condemned working targets.
3. **Side rewards could never be obtained (found by the new "every reward obtainable" test).** Six side locations (Zurkie's cups, Trudi, the Blizar chef, the Ardolis Map-O-Matic) had no event binding, and test mode does not cover them. RYNO 8, Mr. Fungi, Enforcer, Fusion Grenade, Coordinates: Viceron and 3 Gold Bolts were lost in every seed.
4. **A planet load during a delivery could confirm the wrong weapon.** The load replays `WeaponAddedEvent` for every owned weapon, and the native request stayed "busy" across the load, so any replayed weapon confirmed it.
5. **Nothing waited for pauses or loads.** A request sent while paused or loading was judged after 180 frames, and the game might not have run in that time. A request the helper did not take during a load (the pump stops) disabled the DLL for good ("did not pick up the request").
6. **Hint text claimed rewards arrive on Nefarious City while on Nefarious City.** It did not distinguish "the DLL is missing" from "the game did not answer".
7. **The companion stopped restoring after a damaged save** and only printed "waiting for the game (... damaged ...)". It never tried the `.bak` it keeps.
8. **An error in a runtime event, frame or key callback reached rivet_hook**, which switches a callback off after 3 errors in a row (for example the planet tracker, if `rivet.hero()` failed).
9. Minor issues:
   - The shop cursor was a position, not a slot.
   - "nothing for sale yet" was shown when the shop was sold out.
   - F9 did not say what was waiting.
   - Settings meant editing the runtime script.

### Changed (kit 1.4)
- `09_rando_real.lua`:
  - A proven target is kept. A silent item waits (`hold` 10 s, then `skip_visit` until the next planet) while the others proceed.
  - Two different silent items re-open calibration, with the old target tried first (`real_mode_hint`).
  - No target answering pauses delivery only until the next planet (`native_soft_off`).
  - A game-frame clock (`gframe`), a `game_running()` guard on `rivet.time_scale()`, and a 2 s settle time after loads.
  - Uses the inventory-changed frame of the request (`b.asked`). An early finish when the item is already owned (`OWNED_FRAMES`).
  - WeaponType learning (`s.weapon_types`) and late-answer credit after a full replay baseline.
  - A planet load interrupts in-flight requests and withdraws untaken ones.
  - Honest hint texts. F9 lists waiting names.
- `10_rando_runtime.lua`:
  - Side locations without a binding pay with their planet, plus a catch-up for planets finished earlier (runs once, at restore).
  - Shop by slot id, "sold out" and "finish N more planets".
  - Callbacks wrapped with `RANDO-ERROR` logging.
  - Settings merge with validation. Kit version in the log.
- New `04_rando_settings.lua`: keys, real items and weapons on/off, side rewards, logging.
- `RandoCompanion.ps1`: a damaged save falls back to `.bak`. With both damaged it says so clearly and never overwrites them.
- Package layout:
  - `scripts/` holds only what play needs.
  - Test mode and developer tools moved to `extras/`.
  - Docs for install, configuration, features and limitations, verified-in-game status, recovery and testing.
- `rando_give.dll`: unchanged. It is proven in game and verified as built from its source.

### Tests
- New harness: `tests/harness.py` + `tests/sim/rivet_sim.lua` (lupa, Lua 5.4).
  - Companion e2e with PowerShell 7.4.6 and a fake bridge.
  - Native core test. DLL reproducibility check. Log summarizer test.
- Kit 1.4: **68/68 pass**. Kit 15 against the same runtime, companion and seed tests: 42/64. The 22 failures are the bugs above, plus new behaviour.

### Remaining issues / not possible now
- Planet locks, mission order and random starts are not possible without breaking the game's story gating (see FEATURES_AND_LIMITATIONS.md).
- The generator, and so new seeds, is in the `rcra_randomizer` repo, which is not attached to this session.
- No vendor randomization and no bolt-currency rewards.
- Side-mission names are still unbound. They are paid with the planet until rivet.log shows their mission names.
- Everything in 1.4 is verified in the simulator only. In-game checklist: TESTING.md, "Manual checks".

### Next priorities
1. Round 14 in game with kit 1.4: Executor, Mr. Zurkon, pause behaviour, a gadget through the DLL.
2. Read the side-mission names from `RANDO-DISCOVER` lines and bind them in `05_rando_bindings.lua`.
3. Bring the generator repo back into the workflow. Then:
   - Make the solver aware that side locations pay with their planet. It already treats them as planet-local, so the logic stays valid. Only the timing moves earlier.
   - Generate fresh seeds with the 1.4 runtime.
4. If wanted: per-seed weapon-vendor data as a .stage built on ARSENAL_RESTORED's vendor config.


## 2026-11-10: Randomizer 2.0

### Inputs
- The 1.4 project and kit 15.
- The original `rcra_randomizer` generator project was **not attached**. The 2.0 generator was written new, in Lua, so the same code runs in the game and offline. The 1.x model (planets, mission codes, Gold Bolt requirements, side activities) was recovered from the 1.x seed export.

### Investigated
- **Item configs in the dag table** (919 entries). They give:
  - 59 armor bundles (17 randomizable sets, plus default, pre-order and demo outfits);
  - pickup items (Raritanium, weapon upgrades, RYNO plans);
  - 9 unused weapon configs outside the test folders.
- **Script-action classes from the exe's RTTI** (`06_rando_vtables.lua`). The game has `VanityGiveBundleAction`/`VanityGiveSetAction`, `AddCurrencyAction`, `SetWeaponLevelAction`, `UnlockLevelAction` and `CollectibleCollectAction`. None of their code is available here.
- **rivet_hook 2.0.1 source:**
  - `vanity_owns`/`vanity_equip` can check and equip armor, but not grant it.
  - `mem.read` over the bridge reads up to 4 KB per call.

### Built
- `tools/build_data.py`: game database from the dag and the 1.x model, with provenance. Outputs `data/game_db.json` and `scripts/01_rando_data.lua`.
- `scripts/02_rando_generator.lua`:
  - xoshiro256** seeded by FNV-1a; settings normalization and presets; share codes;
  - location and item pools; registry; assumed fill that reserves the first sphere;
  - adversarial shop and price model; graceful degradation with warnings;
  - sphere solver; audit; spoiler log; serializer.
- `scripts/10_rando_runtime.lua`, rewritten:
  - in-game generation sliced by coroutine, with an event buffer;
  - story-mission counting with fallbacks; Coordinates banking; armor-find polling;
  - bindable collectibles; shop with confirmation and owned-item hiding;
  - companion protocol v2 (8-field status, random seeds, spoiler export); start inventory handed out once.
- `09_rando_real.lua`: reads items from the database; syncs the 2.0 inventory; confirms experimental pickups on InventoryChangedEvent. All 1.4 delivery logic is unchanged.
- Companion 2.0: random-seed memory (`-NewRandomSeed`), spoiler files, detection of 1.x scripts.
- `companion/research/Dump-GameCode.ps1` + `tools/analyze_dump.py`: a read-only path to armor, currency and upgrade grants. Validated on the known AddToInventory handler.
- `tools/rando.py`: generate / random / share / batch / settings. Writes pre-generated `00_rando_seed.lua`.

### Bugs found while building (all fixed)
- The shop as part of the assumed fill made `chaos` seeds fail (shop cycles). Fix: shop items are never assumed during the fill.
- Tiny starts (`start_only`) ran out of first-sphere locations. Fix: the first sphere is reserved for the items placed last.
- Random settings failures, each fixed:
  - weapon logic with weapons off;
  - all weapons counted as progression;
  - excluded Coordinates;
  - excluded gating gadgets;
  - shops larger than the income.
- **The registry audit caught excluded Coordinates mislabelled.** Fixed.

### Tests
88 tests, all passing:
- 59 runtime, including every 1.4 delivery regression;
- 7 companion and research-tool;
- 16 generator, with an independent Python verifier;
- 2 native;
- 4 tools.

Batch results:
- 4,000 preset seeds and 18,036 random-setting seeds: all valid.
- 10,000 seeds also pass the independent verifier.

**Real game: none yet for 2.0.**

### Not possible / open
- **Armor grants** need the `VanityGiveBundleAction` code (Dump-GameCode).
- **Mission order and random start planet** were judged impossible in 2.0. 3.0 reopens this (below).
- **Travel blocking:** events can't be vetoed.
- **Spybots, Lorbs and CraiggerBears** need event names.

### Next
1. Round 14 with the TESTING.md procedure.
2. Decode `game_code_dump.json`, then add a verified armor request kind to rando_give.dll v3.
3. Bind side-mission and collectible event names from `RANDO-DISCOVER`.

## Randomizer 3.0: campaign randomization

### Starting point
- An inspection of the 2.0 package showed that its generator, solver, shop, economy, armor
  locations, companion and delivery are implemented and tested offline. Nothing in 2.0 touched
  mission order.
- The original `rcra_randomizer.zip` named in the 2.0 brief was never attached; 2.0 was a rebuild.

### Findings: how the game runs its story
- **One level of regions.** Story overlays follow mission state (game).
- **Mission names.** `MissionStateChangedEvent` carries name, state and previous state (game).
- **Mission-state actions.** Missions change state only through level-script actions
  (`MakeMissionAvailableAction`, `StartMissionAction`, `CompleteMissionAction`, ...). Class
  names and vtable RVAs come from the exe's RTTI.
- **No direct entry point.** No rivet_hook API and no known function loads a mission directly.
- **Node borrowing.** Borrowing a loaded node works (game, `AddToInventoryAction`). So the route
  to mission control is to borrow loaded mission-action nodes; nothing new is patched into the
  exe.

### Built
- `03_rando_campaign.lua`:
  - the registry: 14 visits, with missions, hero, needs, story abilities and provenance;
  - 5 modes and random start;
  - the hard rules;
  - campaign reach for the solver.
- Generator: campaign-aware locations, Coordinates, weapon tiers and the start. Gadgets a
  campaign needs are given at the start when they aren't randomized. The campaign appears in
  the spoiler.
- `11_rando_campaign.lua`:
  - mission research log;
  - node scan (looks for `rivet.hash(mission)` inside loaded action nodes);
  - mission control via borrowed nodes, restored after 45 frames;
  - travel (fly, then warp);
  - the director (F12, advance, blocked visits, saved progress);
  - random start (completes the intro);
  - the lab (Ctrl+F12 scan, Ctrl+F11 experiment, VERIFIED / NO EFFECT lines).
- `06_rando_capabilities.lua` (all unverified) and `tools/build_capabilities.py`.
- `companion/research/Research-Campaign.ps1/.bat` (read-only, one run) and
  `tools/build_campaign_registry.py`.
- Tests:
  - 10,000 campaign seeds, each with the generator audit and the independent `verify_campaign`
    replay;
  - 6,000 of them also pass `verify_fallback` (the game's own order);
  - sequence rules;
  - 13 director tests against a simulated mission system;
  - the research tool under PowerShell.

### Decisions
- **Whole visits move, never single missions.** Missions inside a visit hand over in their own
  scripts.
- **Gated by capabilities.** The director acts only on capabilities verified in the game.
  Without them, campaign seeds fall back to the game's order, which is checked to stay
  finishable, and the HUD and F12 say so.
- **Make available and start only.** The director never completes or removes missions, apart
  from the intro on a random start.
- `new_game_init` is verified only by completing `MIS_INTRO` on a fresh save. It is never
  inferred.
- Test mode's F11 (Gold Bolt) ignores Ctrl, because Ctrl+F11 is the lab.

### Fixed during 3.0
- A local `order` shadowed the planet list.
- Campaign with gadgets off was unfinishable; the needed gadgets now start owned.
- Sparse settings with a campaign failed the fill; planet_locks off is now the last resort, with a
  warning.
- The 2.0 verifier rejected campaign start gadgets.
- Ctrl+F12 also triggered F12.

### Real game
None yet. The three tests in CAMPAIGN.md decide whether campaign modes go live.

### Next
1. Run the three tests in CAMPAIGN.md, then run the two builders to produce the 06/07 files.
2. If the borrowed node gives `NO EFFECT`: decode `StartMissionAction` from `game_code_dump.json`
   and add a native mission request to rando_give.dll v3, byte-checked like the inventory route.
3. Research `DeactivateMissionAction`, to remove the vanilla next-mission marker.

## Round 14 and Randomizer 3.1 (2026-11-11)

### Round 14 results (kit 3.0 in game)
- **The 2.0 layer works in game:**
  - in-game seed generation;
  - real weapons through rando_give.dll (one retry);
  - owned weapons recognised;
  - armor baseline and armor finds;
  - Coordinates banking;
  - the shop and the test keys.
- **3.0 lab failed, for three reasons:**
  - `MissionStateChangedEvent` reports the boot defaults once (MIS_INTRO 2) and nothing when a
    save loads, so the lab took every save for a new game.
  - No Start/MakeAvailable mission nodes were loaded on NefCity, Zurkie's or Corson V.
  - Research-Campaign sent `""` as the filter (the bridge has no quotes), so its lists came back
    empty.
- **The code dump worked.** It shows the mission actions read the mission as a *string* plug
  and call a global mission manager (RVA 0x68DD510). The table, state array, CRC hash and
  states are in rando_give_core.h and CAMPAIGN.md.
- `rivet.hash` matches the manager's hash for MIS_INTRO, MIS_RYNO_PLANS and MIS_HAX_DEFAULT.
- New real mission names from level-script variables: MIS_SARG_02_REVISIT_SHIPS,
  MIS_SVALI_02_SECOND_VISIT, MIS_ARD_01_FIRST_VISIT, MIS_ZURK_02B_VISIT_02B,
  MIS_NEFCITY_01_TRAINSTATION, MIS_SAV_01_POST_MISSION, MIS_SARG_01_POST_MISSION. From events:
  MIS_ZURK_01_VISIT_01.

### Built in 3.1
- **rando_give.dll v3**: mission request kinds query, make_available, start and complete.
  - They replay exactly what the three actions' handlers do, with the same checks.
  - Every handler byte and the first bytes of each called function are compared with the exe.
    The expected bytes are taken from the round-14 dump, and a test proves they match it.
  - Items are unchanged (kind 0).
  - Names live in permanent mailbox slots.
- **11_rando_campaign.lua**:
  - a read-only mission-table reader;
  - native mission calls queued around item delivery;
  - an async director that advances by reading the table;
  - a random start that only finishes an active intro;
  - a new lab: Ctrl+F12 reads the table, Ctrl+F11 runs make + start + fly, or finishes the intro;
  - a session diagnostic line.
- The node-borrowing route is removed.
- build_capabilities.py reads the new VERIFIED lines. build_campaign_registry.py uses the table
  report.
- Research-Campaign asks once per keyword and merges. Dump-GameCode `-Extended` also dumps the
  manager's vtable functions.
- Registry: game-seen names added (see CAMPAIGN.md). Visits may list several names: the first and
  last names the table holds are used.
- Simulator: models the manager in memory and the v3 helper. START → 3 is SIMULATED.
- Generator unchanged (3.0.0): 3.0 seeds carry over.

### Next
1. The three tests in CAMPAIGN.md (one read-only).
2. Then run build_capabilities.py.
3. If START does not give state 3 or does not load the story, decode `vtable+0x120` from the 3.1
   dump.

## Round 15 and Randomizer 3.2 (2026-11-11)

### Round 15 results (kit 3.1)
- rando_give.dll v3 matched the exe's mission code.
- Research-Campaign's lists now work: 213 events, 860 checkpoints, 1216 regions, 361 configs.
- **The system 1 manager (0x68DD510) is NULL**: the 3.1 reader found nothing, and nothing was
  called.
- Every mission action branches on byte 0x6925FA8. The other branch ("system 2") uses manager
  0x68EA390, where missions are components on level actors (handle + component id).
  - Start/SetMissionActive: state 1 and `vt[0xD0]`, then `vt[0xD8]`.
  - Complete: state 3, then `vt[0xF0]`.
  - Replay: `vt[0x108](flag, 1)`.
  - **MakeMissionAvailable returns immediately.**
- The lab printed "mission experiment: false": a pcall return was shown wrongly. Fixed.

### Built in 3.2
- **rando_give.dll v4**: system 2 query/start/complete/replay, exactly per the handlers' other
  branch. Make-available is refused there (`no such action`), vtable entries must point into
  the exe, and the handler/function bytes are checked; the test proves they match both dumps.
- **11_rando_campaign.lua**:
  - Asks the game (async) instead of reading memory.
  - The director starts a visit only if the game opened it, and says so otherwise.
  - The lab: Ctrl+F12 asks for every name and logs the component's vtable code. Ctrl+F11 starts
    an open visit, or tries start then replay on a locked one, or finishes an active intro.
- build_capabilities: mission_control = start verified.
- Simulator: system 2 by default.

### The real obstacle now
Nothing in the game's actions opens a mission in system 2. Next research targets:
- the component's code (lab log);
- the `+0x1B0` state machine;
- the replay experiment.
## Handoff (for a next session)
- Project: `rcra_randomizer_3.2_dev.zip` (git history inside; branch v2).
  - Install folder: `mod/RiftApartRandomizer`.
  - Tests: `python run_tests.py` (needs `pip install lupa capstone`; pwsh optional).
  - Rebuild the database: `python tools/build_data.py`.
  - Rebuild the DLL: `sh mod/RiftApartRandomizer/rando_give_source/build.sh` (clang, lld-link, llvm-dlltool).
- Real game data for tests: `tests/data/round13_rivet.log`, `round14_rivet.log`,
  `round14_game_code_dump.json`, `round14_randomizer_research.lua`, `round15_rivet.log`, `round15_game_code_dump.json`.
- The simulator's assumptions are listed at the top of `tests/sim/rivet_sim.lua`. Change them only from rivet.log evidence.
- To read a new log: `python tools/summarize_log.py rivet.log`, then grep `RANDO-REAL`,
  `RANDO-ERROR`, `RANDO-DISCOVER`, `RANDO-CAMPAIGN` and `RANDO-LAB`.
- To turn the campaign on from lab results: `python tools/build_capabilities.py rivet.log`.

## Randomizer 4.0 (2026-11-11)

### Requirements this release implements
- One Gold Bolt = one item; no shop, no prices, no randomizer currency.
- Random start; Hoverboots and Map-O-Matic always in it.
- New Game initializes the randomizer; save/load and restarts keep the same seed and progress.
- Weapons only from the randomizer (vendor lock); the prologue's own weapons are not rewards.
- Whole campaign playable, no softlocks; finale recognised.

### Built
- Generator 4.0.0 (`02`): see docs/COMPLETION_REPORT.md. Gold Bolts are filled first and must
  hold a grantable item (`G.bolt_worthy`). The progression fill reserves grantable items for
  free Gold Bolts. Too few items → Coordinates turned on → otherwise an explicit refusal.
- Runtime 4.0.0 (`10`): Gold Bolt fallbacks (current planet, any remaining), New Game reset
  (`MIS_INTRO`/`OBJ_INTRO_PARADE_START_CINE`/1, debounced 30 s, pending before the restore),
  progress before the restore merged, no-companion start, vendor lock through
  `rivet.config_set(VendorConfig, "PurchaseWeaponHoldTime", 86400)`, finale on `MIS_MEGA_FINALE`.
- `09`: `RANDO_REAL.new_game()`.
- Companion: `.runN` copies.
- Simulator: config API, vendor (SIMULATED effect), `new_game()`, `load_save()`.

### Evidence used
- New Game signal: round 14 lines 193-194, round 15 lines 171-172; absent from every save load
  (rounds 13-15). `RealLogReplayTests` replays all three logs.
- Map-O-Matic grant: round 15 (`confirmed map_o_matic via native`).
- `config_set`: rivet_hook commit 59440458 (in v2.0.0); `VendorConfig` fields from
  neptuwunium/rivet `Types/VendorConfig.cs`; arrays of structs cannot be written
  (`ddl_visit.cpp resolve_path`), hence the hold-time field rather than prices.

### Results
- `run_tests.py`: 135 tests, 0 failures, 9 skipped (no PowerShell on the build machine).
- `tools/big_batch.py`: 12,000 preset seeds, 8,000 random-setting seeds (7,188 valid, 812
  honestly refused), 10,000 campaign seeds: 0 invalid.

### Open (cannot be settled offline)
- Vendor lock effect, finale name, Gold Bolt names besides "Sargasso 2", companion `.runN`
  under real PowerShell. None of them can block play; see FEATURES_AND_LIMITATIONS.md.

## Randomizer 5.0 (2026-11-11, after round 16)

### Round 16 (kit 4.0, your three planets)
- 4.0 worked: New Game before the restore, start, 4 Gold Bolts (one new name, `Zurkon's 1`,
  matched by the current planet), RYNO 8 / Enforcer / Buzz Blades / Drillhound delivered.
- **Blackhole Storm never arrived**: `wpn_nailgun` taken by the game, nothing added (also round
  15). neptuwunium/rivet `Weapon*Prius`: `WeaponWarpRiflePrius` = spin-up/heat/spread (minigun,
  Blackhole Storm), `WeaponFossilizerPrius` = aim slows time, zoom (Headhunter),
  `WeaponNailGunPrius`/`WeaponRevolverPrius` = empty (cut). Round 13's "Headhunter" delivery was
  `wpn_warprifle`, i.e. the Blackhole Storm.
- Three of four story missions gave nothing (more locations than items).
- The vendor lock blocked ammo too: `PurchaseWeaponHoldTime` = "hold time before a weapon (or
  ammo refill) is purchased" (VendorConfig.cs).

### Built
- Data 3.0.0, generator 5.0.0: see docs/COMPLETION_REPORT.md. Vendor weapons stay in the shop;
  `seed.shop = { mode, order }` (derangement); `G.shop_mapping(order, found)` is the one mapping
  used by spoiler and runtime. 27 armor pieces are items (bolt-worthy through vanity). 27
  `source:<set>_<part>` locations (`holds = "filler"` for punk/reaver/warmachine). Filler keys
  `filler:<bolts|raritanium>:<n>`. Repair order on too few items: armor on, then Coordinates.
  Campaign "needs weapons" errors now count towards lowering weapon logic.
- `rando_give.dll` v5: kind 6 (GiveBundle as VanityGiveBundleAction), kind 7 (config lookup via
  the manager found by rivet_hook's VANITY_HAS_BUNDLE signature, rel32 at +0x22), the handler of
  VanityGiveBundleAction (RVA 0x880720) replaced in the pump's patch pass (skipped if a thread
  is inside it) by `rg_armor_decide` + the output function (RVA 0x12BE510, plugs CD6C8C3D /
  329EA4F1). Mailbox 0x100-0x400: ON, HOOK, SEQ, CALLS, CONFIG_MGR, SIGS, table (48), ring (16).
  Counts up to 100,000.
- `09`: `send_armor`, `G.armor_answer`, aux queue (lookups first, currency only when no item
  waits), `aux_withdraw` on loads and timeouts. `10`: filler payouts, armor-pod prefix, retired
  `lock_vendor_weapons`. `12_rando_shop.lua`: array discovery by item ids (first array in the
  config's first 0x100 bytes with >= 3 vendor ids at a consistent stride), writes + read-back,
  `UpgradeCellYOffset` fraction 1/16 as the per-load mark. `13_rando_armor.lua`: table sync,
  ring reader, vanity_owns polling fallback and baseline.
- Simulator: v5 kinds, armor ring, invented vendor layout (array +0x88, 0x58 stride, Item +0x10),
  currency events. Harness: vendor memory per game, armor-aware `owns`/`give_count`.

### Results
- `run_tests.py`: 151 tests, 142 passed, 9 skipped (PowerShell; running a downloaded pwsh was not
  allowed in the build environment).
- `tools/big_batch.py`: 30,000 seeds, all valid, none refused.

### Open (round 17 decides)
- Do armor pods / Zurkie's / the Lorb monk use VanityGiveBundleAction? (`RANDO-ARMOR source`)
- Does the vendor screen read ItemDatas live? (`RANDO-SHOP vendor ...` + what you see)
- Currency counts as amounts? (`GainBoltEvent`, `GainRaritaniumEvent` in RANDO-DISCOVER)
- Which two of punk/reaver/warmachine are Robot Disguise / Wasteland Gear?

## Handoff (5.0)
- Project: `rcra_randomizer_5.0_dev.zip` (git branch v5). Tests: `python run_tests.py` (needs
  `pip install lupa capstone`); data: `python tools/build_data.py`; DLL:
  `sh mod/RiftApartRandomizer/rando_give_source/build.sh`.
- Real data for tests: rounds 13-16 rivet.logs, round 14/15 code dumps (tests/data).

## 2026-11-11: 6.0 "Complete Edition" spec → kit 6.0 (without ARSENAL_RESTORED)

### Investigated
- The 6.0 spec: one mod with ARSENAL_RESTORED 5.7 integrated, unified weapon registry, every
  weapon with a verified route, no empty rewards, the shop separate from rewards.
- ARSENAL_RESTORED 5.7.stage: not reachable (the Drive link needs a sign-in; this build cannot
  reach the user's PC). Decision (user): build 6.0 without it. docs/ARSENAL_RESTORED.md says
  what integration needs.
- Guides (PowerPyx): all 20 normal-game weapons come from Ms. Zurkon; Shatterbomb 1,250 bolts;
  RYNO 8 free after all 10 Spybots; Pixelizer and Bouncer only in Challenge Mode.

### Built
- Data 4.0.0: `WEAPON_ACQUISITION` / `WEAPON_EVIDENCE` in build_data.py →
  `data/weapon_registry.json` and docs/WEAPONS.md (40 configs: start_fixed 1, shop_fixed 2,
  pool 17, arsenal_restored 9, disabled 11).
- Generator 6.0.0: `G.in_weapon_pool`, `G.vendor_weapons`; the pool fills the 15 free vendor
  slots first (up to 50 shuffles for a derangement), then the start (capped, with a warning),
  then locations. `seed.shop = { mode, slots }`, seed format 6, share code RA6. Retired:
  `include_hidden_weapons`, `experimental_pickups`, `experimental_collectibles` ("phantom").
  Audit: one route per pool weapon, slots from the pool, non-pool weapons never placed.
  Defaults: `include_arsenal_restored = false`, `weapon_logic = "none"`. Preset `classic` is an
  alias of `standard`.
- `12_rando_shop.lua`: slot map instead of a permutation; slots outside the map left alone and
  logged; `H.compensate` gives non-vendor shop weapons once (saved as `shop_given`) when the map
  cannot be applied (shop_runtime off, no config API, helper older than v5 after 7200 frames,
  array not found, missing slots). `10`: the shop tick always runs; state format 6. `09`: a
  refused currency gift is shown on screen.
- Tests: `test_registry.py`, `test_regression_v5.py` (5.0 generator from git 2866d4a), shop
  tests rewritten, verifier extended to the slot map and the one-route rule.

### Results
- `run_tests.py`: 164 tests, 155 passed, 9 skipped (PowerShell, as before).
- `tools/big_batch.py`: 34,000 seeds, all valid.

### Open (round 17 decides)
- Does the vendor screen sell what the slot map writes (and Pixelizer/Bouncer in a normal game)?
- The 5.0 questions: armor sources through VanityGiveBundleAction, currency amounts, the folder
  identities of punk / reaver / warmachine.

## Handoff (6.0)
- Project: `rcra_randomizer_6.0_dev.zip` (git branch v6). Tests: `python run_tests.py` (needs
  `pip install lupa capstone`, git for the regression test); data: `python tools/build_data.py`;
  DLL: `sh mod/RiftApartRandomizer/rando_give_source/build.sh` (unchanged since 5.0).

## 2026-11-12: 7.0 "Ultimate Edition" spec → kit 7.0

### Investigated
- All of 6.0 (code, data, tests, rounds 13-16 logs, round 14/15 code dumps). Baseline: 164 tests,
  0 failures.
- **Level randomization, again.** The round 15 dump decoded further:
  - `UnlockLevelAction` (`0x89DA00`) flips bit n (1-10) of a mask at a global's `+0x30`
    (`0x89C1E0`); `IsLevelUnlockedAction` tests it (`0x89C140`).
  - `SetPlanetaryTravelAction` (`0x607500`) stores one bool in one global byte (RVA `0x5FFD3C0`):
    all travel on/off.
  - Neither touches the mission manager or the overlays. Mission reordering stays impossible
    (system 2, no make-available).
- **Travel in the logs** (round 16):
  - the parade's rifts and in-mission rifts change planets without `PlanetMenuAcceptEvent`;
  - so does the story's own move NefCity → Sargasso;
  - menu travel always comes with `PlanetMenuAcceptEvent` (DestinationCheckpointName) right
    before `PlanetChangedEvent`.
- **Prices** from gamepressure's weapon list (15 vendor weapons = 255,250 Bolts); Raritanium
  scale from guides (mini-boss +3).
- **ARSENAL_RESTORED:**
  - the `.stage` is still unavailable;
  - Predator Launcher, Volcanic Eruptor and Schrodinger were delivered in rounds 13-16 with the
    mod installed;
  - Mr. Zurkon's item config is the mod's own asset, so it serves as an installation marker.

### Built
- Data 5.0.0: vanilla prices, planet checkpoint codes / known checkpoints, `arsenal_marker`.
- Generator 7.0.0:
  - settings: `levels` → `planet_locks` + `travel_lock`; aliases `restored_weapons`,
    `mission_order`; 6.0 filler converted;
  - currency: per-location amounts (ranges, scaling, budgets, Bolts share), start currency;
  - shop prices (vanilla / weapon / percent / random, own RNG stream); `start_items`;
  - start Coordinates with travel lock = story arrivals (+ next / random);
  - a game-order campaign object for level locks (weapon tiers by story index);
  - reordered campaigns must hold in the game's own order (alt reach during the fill, final
    check);
  - five presets; audit extended; spoiler LEVELS / SHOP prices / CURRENCY / NOTES; format 7,
    `RA7`.
- `03`: `arrival = "story"` (intro, NefCity, Sargasso), `camp.vanilla`.
- `14_rando_travel.lua`:
  - menu accept → arrival → a warp back after 180 frames when locked;
  - checkpoints: learned / known / searched by code;
  - bank fallback; `levels_runtime`; Ctrl+F9 escape hatch.
- `10`:
  - start currency; banking rules under travel lock; Coordinates message;
  - `restored_weapons = "auto"` defers generation until `rando_set_arsenal` (companion) or
    3,600 frames → false.
- `12`: Price field search (u32 / f32 equal to the slot's own vanilla price in ≥ 3 slots, none
  contradicting), writes and read-back.
- Companion: read-only toc search for the marker; `-GameDir`.
- Tests:
  - `test_levels.py` (21, incl. a simulated New Game → finale on 36 level-locked seeds);
  - `test_regression_v6.py`; mutation tests;
  - verifiers extended (currency, prices, levels, start items); `verify_campaign` for level
    locks;
  - sim: vanilla prices in the vendor layout.

### Bugs found while building (fixed)
- 6.0's reordered campaigns + Coordinates could be **unfinishable in the game's own order** (the
  start opened the reordered order's first planets only). Fix: the story's own planets open too;
  the fill respects both orders.
- The game-order fallback modelled banked Coordinates as blocking the story. Fix: only
  `travel_lock` blocks it.
- Weapon tiers in the game's order differed between the solver and the item verifier (campaign
  position vs story index). Fix: story index in the game's order.

### Results
- `run_tests.py`: 199 tests, 190 passed, 0 failed, 9 skipped (PowerShell 7: running a downloaded
  pwsh was blocked in the build environment).
- `tools/big_batch.py`: 34,000 seeds, all valid.

### Open (round 17 decides)
- The warp back; the Price field; currency amounts; armor sources; the toc check.

## Handoff (7.0)
- Project: `rcra_randomizer_7.0_dev.zip` (git branch `v7`).
- Tests: `python run_tests.py` (`pip install lupa capstone`; git for the regression tests).
- Data: `python tools/build_data.py`.
- Batch: `python tools/big_batch.py`.
- DLL: unchanged since 5.0.

## 2026-11-12: 8.0 "Zurkie's Battleplex starting hub" spec → kit 8.0 (experimental)

### Investigated
- **The New Game start.** The built mission graph (`MissionGraphBuiltGame`,
  `InitMissionGraphNodeGameDef`) carries `NewGameLoadInfo`, an `ObjectiveLoadInfo` with
  `SpawnCheckpoint`, `SpawnAsHero`, `SpawnLoadout` and `BackpackLoadout`; every mission or objective
  node has the same block (DDL, neptuwunium/rivet). It is asset data, so it can't be changed at run
  time.
- **Mission availability.** `MissionStates`:
  - 0 Inactive ("prerequisites not met");
  - 1 Available;
  - 2 Active;
  - 3 Complete Cleaning;
  - 4 Complete Finished;
  - 5 Failed.

  These match the events (MIS_INTRO 2, the cups 1). The mission graph's And/Or/InputCount/Not/GST
  nodes decide availability; the saved data per node is `MissionSaveDataShared`.
- **The state record, decoded from `State()`** (RVA 0x1A44E70, both dumps): `obj->vt[0x38]`,
  `TableFind(mgr+0x1B0)` (RVA 0x1BDAFD0), `EntryFind` (RVA 0x1BDB000), then `*(*(e+0x28)+0x30)`.
- **Levels and travel.** `UnlockLevelAction` → bit n (1..10) at RVA 0x5161238 + 0x30 (setter RVA
  0x89C1E0). `SetPlanetaryTravelAction` → byte RVA 0x5FFD3C0. Also decoded:
  - `OverridePlanetLandingCheckpointAction` (table RVA 0x5161530);
  - `SkipObjectiveAction`;
  - `AdvanceMissionObjectiveAction`;
  - `ReloadToObjectiveAction` (too large to replay).
- **rivet_hook 2.0.1:**
  - `warp` loads another planet's region and moves the save's checkpoint;
  - `fly` hands the ship listener the menu's accept;
  - `hero_play_as` is the game's own swap;
  - `rivet.overlay` refuses story overlays;
  - Lua runs on the game thread, with a render-thread fallback during loads.
- Full report: docs/RESEARCH_8.0.md.

### Built
- `rando_give.dll` **v6**: kinds 8 (mission state write), 12 (probe), 9/10 (level mask set/read)
  and 11 (travel byte). Each kind runs only when its code matches byte for byte; the matches are
  reported in `MB_V6` (0x78).
- Generator 8.0.0:
  - `hub` settings and presets (`hub` is the default in 04);
  - `seed.hub` from `C.hub_plan` (03): start pair, unlock queue, destinations, finale, an example
    path;
  - `C.hub_check` explores every subset of finished destinations;
  - audit and spoiler sections; format 8; share code `RA8`;
  - hub keys stay out of a 7.0 seed's fingerprint.
- `15_rando_hub.lua`:
  - the New Game trigger (the wrench) and the warp to Zurkie's (with fallbacks);
  - the prologue's state write and reward;
  - Coordinates;
  - F6/Ctrl+F6 travel (fly, then warp);
  - the mission ladder (start → write available → start → replay → explore);
  - completion by story or by hand, rewards, unlocks, the automatic return;
  - the ship's menu (sent back without Coordinates);
  - the keeper (parade on a load) and the startup guard;
  - hero swaps, research lines, the restore hooks.
- `10`: hub hooks and options; story2's `next_planet` fallback is off in hub seeds; the restored
  state keeps this session's current planet. `11`: v6 kinds, nameless requests, the DDL state names.
- Simulator:
  - warps and flights that land;
  - checkpoint lists;
  - hero swaps;
  - v6 kinds;
  - the parade objectives.
- Tests: `test_hub.py` (32); regression tests now compare the helper's source paths (v5 ⊂ v6).
- Docs: HUB.md, RESEARCH_8.0.md, KNOWN_ISSUES.md, COMPLETION_REPORT.md, TESTING.md (8.0 checklist),
  BATCH_8.0.txt, the hub example spoiler.

### Results
- `run_tests.py`: 231 tests, 222 passed, 0 failed, 9 skipped (PowerShell 7 unavailable).
- `big_batch.py`: 43,000 seeds valid (9,000 hub seeds + hub settings in the random batch).

### Open (the first 8.0 session decides)
- The warp out of the parade.
- The state write's effect (does a mission start and load its story?).
- Replay.
- The level bits.
- The ship at Zurkie's.
- Landing checkpoints.
- Hero swaps on arrival.

## Handoff (8.0)
- Project: `rcra_randomizer_8.0_dev.zip` (git branch `v8`).
- Tests: `python run_tests.py`; batch: `python tools/big_batch.py`.
- DLL: `sh mod/RiftApartRandomizer/rando_give_source/build.sh` (v6).
- Next: read the first session's `RANDO-HUB` lines (`tools/summarize_log.py`). Then:
  - if the state write works, drop explore as the common path;
  - if it doesn't, decode the component's `vt[0xD0]` and the graph's evaluation from a new code
    dump (Dump-GameCode `-Extended` with these RVAs);
  - consider changing `NewGameLoadInfo` by `.stage` once the mission graph asset is available.

## 2026-11-12: round 17 log → kit 8.1

The 8.0 hub ran in the game (round 17, the v2.618 folder): it warped to Zurkie's, opened the
Coordinates, forced MIS_INTRO, set the level bits, flew to Nefarious City, and forced and started
MIS_NEFCITY_01 and MIS_ZURK_01_VISIT_01. Fixes:
- 09_rando_real.lua:672 called `u32_at` (a local defined at line 792) → `G.u32_at`. A static test
  now checks every script for top-level locals used above their definition.
- Torren IV / Cordelion "no checkpoint known": checkpoint catalog in 14_rando_travel.lua. It
  places rivet.checkpoints() entries by area, then by name; scores them; fills one filter every 4
  frames and slices long answers. Hub trips wait for it. Menu landings are remembered
  (T.remember). With no checkpoint, the hub points to the ship's menu. New planet codes
  (NEFARIOUS, MOLONOTH, KEDARO, ARDOLIS, ZORDOOM) and area fragments are in build_data.py.
- 12_rando_shop.lua: the vendor search runs as a coroutine job, 2 reads a frame. Failed jobs
  count as tries (MAX_TRIES then off + compensation). 8.0 retried forever.
- Level bits are re-applied on any planet when the hub has started and the mask is incomplete (a
  save load clears it).
- Registry: MIS_BLIZAR, MIS_CORD_01_FIRST_VISIT, MIS_ZURK_02B_VISIT_02B, MIS_SARG_02_REVISIT_SHIPS,
  MIS_MEGA_FINALE (round 17 queries). Entries: CHK_SARG_02_MININGPLATFORM_LANDINGPAD (sargasso_2)
  and CHK_MEGA_FINALE_START (finale).
- ARSENAL_RESTORED rivet_hook version:
  - rivet.toml lists mods/ARSENAL_RESTORED(.stage);
  - companion\Install-ArsenalRestored.ps1/.bat installs it;
  - the companion detects loose installs through rivet.toml.
  The zip was not reachable from the build machine.
- Generator unchanged (8.0.0): same fingerprints, so 8.0 progress carries over. KIT and hub
  version are 8.1.0.

## Handoff (8.1)
- Next log: check `RANDO-TRAVEL checkpoint catalog:` (what Torren IV / Cordelion got) and
  `RANDO-SHOP vendor ... search done after N frames`.
- Check `landing on X remembered` and that no "ran past the 8 ms frame budget" lines remain.
- PowerShell changes are untested here (no pwsh).

## 8.2 (2026-11-12): test travel, round 18 catalog fix
Round 18 log (8.1, v2.618 install, seed kit-bolt-kit-198 with ARSENAL_RESTORED, fingerprint
4d170014c0c6): a save with the whole story complete. The hub started (Ctrl+F6), the level bits and
travel flag were set, the ARSENAL_RESTORED .stage loaded through rivet_hook.
- 16_rando_testtravel.lua (new): test_travel = true (runtime option, seed unchanged). F7 planet,
  F8 landing point, Ctrl+F7 warp, Ctrl+F8 fly. Test trips are claimed in process_planet before the
  hub; the hub's menu send-back, keeper and startup guard and 14's level-lock send-back are skipped
  while it is on. Trips go into the history as [TEST TRAVEL].
- 14_rando_travel.lua: the catalog ran past the frame budget 11 times (lines 115/140/141/197) and
  never logged "checkpoint catalog:". Code lookup table per token, area and score caches, time-
  sliced placement (1.5 ms), linear best pick, top-N ranking. Same planet as 8.1 for every logged name.
- 15_rando_hub.lua: H.check_levels(pid) split out of on_arrival (test trips call it too).
- Not changed: shop (AR replaces ven_weapon_vendor.config: 0 vendor weapons at +0x48), armor
  budget errors (13:117, 13:256), Pixelizer delivery without an answer.
- Tests: 262 ran, 0 failed, 17 skipped (9 pwsh, 8 need the 5.0/6.0 git history, which the 8.1 dev
  zip did not include). New: tests/test_v82.py (15).

## Handoff (8.2)
- Next log: `RANDO-TEST` lines for each trip (selected / warp / arrived), the `RANDO-TRAVEL
  checkpoint catalog:` line (it should appear now), and no 14_rando_travel frame-budget lines.
- For each planet: which landing point worked by warp and by fly. Put the good ones in
  01_rando_data.lua `checkpoints.known` (through tools/build_data.py); check whether that changes
  the fingerprint first.

## 8.3 (2026-11-12): the story starts where you land, keyboard keys
Round 19 log (8.2, v2.618 install; rivet_hook printed "game version mismatch, invalidating
pointers" but everything worked; the companion answered late, so the seed was made without
ARSENAL_RESTORED: b25846f17df5). Test trips to Viceron / Torren IV / Cordelion started no story
(8.2 claimed the landing); Cordelion's MIS_CORD_01_FIRST_VISIT was "already active" and left alone.
Round 17 explains active-but-still: the first objective is "go to <planet>"; started on the
planet it finishes at once (MIS_ZURK_01_VISIT_01), started elsewhere it never does (MIS_NEFCITY_01).
- 15_rando_hub.lua: H.story_dest / H.story_here (first unfinished destination of the planet, hub
  order ignored), called from test-trip landings, menu landings (open planets too), and the
  existing hub trips. h.obj records each mission's last objective. H.stuck: active + last step a
  GO_TO (or none seen) + not started this session -> set_state 1, start; refused -> set_state 2,
  replay. H.watch_story reports a story still at GO_TO after 1200 frames. Story key (/), Ctrl twice
  forces a restart ([STORY RESTART BY HAND]).
- 10_rando_runtime.lua: R.VK / R.vk (Windows virtual-key codes, checked against rivet.key("F6") ==
  0x75), R.bind_key (RANDO-KEY log per press), R.bind_setting (+ legacy F key), R.key (on-screen
  names). Defaults ; ] [ . , / '. Unresolvable keys fall back to F9/F6/F5/F7/F8/F4/F12.
- 11 / 14 / 16: keys through R.vk / R.key; campaign key also binds F12 with legacy_f_keys.
- Tests: 285 ran, 0 failed, 17 skipped. New tests/test_v83.py (23), tests/data/round19_rivet.log.

## Handoff (8.3)
- Round 20: RANDO-KEYS line (keyboard keys on?), RANDO-KEY lines for ] . , / ; presses.
- Per landing: "story on arrival", then "start"/"restart" results, and whether the mission's
  GO_TO objective reaches state 2 (ObjectiveStateChangedEvent). If a restart is refused, the
  "restart: back to active" and replay lines.
