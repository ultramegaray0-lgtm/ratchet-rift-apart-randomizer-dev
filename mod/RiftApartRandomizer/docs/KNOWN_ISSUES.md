# Known issues (Randomizer 10.0)

9.0 has passed every automated test, but it has **not run in your game yet**. Everything below
comes from your logs of rounds 13-22, from the code, or from the simulator. Each item says which.
Use this page to tell a known issue from a new one.

## 0a. Since 10.0

- **Nothing of the 10.0 hub has run in the game.** The steps it uses were seen working in round 17
  (the warp to Zurkie's, the mission writes and starts, the travel flag and level bits). Three things
  are new and untested: Nefarious City loaded at `CHK_NEFCITY_START`, the prologue resumed at the
  parade's checkpoint, and the warp back to Zurkie's after the game's own follow-on travel.
- **Starts are only known for three destinations** (Nefarious City, Zurkie's first visit, the
  prologue). The others warp to their landing pad, or fly there when a ship answers. The first
  checkpoint their story triggers is learned for the next run. If a story waits at its "go to" step,
  it is loaded once more; after that, `/` or `Ctrl+[` twice.
- **Heroes.** Round 20 showed every hero swap failing under 8.3; 8.4's confirmation check has never
  appeared in a log. A destination started as the wrong hero may stall at its first step.
- **Spybots are not reward locations.** Their pickup event has never appeared in any log, and a
  location that never triggers would lose its reward. The randomizer will add them once one log
  shows the event.
- **The randomizer gives no Gold Bolts.** There is no verified way to add a real one, and a fake one
  is exactly what you asked to avoid. So Gold Bolts are neither rewards nor shop replacements.
  `configs/pickup/pup_gold_bolt_item.config` exists in your game's files; whether granting it counts
  as a real Gold Bolt is untested.
- **Shop replacements are closed slots, not gadgets or armor.** The vendor sells weapon items only.
  Putting a gadget or armor id into a weapon slot was judged too risky to try blind. Gadgets and
  armor are rewards at locations instead.
- **Armor pods hold weapons, armor and gadgets, but not Coordinates.** Their planets are not known
  (polling finds a piece after the fact, sometimes on the next planet), so the solver cannot rely on
  them.
- **Closed slots and the frame-budget fix are untested.** If the vendor still cannot be changed, it
  sells its usual weapons, some of which are rewards in your seed (said on screen).
- **The prologue stays active** while you play other destinations. If loading a save ever drops you
  back into the parade, that is the reason: `[` twice returns to Zurkie's.

## 0. Since 9.0

- **No hub.** A New Game plays the prologue, then Nefarious City, then Sargasso (the game's own
  travel). The randomizer moves you nowhere. 8.0-8.5's hub items in section 1 below (heroes,
  priming, reloads, hub trips) no longer apply; they are kept for the record.
- **A leftover `15_rando_hub.lua`** from an older kit is reported at start (`RANDO-KIT ... delete`).
  With a 9.0 seed it does nothing, but it binds the old hub keys. Delete it.
- **The mission order in the spoiler** (your default `planet_shuffle`) is not followed in the game:
  your game cannot open a mission out of order (CAMPAIGN.md). The game's own order is played, and
  every seed is proven finishable in it.
- **Punk and Reaver armor sources** (your 8.5.2 data) are still 6 filler-only locations. Their
  pieces are owned from the start, so those locations probably never pay (offline: they are not
  intercepted, and the start-owned pieces are in the armor baseline). Their currency counts toward
  the Bolts/Raritanium budgets.
- **Raritanium with your defaults** (min 120, budget 2,000): when more than 16 rewards are Raritanium,
  every one gives 120 (the spoiler's NOTES say so).

## 1. From 8.4/8.5, with the hub (kept for the record; 9.0 has no hub)

1. **Whether the hero fix starts every story.** The rule "a story's first step needs the visit's
   own hero" fits all seven clean cases in rounds 17 and 20 (CHANGELOG.md). It is an inference, not
   game code. If a story still waits at "go to <planet>" with the right hero, 8.4 reloads it once.
   If it still waits after that, press `/` (reload again) or `[` twice and come back. Send the
   rivet.log lines `hero:`, `prime`, `story still waiting`, `reload:`.
2. **Starting a story before the trip.** In round 20 a story that was already active when you
   travelled (Savali) finished its first step on landing. 8.4 now does this on purpose for hub
   trips and test-travel warps. No story has yet been started on purpose from another planet.
   `story_prime_before_travel = false` switches it off: the story then starts after landing, as in 8.3.
3. **The reload trip** (out to Zurkie's and back) uses the same warps as a hub trip, which work.
   It has never been used for a stuck story. `story_reload_stuck = false` switches it off.
4. **New entry points.** `CHK_ZORDOOM_START` (Viceron) and `CHK_CORD_A_START` (Cordelion) are names
   your game listed, but nobody has warped there yet. `CHK_ARD_START` (Ardolis) worked in round 20.
   Torren IV still has no known story start: the catalog picks one.
5. **Viceron's broken lighting (round 20).** It happened after a warp to
   `CHK_ZORDOOM_LANDING_COMBAT`, a mid-mission point, as Ratchet, with the story not yet running.
   The cause is not proven. 8.4 changes all three (story start point, Rivet, story started first).
   rivet_hook's docs say a planet's story overlays load from the save's mission state, which fits.
   If the lighting is still wrong, say where you landed (`travel:` line).
6. **The shop's new layout.** Reading the slot list as an array of pointers matches the game's data
   definition and explains rounds 18-20's "only 0 vendor weapons". It has only run in the
   simulator. If it fails, the old fallback still gives you the seed's non-vendor shop weapons once.
   `RANDO-SHOP vendor ... slot objects by pointer` in rivet.log means it worked. The Price field
   search and the slot map writes have never run in your game.
7. **ARSENAL_RESTORED detected in game.** This depends on Mr. Zurkon's item config being loaded when
   the game starts. If it isn't, the companion still decides as before. `RANDO-SEED
   ARSENAL_RESTORED is installed (the game has ...)` means the in-game check found it.

## 2. Known limitations (by design or engine)

- **The parade.** A new save always starts in the parade (9.0: it plays to its end as in the game).
- **Travel can only be undone after landing, not blocked before.**
- **Whole visits move, never single missions.** The randomizer can't reorder or skip objectives
  inside a mission.
- **A mission inside a visit may swap the hero itself** (Zurkie's 1: Ratchet, then Rivet in the
  arena). 8.4 only sets the hero before a story starts, or while its first step waits. It never
  sets it in the middle of a story.
- **Story abilities come from the story itself** (Phantom Dash, Hurlshot, ...). In the game's own
  order they always come before they are needed.
- **ARSENAL_RESTORED's vendor** sells the mod's weapons in its own slots. Those slots are not moved.
  A seed with the mod may also give one of those weapons as a reward. You then own it, and the
  vendor shows it as owned.
- **Armor you already owned** before a seed started can pay its source location when the randomizer
  sees it (round 18, a finished save). On a New Game this cannot happen.
- **Progress made while the companion is closed is not saved.**
- **The last ~2 seconds before the game closes.** The companion saves every 2 s. If the game closes
  (or crashes) right after a reward, the save can be one step behind: a Bolts/Raritanium payment
  sent in that moment can come again on the next start, and a location collected in that moment
  can be forgotten (its reward came, but the randomizer counts the location as not found). Close the game from its menu
  and give the companion a moment; its window shows "saved (version ...)" after each change.
- **Loading an older game save does not undo randomizer progress.** Items the randomizer gave after
  that game save are gone from the game's inventory, but the randomizer still counts them as given
  and does not send them again. A load only replays part of what you own, so the randomizer can't
  safely tell a lost item from an owned one. Play forward from your latest save in a seed.

## 3. Still open from earlier rounds

- **Glitch deliveries** are never confirmed by an event (round 16 onwards). The delivery is retried,
  then counted as given.
- **Currency amounts.** In round 20, "currency sent: 3000 / 8250 Bolts" was logged. Whether the game
  added exactly that amount has not been checked.
- **"rivet_hook: game version mismatch, invalidating pointers"** (rounds 19-20) is rivet_hook's own
  message. Everything that uses rivet_hook still worked. rando_give.dll checks the game's bytes
  itself (0x7 = all paths matched).
- **The PowerShell companion** is checked by hand only. PowerShell 7 could not run on the build
  machine, so its 9 tests were skipped (8.5 changes one branch of it: a refused save is kept aside).

## 4. Fixed in 8.5 (see CHANGELOG.md; found in the code, none reported from a game yet)

- A mission call that timed out could still run later; a loading screen counted as a timeout.
- An item or currency request with no answer, or in flight at a New Game, could run later.
- The companion's late restore dropped this session's currency, could re-send a confirmed item, and
  lost armor sources, shop gifts and the hub's objective record.
- A New Game kept the hub's record of the old run (no automatic reload of a destination reloaded there).
- Shop-only weapons had no route without a working rando_give.dll, or when the vendor was never found.
- A planet-menu landing (levels seeds) was saved late and not filtered.
- A save the game refused was overwritten by the companion.

## 5. Fixed in 8.4 (see CHANGELOG.md)

- Stories that did not start, and Viceron as Ratchet: the save's hero was trusted, and 4
  registry heroes were wrong.
- 8.3's automatic restart, which never moved a story.
- A hub trip to a test trip's mid-mission checkpoint (Torren IV).
- "weapon type 1002 ... 1012 is weapon:burst_pistol".
- The shop's "only 0 vendor weapons" (rounds 18-20).
- ARSENAL_RESTORED treated as not installed because the companion answered late.
- The campaign message from the F12 key in a hub seed.
