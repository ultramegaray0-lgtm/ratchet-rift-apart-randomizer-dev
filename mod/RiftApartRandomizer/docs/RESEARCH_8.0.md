# Randomizer 8.0: technical research report

What was investigated for the Zurkie's Battleplex hub, where each answer comes from, and which
approach 8.0 implements. **Nothing in 8.0 has run in your game yet.** Every finding is marked by its
source:

- **game**: your rivet.logs (rounds 13-16) or your code dumps (rounds 14/15, `tests/data`);
- **exe**: disassembly of those dumps;
- **DDL**: the engine's own type definitions (neptuwunium/rivet, `Rivet.DDL.RCRA`, 8,211 types);
- **rivet_hook**: rivet_hook 2.0.1's source and docs.

Inference is called inference.

## 1. How a new game starts

| Question | Finding | Source |
|---|---|---|
| How is the initial level selected? | The whole game is one level (`i29`) made of regions; every planet is a region. A new game doesn't choose a level, it chooses a **spawn checkpoint**. | rivet_hook (`travel.hpp`, docs "Travel"), game (earlier rounds) |
| How is the initial spawn point chosen? | The built mission graph (`MissionGraphBuiltGame`, `InitMissionGraphNodeGameDef`) carries **`NewGameLoadInfo`**, an `ObjectiveLoadInfo`: `SpawnCheckpoint`, `DimensionCheckpoint`, `SpawnAsHero`, `LightingMode`, `SpawnLoadout`, `ChallengeSpawnLoadout`, `BackpackLoadout`. Every mission and objective node has the same block for "loading directly into this mission/objective state". | DDL (`MissionGraphBuiltGame.cs`, `ObjectiveLoadInfo.cs`) |
| How is the inventory initialized? | By that `SpawnLoadout` (an item loadout config) and the backpack (`ClankPackLoadoutConfig`). The Burst Pistol is owned on a fresh save. | DDL; game (round 14) |
| How are mission and campaign state initialized? | Each mission node has saved data, `MissionSaveDataShared`: `MissionState`, `MissionFlagsShared`, `MissionDataStore`, `CompletedCount`, `SyncOutputState`. A mission is **Inactive** until its prerequisites in the mission graph are met (the enum's own description). The graph's logic nodes are `And`, `Or`, `InputCount`, `Not`, `GlobalSaveTable`, `XOr` start/end and `Debug`/`Demo` chains. Each mission node has `AllowAvailable` and `UnlockBehavior` (`Available` / `Start`). At boot the game reports MIS_INTRO as **2 (Active)** and the Zurkie's cups as **1 (Available)**. | DDL (`MissionGraphSharedDef`, `MissionNodeBuiltShared`, `MissionNodeSharedDef`, `MissionStates`); game (rounds 13-15, first lines) |
| What does the new-game sequence look like? | `OBJ_INTRO_PROLOGUE` 2, `OBJ_INTRO_PARADE_START_CINE` 1, Corson V ("Malinon") loads, then `START_CINE` 2, `PARADE_START` 1/2, `PICKUP_WRENCH` 1/2, `GOING_DOWN` 1, `VELDIN_*`, `HALL_OF_HEROES_*`. This sequence appears on a new game and never on a save load. | game (round 14 lines 193-214, round 15 lines 171-235, round 13 loads only) |
| How is Zurkie's Battleplex loaded? | Like any planet: by a checkpoint warp into its region. The ship's planet menu sends `DestinationCheckpointName = CHK_ZURK_00_DEFAULT` with the tunnel `CHK_TRANSITION_TO_ZURKIES`. Other checkpoints seen: `CHK_ZURK_LANDING_SHIP`. The planet event name is `Zurkon`. | game (round 14 line 171; rounds 13/16) |
| Can the Battleplex be a New Game destination directly? | **Not by changing the start data at run time.** `NewGameLoadInfo` is a string in the built mission graph asset. That asset isn't a loaded config (`rivet.config_set` only writes numbers), and rivet_hook refuses string writes. Changing it means replacing the mission graph asset with a `.stage` (Overstrike), which needs that asset from your game files plus a DDL writer. Neither is available to this build. | DDL, rivet_hook docs (Configs, Prius fields) |
| So how does 8.0 do it? | At run time: the parade starts as always. Once Ratchet has his wrench (`OBJ_INTRO_PARADE_PICKUP_WRENCH` = 2), rivet_hook's checkpoint warp takes him to `CHK_ZURK_00_DEFAULT`. The warp is the engine's own checkpoint warp, which level scripts use, and it keeps the hero. The save's current checkpoint moves with it. MIS_INTRO is then written as Complete Finished in its save record (below), so the save no longer holds an active prologue. If the parade comes back on a load, the runtime warps to Zurkie's again. | implementation (`15_rando_hub.lua`) |

**Not assumed:** that loading Zurkie's initializes the campaign. It doesn't. Story overlays follow
mission state (rivet_hook docs: the custom overlay system loads them "while the save's mission
state calls for them"). That is why 8.0 handles mission state separately (section 3).

## 2. Coordinates and planet travel

| Question | Finding | Source |
|---|---|---|
| What does the ship's travel do? | The planet menu hands the ship's level-script listener (`OnPlanetMenuRTTEventAction`) two names and fires its accept output. The ship takes off, plays the tunnel and warps to the destination. `rivet.fly(destination)` does exactly that with any destination, when a ship listener is loaded near the hero. | rivet_hook (`travel.cpp`: `SHIP_VAR_TUNNEL 0x136b3eab`, `SHIP_VAR_DESTINATION 0x41f2d10d`, `SHIP_OUT_ACCEPT 0x482fae17`) |
| What decides which planets the menu offers? | Unknown. Two candidates were decoded: **`UnlockLevelAction`** (handler RVA 0x89DA00) sets or clears bit *n* (n = 1..10) of the u32 at global RVA 0x5161238 + 0x30 (`SetBit` RVA 0x89C1E0; `IsLevelUnlockedAction` tests it, RVA 0x89C140). The same global has a second mask at +0x2C and a number at +0x20. There are 10 levels, and the model has 10 planets (inference: the menu's planets). **`SetPlanetaryTravelAction`** (RVA 0x607500) stores one byte at RVA 0x5FFD3C0: all planetary travel on or off. | exe (round 15 dump; both dumps byte-identical) |
| Other travel actions | `OverridePlanetLandingCheckpointAction` (RVA 0x8FB310) keeps a per-planet landing override in a table at RVA 0x5161530. `PlanetMenuCheckpointWarpAction` (RVA 0x8FB4C0) is the menu's warp. `CheckpointWarpAction` and `LoadLevelAction` were dumped too. | exe |
| Can Coordinates unlock real planet travel, not only a flag? | **Yes, through the hub's own travel.** F6 / Ctrl+F6 fly (ship) or warp to the destination's checkpoint. This is real planet travel and doesn't depend on the menu. On top of that, 8.0 sets every level bit and the travel byte at Zurkie's, so the ship's menu may offer the planets too. A menu choice without Coordinates is undone on landing (warp back to Zurkie's). | implementation |
| Can travel be blocked before it happens? | No. Events can't be vetoed, and the menu event's strings are read-only. A trip can only be undone after landing. | rivet_hook (7.0 finding) |

## 3. Planet and mission randomization: the full investigation

| Item | Finding | Source |
|---|---|---|
| Planet selection data | Planet menu → ship listener vars (above); `PlanetMenuAcceptEvent` comes right before `PlanetChangedEvent`; the story's own travel and rifts come without it | rivet_hook, game (round 16) |
| Mission IDs | Missions are found by **name** (CRC hash, `rivet.hash`). The registry has 19 names over 14 visits: 11 visits have names seen in your game (logs, level-script variables), 3 have names from your `dag` (Blizar, Viceron, the finale) | game, exe |
| Mission transition functions (system 2, your game) | **Start**: only when the state is 1 (Available) and the component's `vt[0xD0]` agrees; then `vt[0xD8]`. **Complete** ("complete" input): only from 3 (Complete Cleaning); then `vt[0xF0]`. The other input calls `vt[0xE8]`. **Replay**: `vt[0x108](flag, 1)`. **MakeMissionAvailable**: does nothing at all. **SkipObjectiveAction** (RVA 0x8D7A20): an objective in state 1 → RVA 0x8DB080. **AdvanceMissionObjectiveAction** (RVA 0x19CFD40) and **ReloadToObjectiveAction** (RVA 0x8882B0, loads the game into a mission objective, with about 25 calls into the load system) are also dumped | exe |
| Mission state storage | **New in 8.0:** `State()` (RVA 0x1A44E70) reads `id = obj->vt[0x38]()`, `key = *(*(obj+8))+8`, `t = TableFind(mgr+0x1B0, key)` (RVA 0x1BDAFD0), `e = EntryFind(t, id)` (RVA 0x1BDB000), and state = `*(*(e+0x28)+0x30)`. That record is the node's saved data (`MissionSaveDataShared`). The numbers match the DDL enum and the events | exe, DDL, game |
| Level loading functions | rivet_hook's warp (`HERO_REQUEST_CHECKPOINT_WARP`) loads the checkpoint's region; `rivet.overlay` loads about 25 non-story overlays and refuses story overlays (the custom overlay system unloads them within a frame unless mission state calls for them) | rivet_hook |
| Story progression flags | The per-node mission save data above, plus the mission graph's `GlobalSaveTable` nodes (`GlobalSaveTableSetKeyAction` dumped) | DDL, exe |
| Planet availability flags | The level mask and the travel byte (section 2); their meaning for the menu is unknown | exe |
| Checkpoint initialization | `ObjectiveLoadInfo.SpawnCheckpoint` per mission/objective; a warp moves the save's current checkpoint | DDL, rivet_hook |
| Mission completion callbacks | `MissionStateChangedEvent` (3/4), `MissionCompleteEvent`, `EndMissionDevstatsEvent`, `MissionObjectiveCompleteEvent` | game |
| Save-game campaign state | `MissionSaveDataShared` per node (in `CampaignSave`) | DDL |
| Travel menu behaviour | as above; in hub mode a menu landing on a planet without Coordinates is sent back to Zurkie's | game, implementation |
| Character and level initialization | `ObjectiveLoadInfo.SpawnAsHero`; `rivet.hero_play_as` is the game's own hero swap (`TransformationEvent`) | DDL, rivet_hook |
| Dependencies between planets and story missions | The mission graph (And/Or/... nodes) decides availability. The registry keeps the dependencies the game's scripts rely on: revisits after first visits; Viceron after the Phantom Dash (Nefarious City) and the Hurlshot (Torren IV); the finale last. | DDL, registry (3.0) |
| Can a planet be unlocked and visited outside the story order? | **Visited: yes** (a warp loads an unreached planet without its story; earlier rounds). **Its story: unknown.** That is the 8.0 experiment (below). | game, implementation |

### Approaches, and what 8.0 does with each

| Approach | Status in 8.0 |
|---|---|
| Direct planet loading (checkpoint warp, ship flight) | **Implemented**: hub travel, the return to Zurkie's, the New Game start, the keeper |
| Direct mission loading through `ReloadToObjectiveAction` | **Investigated, not implemented.** The handler makes about 25 calls into the load and mission systems, most not in the dumps, so it can't be replayed with byte-checked calls. Borrowing a loaded node of that class would need string vars, which can't be written. |
| Changing `NewGameLoadInfo` (start at Zurkie's as data) | **Investigated, not possible here.** It needs the mission graph asset from your game and a DDL writer (see section 6). |
| Making a mission available (`MakeMissionAvailableAction`) | **Not possible**: a no-op in system 2 (round 15) |
| Modifying progression flags: writing a mission's state record | **Implemented, experimental** (`rando_give.dll` v6 kind 8, `hub_force_missions`). It writes 1 (Available) into an inactive destination mission's record, then calls the game's own start. It writes 4 into MIS_INTRO (`hub_intro = "force"`). Whether the mission system acts on such a write is unknown. |
| Replaying a mission | **Implemented**, as the ladder's next step |
| Redirecting mission transitions / replacing destination IDs | **Not needed.** The hub chooses the destination itself, and travel isn't redirected. |
| Custom randomized destination tables | **Implemented**: `seed.hub` (start pair, unlock queue, destinations, finale), checked over every order a player could choose |
| Intercepting planet travel requests | **Implemented**: `PlanetMenuAcceptEvent`, then a warp back from a planet without Coordinates |
| Battleplex as the hub (warp out, finish, warp back) | **Implemented**: the main 8.0 loop |
| Loading other planets INTO the Battleplex (its mission structures, arena overlays) | **Investigated, not possible.** The arena platforms are among the non-story overlays `rivet.overlay` can load. A planet's missions, though, live in that planet's story overlays, which only its mission state loads, at the planet's own place in the level. Arena missions are their own mission types (`ArenaBronzeCup`, ...). The closest working alternative is the hub loop. |

### The mission ladder (one destination)

1. Ask the game for each of the visit's missions (`State()`); unknown names are skipped.
2. **Active** (2): it's running.
3. **Available** (1): the game's start call.
4. **Inactive** (0): with `hub_force_missions`, write 1, then the game's start call.
5. If not active: the game's replay call.
6. If still not active: **explore**. Gold Bolts, armor pods and side activities pay as always. Ctrl+F5 twice finishes the destination by hand (recorded in the history).

Every step is logged (`RANDO-HUB`). Rounds 14-16 never ran any of these mission calls, so the
first playtest decides which steps work.

## 4. Campaign progression and completion

| Topic | How 8.0 handles it |
|---|---|
| Mandatory story missions | Every registry visit except the parade is a destination |
| Rivet and Ratchet missions | Each visit has its hero. Rivet's visits swap the hero to Rivet on arrival; Zurkie's swaps back to Ratchet (`hub_hero_swap`). |
| Clank and Glitch sections | They are part of their visit's missions, so they play inside their destination. They are not separate destinations. Clank and hacking puzzles are overlays loaded on request by the game's rifts and puzzles (rivet_hook docs); that their missions load them is inference. |
| Mandatory bosses | Part of their visit (Seekerpede, Francois, Cordelion boss, Zordoom warden, Emperor Nefarious). No item gates them: the 8.0 hub plan doesn't use `weapon_logic`. |
| The final mission | The finale (Corson V, `MIS_MEGA_01_RIVET`, `MIS_MEGA_FINALE`) opens when every other destination is finished (`hub_finale = "half"`: half of them). Its Coordinates come then. |
| Tracking completion | `S.hub.done`, saved by the companion. A destination finishes on its last mission's completion, or by hand. |
| Avoiding repeats | A finished destination is never offered again. Revisits are separate destinations after their first visit. |
| Mission dependencies | Only the game's own (above). The plan is checked over **every** subset of finished destinations (up to 4,096 situations): from each reachable situation, something is still open until the finale. |

## 5. Test results (offline)

See TESTING.md: 43,000 seeds (9,000 hub seeds plus hub settings within the random-settings batch),
231 tests (222 passed, 9 skipped for PowerShell), the DLL's v6 paths checked against both code dumps, and real New Game event streams
from rounds 14-16 replayed into hub seeds.

## 6. What would make the next step possible

1. **Your first playtest's rivet.log.** The `RANDO-HUB` lines answer, in one session:
   - does the warp from the parade land on Zurkie's?
   - does the state write make a mission available and startable?
   - does the story load?
   - what are the level bits?
   - which LANDING / MEGA checkpoints exist?
2. To change the New Game spawn as data instead (`NewGameLoadInfo`), the mission graph asset is
   needed. Its path is in your `dag` (search for `mission` + `graph`); it can be exported with the
   Overstrike Modding Tool. Then a `.stage` can replace `SpawnCheckpoint` with `CHK_ZURK_00_DEFAULT`.
   That needs a DDL writer for that asset type (rivet's DDL has the reader).
