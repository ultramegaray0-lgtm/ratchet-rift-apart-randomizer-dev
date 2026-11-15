# The hub and planet shuffle (10.0)

This is the player guide for 10.0's default mode (`hub = true`). The technical notes are at the end.

> **v0.51 (build 10.0.2): the hub is Nefarious City.** A new game goes there once the parade has
> handed Ratchet back after his wrench, with the city's story started (loaded at
> CHK_NEFCITY_START); the prologue is written complete there (`hub_prologue = "keep"` leaves it as
> a destination). Where this guide says Zurkie's as the hub, read Nefarious City; the Battle Arena
> is an ordinary destination now. See CHANGELOG.md, 10.0.2.
>
> **v0.52 (build 10.0.3): the city loads at its opening scene.** Round 24 showed the story never
> leaving "go to Nefarious City" at CHK_NEFCITY_START. The hub now ends the prologue first, starts
> the story with its train-station mission, and warps to the checkpoint the game itself loads after
> the prologue (hash 3046787773, named at run time). See CHANGELOG.md, 10.0.3.
>
> **v0.53 (build 10.0.4): the boss fight's shifts.** Round 25: the city's boss fight rifts Ratchet
> to Savali or Sargasso, and with the hub's planetary travel on the game played them as ship
> landings (Ratchet fell to his death). The travel byte and the level bits are now left to the game
> while a destination runs, and go on again when none is running. See CHANGELOG.md, 10.0.4.
>
> **v0.54 (build 10.0.5): planet shuffle on `0`, items given back.** `0` switches planet shuffle
> off and on (saved with the randomizer state): off, the hub and the levels lock leave travel,
> levels and stories to the game; items stay randomized. `[` no longer goes back to the hub (it only
> cancels the automatic return). After the hub's own trips and loads elsewhere, an emptied
> inventory is sent again; `Ctrl+0` twice does it by hand. A load on another planet is no longer
> taken for the game's own story travel in a later session (round 26). See CHANGELOG.md, 10.0.5.

> **Dev 10.11 (kit 10.0.7, generator 10.11.0): a new planet starts at its intro.** When Coordinates
> arrive (and whenever no story runs: at the hub, after a finish), the next visit of every open
> planet is made active, as the game does when a visit ends; the ship's flight then lands the way the
> game's own arrival does and the first mission starts there, with nothing loaded again. A landing
> whose story was not active yet starts it and loads the visit's **intro** (Savali:
> CHK_SAV_01_LANDING, Blizar: the destroyed pad, Sargasso: its arrival scene by hash, ...). A planet
> whose first visit still waits for another visit (Viceron before Torren IV's Hurlshot) sends you
> back with the reason and is never offered as a revisit; `]` lists first visits before revisits.
> The game's own trip to a planet whose first visit is open (Nefarious City's end → Sargasso) is
> played there. Seeds: Coordinates are never on a revisit or the finale, and always where their
> planet's first visit can be played at once (Viceron's at Torren IV's story). See CHANGELOG.md.

**Nothing of 10.0 has run in your game yet.** `VERIFICATION_REPORT.md` separates what your logs have
shown from what has only passed offline tests.

## How a run goes

1. **New Game.** The parade on Corson V starts as usual (a new save always starts there). When Ratchet
   picks up his wrench, the randomizer takes him to **Zurkie's Battleplex**: the hub.
2. **Choose your first mission** at Zurkie's. `]` shows the next choice, `Ctrl+]` goes:
   1. **Prologue: the parade on Corson V.** It carries on from the checkpoint the parade had reached
      when you left. The prologue is still running in your save, so this works the way loading a
      save there does.
   2. **Battle Arena: Zurkie's Battleplex.** Zurkie's first visit (`MIS_ZURK_01_VISIT_01`, Ratchet):
      meeting Zurkon, the arena's intro and its first challenges.
   3. **Nefarious City.** `MIS_NEFCITY_01` (Ratchet), loaded at `CHK_NEFCITY_START`, where the game
      itself loads the city's story.
3. **Planet shuffle.** Every other planet opens when you hold its **Coordinates**. Coordinates are
   items of your seed, so they can be at any location: a Gold Bolt, a story mission, a side activity
   or an armor pod. A destination also opens only once the visits it depends on are done (Sargasso's
   second visit after its first, Viceron after Phantom Dash and the Hurlshot, and so on), and the
   **finale** opens last, after everything else. The solver proves that every seed can be finished,
   in whatever order you choose.
4. **Finishing a destination** pays its story-mission and side-activity rewards and lists what is
   newly open. After `hub_return_delay` seconds (12) you are back at Zurkie's. Press `[` to stay
   longer. If the game's own story moves you somewhere first (Nefarious City → Sargasso, the
   prologue → Nefarious City), you are brought back to Zurkie's from there, so the game's linear
   order never takes over. With `hub_follow_story = true` you carry on instead, when that
   destination is open anyway.
5. **The ship's planet menu** works as well. Landing on a planet whose Coordinates you lack sends you
   back to Zurkie's. Landing on an open planet starts its next destination.
6. **Revisits.** Once a planet's destinations are done, or none is open yet, it shows up in the `]`
   list as "revisit": you travel there with no story, to pick up Gold Bolts, armor and the rest.

## Keys

| Key | Does |
|---|---|
| `]` / `Ctrl+]` | next destination / go (before the hub has started: go to Zurkie's) |
| `[` twice | back to Zurkie's (once: cancel an automatic return) |
| `Ctrl+[` twice | finish this destination by hand (recorded in the history) |
| `/` | start the story of the planet you are on |
| `;` | status |

The old F keys work too while `legacy_f_keys` is on: F6 is `]`, F5 is `[`, F4 is `/`.

## If a destination will not start

The hub logs every step as `RANDO-HUB`. A launch does this, in order:

1. **Hero.** The visit's hero is set and confirmed (`hero: X confirmed`).
2. **Mission.** The mission is asked from the game and then:
   - active: left as it is;
   - available: started;
   - inactive: "available" is written into its save record, then it is started (`made available`,
     `start`);
   - complete: the destination counts as finished;
   - refused: the replay call is tried, otherwise you explore (`explore`).
3. **Trip.** A warp to where the mission really begins, or the ship / a warp to the landing pad when
   that is not known yet.
4. **First step.** If the story is still at its first "go to <planet>" step 20 s later, that
   checkpoint (or the other load point) is loaded once more.
5. **Hand finish.** If nothing helps, `Ctrl+[` twice finishes the destination by hand, so the
   campaign never blocks.

## Rewards, shop and Gold Bolts (also 10.0)

- **Rewards are spread** (`distribution = "spread"`): items are shared out over Gold Bolts, story
  missions, side activities and armor pods in proportion to their number. At least `early_weapons`
  (2) weapons and one Coordinates are where the start alone can reach.
- **Gold Bolts stay real Gold Bolts.** Picking one up counts in the game as always; the randomizer
  adds that location's reward (an item, or Bolts/Raritanium). The randomizer never hands out a fake
  Gold Bolt: it has no verified way to grant a real one (`KNOWN_ISSUES.md`).
- **Shop vs rewards** (`shop_weapons = 8`): Ms. Zurkon sells 8 different weapons. Her other 7 normal
  slots are closed, and those weapons are rewards instead. A weapon at the start or at a location is
  never for sale. ARSENAL_RESTORED's weapons are always rewards, and the slots its vendor adds for
  them are closed. A closed slot shows the Burst Pistol, which every save owns, so nothing can be
  bought there.

## Settings

Seed settings (`04_rando_settings.lua`; they change the seed):

| Setting | Default | |
|---|---|---|
| `hub` | `true` | `false`: 9.0's story start (prologue → Nefarious City → Sargasso) |
| `distribution` | `"spread"` | `"goldbolts_first"`: 4.0-9.0's fill |
| `shop_weapons` | `8` | 0-15 |
| `early_weapons` | `2` | 0-6 |

A hub seed always uses Coordinates and locked travel (`planet_locks`, `travel_lock`), and its order is
the hub's own (`campaign_mode` is ignored, with a note).

In-game options: `hub_runtime`, `hub_trigger` (`"wrench"`), `hub_force_missions`, `hub_replay`,
`hub_levels`, `hub_travel_flag`, `hub_fly`, `hub_auto_return`, `hub_return_delay`, `hub_hero_swap`,
`hub_follow_story`, `key_hub`, `key_hub_return`, `key_story`, `key_shuffle`, `restore_inventory`,
`shop_close_slots`
(`CONFIGURATION.md`).

## Technical notes: what each step rests on

| Step | Evidence | Status |
|---|---|---|
| Warp to `CHK_ZURK_00_DEFAULT` at the wrench | Round 17 (kit 8.0): landed on Zurkie's | seen in game |
| Inactive mission → available → start → active | Round 17: `MIS_NEFCITY_01`, `MIS_ZURK_01_VISIT_01` (played to completion), `MIS_ZURK_02B` | seen in game |
| Travel flag + level bits 1-10 | Round 17: the menu then offered Blizar and Savali | seen in game |
| Hero swap confirmation | 8.4 rule from round 20 | not seen working yet |
| Nefarious City starts at `CHK_NEFCITY_START` | Rounds 16 and 23: with `MIS_NEFCITY_01` active the game loaded hash 2052464476 = CRC-32("CHK_NEFCITY_START"). 8.x landed at `CHK_NEFCITY_SHIP` and the story stayed at `OBJ_NEFCITY_GO_TO_NEFCITY` (rounds 17, 22) | inferred from logs; the hub's warp there is untested |
| Arena starts at `CHK_ZURK_00_DEFAULT` | Round 23: the planet menu's own landing for `MIS_ZURK_01_VISIT_01`; round 17 played the visit from there | inferred |
| Prologue resumes at the parade's checkpoint | The prologue stays active; warping to its last checkpoint is what a save load does. Round 23: hash 934271974 at the wrench | untested |
| The game's follow-on travel undone | Rounds 17/19: warps from any planet work | untested in this role |
| Checkpoint names from hashes | 29 listed names match hashes in rounds 13-23 | verified offline against real logs |
| Learned starts | The first checkpoint a destination's mission triggers on its planet | untested |

The simulator (`tests/sim/rivet_sim.lua`) models these rules, and `tests/test_v100.py` plays whole
campaigns in it. It is not the game.
