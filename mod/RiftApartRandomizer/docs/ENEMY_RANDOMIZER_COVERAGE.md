# Enemy Randomizer coverage (dev 10.30, kit 10.0.19)

Every enemy the real game has shown in a log (rounds 31-40, `python tools/enemy_census.py`), the spawning mechanisms,
and what is done for each. Dev 10.30: a spawn is no longer taken as proof - a replacement is used only when the game has
shown it can be KILLED there (see "Combat compatibility"). Statuses mean exactly one thing each:

| Status | Meaning |
|---|---|
| **COMBAT-VERIFIED** | dev 10.30: a real log shows the replacement spawned in its place AND dying / its fight completing (the only pairs `enemy_compat = "verified"` uses) |
| **REJECTED** | dev 10.30: in-game evidence that the replacement does not die there (or the same direction): never used |
| **IN-GAME VERIFIED** | a real rivet.log shows the game spawning the replacement in its place (`VERIFY ... REPLACEMENT SPAWNED`) - spawning only, not fighting |
| **AUTOMATED TESTED** | the production code does it in the simulator (tests/test_v1027-v1030); nothing more |
| **IMPLEMENTED** | the code handles it; no test names it and no log shows it |
| **PARTIALLY SUPPORTED** | handled in some situations only (the column says which) |
| **UNSUPPORTED** | the randomizer cannot change it; the reason is given |
| **PROTECTED** | deliberately never changed and never used as a replacement |

## How an enemy is replaced (all mechanisms share one engine)

A spawner spawns the template actor held by one of its **script variables**. Before the spawner runs, the randomizer
writes another enemy's template into that variable (16_rando_spawners.lua, section SP.V; rando_give.dll v7). The game's
own spawner then spawns, counts and completes the encounter. A replacement must be a template **loaded on the current
level** - the game cannot spawn an actor whose template is not loaded, and rivet_hook has no way to load one.

| Mechanism | Variable | Tie spawn -> spawner | Status |
|---|---|---|---|
| Factory spawner (SunsetSpawnerFactory; arena waves, most ordinary fights) | `Templates` | SpawnFactory field of the event | **IN-GAME VERIFIED** spawning (round37: 6/6; round38: 11/11; round39: 3/3; round40: 8/9, 1 ignored); fighting: per pair, see "Combat compatibility" |
| Single-enemy node spawner (SpawnerScriptAction) | `Template` (one actor) | spawn point index (`Location` variable, round39) | AUTOMATED TESTED (changed 0 times in the game so far: round38-39 never tied a node spawn - fixed in 10.29) |
| Group node spawner (robomutt / thug / mixed waves) | `Template` holding an actor GROUP | spawn point index (group `Location`, expanded by rivet.script_node) | AUTOMATED TESTED; first run learns the members, later runs change; not yet seen in the game |
| Delayed / scripted / repeated encounter spawns | the same spawners as above (the event comes when they run) | same | covered by the rows above |
| Checkpoint retries, repeated encounters | the same variables, put back on every load and changed again | - | IN-GAME VERIFIED (round38-39: put back OK on every checkpoint, re-armed with the same pick) |
| Amoeboid split children, projectiles (wasp shots), anything a bot spawns itself | none (SpawnLocation 0, no spawner) | - | **UNSUPPORTED**: no spawner variable exists; the parent is randomized instead |
| Enemies placed in the level (no spawner) | none | - | **UNSUPPORTED**: nothing to write before they exist; rivet_hook cannot spawn or swap actors |
| "Direct spawn calls" by game code | - | - | none seen in any log: every enemy creation the game reported came as a SpawnerSpawnEvent of a factory or node |

## Combat compatibility (dev 10.30)

Round40: the randomizer logged every A1 replacement as a success, yet the pirate robot shooters a bladeball factory
spawned could not be killed (8 of 8 replaced shooters had no death in run 1, 7 of 8 in run 2; every other replacement
died). So a replacement is now a PAIR - spawner kind | original kind > replacement kind - and `enemy_compat`
(04_rando_settings.lua) decides which pairs are used:

| Pair (kinds as the game's cut names / family) | Status | Evidence |
|---|---|---|
| factory: Pirate Robot Shooter > Pirate Robot Brawler | **COMBAT-VERIFIED** | round37: 20/20, A1 completed twice; round40: replaced brawlers died, A1 completed twice |
| factory: Pirate Robot Shooter > Pirate Bladeball | **COMBAT-VERIFIED** | round38-40 spawned in A1, A1 completed; round40: they died |
| factory: Pirate Bladeball > Pirate Robot Brawler | **COMBAT-VERIFIED** | round38-40 spawned in A1, A1 completed; round40: they died |
| factory: Pirate Bladeball > Pirate Robot Shooter | **REJECTED** | round40: unkillable (your report; 15 of 16 never died) |
| factory: Pirate Robot Brawler > Pirate Robot Shooter | **REJECTED** (by rule) | the same direction (melee swarmer factory -> shooter); round40: the game ignored it once |
| every other pair (thugs, Sargasso, Cordelion, all node / group spawners, every boss-tier pair) | unverified | no real log shows one dying: NOT used with "verified" |

- `"verified"` (default): only COMBAT-VERIFIED pairs (built in above, or verified in your own game - kept in the save).
- `"trial"`: also unverified pairs of the SAME bot class, one spawner per level at a time, watched. The first death of
  one of its bots verifies the pair for your save (`COMBAT VERIFIED`); a bot alive 45 s after its spawn while 6 other
  bots died rejects it (`COMBAT CHECK FAILED`), puts its spawners back at once and says so in the corner.
- `"any"`: 10.29's rules, not safe (only the simulator tests of the scheduling use it).
- Every replaced bot in every mode is watched the same way; the initialization check also rejects a pair whose bot
  spawns without a component the game's own enemies of that kind have.
- What is NOT known: why the shooter from a bladeball factory cannot die (the swarmer slot's spawn / entrance, or the
  one template actor every shooter replacement clones). CHANGED lines name the template now, so a future log can tell.

## Enemies seen in the real game

Identity = the actor asset name (dev(spawnprobe) round31-39; 10.29 reads it for every spawn), bot class from the DDL.

| Enemy (game name -> display) | Class / family | Planet | Spawn mechanism | Replacement supported | Automated tested | In-game verified |
|---|---|---|---|---|---|---|
| enm_pirate_robot_shooter -> Pirate Robot Shooter | GameBotShooter / ground | Zurkon | factory | replaced: **COMBAT-VERIFIED** (-> brawler, -> bladeball); as a replacement: **REJECTED** (round40: unkillable from a bladeball factory) | AUTOMATED TESTED | replaced: round37-40; as replacement it spawned (round38, round40) but could not be killed (round40) |
| enm_pirate_robot_melee -> Pirate Robot Brawler | GameBotMeleeSwarmer / swarmer | Zurkon | factory, group node | as a replacement: **COMBAT-VERIFIED** (for robot shooter and bladeball factories); replaced: only by verified pairs (none yet) | AUTOMATED TESTED | as replacement round37-40 (died in round40) |
| enm_pirate_bladeball -> Pirate Bladeball | GameBotMeleeSwarmer / swarmer | Zurkon | factory, group node | replaced: **COMBAT-VERIFIED** (-> brawler); -> robot shooter **REJECTED**; as a replacement for robot shooter factories: **COMBAT-VERIFIED** | AUTOMATED TESTED | both ways round38-40 |
| enm_thugs4less_shooter (ground) -> Goons-4-Less Shooter | GameBotShooter / ground | Zurkon, Sargasso | factory, group node | IMPLEMENTED | AUTOMATED TESTED | changed in round38-39, never spawned while changed: not verified |
| enm_thugs4less_shooter (jetpack) -> Goons-4-Less Jetpack | GameBotShooterJetPack / flyer | Zurkon, Sargasso | factory | IMPLEMENTED (flyer) | AUTOMATED TESTED (told apart from the ground thug) | **IN-GAME VERIFIED** replaced: round38 BBE9 jetpack thug -> wasp |
| enm_thugs4less_melee -> Goons-4-Less Brawler | GameBotMeleeSwarmer / swarmer | Zurkon | group node | PARTIALLY SUPPORTED: replaced through its group; never a replacement (no single-actor variable holds it) | AUTOMATED TESTED | no |
| enm_thugs4less_robomutt -> Goons-4-Less Robomutt | GameBotMeleeSwarmer / swarmer | Zurkon | group node | PARTIALLY SUPPORTED: as above | AUTOMATED TESTED | no |
| enm_indigenous_wasp -> Sargasso Wasp | GameBotShooterJetPack / flyer | Sargasso | factory, node | IMPLEMENTED (flyer) | AUTOMATED TESTED | **IN-GAME VERIFIED** as replacement (round38, 3 wasps) |
| enm_indigenous_hornedtoad -> Sargasso Horned Toad | GameBotMeleeSwarmerJumper / swarmer | Sargasso | factory | IMPLEMENTED | AUTOMATED TESTED | changed, never spawned while changed: not verified |
| enm_amoeboid_small/medium/large_ps4 -> Amoeboid | GameBotAmoeboid / swarmer | Cordelion | factory (+ split children) | PARTIALLY SUPPORTED: replaced by another species only; sizes never replace each other (10.29) | AUTOMATED TESTED | size swaps verified in round39 (now disabled on purpose) |
| enm_indigenous_grunthor -> Grunthor | GameBotGrunthor / large (boss tier) | Sargasso | factory | IMPLEMENTED for the Boss Randomizer (`=`) - needs a second boss-tier kind on the same level; never for `-` | AUTOMATED TESTED (boss tier with boss tier only) | no (Sargasso showed no other boss-tier kind) |
| enm_seabase_boss | BossBotUnderwaterBaseJuice / story boss | Cordelion | node | **PROTECTED** (story boss) | AUTOMATED TESTED (never changed) | protected in round39 |
| enm_indigenous_poolshark -> Pool Shark | GameBotPoolShark / unclear | Cordelion | factory | **PROTECTED** (hazard; behaviour unclear) | - | protected in round39 |
| burrower_beetle | GameBotMountBeetle / mount | Sargasso, Zurkon | node | **PROTECTED** (a mount you ride) | - | protected in round38 |
| npc_* (civilians, miners, vendors, helper bots, Zurkon jr.) | NPCBot / friendly | all | factory, node | **PROTECTED** | AUTOMATED TESTED (pub NPC factories untouched) | protected in every round |

## Enemy classes the game's DDL defines but no log has shown yet

These are handled by their bot class the moment a spawner spawns them (role and movement group from
SP.FAMILY_CLASSES). Status for all: **IMPLEMENTED** by class, not tested by name, not seen in the game.

- Regular enemies (role "enemy"): turrets (GameBotShooterTurret), flyers (GameBotMeleeSwarmerGroundFlyer, GameBotMeleeFlier,
  GameBotShooterNymphFlyer, GameBotShooterHeli, GameBotDarterBat, GameBotShooterBlargSaucer, GameBotShooterBlargBomber),
  swarmers (GameBotMeleeSwarmerBurrower), ground (GameBotShooterExtermibot, GameBotShooterConstructorBot,
  GameBotShooterMrsZurkonMinion, GameBotMeleeBase, GameBotShooterBase).
- Boss tier (role "boss", `=` only): GameBotMeleeLarge, GameBotTankBase, GameBotDoom, GameBotMangler,
  GameBotShooterArmoredTransport; and any regular kind that showed a health bar.
- PROTECTED: story bosses (BossBotCordelionNefarious, BossBotNefariousBlimp, BossBotNefariousFinale,
  BossBotUnderwaterBaseJuice, BossBotZordoomMonster, GameBotSargassoCentipedeBoss, BossBase), friendlies (Clank lemmings,
  sheep, test dummies, non-firing shooters, Infobots, NPCBot), mounts, and the unclear classes (BotHexapod,
  GameBotPufferFish, GameBotPoolShark, GameBotMrFunGuy, GameBotTelepathipus).
- A bot with none of these classes is logged once ("spawned actor not classified") and left alone.

## Bosses

| Boss | Can be randomized? | Why |
|---|---|---|
| The 8 story bosses (Nefarious blimp, Seekerpede, Francois' arena fight, the Fixer chase, Cordelion boss, Zordoom warden, the Juice / seabase boss, Emperor Nefarious) | **PROTECTED** | their fights are scripted around one specific actor (BossBot* classes, boss script actions, phase managers); another actor would not run those phases. Their checkpoint areas also put every change back (story boss area). |
| Boss-tier bots of ordinary encounters (Grunthor, large melee bots, tanks, Dooms, Manglers, armored transports, health-bar enemies) | **IMPLEMENTED, not combat-verified** (`=` Boss Randomizer, same engine) | swapped only with another boss-tier kind of the same movement group loaded on the same level; never with a regular enemy, never by `-`. Dev 10.30: like every pair it needs in-game proof that the replacement dies - none exists (round40: "0 boss spawner(s) changed here"; no level so far showed two boss-tier kinds), so with `enemy_compat = "verified"` it changes nothing; a "trial" round can prove a pair. |
| Minibosses as regular enemies / regular enemies as minibosses | **PROTECTED** | a health-bar enemy where a regular one is expected (or the reverse) changes an encounter's difficulty and pacing; not offered. |

## Why "the enemies were the same" (round39) and what 10.29 changes

1. The pool is what the level has loaded. On Zurkon's arena that is pirates and thugs; on Sargasso wasps, toads and
   thugs; on Cordelion amoeboids. 10.28 picked among them by hash only: pirates became other pirates, small amoeboids
   large ones. **10.29 picks another species whenever the level has one** (a pirate becomes a thug) and never a size
   variant of the same creature.
2. Changes were made too late. 10.28 searched node records for every ambient spawn (513 in one Zurkon visit); the
   arena's factories spawned before they were planned. **10.29 ties spawns by their spawn point in one lookup**, skips
   spawners known to make no enemy, and picks again for a changed spawner that has not spawned when a new kind is learned.
3. Nothing told you. **10.29 shows a corner note for every changed spawner's first spawn** ("[ENEMY RANDOMIZER] SUCCESS -
   Original: Pirate Robot Shooter -> Replacement: Goons-4-Less Shooter"; `enemy_notify = false` turns it off), logs a
   `SPAWN ...` line for every enemy spawn with the reason when it kept its enemy, and Ctrl+`-` says "N of M enemy
   spawns here were replaced".

## Limits that need the game (not solvable in the scripts alone)

- **First wave of a kind the save has never seen**: template actors never answer before a spawn (0 of >100 asks,
  round38-39), so the first spawn of a new kind on a new save is original; afterwards the save knows it by uid.
- **Cross-planet enemies**: a template must be loaded on the level. Loading another planet's actor needs a game
  function rivet_hook does not expose.
- **Thug brawlers and robomutts as replacements**: they exist only inside group variables (no single-actor variable
  holds their template), so they can be replaced but not used as a replacement.
