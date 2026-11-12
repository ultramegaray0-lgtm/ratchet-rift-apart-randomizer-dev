# Campaign randomization (experimental; unchanged since 3.2)

> **8.0:** the Zurkie's hub (HUB.md, RESEARCH_8.0.md) builds on the mission-system findings here and adds the saved-state write (rando_give.dll v6). The 3.x director and lab below are unchanged.

> **7.0 note.** The playable campaign randomizer in 7.0 is **locked levels** (LEVELS.md): each
> planet's travel needs its Coordinates, and the story keeps the game's mission order. This page
> covers the older experiment of reordering the missions themselves, which your game's mission
> system does not allow (below). 7.0 renamed its presets (`campaign` is now locked levels; the old
> one is `mission_shuffle`) and proves every reordered seed finishable in the game's own order too.
> 7.0 also decoded `UnlockLevelAction` from the round 15 dump: it flips a bit of a 10-bit mask, not
> a planet's story (RESEARCH.md).

> **4.0 note.** Nothing on this page is needed to play. The default presets play the game's own
> story order with randomized items (DESIGN.md). The campaign presets below still generate and
> prove reordered campaigns, but in your game they fall back to the game's order until the
> tests here verify mission control. Round 15 showed why that is hard: in your game's mission
> system nothing opens a mission except the game's own scripts.

The campaign layer randomizes the **order of the campaign**: which planet visit comes next,
where the revisits fall, and (in two modes) where you start. Each seed proves that its order
can be finished. This page explains how the game runs its story, what the randomizer does with
it, what has been verified and what has not, and the exact obstacles.

**The short version:**

- Campaign orders are generated and proven finishable for every seed. This is tested offline
  on 10,000+ seeds with two independent checkers.
- **Rounds 14-15 (2026-11-11)** settled how the game's mission system works, from dumps of your
  game's own code:
  - Your game runs the *second* of the two mission systems in the exe ("system 2"). The one 3.1
    targeted is empty there.
  - In system 2, the game's own actions can **start a mission the game has made available**,
    **complete an active one**, and **replay** one.
  - **They cannot make a mission available.** `MakeMissionAvailableAction` does nothing at all
    in system 2.
- So with the game's own actions, the randomizer can start a visit **only once the game itself
  has opened it**. A truly reordered campaign needs one more piece: understanding what opens a
  mission in system 2. That is research the next tests collect, including what *replay* does
  to a locked mission.
- Following the order in the game needs three abilities:
  - starting the next visit (`mission_control`);
  - travelling there (`travel`);
  - for a random start, finishing the intro (`new_game_init`).
- 3.2 can **ask the game** for every mission's state. This is read-only, through
  rando_give.dll v4. None of the three abilities has been seen working yet.
- Until they are verified, a campaign seed is played in the game's own order. Its randomized
  rewards still work, and the randomizer says so clearly. It never changes the story with an
  untested method.

## How the game runs its story (what is known)

| Fact | Source |
|---|---|
| The whole game is **one level** (`i29`) made of regions. Planets are regions; about 860 checkpoints | **game** (rivet_hook `level.regions/checkpoints`, earlier rounds) |
| A planet's story content lives in **overlay regions** that load according to the save's **mission state**. Overlays cannot be loaded by hand | **game** (earlier rounds: a warp onto an unreached planet loads it without its story) |
| Missions are named by **strings** (`MIS_INTRO`, `MIS_ZURK_01_VISIT_01`, `MIS_SARG_02_REVISIT_SHIPS`, ...) | **game** (round 14: level-script mission variables are typed `string`; devstats and MissionStateChanged events) |
| Every mission action has **two branches**, chosen by a byte at RVA `0x6925FA8`. **System 1:** a manager at RVA `0x68DD510` with a mission table and a state array. **System 2:** a manager at RVA `0x68EA390`, where missions are **components on level actors** | **exe code** (round 14 dump) |
| **Your game runs system 2:** the system 1 manager pointer is NULL | **game** (round 15: Dump-GameCode read `0x0`; the 3.1 reader found "no mission manager") |
| System 2: `h = Lookup(mgr2, hash)` (RVA `0x1A44CB0`), `state = State(mgr2, h)` (`0x1A44E70`), `obj = Component(Resolve(h), h.component)` (`0x1185DA0`, `0x1184B50`). **Start:** if state == 1 and `obj->vt[0xD0]()`, then `obj->vt[0xD8]()`. This is shared by StartMissionAction and SetMissionActiveAction. **Complete:** if state == 3, `obj->vt[0xF0]()`. **Replay:** `obj->vt[0x108](flag, 1)`. **Make available:** nothing at all | **exe code** (handlers of all five actions) |
| The engine hash is CRC-32 with start value `0xEDB88320` and no final xor, the same as `rivet.hash` | **exe code** + **game** (matches MIS_INTRO = 1000115474, MIS_RYNO_PLANS, MIS_HAX_DEFAULT) |
| States as the actions use them: start needs 1, complete needs 3 and sets 4. 0 counts as locked. A running intro reported 2 | **exe code** (handlers); 2 from the game's event |
| The game does **not** report mission states when you load a save; its events report the boot defaults (intro running) once | **game** (round 14 log) |
| `StartMissionAction` / `MakeMissionAvailableAction` nodes were **not loaded** on Nefarious City, Zurkie's or Corson V | **game** (round 14: `script.nodes` and the lab scan found 0) |
| Travel: rivet_hook's `level.fly` (the ship's landing) and `level.warp` (moves the hero **and the save's checkpoint**) | rivet_hook documentation. `fly` is untested in your game |

There is **no "load mission X" function** to call. The story moves when the scripts already
placed in the level run these actions. So 3.0 drives the story the same way the game does: it
borrows a loaded `MakeMissionAvailableAction`/`StartMissionAction` node, gives it the mission
it should act on, and signals it.

## The registry: 14 planet visits

A **visit** is a continuous stretch of the story on one planet. Missions inside a visit stay
together, because their scripts hand over to each other directly. The randomizer moves whole
visits.

| # (vanilla) | Visit | Missions | Hero | Needs | Gives | Source |
|---|---|---|---|---|---|---|
| 1 | corson_intro | MIS_INTRO | Ratchet | | | game |
| 2 | nefcity_1 | MIS_NEFCITY_01 | Rivet | | Phantom Dash | game |
| 3 | sargasso_1 | MIS_SARG_01_FIRST_VISIT, MIS_SARG_01_CLANKPUZZLE | Rivet | | | game |
| 4 | scarstu_1 | MIS_ZURK_01_VISIT_01 | Ratchet | | | game (round 14) |
| 5 | savali_1 | MIS_SAV_01 | Ratchet | | | game |
| 6 | blizar_1 | MIS_BLIZAR_01 | Rivet | | | dag |
| 7 | torren_1 | MIS_MOL_01_FIRST_VISIT | Rivet | Hoverboots | Hurlshot | game (round 14) |
| 8 | cordelion_1 | MIS_CORD_01_FIRST_VISIT, MIS_CORD_BOSS | Ratchet | | | game (round 14) + dag |
| 9 | scarstu_2 | MIS_ZURK_02, MIS_ZURK_02B_VISIT_02B | Rivet | after scarstu_1 | | game (round 14) + guide |
| 10 | ardolis_1 | MIS_ARD_01_FIRST_VISIT | Rivet | Hoverboots | | game (round 14) |
| 11 | sargasso_2 | MIS_SARG_02_REVISIT, MIS_SARG_02_REVISIT_SHIPS | Ratchet | after sargasso_1 | | game (round 14) + dag |
| 12 | savali_2 | MIS_SVALI_02_SECOND_VISIT | Ratchet | after savali_1 | | game (round 14) |
| 13 | viceron_1 | MIS_ZORD_01 | Ratchet | Phantom Dash, Hurlshot | | dag |
| 14 | finale | MIS_MEGA_01_RIVET, MIS_MEGA_FINALE | Ratchet | always last | | dag |

"guide" means the name follows the dag pattern, and the visit follows the published mission
list (gamepressure's list of all missions). A visit may list more than one name. The director
uses the first and the last name that the game's mission table actually holds, so a guessed name
that doesn't exist does no harm. Lab Ctrl+F12 lists which names exist, and
`tools/build_campaign_registry.py` turns a research zip into
`scripts/07_rando_campaign_registry.lua`.

## Modes (`campaign_mode`)

| Mode | Preset | What changes |
|---|---|---|
| `vanilla` | standard, coordinates, chaos (and the aliases extended, armor, classic) | the game's order (2.0 behaviour) |
| `planet_shuffle` | planet_shuffle | the planets' first visits are shuffled; each revisit comes after its planet's first visit |
| `mission_shuffle` | campaign | every visit, including revisits, goes anywhere the rules allow |
| `full` (+ `random_start`) | full_campaign | mission shuffle with a random first visit |
| `chaos` | campaign_chaos | full, with the widest start choice |

These rules always hold:

- the finale is last;
- a revisit comes after its first visit;
- Phantom Dash and Hurlshot (story abilities) come before Viceron;
- the intro is first unless the start is random.

## How the solver uses the order

- A location belongs to the visit that contains it, and is in logic only once that visit is
  reachable.
- A visit is reachable when every earlier visit in the order is finished, its gadgets are owned
  and (with planet locks) its Coordinates are owned.
- The starting Coordinates are those of the first planets in the order.
- Gadgets a visit needs that the randomizer won't hand out (for example, gadgets off) are given
  at the start.
- Weapon tiers follow your position in the campaign, not the vanilla planet number.
- A seed whose order can't be finished is rejected and generated again. The 2.0 fallbacks (a
  smaller shop, lighter weapon logic, more starting Coordinates) apply, and each one is listed
  in the spoiler.

## What the runtime does (`11_rando_campaign.lua`)

1. **Asking** (read-only). Through rando_give.dll v4, the runtime asks the game for a mission's
   state with the same two calls the actions make first. Once per session it logs
   `RANDO-CAMPAIGN mission system 2: MIS_INTRO is ...`.
2. **Capabilities.** `06_rando_capabilities.lua` says which changes have been verified in your
   game. The kit ships with all of them `false`.
3. **Not verified** (the state of this kit): F9 shows `campaign <mode>: not available yet
   (missing mission_control, travel)`. F12 says the same. You play the game's own order, and
   every randomized reward works as in 2.0.
   - This stays finishable. An independent checker replays 6,000 campaign seeds in the game's
     own order (`verify_fallback` in tests/test_campaign.py): every reward and every Coordinates
     item is still paid out.
4. **Verified:**
   - Every two seconds, the director asks about the current visit's missions. When the last
     one is complete (4), it announces the next visit.
   - **F12** starts that visit's first mission, **if the game has opened it** (state 1). It
     then flies you there.
   - If the game hasn't opened it, F12 says so (`... is not open in your game yet`) and
     changes nothing.
5. **Random start, with `new_game_init` verified:** on a new game, once the intro is active
   (3), the randomizer finishes `MIS_INTRO` the way `CompleteMissionAction` does, and passes
   over its later slot.
6. **Progress** is saved by the companion with the rest of the seed's progress.

## Obstacles

1. **No make-available in your game's mission system.** The game alone opens missions. Until
   it's known what opens a mission in system 2, the randomizer can only follow an order whose
   next visit the game has already opened.
   - In Rift Apart that is the game's own order, plus the few points where several planets are
     open at once.
   - Next research:
     - the mission component's functions, whose code the lab now writes into rivet.log;
     - the `+0x1B0` state machine behind `State()`;
     - what **replay** does to a locked mission (lab test 2).
2. **What START does** (state 2? the story loading?) is what lab test 2 shows.
3. **State 2.** The running intro reported 2, and *complete* needs 3. Lab test 3 shows whether
   the intro reaches 3.
4. **The vanilla hand-off still runs**, so you may see the game's own next mission marker.
5. **Hero switching:** whether starting a mission this way switches Ratchet/Rivet is
   unverified.
6. **Warping moves the save's checkpoint.** F12 flies first; warp is the fallback.
7. **Grants that can't be made** (from 2.0, unchanged): armor is tracked rather than added, and
   health and upgrade items are not randomized.

## The in-game tests

Back up your save folder first. Tests 2 and 3 change the story of the save they run on, so
use a **spare save slot**, or a copy. Install the 3.2 files, **including the new
rando_give.dll (v4)**, and turn test mode on (`extras\test_mode\07_rando_testmode.lua` into
`scripts`).

| # | Test | Time | Changes anything? |
|---|---|---|---|
| 1 | Load any save, stand on a planet, press **Ctrl+F12** and wait 3 s. Then run `companion\research\Research-Campaign.bat` | 4 min | no (only asks) |
| 2 | A spare save **past the intro**: press **Ctrl+F11**. The lab asks every mission, then: if a visit is open (1), it starts it; if none is, it tries *start* and then *replay* on the next locked visit. 2 s later it flies there. Note which character you are, whether the planet's story is there, and what the HUD said | 5 min | yes: the spare save's story |
| 3 | **New Game** in a spare slot. As soon as you control Ratchet in the parade, press **Ctrl+F11**. If the HUD says the intro isn't active yet, play a minute more and press it again | 5 min | yes: the spare save's story |

Send back `rivet.log` after the tests, and the `campaign_research_<date>.zip` from test 1.
The lines that matter start with `RANDO-LAB`:

- `RANDO-LAB mission X <state> (system 2)` is what the game answered for each mission name;
- `RANDO-LAB VERIFIED read (N missions answered, system 2)`;
- `RANDO-LAB VERIFIED native start|complete|replay (mission X went a -> b)` means that action
  changed the state;
- `RANDO-LAB NO EFFECT ...` means it didn't, with the game's reason;
- `RANDO-LAB code slot 0x.. rva 0x.. <bytes>` is the mission component's code, for the next
  research step;
- `RANDO-LAB VERIFIED travel CHK_... (fly)`.

From these:

```
python tools/build_capabilities.py rivet.log                       # -> scripts/06_rando_capabilities.lua
python tools/build_campaign_registry.py campaign_research_X.zip    # -> scripts/07_rando_campaign_registry.lua
```

Copy the files into `<game>\scripts`. Start and travel verified → F12 follows the campaign
wherever the game has opened the next visit.
