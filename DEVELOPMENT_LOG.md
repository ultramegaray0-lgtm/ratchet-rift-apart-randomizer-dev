# Development log: Rift Apart randomizer

Earlier rounds (1-12) are summarised in the claude.ai project docs
`RiftApart_Randomizer_phase1.md` and `RiftApart_Randomizer_phase2.md`. The generator and solver
live in the `rcra_randomizer` repository, which was not available in this session.

## 2026-11-18: dev 10.29 (kit 10.0.18): the Enemy Randomizer overhaul (round39: "the enemies were the same")

- Asked: a comprehensive, provable Enemy Randomizer (registry, every spawn mechanism, visible verification, meaningful
  picks, bosses investigated, performance, tests, a coverage report); no new test until the development side is done.
- Log: tests/data/round39_rivet.log (dev 10.28 scripts, v7 helper, spawnprobe on; NefCity, Sargasso, Zurkon A1 / A3 /
  pub, NefCity, Cordelion; game path replaced). Player: "didn't notice any new enemies, but I could be wrong".
- WHAT ROUND39 PROVES (real game):
  * The player was right: 3 replacements in the whole session, all Cordelion amoeboid size swaps (C0DE, D3BB, E0F4:
    small <-> large, VERIFY REPLACEMENT SPAWNED). Zurkon A1's 8 factories were CHANGED within the last lines before
    A1 ended (EndReason=0): nothing of A1 was replaced. Sargasso: 8 CHANGED, none spawned before the reload.
  * Cause 1, throughput: "SpawnFactory-0 spawns tied to nothing 513" on one Zurkon visit - 10.28's per-spawn search
    over node records (portals, cars) let the queue fall minutes behind; factories spawned before being planned.
  * Cause 2, no node ever tied ("node Template: 116 kind not known yet"): Sargasso's nodes were listed ~40 s after
    the planet loaded, and 10.28 gave up a spawn point after 3 misses. spawnprobe shows the fix: every node's
    Location variable (2761897147 = rivet.hash "Location") holds exactly the event's SpawnLocation (8cfa5b53:
    {1103873} / spawn at 1103873; ede61f1b {1103881}; a33fd482 {1103468}).
  * Cause 3, the pool: 10.28 picked by hash among the level's kinds - pirates for pirates, amoeboids for amoeboids.
  * The pub brawl's group wave (1119710-18: thug brawler, thug shooter, robomutt, pirate shooter, pirate brawler) tied
    to nothing: its spawn points are created at stream-in (handles 1119xxx), after the listing.
  * BotDeathCompleteEvent names its bot (Cordelion: 66 deaths, 19 of ours); the story Juice boss, pool sharks, miners
    were protected; template actors still never answer (40 asks, 0).
- BUILT (16_rando_spawners.lua SP.V; enemy.lua; boss.lua; settings): see CHANGELOG "Dev 10.29". In short: spawn-point
  index + deferred re-tie; not-enemy spawners skipped; species-first picks, no size variants, re-pick before spawn;
  asset-name identity + display names; per-spawn ledger, per-level summary, queued corner notes (enemy_notify);
  re-entrant spawn processing (no drop, no double count); Boss Randomizer on the same engine with boss-tier pools.
- NOT POSSIBLE with rivet_hook + rando_give.dll v7 (documented in ENEMY_RANDOMIZER_COVERAGE.md): enemies from other
  planets (template not loaded), enemies without a spawner, split children / projectiles, first spawn of a kind the
  save never saw, thug brawlers / robomutts as replacements (only inside group variables).
- Tests: tests/test_v1029.py (25): 7 parse round39; 18 simulator (ledger and reasons, species picks, size variants,
  notes and their queue, failure reporting, group via spawn point, late listing, flyers, ground vs jetpack thug,
  checkpoint determinism, two planets, boss tier rules, boss switch, 600-spawn busy level, budget storm). 4 older tests
  follow the new rules (banner, the new note, Ctrl+- text, boss route). Full suite: 769 run, 0 failures, 23 skipped.
- Verified in the game: nothing of 10.29. Factory route: IN-GAME VERIFIED (round37-39). Next: TESTING.md 2-dev16.

## 2026-11-18: dev 10.28 (kit 10.0.18): round38 - the Enemy Randomizer's first real run, four bugs fixed

- Asked: no Boss / Chaos work; perfect the Enemy Randomizer: audit the 10.27 run (Phase 1), then cover every practical
  spawning method (Phase 2). Log: tests/data/round38_rivet.log (dev 10.27 scripts, v7 helper, spawnproof standing down,
  spawnprobe on; NefCity, Zurkon A1 twice, A3 started, A5 area, Sargasso, NefCity; game path replaced). No on-screen
  observations came with it.
- CONFIRMED IN THE GAME (round38):
  * factory adapter: 57 CHANGED, 11 VERIFY, 11 REPLACEMENT SPAWNED, 0 ORIGINAL, 0 other. Zurkon A1 (robot sh / me /
    bladeball, every direction) and Sargasso: BBE933CB "enm_thugs4less_shoo (jetpack, flyer) -> enm_indigenous_wasp",
    3 wasps spawned - the first replacement off Zurkon and the first for flyers. Both A1 runs ended EndReason=0.
  * checkpoint reloads: 27 put back OK; the same factories re-armed on the next try (deterministic by seed + node id,
    except when a new kind was learned in between: A97C435B went robot_me -> bladeball -> thugs as the pool grew).
  * rules: Grunthor learned "large ... role boss", burrower beetle "mount ... never", miners / vendors / helper bots
    "friendly ... never" - never touched. Group members learned for 2 nodes (8B848504: thug melee, thug shooter,
    robomutt; AA509229: bladeball, robot sh, robot me); vehicle group A86FB955 kept out (member "-").
- BUGS SEEN (fixed in 10.28):
  1. False stuck: BotDeathCompleteEvent came (DISCOVER) but never with a bot the randomizer could match, so every
     changed A1 factory was "stuck" 180 s after its last spawn while the fight went on: 5 blocks saved for the seed and
     5 notes. Fix: V.gone (a bot that no longer answers rivet.components / rivet.name is gone), stuck = bots alive AND
     the whole level quiet (any death, enemy spawn or gone bot counts) for 180 s; stuck puts back for the level and
     counts a retry; V.migrate drops 10.27's "without a death" blocks.
  2. Frame budget: 100 RANDO-ERRORs at 16_rando_spawners.lua:2369/2370/1634 (the arm pass loop and vpace - the hook's
     error lands on our own lines, outside every pcall), each killing the job after 2 restarts: spawn batches lost,
     the arm pass restarted from spawner 1; one checkpoint put-back cut short (:2057). Fix: V.pump with persistent
     progress (V.pending put-backs first, the queue one spawn at a time, the plan cursor), restarts until 40 without
     progress, budget errors counted; the arm pass only when lvl.dirty; V.SLICE 1 ms; V.put_back safe everywhere.
  3. Cost: each batch with a SpawnFactory-0 spawn (ambient portals and cars, constantly) searched every node twice.
     Fix: V.tie_one with a location cache (checked against the node's own spawn record - waves may share spawn
     points) and a negative cache (3 misses).
  4. Cut names: ground and jetpack shooter thug both "enm_thugs4less_shoo". Fix: V.same_kind = name + bot family.
- FOUND (real game, used now): the node variable 942662419 (name unknown, no rivet.hash match) holds a node's SPAWNED
  actors (portal nodes: = LastSpawn; vehicle group node: a group of 3 cars); rivet.script_node expands actor groups.
  The Spawner spawn list is a 17-entry ring to the end of the 432-byte component (A86FB955 counted 115 spawns).
  Template actors never answer before a spawn: 0 of >90 asks on 3 planets (asking now stops after 40).
- NOT CHANGED, STILL OPEN: group nodes were never re-listed / tied on the second run (A5's thugs at spawn index 8 / 9
  tied to no record); single-enemy nodes: 0 changed (the ones seen spawn portals / cars / props; Sargasso's node wasp
  never fresh with a known kind). 10.28 adds a third tie (spawned-actors variable, group expansion) and the "level
  detail" + "tied to no spawner variable" lines so round39 says exactly why.
- Tests: tests/test_v1028.py (22): 7 parse round38's real log, 15 simulator on the production code (the fixes above).
  test_v1027: 3 tests follow the new rules (put back on leaving a planet, stuck = level-only put-back, the write line).
  Full suite: 744 run, 0 failures, 23 skipped.
- Verified in the game: factory route of 10.27 (round38). Nothing of 10.28 has run. Next: TESTING.md 2-dev15.

## 2026-11-18: dev 10.27 (kit 10.0.18): the Enemy Randomizer on the variable route

- Asked: turn round37's proven factory method into the Enemy Randomizer (the `-` key), cover every normal enemy and
  spawning mechanism (robomutts / thugs included), one registry, no more investigation-only rounds.
- Why the old Enemy Randomizer never worked: enemy.lua was a client of 16_rando_spawners' census route (10.12-10.20),
  which looks for a Prius `Templates` list in SpawnerScriptAction nodes. No real log ever showed one (the census read
  0 nodes every round); the enemy is decided by script VARIABLES instead (round35-37).
- Built (16_rando_spawners.lua section SP.V, ~900 lines, the production code):
  * adapters: factory (SunsetSpawnerFactory `Templates`, plug 3990217346 - PROVEN), template (SpawnerScriptAction
    `Template` single actor, 1835115251), group (the same variable holding an actor group, GROUP_BIT 0x80000000 -
    round35-37's robomutt / thug / robot / bladeball waves with SpawnFactory 0). Factories nodes are covered by their
    factories. Spawns tie to factories by SpawnFactory, to nodes by LastSpawn then the Spawner's spawn list.
  * registry: template -> name / bot class / family / role, from spawns, from the template actor before any spawn
    (rivet.components + rivet.name of the handle: unknown whether your game answers; logged per scan), and from the
    save (state.enemy_reg by uid; rivet.find_uid adds known enemies loaded on another level). Group members:
    state.enemy_groups by node id. Both kept over New Game and the companion's restore.
  * rules: role "enemy" only (SP.FAMILY_CLASSES + name exclusions + health bar = boss tier); walkers (ground,
    swarmer) / flyers / turrets stay in their group; another kind; loaded here; picks by seed + spawner id + original
    name (stable over loads); a template that spawned two kinds is MIXED and never used; uid form kept as the proven
    write (none -> none). Only spawners with 0 spawns on this level (counted even while off) and shared variables only
    if every user is fresh.
  * verification and safety: first spawn of each change -> REPLACEMENT / ORIGINAL / SOMETHING ELSE; ORIGINAL puts it
    back; 2 ORIGINAL with 0 REPLACEMENT switches the adapter off for the session (all its changes put back). Put back
    on checkpoint load, level / planet change, `-` off, story boss area (back on after it), stuck 180 s, 5 retries
    (then kept original for the seed: spawn_blocked "v:<id>"); only a variable that still holds exactly what was
    written, same generation. Jobs sliced at 1.5 ms, budget errors yield and retry, a failed read is read again.
  * a group is replaced by ONE enemy, re-chosen after every spawn (a mixed wave); a group with a non-bot member or
    walkers + flyers is never changed; groups change from their second run (the first learns the members).
- enemy.lua: route "vars"; status / Ctrl+`-` from SP.V.status(). Setting `enemy_route = "census"` keeps the old route
  (the v1012-v1019 tests use it: they cover the code Boss / Chaos still run). Boss / Chaos unchanged (still nothing in
  the game). dev(spawnproof).lua stands down while the Enemy Randomizer is ON.
- Tests: tests/test_v1027.py (40) on the PRODUCTION code: 5 rule tests; 31 simulator tests (synthetic memory; the
  simulated game spawns what the variable holds - proven for factories, ASSUMED for nodes and groups); round37's real
  factory data replayed (the engine changes 1097939/40/44 like the experiment, plus the bladeball factories, all
  REPLACEMENT SPAWNED, the pub's NPC factories untouched); the 6/6 / 20/20 benchmark. Full suite: 722 run, 0
  failures, 23 skipped (9 pwsh, 14 old git history).
- Verified in the game: NOTHING of 10.27. In-game evidence for the method: round37 (factory route, robot shooter ->
  robot melee). Visual confirmation: none yet. Next: TESTING.md 2-dev14.

## 2026-11-18: dev 10.26 RESULT (round37): the first enemy replacements in the real game

- Log: tests/data/round37_rivet.log (dev 10.26 scripts, v7 helper; Zurkon, challenge A1 played twice to the end).
- CONFIRMED BY THE GAME'S OWN DATA: two experiments, each "enm_pirate_robot_sh -> enm_pirate_robot_me on 3 factory(ies)
  that have not spawned yet" (1097939/40/44, then 1104436/37/41). All 6 writes read back OK. All 6 factories' first
  spawns: "VERIFY ... REPLACEMENT SPAWNED". All 20 spawns of armed factories were enm_pirate_robot_me
  (GameBotMeleeSwarmer) where these factories had held the robot shooter; 0 ORIGINAL, 0 SOMETHING ELSE. Both A1 runs
  completed (EndReason=0, ~228 s each, as before); all 6 variables put back OK at the next checkpoint; no RANDO-ERROR.
  ("Spawned" = rivet.name / rivet.components of the handle the SpawnerSpawnEvent carried: what the engine created.)
- PENDING: the player's own on-screen observation (melee robots in place of shooter robots in those waves).
- So the mechanism for the Enemy / Boss / Chaos Randomizers is found: write another enemy's Templates value into a
  SunsetSpawnerFactory node's "Templates" script variable (SceneManager script variables, rando_give.dll v7) BEFORE
  that factory spawns. The kit's 16_rando_spawners / enemy / boss / chaos do NOT use it yet - they still do nothing.
- Tests: tests/test_v1026_result.py (5, real log).

## 2026-11-18: dev 10.26 (kit 10.0.17): fresh factories only

- Log: tests/data/round36_rivet.log (dev 10.25 scripts, v7 helper; Zurkon arena challenge A1 replayed and completed,
  then two more A1 starts).
- CONFIRMED (real game): FIRST WRITE of an enemy Templates value. "factory 1109878 chosen (a factory that already
  spawned first; spawned 4 time(s))", "ARMED ... Templates variable 25747 ... enm_pirate_robot_me (handle 1109383) ->
  enm_pirate_robot_sh (handle 1109378); read back OK", later "put back (level changed: checkpoint loaded) ... variable
  OK". The game kept running and A1 completed.
- NOT VERIFIED: factory 1109878 spawned 4 times before the write and 0 times after it (the fight went on with other
  factories: 1109879..1109889). Each arena wave has its own factories, each spawning once per wave - v5's "a factory
  that already spawned first" was the wrong choice (round35's repeat spawns were within one wave).
- Same rule as round35 with new handles: 3 Templates values (1109378 robot_sh, 1109383 robot_me, 1109384 bladeball),
  every factory one kind. Factory variables now print with names (Templates / Locations / InitialCount).
- dev(spawnproof).lua v6: P.try_arm_factory builds, from factories not yet spawned on this level, a list per Templates
  value; picks the learned enemy kind with the most fresh factories and a replacement of the same role and another
  kind; arms them all (up to 8) as one EXPERIMENT (at most 3 a session; factory arms no longer use the node route's
  swap budget); each verifies on its own first spawn; "factory route waiting: ..." when nothing fits. On-screen names
  use the last path segment (round36 showed "next enemy here should be another enemy": names are cut at 64 chars).
- Banner dev 10.26. Tests: tests/test_v1026.py (6, real log); test_v1025's 5 simulator tests rewritten for v6 (spent
  factory never armed, every fresh factory of the kind armed, put back at once when ignored). Full suite: 677 run, 0 failures, 23 skipped.
- Verified in the game: one write + put back of an enemy Templates value, harmless. No replacement seen yet. Next:
  TESTING.md 2-dev13.

## 2026-11-18: dev 10.25 (kit 10.0.17): the factory's Templates variable

- Asked: "still nothing". Log: tests/data/round35_rivet.log (v7 helper in the game; scripts still dev 10.23 -
  spawnproof v3, banner "Randomizer dev 10.23"; NefCity, Zurkon arena challenge A1 replayed and completed).
- CONFIRMED (real game): FIRST real run of the experiment. SceneManager 7FF7A5857580 (1x), scans of 183-197 nodes
  (106 Template, 79-91 Factories), 970 spawns tied to nodes in A1 (LastSpawn / Spawner slot), 11 budget retries and no
  job lost. No ARMED: v3 only swaps SpawnerScriptAction variables; the arena factories the events name tie to no node
  (most factory spawns "no node"), and the Template nodes spawned portals only.
- FOUND (real game): every arena enemy came with SpawnFactory = a SunsetSpawnerFactory node, and that node's own
  variables are "Templates" (3990217346), "Locations" (2501629366), "InitialCount" (2429945776, pub factories) and one
  holding the factory itself (3368780241) - names = rivet.hash. A1's factories 1097946..1097957 held 3 Templates
  values: 1097446 -> enm_pirate_robot_sh (factories 948/949/953/957), 1097451 -> enm_pirate_robot_me (946/954/956),
  1097452 -> enm_pirate_bladeball (947/951/952/955); every factory spawned only its kind (up to 13 spawns each). The
  spawn location is the factory's Locations value (1097957 -> 1097478). The pub's factories 1087087..1087101 follow the
  same pattern (Templates 1086734..1086754, ambient NPCs).
- Other spawn routes seen: wave enemies with SpawnFactory 0 from SpawnerScriptAction nodes whose Template variable is
  an actor GROUP (80C006D9: robomutt / thugs / robot / bladeball from one node) - not handled yet.
- dev(spawnproof).lua v5 (factory Templates route): P.scan_factories lists SunsetSpawnerFactoryScriptAction nodes
  (rivet.script_nodes) and reads each Templates variable plug (same ScriptPlugs layout); learn() reads the spawning
  factory's Templates value and learns value -> enemy; P.try_arm_factory swaps ONE factory's Templates (another
  learned enemy, same role, other kind; a factory that already spawned first, a fresh one after an ORIGINAL verdict;
  one experiment at a time; variable users counted); VERIFY on the next spawn of any factory using the variable, the
  next 6 logged "[ARMED factory variable ...]"; put back on the next checkpoint / level, or at once when not replaced.
  learned names / roles are no longer overwritten with nil by actors already gone (v3's 9/10/11 oscillation).
- Banner dev 10.25 (kit scripts still 10.0.17). Tests: tests/test_v1025.py (11): 6 on the real log (incl. "one
  Templates value, one kind" parsed from the log), 5 simulator. Full suite: 671 run, 0 failures, 23 skipped (9 pwsh, 14 old git history).
- Verified in the game: nothing of 10.25. Enemy / Boss / Chaos: NOT working. Next: TESTING.md 2-dev12.

## 2026-11-18: dev 10.24 (kit 10.0.17, rando_give.dll v7 in the kit): the helper that was never copied

- Asked: "Nothing changed". Log: tests/data/round34_rivet.log (dev 10.23, kit 10.0.17; companion on from the start;
  NefCity, Zurkon arena challenge A1 replayed and completed, NefCity; game path replaced).
- CONFIRMED (real game): kit 10.0.17 complete; spawnproof v3 subscribed its own planet and spawn events ("planet yes,
  spawns yes"); the 10.23 planet fix WORKED: "level reset (planet Zurkon): ON ZURKON - active", the randomizer itself
  logged "RANDO-PLANET Zurkon scarstu", every Zurkon checkpoint "on scarstu".
- BLOCKER (real game): "RANDO-SPAWNPROOF no script variables: rando_give.dll is v6, v7 is needed (copy the kit's)".
  The game folder had the kit's top-level rando_give.dll (v6); v7 was only in rando_give_source/dev_build and every
  TESTING step since 10.21 asked for a manual copy. Nothing was scanned, armed or written. The experiment has still not
  run; nothing is known for or against the Factories mechanism.
- v7 evidence (round32, real game, v7 copied that time): SceneManager found (signature 1x), RANDO-REAL direct delivery
  ready, RANDO-ARMOR armor give verified, mission helper ready - every v6 function plus the SceneManager.
- Kit: rando_give.dll := the v7 build (sha256 8055703e..., byte for byte the source's build, test_native). The v6
  binary (efb92723...) moved to rando_give_source/release_v6/; tools/build_public_release.py packages it
  (RELEASE_DLL), validate_release unchanged, so a public package is unchanged. dev_build/ removed.
- dev(spawnproof).lua v4: "BLOCKED: no script variables: <why>" logged and shown on screen ("SPAWNPROOF BLOCKED: ...")
  on every Zurkon level where it cannot work (was: one log line per session).
- Banner dev 10.24; kit scripts unchanged at 10.0.17 (only dev(spawnproof) and the banner string changed).
- Tests: tests/test_v1024.py (10): 4 on the real log, 4 on the DLL files (hashes, public plan, no dev_build), 1 on
  round32's v7 evidence, 1 simulator (BLOCKED on screen with a v6 helper). Full suite: 659 run, 0 failures, 23 skipped (9 pwsh, 14 old git history); test_native rebuilt the source with clang and got the kit DLL byte for byte.
- Verified in the game: nothing of 10.24. Enemy / Boss / Chaos: NOT working. Next: TESTING.md 2-dev11.

## 2026-11-18: dev 10.23 (kit 10.0.17, rando_give.dll v7 developer build): the lost planet

- Asked: "Enemies/bosses didn't got randomized. Also, update it in github next time", with a brief (find the real
  blocker; no speculative implementation; one real in-game replacement; diagnostics; honest report). Log:
  tests/data/round33_rivet.log (dev 10.22, kit 10.0.16; seed = random, companion started late; NefCity, Zurkon
  arena challenges A1 and A2 replayed and completed; game path replaced).
- DIAGNOSIS (real game, this log):
  * The experiment NEVER RAN. "RANDO-SPAWNPROOF v2 loaded" is its only line. v2 acted only where
    RANDO.state.current_planet == "scarstu".
  * Why the state was wrong: the seed waited for the companion; every event went to the pre-seed buffer (500,
    first come first kept). NefCity's load filled it; the PlanetChangedEvent to Zurkon (DISCOVER line present) was
    dropped. After "replaying 500 event(s)" the session logged only "RANDO-PLANET NefCity nefarious_city", and
    every Zurkon checkpoint "on nefarious_city". Reproduced in the simulator (without the fix: "dropped:
    PlanetChangedEvent 3, SpawnerSpawnEvent 125").
  * So round33 says NOTHING about the Factories mechanism. The spawner layer's events did flow after the seed
    (RANDO-SPAWNERS spawn lines during A1/A2), the 16 census again read 0 nodes (expected; it looks for Templates).
- What is known to work (real game, earlier logs): rivet.script_nodes lists 185-197 SpawnerScriptAction nodes on
  Zurkon; their variable plugs and the SceneManager's script variables read correctly (v7 helper, signature 1x);
  LastSpawn and the Spawner slot list tie spawns to nodes; rivet.write / read-back work (items, armor). Known NOT
  to work: Prius-based Templates (10.12-10.20), Template-variable swaps for enemies (round32: enemy nodes have
  none). Unverified: whether swapping a node's Factories variable (or its Spawner +0x48 copy) changes the enemy.
- Native route considered: rivet_hook's rivet.detour only skips / passes component update slots (no argument
  rewrite, no Lua callback); it cannot intercept a spawn. A rando_give.dll hook of the engine's spawn function needs
  that function's address and code, which no log or file here contains. Not started; the Lua-level Factories swap
  must be tested first (it costs one challenge).
- 10_rando_runtime (kit): R.BUFFER_KEEP classes (planet, level, checkpoint, save, mission, objective, mission
  devstats, weapon / gadget added, bolts, raritanium, purchase) are never dropped (cap 2000); others keep the 500
  bound; the replay line lists kept / dropped.
- dev(spawnproof).lua v3: direct rivet.on_event for PlanetChangedEvent and SpawnerSpawnEvent (2 callbacks; falls back
  to the spawner layer's copy if refused); planet from the event name "Zurkon" (state as fallback); "level reset (...):
  ON ZURKON - active / not Zurkon - inactive (event planet X, randomizer state Y)"; "inactive: N spawn(s) ignored";
  on-screen "SPAWNPROOF ARMED: next X here should be Y" and "SPAWNPROOF: <verdict> (name)"; duplicate deliveries of a
  spawn ignored. test_v81's static check caught a use-before-definition (planet() in P.reset) - fixed.
- ENEMIES_AND_BOSSES.md and CHAOS.md open with "NOT WORKING IN THE GAME". Kit 10.0.17 (every RANDO_FILES tag),
  banner dev 10.23.
- Tests: tests/test_v1023.py (21): 4 on the real log, 2 buffer tests in the simulator (the planet one fails without
  the fix), 5 spawnproof v3 tests in the simulator. Full suite: 650 run, 0 failures, 23 skipped (9 need pwsh, 14 need old git history); native: the v6 and v7 DLLs rebuild byte for byte (test_native). No native code changed.
- Verified in the game: nothing of 10.23. Enemy / Boss / Chaos: NOT working. Next: TESTING.md 2-dev10.

## 2026-11-18: dev 10.22 (kit 10.0.16, rando_give.dll v7 developer build): the Factories variable

- Asked: "tried 2 battles, 1 normal enemies, 1 boss. Nothing randomized. Solve. Even if it was an exe or dll."
  Log: tests/data/round32_rivet.log (dev 10.21; NefCity, Zurkon arena challenges A1 and A2 replayed and
  completed, NefCity; Chaos ON from the save; game path replaced).
- CONFIRMED (real game): v7 helper found the SceneManager (signature matched 1x); spawnproof v1 scanned 185-197
  nodes on Zurkon (106 with a Template variable, 124-126 with LastSpawn) and tied spawns through LastSpawn. It
  NEVER armed: "0 regular-enemy template(s) learned" every time.
- WHY (real bytes): every Template-variable spawn on Zurkon was a rift portal (anomaly_portal_*) or a prop. The
  enemy spawns came from nodes WITHOUT a Template variable ("Template variable none"): their variable is
  838143302 = rivet.hash("Factories") (the DDL's SpawnerPrius FactoryGroup), one actor in the
  1087129..1087143 range - the same range as the SpawnFactory field's SunsetSpawnerFactoryScriptAction actors.
  The Spawner component agrees on 9 dumped nodes: +0x48 = factory, +0x50 = template, +0x58 = location (factory
  nodes: +0x50 = +0x58 = 0; portal nodes: +0x48 = 0 and +0x50 / +0x58 = their Template / Location variables);
  +0x9C = count and +0xDC = slots of 12 bytes { spawned handle, location handle, f32 time } (node 9620735f's
  slot = 1097158 = v1's LastSpawn tie; cd8dc00e's slot = its LastSpawn variable 1105863).
- ALSO: v1's jobs died on "ran past the 8 ms frame budget" 13 times (lines 101/133/244/272/400, outside a
  pcall: the job ended and its spawns were lost), and v1 logged only the first 12 spawns per level (pub bots and
  portals), so the challenges themselves left no spawn lines.
- DDL (neptuwunium/rivet docs/ddl/rcra_ddl.json): SunsetSpawnerFactoryPrius has NumForcedHealthDrops,
  BotSetupData (intro / wander flags) and SetupControllerData - no template field. So where a Factories node's
  enemy template lives is NOT known; v2 tests the cheapest hypothesis (the factory decides what spawns) and
  describes each factory's own script-node variables for the next step.
- dev(spawnproof).lua v2: slot = Template variable, else Factories variable; spawns tied by LastSpawn, then by
  the Spawner slot list; learns per slot value what spawned (MIXED if a value spawned two kinds: never used);
  arms nodes not yet seen spawning (up to 4 a session, 2 at a time), same kind and role (enemy / boss) only;
  writes the variable (uid +0x00, actors +0x10, checked and read back) and the Spawner's cached copy if it
  already holds the old value; VERIFY on the node's next spawn; put back on the Spawner's stop or a level
  change. Every unit of work is guarded against budget errors (yield and retry); a job killed outside a
  guard restarts (twice). Logs: 40 enemy / boss spawns per level, 6 others, 12 factory descriptions, a level
  summary. Banner dev 10.22 (R.RELEASE); kit files otherwise unchanged (10.0.16).
- NOT DONE: a native (rando_give.dll / exe) spawn hook. Finding the engine's spawn function needs the exe's code
  (Dump-GameCode around the Spawner vtable 7FF7A20F83E8 or the SpawnerSpawnEvent sender); not available here.
- Tests: tests/test_v1022.py (20): 6 on the real log, 4 on the real Spawner bytes, 10 in the simulator (a
  real-style budget hook that raises inside the coroutine and clears itself). test_v1021's simulator tests
  follow v2's wording.
- Verified in the game: nothing of 10.22. Enemy / Boss / Chaos still change nothing. Next: TESTING.md 2-dev9.

## 2026-11-17: dev 10.21 (kit 10.0.16, rando_give.dll v7 developer build): the Template variable

- Asked: make Enemy / Boss / Chaos actually work; one controlled in-game replacement first. Log:
  tests/data/round31_rivet.log (dev 10.20 with dev(spawnprobe); NefCity, Zurkon arena challenge A1 replayed
  and completed, NefCity; Chaos ON from the save, Enemy/Boss toggled; game path replaced).
- CONFIRMED (real game): kit 10.0.15 / dev 10.20 loaded, 25/25 scripts. The probe lost PlanetChangedEvent
  and CheckpointTriggeredEvent ("too many callbacks registered, the limit is 64": rivet_hook allows 64 event
  callbacks in all), so it never re-indexed on Zurkon: its index there listed only the two hub nodes
  a74767e9 / d4f89629 (also on NefCity), its 6 spawn descriptions were ambient NPCs, its sweeps saw nothing.
  The 16 census on Zurkon listed 0 nodes 5 times (round30: 120-197). No arena encounter was observed.
- CONFIRMED (real game, ComponentInfo via the node's actor): SpawnerScriptAction (size 128, id 31B870E3) and
  Spawner (432, id FC56D431 = hash "Spawner") both have a Prius TYPE, prius size 0, ReadWrite, and
  ddlPriusData 0 on both instances.
- CONFIRMED (real game, rivet.script_node on the hub nodes): a SpawnerScriptAction has VARIABLE PLUGS
  "Template" (1835115251, actors), "Location" (2761897147, actors), "MaxAlive" (161848772, float 1.0),
  "NumSpawns" (1830449615, float 1.0), "LastSpawn" (406637480, actors) and output "OnSpawned" (2046202852).
  Names = rivet.hash (reflected CRC-32, start 0xEDB88320) of these words. The real plug block matches
  rivet_hook's ScriptPlugs exactly (in 1 / out 1 / vars 5, zone, owner = node handle 0x2144C2).
- HYPOTHESIS (not proven): the node spawns the actor held by its Template variable; LastSpawn holds its last
  spawn. Supported by: the names, NumSpawns / MaxAlive also coming from variables, round30's census showing
  readable varGroups (plugs +0x10) on many Zurkon nodes. UNKNOWN: whether arena nodes use the Template
  variable, and whether the node reads it at each spawn or only once.
- HYPOTHESIS: rivet.script_nodes returns a partial (even empty) list when the 8 ms callback budget runs out
  (rivet_hook nodes() stops on expired() and l_script_nodes drops "truncated"); the shop's search ran past
  the budget on Zurkon in the same callback as the census.
- rando_give.dll v7 (rando_give_source/dev_build/; the kit keeps the verified v6 for the release builder):
  finds the SceneManager with rivet_hook's own SCENE_MANAGER signature (lea rcx, [rip+x]; exactly one match,
  as rivet_hook requires) and publishes it at mailbox +0x128 (+0x130 match count). Read only.
- 16: SP.listen / SP.notify_listeners (developer files share the layer's callbacks; checkpoints as
  "Checkpoint"). dev(spawnprobe) uses it, prints actors variables, asks at most 4 components per actor.
- New dev(spawnproof).lua (developer file): on Zurkon only, every 2 s lists the nodes, reads their variable
  plugs and the variables (SceneManager +0x75A0, 0x40 each, generation checked); ties each spawn to its node
  through LastSpawn and learns what each template is from what it spawned; arms ONE node (not spawned,
  Template holds one actor, not shared, a regular enemy) with another learned regular-enemy template of
  another asset (check, write uid +0x00 and handle +0x10, read back); VERIFY on its next spawn; put back when
  its Spawner stops; a reload is never written. Kit 10.0.16, banner dev 10.21.
- Tests: tests/test_v1021.py (14): 5 on the real log, 2 on the real plug-block bytes, 7 in the simulator
  (synthetic memory; one caught a real bug: a learned template was overwritten by the armed node's own
  spawn). Native core test for the signature; the dev DLL is byte for byte the source's build. 609 run, 0
  failures, 23 skipped.
- Verified in the game: nothing of 10.21. Enemy / Boss / Chaos still change nothing. Next: TESTING.md 2-dev8.

## 2026-11-17: dev 10.20 (kit 10.0.15, generator 10.11.0): evidence instead of another offset

- Asked: "Dev 10.19 still does NOT work in the actual game ... a serious engineering investigation, not
  another cycle of guessed offsets". Log: tests/data/round30_rivet.log (dev 10.19, kit 10.0.14; save with
  Chaos ON; NefCity, Zurkon arena challenges A2 / B3, Ardolis, Cordelion; game path replaced).
- CONFIRMED in the game (the log): kit 10.0.14 and banner dev 10.19 loaded; 24/24 scripts; no Lua error;
  "all 12 required scripts are 10.0.14". 17 censuses logged (1-18, number 5 never reached the log), all
  "0 spawner node(s) read, 0 template(s)", 2-197 nodes skipped each. Toggles: "0 spawner slot(s) put back".
  Nothing was written; Enemy, Boss and Chaos behaved identically (nothing to act on). Since 10.12 no census
  in any of your logs has read a node.
- CONFIRMED: node +0x60 (u32) == its Spawner component's own handle (+0x1C) in 6 of 6 dumped pairs; both
  components' +0x10 point at the same Actor; Spawner handle = node handle + 1. The SpawnerStoppedEvent's
  SpawnerComponentHandle is that handle (2182844 = 0x214EBC = node b38522d499c03015's Spawner). So the
  node <-> Spawner <-> stop-event route is real.
- REFUTED: 10.19's premise that the Spawner component carries the Templates list. Spawner (432 bytes):
  ddlPriusData +0x08 = 0, and the 306 bytes that reached the log hold no heap pointer but the actor (+0x10);
  module pointer +0xD0 in one node. Values seen: +0xA8 two floats 0.035, +0xC0 -1.0f, +0x20..+0x3F -1 (the
  update list slots), +0xC8.. small u16 + hash-like bytes in some nodes. The census reasons show readable
  pointers in some Spawners at +0x198 (a target that is readable and has a readable pointer at +16) - in
  the 126 bytes the log never showed.
- Two diagnostic bugs found: (1) rivet_hook's l_log formats a line into a 0x400 buffer: every 432-byte
  Spawner dump was cut at 306 bytes. (2) SP.layout_at accepted three empty lists, so zero-filled memory (the
  unused tail of a Spawner, through the 10.19 `inline` route) was reported as "factory-only spawner (no
  Templates)" and stopped that node's other routes.
- Research (no game): rivet_hook develop @0bdb394: script.hpp says +0x58 is the plug block (ScriptPlugs,
  0x28: zone +0x1C, owner +0x24), not a Prius; actor.hpp gives Actor (0xC0: actorAsset +0x30, components
  +0x68, count +0x70) and ComponentInfo (name +0x60, size +0x78, prius +0xC8, prius_behavior +0xE7);
  rivet.read is capped at 512 bytes; rivet.find_uid is the engine's own uid lookup (cheap); script_signal's
  properties() also only follows ddlPriusData. Nothing in rivet / rivet_hook says where a script node's
  Prius lives after creation.
- Unknown (needs the game): where the running encounter's Templates are; whether the game copies them
  before a write could matter; which component class a spawned bot reports.
- 16: SP.log_dump (96-byte lines) for every dump; SP.layout_at: three empty lists -> "all three lists empty
  (zeroed memory, not a Prius)", factory-only only with a factory or a spawn point. Behaviour otherwise
  unchanged (it still reads 0 nodes in your game - expected).
- New dev(spawnprobe).lua (read-only; HELD out of every release as a dev file): index per load (node,
  Spawner by handle == +0x60, snapshot, histogram of readable-pointer offsets), spawn descriptions (uid,
  actor asset id / name, Template flag, classes; SpawnFactory too), sweeps after spawns (Spawner bytes that
  changed), stop/start events matched by handle (diff since the index), deep probes (ComponentInfo of every
  component on the node's actor, node / Spawner / plug bytes, every block one pointer away dumped, two away
  searched, rivet.find_uid on each 8-byte value: `UID HIT` names the actor). Frame-budget stops are retried.
- Kit 10.0.15, banner dev 10.20 (every RANDO_FILES tag, C/H/TT versions, build_data, build_public_release
  BUILD, the tests that assert the kit). INSTALL.txt lists dev(spawnprobe); harness `spawnprobe=True`.
- Tests: tests/test_v1020.py (17). TheLogTests (5) assert the facts above on the real log. Spawner-layer
  tests (3) use the REAL node / Spawner bytes of b38522d4 (unseen tail zero-filled) and all 3 fail against
  10.19 (it says "factory-only", dumps nothing, lines too long). Probe tests (9) use the same real bytes;
  pointers / uids / changes in them are SYNTHETIC and labelled. 595 run, 0 failures, 23 skipped.
- Verified in the game: nothing of 10.20 yet. Enemy / Boss / Chaos randomization: NOT working (KNOWN_ISSUES
  0l). Next: TESTING.md 2-dev7 (one Battleplex challenge, send rivet.log).

## 2026-11-17: dev 10.19 (kit 10.0.14, generator 10.11.0): the node's Spawner component

- POST-MORTEM (10.20): refuted in the game by round30_rivet.log - the Spawner component has no Prius
  either; nothing below "Conclusion" held. Kept as written.

- Asked: "no enemy/boss randomized", with tests/data/round29_rivet.log (dev 10.18; Zurkon, NefCity,
  Sargasso, Ardolis; save with Chaos ON).
- Log evidence: every node skipped (rivet no prius; ddlPriusData 0; no pointer route); the global
  find_component("Spawner") "ran past the frame budget"; census restarted up to 4 times on a level.
  `spawn:` lines: sender == field SenderHandle == SpawnedHandle (the bot sends it); location uids are bit-63
  zone uids. Six `dump` lines (Zurkon), all alike: vtable +0, ddlPriusData 0, actor +0x10, timeScale 1.0,
  own handle +0x1C (0x406E8E, 0x406E90 ...), updateListIndex all -1, uid twice +0x48/+0x50, plugs +0x58,
  **+0x60 = own handle + 1**, +0x64 = 0x80B003E8 (group bit), +0x70.. 1, 1, 1.
- Conclusion: the node made a component right after itself and keeps its handle. rivet.hash("Spawner") =
  4233548849 = SpawnerPrius's component_id (checked with the hash rivet_hook documents: MIS_INTRO and
  PerformWarpEvent reproduce). SpawnerScriptActionPrius extends SpawnerPrius: the Spawner component carries
  the Templates list.
- 16: SP.spawner_of(node, addr) - u32 at +0x60, rivet.component(node.actor, "Spawner") (+ any other
  `*Spawner*` class of rivet.components), used only if c.handle equals it; SP.find_prius(c2, addr2, short)
  with up to 0x200 bytes of the component read, own pointers from +0x48, new `inline` route (strict) and
  path; rec.spawner_component / spawner_class; rec_by_handle matches it; diagnostics (component list / dump)
  for 6 nodes; event_diag for 3 start/stop events a level; per-node pcall + yield on a budget error (3
  tries), SP.CENSUS_RETRIES 8; SP.SCAN_SPAWNER_COMPONENTS false.
- Simulator: spec.comp = prius / holder / inline / elsewhere (node +0x1C own handle, +0x60 Spawner handle,
  +0x64 group; Spawner on the node's actor), SpawnerSpawnEvent sent by the bot, Started/Stopped carry the
  Spawner handle.
- Kit 10.0.14, banner dev 10.19. tests/test_v1019.py (11); test_v1018's placed-Spawner test opts into the
  scan; test_v1017's retry text /8. 578 run, 0 failures, 21 skipped.
- Open (needs the game): the Spawner component found on the node's actor (`layout prius/spawner/...`);
  `verify ... TOOK EFFECT`.

## 2026-11-17: dev 10.18 (kit 10.0.13, generator 10.11.0): spawner Prius reached by hand

- Asked: "Still nothing randomized. Take your time, investigate and fix, and make no mistake. Next try
  HAVE to work. Use any means necessary." Log: tests/data/round28_rivet.log (dev 10.17, kit 10.0.12; save
  with Chaos / Enemy / Boss ON, nothing learned; NefCity, Cordelion, Zurkon, Malinon).
- Log evidence: 22 censuses, 0 nodes read, every node "no Prius and the instance is only 128 bytes".
  rivet `[rivet] game version mismatch, invalidating pointers` (new; rivet re-finds its signatures).
  SpawnerSpawnEvent fields again SpawnFactory / SpawnIndex / SpawnLocation / SpawnedHandle; no
  SpawnerStartedEvent; many spawns before the first census (the level's load population).
- Research (no game): rivet_hook source (github.com/neptuwunium/rivet_hook @ 2.0.1):
  * l_component pushes `prius` only when find_component got data: it follows ComponentInfo.prius only;
    script nodes evidently have none there (both logs). script_signal.cpp properties() says the same
    ("if it keeps them").
  * src/game/script.hpp: ScriptAction = Component (0x48) + instanceUid +0x48 + graphUid +0x50 +
    plugs +0x58; the node's own fields from +0x60 (as AddToInventoryAction's item at +0x60, 09's
    ITEM_OFFSET). SpawnerScriptAction's 128 bytes leave 32 bytes: no room for its lists.
  * Component.ddlPriusData +0x08 -> holder { vtable, int32 count +8, data +16 } (ddl_visit.hpp).
  * dynamic arrays { T *data; int32 count; int32 capacity }, "confirmed against live instances".
  * rivet.find_uid parses hex text; actor_by_uid needs a valid actor (scene object).
  neptuwunium/rivet DDL dump (docs/ddl/rcra_ddl.json): SpawnerScriptActionPrius (144) extends SpawnerPrius
  (120, component "Spawner"); Templates / SpawnLocations / FactoryGroup are TUID (type 17) dynamic arrays;
  ActionType +120 default 60; SpawnerSpawnEvent also has SenderHandle (+44), hidden by RANDO-DISCOVER's
  noise list. Factories (SunsetSpawnerFactory) carry setup data, not templates. Every GameBot* class is in
  SP.FAMILY_CLASSES; added NPCBot (friendly) and BotHexapod (never).
- 16: SP.find_prius routes rivet / holder / scan (node pointers as Prius or holder; strict) / deep (a runtime
  object: fields embedded or a pointer; strict; SP.DEEP_NODES 4 per session); SP.path_hint follows the last
  working path first; SP.try_prius checks SP.layout_at at +8 (short for SpawnerPrius) and scores ActionType
  60 / a loaded uid (rivet.find_uid) among the templates or spawn points. array_at trusts only the count.
  Dumps (instance, holder, holder data, node pointers) for the first 6 failing nodes a session. Spawner
  components via rivet.find_component("Spawner", exact) (failure logged once, never stops the census).
  SP.learn_template (find_uid + rivet.components, kept per session as SP.tpl_seen = family/false, learned
  again into a replaced save). Pre-census spawns -> SP.started_handles / SP.started_locs. on_level /
  checkpoint load drop a running census (SP.job = nil). SP.pause yields inside long searches (slice clock
  set at each resume). "verify" log on a changed node's first spawn (SP.tpl_class); "spawn:" lines for the
  first 5 spawns a level; "Prius routes (census N)" and skip reasons grouped. Holder count > 1 only noted:
  two nodes reaching one Prius are caught by the shared-list rule.
- chaos.lua: C.check_loaded (inside the census) - another planet's template joins the pool only where
  its template actor is loaded; without rivet.find_uid 10.13's behaviour.
- Simulator: rivet.uid / find_uid / components moved out of rivet.component (10.17 had nested them: they
  existed only after rivet.component had run - the 10.17 tests passed partly by that accident). Node models
  holder (both logs: 128 bytes, no rivet prius, ActionType 60), ptr, deep embed / ptr, spawner_component,
  same_prius_as, holder_count; template actors with uids (templates_unhatched); sender_field.
- Kit 10.0.13, banner dev 10.18. Logs kept: tests/data/round27_rivet.log (10.15) and round28_rivet.log
  (10.17), game path replaced.
- Verified only offline: tests/test_v1018.py (18); test_v1013 cross-planet tests changed for the loaded
  rule; test_v1017 expectations updated for the new reasons. 567 run, 0 failures, 21 skipped.
- Open (needs the game): which route finds the Prius (expected: holder); template actors answering
  find_uid / components; `verify ... TOOK EFFECT` (the engine reading Templates at each spawn).

## 2026-11-17: dev 10.17 (kit 10.0.12, generator 10.11.0): Enemy / Boss / Chaos Randomizers fixed

- Asked: "enemy, boss and chaos randomizer didn't work. Fix it", with a rivet.log (dev 10.15 kit 10.0.11 and
  10.16's ON defaults; NefCity, Sargasso, Cordelion). Dev repo only. Base: 8f7948d (dev 10.16, which only
  turned Omega / Enemy / Boss ON in 04 and left kit 10.0.11 and banner 10.15).
- Log evidence: 32 censuses, all "0 spawner node(s) read, 0 template(s), 2..326 skipped", every listed node
  "cannot read the node" (so rivet.component found each node: the read failed). Two
  "census: 16_rando_spawners.lua:542/437: ran past the 8 ms frame budget" dropped a census each. Toggles
  logged "0 spawner slot(s) put back". SpawnerSpawnEvent fields: SpawnFactory, SpawnIndex, SpawnLocation,
  SpawnedHandle; no SpawnerStartedEvent seen.
- Cause (rivet_hook source, github.com/neptuwunium/rivet_hook src/scripting.cpp l_component/find_component
  and docs/LUA_SCRIPTING.md): rivet.component returns `size` = ComponentInfo.size (the instance) and
  `prius` / `prius_size` = the Prius data (ddlPriusData -> holder +16 -> data). read_node read
  min(0x100, size) bytes of the instance and needed 0x88: the SpawnerScriptAction instance is smaller.
- 16: read_node reads SP.PRIUS_READ (0x90) bytes at `prius` and checks SP.layout_at at SP.PRIUS_X (+8);
  instance search only without a Prius and never past `size`. rec.where, census line "layout prius +0x8".
  rec.locs (SpawnLocations ids) -> lvl.loc_index; handlers get (fields, ev): sender = SenderHandle field,
  else ev.sender; SP.rec_of_spawn falls back to rivet.uid(SpawnLocation). classify_actor: one
  rivet.components call (old loop as fallback), "spawned actor not classified" logged once per class set.
  Census budget errors (also from rivet.script_nodes) reschedule the census (SP.CENSUS_RETRIES 5).
- Kit 10.0.12 (every RANDO_FILES tag, C/H/TT versions, build_data, build_public_release BUILD), banner
  "Randomizer dev 10.17". test_v1012 kit-check test fixed for 10.16's ON defaults (it failed since 10.16).
- Simulator: spec.prius (instance 0x60, fields behind `prius` at +8, real SpawnerSpawnEvent fields with
  SpawnLocation handles and rivet.uid), spec.nosender, spec.small (the 10.16 failure), rivet.components.
- Verified only offline: tests/test_v1017.py (10; all 10 fail against the 10.16 spawner file); 548 run,
  0 failures, 21 skipped.
- Open (needs the game): the census line should now read nodes; does a Templates write in the Prius change
  what spawns (or does the node copy it at start)? Which bot class names rivet.components returns (watch
  for "not classified"). Not touched: the vendor array (0 weapons at +0x48), RANDO-OMEGA inventory not found.

## 2026-11-16: dev 10.15 (kit 10.0.11, generator 10.11.0): Omega weapons

- Asked: Omega weapons (New Game+) in the randomized item pool as separate items, with smart
  ownership: an Omega first gives the weapon as its prerequisite; the weapon after its Omega never
  downgrades it; never duplicate; never overwrite a higher tier; for every weapon that has an Omega.
  Investigate how the game does it first. Dev repo only; public repo and release untouched.
- BASE: this repository's main was dev 10.13 (376a887). The 10.14 optimization pass (project doc
  RiftApart_Randomizer_10.14.md) was delivered as a patch and never pushed, so it is NOT in here; this
  work is on top of 10.13. Kit 10.0.11 (10.0.10 was 10.14's number) so the two never share a version.
  Applying the 10.14 patch on top of this will conflict at least on the RANDO_FILES version tags.
- Research (static, neptuwunium/rivet's DDL + your dag): no Omega item config exists (919 dag item
  ids, none "omega"); `WeaponItemPrius.Omega` (bool, 0x534A51FB) is the Omega state of the owned
  weapon, next to XP / ammo / Mods; `ItemPrius.ItemConfigHash` is the weapon's 64-bit id;
  `VendorItemData.OmegaPrice / OmegaRequiredCardBonus / OmegaOnly` are the vendor's Omega purchase;
  `GameCampaignSave.IsChallengeMode / FirstOmegaWeaponPurchased`; no script action sets Omega. So
  AddToInventory can never give an Omega, and giving the weapon never makes it one.
- Data (tools/build_data.py OMEGA_NAMES): 20 `omega:<weapon>` items, category `omega`, the weapon's
  id, in-game names from the guides (14 listed by name, 6 assumed). Data version kept 5.1.0.
- Generator: `omega_weapons = false`; left out of the fingerprint while false
  (G.FINGERPRINT_SINCE_10_15), and the placement streams use G.placement_fingerprint (without it), so
  ON = the same seed + Omegas on currency spots (own stream). Audit and spoiler know them.
- Runtime 10: R.grant_omega / R.omega_tier / R.omega_applied; state `omega`, `omega_prereq` (saved,
  merged with the furthest status, reset by New Game; `omega_cal` kept over New Game).
- New scripts/17_rando_omega.lua (optional, HELD_BACK from player packages): inventory records by item
  id in `rivet.component(hero, "ItemInventory"...)`; the flag's byte learned from two Omega purchases
  (bytes 0 -> 1, bool in all other records, 0 in at least one; intersection must leave exactly one)
  or `omega_flag_offset`; one-byte write with id re-check and read-back, only for weapons the game
  confirmed; keep pass after loads / resends / every 10 s. Nothing written before the byte is known.
- Simulator: an invented inventory layout, Omega purchases, the worst case "a resend clears the flag".
- Verified only offline: tests/test_v1015.py (32); 536 run, 0 failures, 21 skipped. Older tests changed
  only for the kit version / banner / script list / subscription count. Seeds with omega off checked
  identical to 10.13 against git. docs: OMEGA.md, TEST_REPORT_10.15.md, CHANGELOG, KNOWN_ISSUES 0h,
  TESTING 2-dev5, CONFIGURATION, VERIFICATION_REPORT, INSTALL.txt, 04.
- Open (needs the game, TESTING.md 2-dev5): the inventory component's class name and record layout;
  does an Omega purchase report PurchaseWeaponEvent; does the game honour and save a flag written from
  outside; Omega outside Challenge Mode. Ms. Zurkon's own Omega upgrades are left for sale.

## 2026-11-16: dev 10.13 (kit 10.0.9, generator 10.11.0): Chaos Randomizer

- Asked: a third, independent randomizer (`chaos.lua`): anything can become anything (any enemy or
  boss, any planet, any encounter), no compatibility rules, no progression protection, no
  put-backs. OFF by default, its own key (asked again in chat: "give chaos a shortcut like enemy's /
  bosses"), saved, priority over the Enemy / Boss Randomizers while ON, their behaviour back when
  OFF, their settings untouched. Code integrity kept. Dev repo only; seeds unchanged.
- chaos.lua: key `BACKSPACE` (after 0 - = on the number row; Ctrl: status). It registers with
  16_rando_spawners as a priority client (`role = "any"`, `guards = false`) with its own
  `assign(lvl, slots)`. The pool is this level's templates plus every template seen with Chaos on, on
  any planet (`state.chaos_seen`, cap 1000, kept over New Game), plus 10.12's `spawn_learned`; minus
  learned friendly / mount (not enemies). The seed ranks the pool for each slot, picks avoid
  repeats until the pool is used up, and a slot never keeps its own template.
  `chaos_cross_planet = false` keeps one planet.
- 16_rando_spawners: `SP.priority_client`, `guarded_name` / `SP.guarded_rec` (the watchdogs, the
  retry limit, the wrong-family block and the story boss area put-back skip unguarded slots;
  `SP.revert_guarded` for boss areas), the plan's priority branch (no idle / zone / blocked rule),
  `SP.set(off)` re-plans the others, client hooks `on_census` / `after_restore`, the written record
  pruned of gone nodes after each census (no growth over planets). With Chaos off, behaviour is
  identical: tests/test_v1012.py is unchanged and passes.
- 10: `chaos_randomizer`, `key_chaos`, `chaos_cross_planet`; the status line; chaos optional in the kit
  check. Kit 10.0.9, banner "Randomizer dev 10.13". build_public_release HELD_BACK = chaos.lua;
  validate_release rejects it and counts the kit's scripts instead of a fixed 13.
- Simulator: nodes may belong to one planet (listed only while it is loaded); BACKSPACE key.
- Verified only in the simulator: tests/test_v1013.py (23); 504 run, 0 failures, 21 skipped.
  docs: CHAOS.md (the risks), TEST_REPORT_10.13.md, CHANGELOG, TESTING "2-dev3", KNOWN_ISSUES 0g,
  VERIFICATION_REPORT, CONFIGURATION, INSTALL.txt, 04.
- Open (needs the game): everything of 10.12's list, plus: do other planets' templates spawn (or
  crash)? Do story boss templates spawn from ordinary spawners? Does the game pass BACKSPACE to
  rivet_hook without using it itself? Frame time with every slot written.

## 2026-11-15: dev 10.12 (kit 10.0.8, generator 10.11.0): Enemy Randomizer and Boss Randomizer

- Asked: an Enemy Randomizer (`enemy.lua`) and a Boss Randomizer (`boss.lua`), separate and
  independently switchable in the game, both OFF by default and saved; the top priority is that
  randomized enemies and bosses never stall progression (doors, objectives, arena exits, cutscenes,
  multi-enemy encounters, boss phases). Implement, not only investigate. Dev repo only (the public
  release repo is untouched). Seeds unchanged (generator not touched).
- Research (static, no game): neptuwunium/rivet's DDL dump (docs/ddl/rcra_ddl.json, Types/*.cs).
  Combat encounters spawn through `SpawnerScriptAction` nodes (vtable in dev(vtables).lua):
  `SpawnerScriptActionPrius` = FactoryGroup +8, Templates +32 (List of 8-byte actor refs),
  SpawnLocations +56, 8 flags +76..83, NumSpawns +108, MaxSimultaneousSpawns +112, MaxActivations +128,
  OnNumDeadTrigger +132. The node counts its spawns and dead and fires its outputs; encounter
  completion is the node's, not the enemy type's. Events: SpawnerStartedEvent/StoppedEvent
  {SpawnerComponentHandle}, SpawnerSpawnEvent {SpawnedHandle, SpawnIndex}, BotDeathCompleteEvent,
  HealthBarShowEvent {IsFriendly}, BossPhaseChangeEvent. Bot components GameBot* (turret, flyers,
  swarmers, shooters, large) and story bosses BossBot* / GameBotSargassoCentipedeBoss with their own
  script actions (BossChaseController, BossCentipedeGetPilotActor, FinaleBoss*). Calibration: round 13's
  probe shows AddToInventoryAction's ItemConfig at +0x58 (Prius +16), so script-node fields start near
  +0x48..0x50: SpawnerScriptAction's FactoryGroup is expected at +0x50 (preferred, not trusted).
- Design: change only the Templates ids of nodes that have not started; the node itself spawns,
  counts and completes (no deletion, no own spawning, no output fired, no mission write). Templates
  are learned (rivet.component on the spawned actor) before they are used or replaced; same planet,
  same tier, same family; story bosses / friendlies / unclear classes never. Boss tier is permuted.
  Safety nets only put back (spawn timeout 20 s, stuck 180 s, 3 loads, wrong family, story boss
  areas). Layout found per node by signature (ambiguous -> skipped).
- New: scripts/16_rando_spawners.lua (shared layer), scripts/enemy.lua (`-`), scripts/boss.lua (`=`);
  all optional in the kit check. 10: settings enemy_randomizer / boss_randomizer (false), key_enemies,
  key_bosses, spawner_runtime; R.subscribe; frame call; status line; New Game keeps the switches and
  state.spawn_learned / spawn_blocked; restore hook (a choice before the restore wins). 14: checkpoints
  passed on. 04 documents them. Kit 10.0.8 (every RANDO_FILES tag, C/H/TT versions, build_data,
  build_public_release BUILD and OPTIONAL list), banner "Randomizer dev 10.12".
- Simulator: tests/sim/rivet_sim.lua models spawner nodes (DDL layout, Templates read at each spawn,
  dead count, "all dead" -> objective + door), spawned bots' components, health bars, checkpoint
  reloads that keep or renew nodes. ALL SIMULATED.
- Verified only offline: tests/test_v1012.py (32); 481 run, 0 failures, 21 skipped (as before). Older
  tests changed only where the file list (16 release scripts), the kit version or the banner changed.
  big_batch not re-run (generator unchanged). docs: ENEMIES_AND_BOSSES.md, TEST_REPORT_10.12.md,
  CHANGELOG, TESTING (gameplay plan "2-dev2"), KNOWN_ISSUES 0f, VERIFICATION_REPORT, CONFIGURATION.
- Open (needs the game, TESTING.md 2-dev2 / ENEMIES_AND_BOSSES.md section 7): does the signature find
  Templates (census line)? Do spawned actors answer rivet.component with GameBot* classes (learning)?
  The events' real field names (SenderHandle of a spawn = node component or actor?). Does a write
  before the node starts change what it spawns? Encounter completion with replacements; frame time.

## 2026-11-15: dev 10.11 (kit 10.0.7, generator 10.11.0): planet shuffle starts new planets at their intro

- Asked: make planet shuffle really work: new Coordinates -> fly to the new planet -> its intro plays
  and its first mission starts; players reach Coordinates and first visits first, not revisits. Dev
  repo only (the public release repo is untouched). From now on every dev update adds 0.01 to the
  file names (this one: 10.11).
- Cause found in the code (no new log): the hub started a planet's story only after the planet-menu
  landing, then warped on the planet to a pad or a learned checkpoint; the game had played its arrival
  without the story. Blizar's entry was the intact pad, but round 17 shows the game's own menu landing
  for MIS_BLIZAR on the destroyed one. A planet whose Coordinates came before its first visit's
  needs (Viceron before the Hurlshot) was listed as a "revisit" with nothing to play.
- Log evidence used (tests/data): the game makes the next visits active at a visit's end, before the
  menu is used (round 17 lines 1019-1028: MIS_SAV_01, MIS_BLIZAR 0 -> 2; round 16 line 384:
  MIS_ZURK_01_VISIT_01), and its menu then lands at CHK_SAV_01_LANDING / CHK_BLIZAR_B_LANDINGPAD_DESTROYED
  (round 17 lines 1065, 1113). Sargasso's arrival: the first checkpoint after CHK_TRANSITION_TO_SARG is
  hash 2498464355 in rounds 16 and 23 (name not found by a 3-token brute force over the known name
  parts; 2999919277 = CHK_SARG_01_CAVE_ENTRANCE, 100598178 = CHK_SAV_01_START,
  1343868918 = CHK_MALINON_INTRO_NEFCITY, 696621431 = CHK_NEFCITY_BAZAAR were found on the way).
- 15 (kit 10.0.7): H.prime_open / prime_one (between stories, every open planet's next visit made
  active, not the planet you are on); H.on_access (grant hook in 10); planet-menu landings
  (`launch_dest(d, why, { landed = true })`: an active story is left to the game's arrival, a story
  started there loads the intro); H.load_point puts a first visit's intro first while its story is at
  its first step; watch_story reloads at the intro (H.INTRO_STUCK_WAIT); H.first_visit_block keeps
  blocked first visits out of the revisits and sends you back from the menu with H.reason_text;
  hub_follow_new plays the game's own trip to an open first visit. New options hub_prime_open,
  hub_planet_intro, hub_follow_new, hub_blocked_home (all true).
- 03: `intros` per visit, C.OPENINGS.sargasso_1, C.hub_available orders first visits before revisits,
  C.hub_why; the placement rules C.progression_spot_ok / C.coords_spot_ok / C.done_at.
- 02 (generator 10.11.0): coords_first_visit = true: G.spot_ok / G.filter_spots in both fills and the
  early Coordinates; constrained Coordinates placed first (G.constrained_last); exceptions recorded in
  the hub plan; audit check. Every seed changes.
- Verified only offline and in the simulator: tests/test_v1011.py (20); 449 run, 0 failures, 21
  skipped; big_batch 56,600/56,600 valid (with the independent first-visit check on every hub seed).
  The simulator now also lists CHK_SAV_01_START and CHK_MOL_START (your game's names, rounds 24-26).
- Open (needs the game): does a visit the hub made active before the flight land at its intro (the
  game's per-planet landing override is set by its own story scripts; whether a DLL start does it is
  unknown)? If not, the stuck-step reload loads the intro after a minute. Sargasso's arrival scene
  name. The intros only listed by the game (Torren IV, Cordelion, Viceron, the finale).

## 2026-11-15: dev 10.1 (generator 10.1.0, data 5.1.0): Spybots and Lorbs hold items; three weapons are items

- Asked: Spybots and Lorbs were defined as locations but the generator never used them; make them hold
  items. Put the Burst Pistol, Shatterbomb and RYNO 8 into the item pool. Dev repo only (the public
  release repo is untouched); kit stays 10.0.6.
- Data (tools/build_data.py): 10 Spybots, 12 Lorbs on Savali (counts from the guides), `holds = "any"`;
  acquisition `reward` for the three weapons. build_data's kit stamp fixed to 10.0.6 (it wrote 10.0.3).
- 02: `collectibles = true` puts them in the location pool; they stay out of logic (no pickup event
  bound), so only non-progression items or currency go there. Reward-only weapons: always at a
  location, never in the 15 shop slots, never a random start weapon. G.GAME_GIVEN is empty;
  G.DUD_REWARDS keeps the Burst Pistol (the game hands one out anyway) off Gold Bolts, early weapons
  and weapon_logic. Audit and spoiler updated.
- 12 (comment only): Shatterbomb's and RYNO 8's own slots are closed by the existing rule (a slot whose
  weapon the seed gives at a location is closed).
- Verified only offline and in the simulator: tests/test_v101.py (10), 429 run, 0 failures,
  21 skipped; big_batch 56,600/56,600 valid. Test changes where the rules changed: registry counts,
  the independent verifiers (reward-only weapons, collectibles), version strings, round 24's
  fingerprint (every seed changes), two seed-dependent picks, the sphere-1 item floor 5 -> 4 (one of
  200 seeds: 22 more locations share the items).
- Open (needs the game): bind the Spybot and Lorb pickup events (05 `collectible_events`) from a
  rivet.log with discovery on; until then those 22 locations do not pay. Closed Shatterbomb/RYNO
  slots on the real vendor screen. The Burst Pistol reward stays a dud until a starting copy can be
  removed.

## 2026-11-13: Public Release v0.54 (build 10.0.5): planet shuffle on 0, items given back, no stale guard

- Round 26 (v0.53, a restored save continuing on Viceron): no key, no planet menu, yet `the game's
  own story took you to viceron - back to the hub`. The guard after a finish read `h.finished_at`, a
  saved frame of an earlier session. Now this session's frames only.
- The Viceron load replayed no weapon against 15 items given: the save had lost its inventory
  (cause unknown). 09: `G.restore_inventory` sends every known item again (lost ones come back,
  owned ones stay quietly); automatic after hub trips and loads elsewhere when fewer than half of
  the known weapons are reported; `Ctrl+0` twice by hand.
- `0` toggles planet shuffle (state.planet_shuffle_off, saved by the companion, kept over New Game).
  `[` no longer goes home. Banner `Randomizer v0.54 (kit 10.0.5)`. Shop: better reasons, smaller slices.
- tests/test_v054.py (22), round26_rivet.log added. Kit 10.0.5, generator 10.0.2.
- Branch release-v0.54. Details: mod/RiftApartRandomizer/docs/CHANGELOG.md.

## 2026-11-13: Public Release v0.53 (build 10.0.4): the boss fight's shifts find planetary travel off

- Round 25 (v0.52's first run, a restored save at nefcity_1): the city's story ran to
  CHK_NEFCITY_HEAVY_FIGHT. Its rift to Savali (CHK_NEFCITY_HEAVYSHIFT_SAVALI) landed Ratchet with the
  ship on ground that is not there; he fell and died, three shifts in the log.
- The hub had turned the planetary travel byte on and set the level bits on arriving in the city,
  and again after each death reload (the load had cleared them). The game has both off during the
  city's story; the shift was played as a ship landing (inference).
- 15: H.apply_world does nothing while a destination runs; H.take_back_world before the hub's own
  story is launched; on again when the city's story finishes; a quiet return from the story's own
  shifts. Kit 10.0.4, generator 10.0.2.
- tests/test_v053.py (8), round25_rivet.log added; 379 run, 0 failures, 17 skipped.
- Branch release-v0.53. Details: mod/RiftApartRandomizer/docs/CHANGELOG.md.

## 2026-11-13: Public Release v0.52 (build 10.0.3): the city's story starts at its opening scene

- Round 24 (v0.51's first run): the city's story stayed at OBJ_NEFCITY_GO_TO_NEFCITY through six
  warps to CHK_NEFCITY_START. Ratchet could move (bolts picked up), so v0.51's walking fix held.
- Round 23 shows the game's own order: MIS_INTRO complete, MIS_NEFCITY_01 started with
  MIS_NEFCITY_01_TRAINSTATION opened, then the city loaded at checkpoint hash 3046787773 (the
  arrival scene), then CHK_NEFCITY_START.
- Fix (asked for: "teleport to the cutscene of the opening"): prologue first, story and train
  station opened, warp to the opening found by its hash at run time. Seeds unchanged.
- Branch release-v0.52. Details: mod/RiftApartRandomizer/docs/CHANGELOG.md.

## 2026-11-13: Public Release v0.51 (build 10.0.2): the hub is Nefarious City

- Request: hub = Nefarious City; its story must work after the warp; Ratchet could not walk right
  after the warp to the hub.
- Cause found for the walking problem (inferred, not seen in a log of v0.5): the warp fired at
  OBJ_INTRO_PARADE_PICKUP_WRENCH = 2, the frame OBJ_INTRO_GOING_DOWN starts; round 23 shows the game
  ignoring everything sent to the hero until GOING_DOWN finished. With the prologue left active,
  nothing ended that sequence. Fix: wait for it (hub_trigger = "parade"), and end the prologue at
  the hub (as round 17's kit 8.0 did).
- Story: MIS_NEFCITY_01 started before the warp to CHK_NEFCITY_START (the game's own order).
- Branch release-v0.51. Details: mod/RiftApartRandomizer/docs/CHANGELOG.md.

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

## 8.4 (2026-11-12): stabilization after round 20 (no new features)
Round 20 log (8.3, v2.618 install, seed b25846f17df5; ARSENAL_RESTORED loaded by rivet_hook but the
companion answered after the 60 s wait).
- Findings:
  - Torren IV's story never left OBJ_MOL_GO_TO_MOLONOTH;
  - Viceron played as Ratchet with broken lighting; its GO_TO finished only after a full reload;
  - Cordelion and Zurkie's 2 "restarted" but never moved;
  - every hero swap logged "rivet -> ratchet failed: already playing as that hero";
  - "weapon type 1002 ... 1012 is weapon:burst_pistol";
  - shop "only 0 vendor weapon(s) at +0x48" again;
  - "Campaign order is not available yet" from F12.
- The rule the logs support (7 clean cases, rounds 17 and 20): GO_TO finishes when the visit's
  own hero is on the planet (at once on a start there, or on a load with the story active). The
  8.3 rule ("started on the planet") was wrong: round 17's NefCity was started on NefCity, as Rivet.
- 15_rando_hub.lua:
  - H.ensure_hero: rivet.hero_play_as until "already playing as that hero" (rivet_hook
    hero_look.cpp play_as), one job at a time;
  - H.activate confirms the hero before start / force / replay, or while an active story waits at
    GO_TO;
  - H.prime before hub trips and test-travel warps;
  - H.watch_story → H.reload_story (once per destination per session, out to Zurkie's or another
    open planet and back, H.bounce);
  - automatic restart removed (Ctrl+/ twice kept);
  - at_hub / finish swap back to Ratchet only when no trip is being prepared.
- 03_rando_campaign.lua: heroes nefcity_1 ratchet, sargasso_2 rivet, ardolis_1 ratchet, viceron_1
  rivet (wiki plot, gamepressure, thegamer); entries CHK_ZORDOOM_START, CHK_CORD_A_START,
  CHK_ARD_START. The fingerprint does not include the registry: same seeds (test_regression_v83).
- 14_rando_travel.lua:
  - tr.landed holds menu landings only; the landed_v = 2 migration moves older entries to
    tr.test_landed;
  - T.remember_test;
  - score 95 for CHK_<code>_START / _A_START / _0n_START; long *_SHIP names score 30.
- 16_rando_testtravel.lua: entries first, then menu landings, then test landings; H.prime before a warp.
- 09_rando_real.lua:
  - types are learned only from purchases (G.last_bought / G.last_unknown, 90 frames, either
    order) and never during a load burst;
  - late answers come only from a burst with exactly one new type, or from an unclaimed type
    after 90 frames;
  - G.sanitize_types drops duplicates; one type per weapon.
- 12_rando_shop.lua: H.discover_pointers (ItemDatas is List<VendorItemData?>: an array of pointers;
  the 8.3 search found the ids in the slot objects after the pointer array, so idx >= count for all).
- 10_rando_runtime.lua:
  - R.arsenal_in_game (rivet.config(DB.arsenal_marker));
  - no AR timeout for seed = "random";
  - R.kit_check (RANDO_FILES tags in every script, build_data / build_capabilities write them too);
  - story_prime_before_travel, story_reload_stuck (story_restart_stuck retired).
- 11_rando_campaign.lua: D.go is silent in a hub seed or the game's own order.
- rando_give_source/build.sh: /timestamp pinned, so the rebuild equals the shipped DLL byte for byte
  (test_native).
- Sim: hero swap ("already playing", swap_frames, swap_refuse), GO_TO steps (go_to, goto_on_start),
  vendor_pointers layout, the round 19/20 checkpoint names.
- Tests: 318 ran, 0 failed, 17 skipped. New: test_v84.py (31), test_regression_v83.py,
  tests/data/round20_rivet.log. big_batch 43,000/43,000. Strict-globals run: clean.

## Handoff (8.4)
- Round 21 (first full playthrough): TESTING.md section 2.
- Lines to read:
  - RANDO-KIT;
  - "hero: X confirmed", "prime <id>:", "story still waiting", "reload:";
  - RANDO-SHOP "slot objects by pointer";
  - "ARSENAL_RESTORED is installed (the game has ...)".
- If a story with the right hero still stalls at GO_TO, compare its objective name and the
  landing checkpoint: the hero rule may need a planet exception.

## 8.5 (2026-11-12): robustness pass on 8.4 (no new features)
- Task: continuous stabilization of 8.4 across 17 areas, no features, seeds/saves/DLL compatible.
  No round 21 log existed, so the audit read the code for failure, lateness and repetition.
- Found and fixed (tests/test_v85.py, 17 of 20 fail on 8.4):
  - mailbox: a timed-out mission call, an unanswered item, and old-run requests at a New Game stayed
    in rando_give.dll's mailbox and could run later. `G.take_back(req)` sets REQ back to DONE and
    keeps an answer that raced in. Mission calls wait through loads (pump not running, scene not
    ready) up to `D.NATIVE_LOAD_WAIT` = 3600 frames.
  - late companion restore: `R.merge_live` (currency of this session kept, delivery status by rank,
    armor/shop/hub records, armor baseline when the save has none).
  - New Game: hub session record and delivery weapon-type session state cleared; deferred hub
    closures read `H.state()` when they run.
  - shop: `H.helper_missing` (no DLL, dead DLL, < v5) and a vendor never found both compensate.
  - travel: menu landings go through `T.remember`; history capped at `R.HISTORY_KEEP`.
  - companion: a refused save is copied to `.refused-<time>` first.
- Considered and not changed: the armor ring replay (worst case gives the game's own piece); the
  finale name match; collectible counts across a restore (collectibles are retired since 6.0 - a
  fix was written, then removed as dead code); the ~2 s companion save window and game-save reloads
  (documented in KNOWN_ISSUES.md 2: no safe automatic answer).
- Sim: `SIM.mailbox.hold` (helper alive, takes no request), SIMULATED.
- Not possible here: PowerShell 7 (download not allowed to run), so the companion tests stay skipped.

## Handoff (8.5)
- Same round 21 checklist as 8.4 (TESTING.md section 2). New log lines only on failure paths:
  "taken back", "aux request withdrawn", "kept n currency payment(s) from before the restore",
  "given directly (rando_give.dll ...)".
- Next real information can only come from a playthrough log.

## 2026-11-12: 9.0 (no hub; the story starts as in the game)

### Asked for
"Make the new version not have the hub. And start with the prologue then Nefarious City." Uploaded:
the user's edited 01-06 and 09 (their 8.5.2 state: the 8.5.1 `C.MODES` fix, their G.DEFAULTS,
Punk/Reaver owned from the start) and the 8.5 install and dev zips.

### Done
- Baseline commit: the user's scripts over 8.5 (`d921fe7`), then branch `v9`.
- 15_rando_hub.lua deleted; hub presets/settings/options retired with log lines; RANDO_HUB calls
  removed from 10, 11, 14, 16; kit check reports a leftover hub script.
- 03: `C.STORY_START` (leading `arrival = "story"` visits: intro, Nefarious City 1, Sargasso 1)
  begins every order; `random_start` retired; no mode needs `new_game_init`.
- 02: generator 9.0.0, format 9, RA9; audit checks the story start; spoiler STORY START line.
- 04: the user's file without hub lines, `preset = "balanced"`; their values and comments kept.
- `build_data.py` now reproduces the user's 01 (it reverted Punk/Reaver when re-run).
- Tests: test_v90 (20); harness pins CLASSIC_TEST_SETTINGS (preset-aware) for the older suites;
  hub tests and the 8.3/8.4 seed-identity regressions removed. 293 tests, 0 failures, 17 skipped.
  big_batch: 41,000/41,000 valid.

### Open
- Nothing of 9.0 has run in the game. Round 23: the TESTING.md checklist.
- The Punk/Reaver armor sources (6 filler-only locations from 8.5.2) probably never pay.

## 2026-11-13: 10.0 (hub start, working planet shuffle, spread rewards, closed shop slots)

### Asked for
The update spec "Functional Planet Shuffle, Mission Selection & Improved Item Pool" (attachment.txt):
- Planet shuffle on by default and actually working.
- A hub start with three choices: the prologue at its real start, the Battle Arena, Nefarious City at its real beginning.
- Meaningful early rewards, with weapons spread out.
- Earnable weapons out of the shop.
- No softlocks.
- Offline and in-game results kept apart.

Uploaded: the round 23 rivet.log and the 9.0 dev and install zips.

### Round 23 findings
- Planet shuffle never ran in 9.0. The director waits for capability lines ("verified") that no build ever wrote.
- `CheckpointTriggeredEvent.CheckpointHash` is the engine's CRC-32: poly 0xEDB88320, start value 0xEDB88320, no final xor. It equals `rivet.hash`.
- Hashing every catalog name showed the game loads Nefarious City's story at `CHK_NEFCITY_START` (2052464476), not at `CHK_NEFCITY_SHIP` (the 8.x landing that stuck at GO_TO in rounds 17 and 22).
- Prologue end order (lines 695-729):
  - Ratchet is on Ardolis when `MIS_INTRO` turns 4.
  - Only then does the game start `MIS_NEFCITY_01` itself and rift to Nefarious City.
  - The first checkpoint there is an unnamed one (3046787773), then `CHK_NEFCITY_START`.
- The shop search overran its frame budget again.

### Done
- 15_rando_hub.lua (new):
  - New Game warps to Zurkie's at the parade's wrench, with the prologue left active and the parade checkpoint remembered.
  - Three start choices.
  - A mission ladder using the DLL calls verified in round 17.
  - Warps to real start checkpoints.
  - A same-planet reload if a story stays at "go to".
  - The planet menu and revisits.
  - `[ORDER KEPT]`: the game's own follow-on travel is undone.
  - After round 23's prologue order, the warp home waits for the new planet's first loaded checkpoint, or `ORDER_KEPT_WAIT`, before going. A launch cancels it.
  - 14 now forwards unnamed checkpoints to the hub too.
- 02/03, generator 10.0:
  - Hub plan with fixpoint reach.
  - Coordinates open planets.
  - Spread fill: early weapons first, one sphere-1 Coordinates, progression, then a proportional fill.
  - Shop split with closed slots.
  - No ARSENAL_RESTORED weapon sold.
  - RA10 share codes.
  - Audit and spoiler sections.
- 12:
  - Closed vendor slots (Burst Pistol id); duplicate listings closed.
  - Fast parsing; smaller chunks.
  - A budget error halves the chunk instead of counting as a try.
- 14: checkpoint names from hashes (`RANDO-CHECKPOINT`).
- Tests:
  - test_v100 (39 tests: an independent sphere-walk verifier, hub start, prologue end order, planet shuffle, campaigns, checkpoint names, shop, real-log replays).
  - The older suites are pinned with `PRE10_SETTINGS`.
  - 332 tests, 0 failures, 17 skipped.
  - big_batch: 56,600 of 56,600 valid.

### Open (needs the game: TESTING.md round 24)
- Every hub step has run only in the simulator. The key test: Nefarious City from the hub at `CHK_NEFCITY_START`.
- The warp home right after the prologue's rift (while the city's opening plays).
- Closed shop slots on the real vendor screen, and the search within budget.
- Not done:
  - Spybots as locations (their pickup event was never seen).
  - Real Gold Bolts as rewards or shop items (no verified grant).
  - Shop weapon slots are closed rather than refilled with gadgets or armor.
