# Enemy Randomizer and Boss Randomizer (dev 10.12, kit 10.0.8)

> dev 10.13: a third, separate feature, the **Chaos Randomizer** (`chaos.lua`, BACKSPACE), has none of the
> rules and safety nets below and **takes priority over both while ON** (their settings are kept, they
> resume when it is OFF). See CHAOS.md.

**Nothing on this page has run in the game yet.** The code, the layout it searches for and the
simulator's encounter model come from the game's type data (neptuwunium/rivet's DDL dump,
`SpawnerScriptActionPrius` and the bot components). Section 7 lists what the first real round has to
confirm.

## 1. Files

| File | What it is | Without it |
|---|---|---|
| `scripts/16_rando_spawners.lua` | The shared layer: reads the level's spawner nodes, learns what each enemy template is, writes and puts back template ids, and runs the safety nets. It does nothing unless a feature below is ON. | `enemy.lua` and `boss.lua` log "16_rando_spawners.lua is not installed" and stay off. Nothing else changes. |
| `scripts/enemy.lua` | The **Enemy Randomizer**: regular enemies (turrets, flyers, swarmers, ground bots). Its key, status line and switch. | No enemy randomization. Bosses still work. |
| `scripts/boss.lua` | The **Boss Randomizer**: boss-tier enemies (large bots, and spawned enemies with their own boss health bar). Its key, status line, switch and the list of story bosses that are never changed (`RANDO_BOSS.STORY`). | No boss randomization. Enemies still work. |

All three are optional in the kit check (`R.OPTIONAL_FILES`) and carry the kit version (10.0.8).
They load after the numbered scripts (rivet_hook loads in name order: digits before letters).
None of them is a developer file; the developer files are still only `dev(name).lua`.

Changes elsewhere, all small: `10_rando_runtime.lua` (settings, `R.subscribe`, the frame call, the
status line, New Game keeps the switches, the restore hook, the kit's optional files),
`14_rando_travel.lua` (every checkpoint is passed on), `04_rando_settings.lua` (documented settings).

## 2. In the game

| Key | |
|---|---|
| `-` | Enemy Randomizer ON / OFF |
| `=` | Boss Randomizer ON / OFF |
| `Ctrl+-` / `Ctrl+=` | what that feature changed on this planet, how many enemy types it knows, how many encounters it put back |

- Both are **ON by default in the private dev kit**. Each key changes only its own feature.
- The choice is saved in the randomizer's save (`state.enemy_rando`, `state.boss_rando`, through the
  companion, like planet shuffle's `0`), and kept over a New Game. A choice made before the
  companion's restore wins over the save's.
- **ON** takes effect for encounters that have not started yet (a running encounter is never changed).
  **OFF** puts every enemy that feature changed back at once (a big level over a few frames), even in
  the middle of an encounter: the node's remaining spawns are the originals.
- No Lua file has to be edited. The settings below only decide the start of a save that never used
  the keys.

## 3. Settings (04_rando_settings.lua; runtime only, they never change the seed)

| Setting | Default | |
|---|---|---|
| `enemy_randomizer` | `true` in the dev kit | the Enemy Randomizer's start for a save without a choice |
| `boss_randomizer` | `true` in the dev kit | the Boss Randomizer's start for a save without a choice |
| `key_enemies` | `"-"` | its key (any key name the other key settings accept) |
| `key_bosses` | `"="` | its key |
| `spawner_runtime` | `true` | `false`: neither feature changes anything, whatever the keys say |

**Presets.** The presets (`balanced`, `full`, `chaos`, `everything`, ...) are seed settings; these
two are per-save switches that do not change the seed. The private dev kit starts both ON so they can be tested immediately. The in-game keys can turn either
one OFF, and that choice is saved. The public player release is not changed by this dev-only default.

## 4. How an enemy is replaced, and why progression keeps working

The game's combat encounters spawn their enemies with **SpawnerScriptAction** nodes in the level's
scripts. Such a node holds a list of actor templates (`Templates`), its spawn points, how many to
spawn, how many may be alive, and a dead-count trigger. It spawns, puts its spawns into its actor
group, counts their deaths and fires its own outputs ("all dead", "num dead"), which the level's
scripts wire to doors, objectives, the next wave and the story.

The randomizer changes **only the 8-byte template ids in that list**, in memory, before the node
runs. It never deletes an enemy, never spawns one, never fires a node output and never writes a
mission, objective or flag. So:

| Requirement | How it holds |
|---|---|
| Doors open, arenas unlock, objectives finish, the story advances | The encounter's own node fires its own outputs when **its own** count says so. The level's wiring is untouched. |
| No controller waits for an enemy that is not there | Nothing is deleted. The node spawned the replacement itself and tracks it like the original. |
| Never early | The randomizer sends nothing. The node completes when the last spawned enemy dies. |
| Multi-enemy encounters | The node's count covers every spawn. Tested with 3 spawns: 2 dead = still running, the 3rd = complete, once. |
| Boss phases | A story boss's phases are its own scripts (never changed). A boss-tier spawn has one death, counted by its node. `BossPhaseChangeEvent` is only logged. |
| No duplicate completion | Only the game completes anything, and only once. |
| Checkpoints, deaths, reloads | After every load the level's spawners are read again. A node that survived the load is recognised (the session remembers each write, so its original is never lost). A node made anew gets the same pick again (the choice depends only on the seed, the node and the pool). |

### Compatible replacements only
- **Same level**: a replacement must be a template that one of this level's own spawner nodes
  uses, so its assets are loaded where it spawns.
- **Same tier and family**: each template is classified from the bot component of an actor the game
  itself spawned from it (`SP.FAMILY_CLASSES`): `turret`, `flyer`, `swarmer`, `ground` (Enemy
  Randomizer), `large` or any family with a boss health bar (Boss Randomizer). A flyer only becomes a
  flyer, a turret a turret, so an enemy is not put where it cannot move or fight.
- **Never touched**: story bosses (`BossBot*`, `GameBotSargassoCentipedeBoss`, `BossBase`),
  friendlies (`GameBotClankLemming`, `...Sheep`, `...TestDummy`, `...NoFiring`, `NPCInfobot`),
  mounts, hazards, classes whose purpose is unclear from the data (`PoolShark`, `MrFunGuy`,
  `Telepathipus`), and every template not learned yet.
- **Same spawn points**: the node's own spawn locations, nav snapping and line-of-sight rules apply
  to the replacement, so it appears where the original would.
- **Boss tier**: each level's boss-tier templates of one family are **permuted** (a derangement of
  the ranked list). A boss that appeared once appears once, as another boss; none is added.

### Learning
A template is used or replaced only after the game spawned it once and the randomizer saw what it is.
So on a fresh save the first encounters of a planet are the game's own; as enemy types are seen, the
other encounters that have not started yet are changed (`plan (learned while playing)` in rivet.log).
What was learned is saved (`state.spawn_learned`, at most 600 templates) and kept over New Game.

## 5. Safety nets (each one only puts an encounter BACK)

| Trigger | Action |
|---|---|
| A changed node starts and spawns nothing for 20 s (`SP.SPAWN_TIMEOUT`) | put back; kept original for this seed |
| A changed node's enemies stay alive 180 s without one death (`SP.STUCK_SECONDS`) | put back and kept; on screen: load the last checkpoint if an enemy cannot be reached |
| A checkpoint is loaded 3 times while a changed encounter was running (`SP.DEATH_LIMIT`: deaths, reloads) | put back and kept; on screen |
| The replacement turns out to be another family than planned | put back and kept |
| You enter a story boss area (a checkpoint with `BOSS`, `FINALE`, `HEAVY_FIGHT` or `CHASE` in its name) | every change put back while you are there; changes resume when you leave |
| A write is refused, reads back wrong, or the node changed under it | that slot is left alone (and the level read again) |
| Two nodes share one Templates list | never changed (one write would change two encounters) |

Kept-original encounters are saved in `state.spawn_blocked` (at most 300) and listed in the history
(`[SPAWNER KEPT ORIGINAL]`).

## 6. Finding the Templates list without trusting an offset

`SP.find_layout` searches the node's first 0x100 bytes for the DDL layout of
`SpawnerScriptActionPrius` (FactoryGroup +8, Templates +32, SpawnLocations +56): three dynamic
arrays `{ pointer, count, capacity }` 24 bytes apart, the two selection enums below 16, the eight
flag bytes 0 or 1, and sane NumSpawns / MaxSimultaneousSpawns / MaxActivations. Zero-filled memory
can make a place 24 bytes off look the same, so if several places match, the one with spawn locations
and no factories wins, then +0x50 (where AddToInventoryAction's first field is in your game). A node
that does not match is skipped and named in rivet.log; nothing is written to it. `census N` lines
report how many nodes were read and at which offsets.

Frame budget: the census reads 2 nodes per frame; writes and put-backs stop after 3 ms and continue
next frame; asking a spawned actor for its components (about 90 calls) happens once per template and
once per changed node.

## 7. What the first real round must confirm (rivet.log)

1. `RANDO-SPAWNERS census 1 (...): N spawner node(s) read ... layout +0x50 xN`. If every node is
   `skipped`, the layout is different in memory: send the log, nothing was changed.
2. `RANDO-DISCOVER SpawnerSpawnEvent ...`, `SpawnerStartedEvent`, `BotDeathCompleteEvent`,
   `HealthBarShowEvent`: their field names (`SenderHandle`, `SpawnedHandle`, `SpawnerComponentHandle`,
   `IsFriendly`) and whether `SenderHandle` of a spawn is the node's component or actor.
3. `RANDO-SPAWNERS learned <id> = <family>`: does `rivet.component(spawned actor, "GameBotShooter")`
   answer? If no template is ever learned, nothing is ever randomized (safe, but the feature is idle).
4. `plan (...): N slot(s) changed`, then the encounter: do the new enemies appear, fight, die, and
   does the door / objective / wave follow? Watch for `put back ... kept so:` lines.
5. A death in a changed encounter, a checkpoint reload, a planet change and a return.

## 8. Known limitations

- Only SpawnerScriptAction encounters are randomized. Enemies placed directly in a level, actor
  spawners (`SpawnerBot*`, `GameSpawnerObject`), proximity spawns and crowd spawners keep their
  enemies.
- **Story bosses are never randomized** (see `boss.lua`): their fights are boss-specific scripts and
  arenas, so per the request they are left unchanged rather than risk progression.
- A fresh save randomizes nothing until enemy types have been seen once; a planet whose encounters
  all use one type per family has nothing to swap.
- The Boss Randomizer needs at least two boss-tier types of one family on a planet.
- The family classes and the boss-area checkpoint words are a reading of the DDL names, not of play.
- Difficulty can change: a weak ground bot can become a strong one of the same family.
