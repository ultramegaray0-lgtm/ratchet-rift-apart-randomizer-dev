# Randomizer 8.1: fixes from your round 17 log

8.1 is 8.0 plus fixes for what your round 17 rivet.log showed. That log came from the install
that worked (the folder named Ratchet.and.Clank.Rift.Apart.v2.618). Your seed carries over: same
fingerprint, same plan, same saved progress. None of 8.1 has run in your game yet.

## What the log showed, and what changed

| In the log | Cause | 8.1 |
|---|---|---|
| `09_rando_real.lua:672: attempt to call a nil value (global 'u32_at')` on every planet change | the line called a local defined 120 lines below it | fixed; a test now checks every script for this kind of mistake |
| `travel to torren_iv impossible: no checkpoint known` (Cordelion too) | Torren IV and Cordelion have no checkpoint named LANDING / SHIP / DEFAULT, and Cordelion's tunnel is called KEDARO, not CORD | **checkpoint catalog** (below) |
| 440 × `12_rando_shop.lua: ran past the 8 ms frame budget`; the shop never changed | the vendor search read up to 16 KB of memory and scanned it in one frame; a failure was retried forever | the search runs a slice per frame (2 reads); it gives up after 5 failed tries and hands out the shop's extra weapons instead |
| levels `unlocked 0x0` after a reload (was `0x7FE`) | a save load resets the level mask; 8.0 only set it at Zurkie's | the level bits are put back on whichever planet you load on |
| `MIS_BLIZAR_01 / MIS_CORD_BOSS / MIS_ZURK_02 / MIS_SARG_02_REVISIT / MIS_MEGA_01_RIVET: not a mission in your game` | guessed names | replaced by names your game has: MIS_BLIZAR, MIS_CORD_01_FIRST_VISIT, MIS_ZURK_02B_VISIT_02B, MIS_SARG_02_REVISIT_SHIPS, MIS_MEGA_FINALE |
| Blizar and Savali chosen in the ship's menu sent you back to Zurkie's | no Coordinates for them yet (by design) | unchanged; the message names the reason |

## The checkpoint catalog (Torren IV, Cordelion and the rest)

`rivet.checkpoints()` lists the level's checkpoints with the **area** each one is in. Round 17
shows these areas: Zurkons, Sargasso (open world), Blizar_Intact, Blizar_Destroyed, Zordoom,
Megalopolis (open world), and interplanetary_space for the planet tunnels.

From about 10 seconds after the game starts, the randomizer fills a catalog. It runs one name
filter every 4 frames, and the last filter lists everything. Each checkpoint goes on a planet by
its area first and its name second. Planet tunnels (CHK_TRANSITION_TO_…) go on none. Each
checkpoint gets a score:

- landing pad 100, landing 90, ship 80, default 70, arrival 45, entrance 40, start 35;
- −60 for each of: cinematic, boss, finale, arena, challenge, return, escape, post-mission,
  teleporter, warp-back, tunnel.

The best one is where the hub warps. rivet.log prints the result once:

    RANDO-TRAVEL checkpoint catalog: corson_v 31=..., torren_iv N=CHK_..., cordelion N=CHK_..., ...

If a trip is asked before the catalog is complete, it waits ("looking for a landing point…"),
for 30 seconds at most.

If a planet still has no checkpoint, the hub says: *"no warp point known for X yet - fly there
from the ship's planet menu"*. Every planet is in that menu (the level bits). A menu landing on a
planet you hold Coordinates for starts its destination as before, and its landing checkpoint is
**remembered**, so the next F6 / Ctrl+F6 trip there works.

Not known yet: whether the catalog's choice for Torren IV and Cordelion is a sensible place to
land. The log line above shows what was chosen, and the menu fallback always works.

## ARSENAL_RESTORED, rivet_hook version

rivet_hook loads loose mods **only** from the paths listed under `[assets] paths` in rivet.toml.
The randomizer's 8.0 rivet.toml listed only `mods/default` (your log: *mod path mods/default does
not exist! skipping*), so a copied ARSENAL_RESTORED folder was never loaded. The companion also
only looked for the Overstrike install, so its weapons stayed out of the seed.

8.1:

- **rivet.toml** lists `mods/ARSENAL_RESTORED` (a folder with info.json) and
  `mods/ARSENAL_RESTORED.stage`. A path that isn't there is skipped, so nothing breaks without the
  mod.
- **companion\Install-ArsenalRestored.bat**: drag the mod's zip onto it. It:
  - copies the mod folder (the one holding info.json) or its .stage into `<game>\mods\ARSENAL_RESTORED`;
  - copies the mod's own .lua files into `<game>\scripts`, never over a randomizer file;
  - adds the path to rivet.toml (the old one is kept as rivet.toml.bak).
- **The companion** finds the rivet_hook version through rivet.toml. If the mod sits in mods\ but
  isn't listed, the companion says so.

The zip itself was not available to this build (Google Drive can't be reached from the build
machine). The installer handles the usual layouts, but it hasn't seen this one. If it says
"nothing copied", send the zip's file list.

## Tested here (offline, simulated game)

247 tests ran: 238 passed, 0 failed, 9 skipped (the PowerShell tests: no PowerShell on the build
machine). 16 of the tests are new in 8.1 (tests/test_v81.py).
The new tests cover:

- the catalog against the 70+ checkpoints your round 17 log listed, placing each on the right
  planet;
- simulated Torren IV and Cordelion trips;
- a trip waiting for the catalog;
- a remembered menu landing;
- level bits put back after a load;
- the shop search spanning frames with at most 2 reads each;
- a failing vendor stopping after 5 tries;
- the registry and the rivet.toml paths.

PowerShell changes (companion detection, installer) are **untested**.
