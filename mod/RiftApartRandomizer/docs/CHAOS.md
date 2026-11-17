# Chaos Randomizer (dev 10.13, kit 10.0.9): EVERYTHING CAN BECOME ANYTHING

> **STATUS (dev 10.24, kit 10.0.17): NOT WORKING IN THE GAME.** No enemy or boss has ever been replaced in your game.
> The switches below load and toggle, but the spawner layer has never read an encounter (see KNOWN_ISSUES 0p).
> A developer experiment, `dev(spawnproof).lua`, is trying to prove one replacement first (TESTING.md 2-dev11).

> **READ THIS BEFORE SWITCHING IT ON.** Chaos has **no protection of any kind**. A door may never
> open, an objective may never finish, a boss may be impossible to beat, an enemy may spawn inside a
> wall or not at all, and a run may become impossible to finish. That is the design. Nothing on
> this page has run in the game yet: the game may also behave in ways no test predicted.

| | Enemy Randomizer | Boss Randomizer | **Chaos Randomizer** |
|---|---|---|---|
| File | `enemy.lua` | `boss.lua` | `chaos.lua` |
| Key | `-` | `=` | **`BACKSPACE`** |
| Replaces | regular enemies | boss-tier enemies | **every enemy and boss** |
| With | same family, same planet | same family, same planet, permuted | **anything seen on any planet** |
| Story bosses | never | never | **yes, both ways** |
| Safety nets | all (ENEMIES_AND_BOSSES.md section 5) | all | **none** |
| Default | OFF | OFF | OFF |

## 1. Switching it

- **`BACKSPACE`**: Chaos ON / OFF. The screen says `CHAOS RANDOMIZER: ON` or `OFF`, with what it
  means for the other two.
- **`Ctrl+BACKSPACE`**: what Chaos changed on this planet, its pool (how many templates, how many
  from other planets) and the other two randomizers' state.
- The status line says `CHAOS ON (N changed here, pool P; enemy/boss randomizers paused)`.
- The choice is saved (`state.chaos_rando`, through the companion, like `0`, `-` and `=`) and kept
  over a New Game. A choice made before the companion's restore wins over the save's.
- Settings in 04 (runtime only, they never change the seed): `chaos_randomizer = false` (the start
  of a save that never used the key), `key_chaos = "BACKSPACE"`, `chaos_cross_planet = true`.
- **Stuck?** Press `BACKSPACE` (Chaos OFF: the original enemies come back at once), then load the
  last checkpoint from the pause menu. The encounter is then the game's own again (or the Enemy /
  Boss Randomizer's, if those are on).

## 2. Priority over the Enemy and Boss Randomizers

- While Chaos is ON it owns **every** spawner slot. The Enemy and Boss Randomizers change nothing;
  whatever they had changed is replaced by Chaos's own pick.
- Their own ON / OFF settings are **never changed** by Chaos. Their keys still switch their settings
  while Chaos is on (it just has no effect until Chaos is off).
- When Chaos goes OFF, every slot it changed goes back to the original enemy, and the Enemy and Boss
  Randomizers plan again from their own settings. Their usual rules then apply, so an encounter that
  started while Chaos was on keeps its original enemies (they never change a running one).

## 3. What can become what

**The pool** is every enemy template the game used in a spawner node:
- on this planet;
- on **every planet visited with Chaos on** in this save (`state.chaos_seen`, up to 1000 templates,
  kept over New Game);
- every template 10.12 learned (`state.spawn_learned`).

`chaos_cross_planet = false` limits the pool to this planet's own templates.

**Included, in both directions:** regular enemies, elites, flyers, ground bots, turrets, large
enemies, mini-bosses, bosses with health bars, **story boss templates** (if a spawner uses them),
unclassified templates (nothing has to be learned first), hazards and the classes 10.12 leaves out
as unclear (`PoolShark`, `MrFunGuy`, `Telepathipus`). So a ground bot can become a giant boss, a boss a
regular enemy, a flyer a turret, a turret a boss, and enemies of one planet appear on another.

**Each slot gets its own pick.** One encounter's enemies become different enemies. Across a level, a
template is used again only once every template in the pool has been used once. A slot never keeps
its own template when anything else exists.

**Picks come from the seed.** The same seed, the same planets seen and the same spawners give the
same chaos. Another seed gives another. As the pool grows (new planets), a pick changes only when
the new template outranks the old one for that slot.

## 4. What Chaos does NOT do (on purpose)

As asked, none of 10.12's protections apply to Chaos:
- no same-type, same-size, same-tier, same-planet or same-encounter rule;
- no compatibility check of any kind;
- no 20 s spawn timeout and no 3-minute stuck check;
- no death / reload limit;
- no story boss protection: story boss areas are not put back, and story boss templates are used
  and replaced;
- no family check of what a replacement turned out to be (it is only learned);
- no "not started yet" rule: an encounter already running is changed for its next spawns;
- no automatic put-back of anything, ever (`state.spawn_blocked` is not used);
- nothing that triggers or repairs progression. Doors, objectives, boss defeats and cutscenes follow
  only from the game's own encounter logic, if they follow at all.

## 5. What stays (code integrity, not gameplay protection)

- Only template ids the game itself used in a spawner node are written. Chaos never makes up an id.
- A write goes only into a node that is still the same live instance, only over the id read there,
  and it is read back. A refused write is not repeated.
- The Templates list is found by its layout's signature (ENEMIES_AND_BOSSES.md section 6). A node
  that does not match is never written.
- A Templates list that two nodes share is not written. Its two encounters could no longer be told
  apart, so it could not be put back when Chaos goes off. It is rare and is named in rivet.log.
- Templates the game has shown to be friendly bots or mounts are left out of the pool and keep their
  own spawners. They are not enemies, and Chaos takes control of enemies and bosses only. A template
  not learned yet is never left out.
- The record of what Chaos wrote is pruned when its nodes are gone (another planet), so it does not
  grow. The plan and the put-back stay within a 3 ms frame budget.

## 6. Risks to expect (all accepted by switching Chaos on)

- **Encounters that never complete.** A replacement that cannot spawn, reach the player, be damaged
  or die leaves its encounter waiting forever: the door stays shut.
- **Bosses that cannot be beaten,** or a boss fight's own scripts waiting for a boss that is not
  there. Defeat sequences and cutscenes may not play.
- **Enemies in the wrong place:** flyers on the ground, large bots in small rooms, turrets on nav
  meshes, enemies inside geometry or falling through the map.
- **Templates from other planets.** Dev 10.18: a Templates entry is a TUID, the uid of a template actor
  the level has loaded (rivet DDL). Another planet's template is now used only where its template actor
  is loaded here (`rivet.find_uid`, checked once per level); one that is not loaded could never spawn.
  An older rivet_hook without `rivet.find_uid` keeps 10.13's behaviour. `chaos_cross_planet = false`
  still limits the pool to this planet's own templates.
- **Clank puzzles and other spawner-driven non-combat scripts** may use templates Chaos has not
  learned as friendly yet, and break.
- **Performance:** many large enemies at once.

## 7. Not in a player package

`chaos.lua` is in the development kit only. `tools/build_public_release.py` holds it back
(`HELD_BACK`), and `release_tools/validate_release.py` fails a package that contains it.
