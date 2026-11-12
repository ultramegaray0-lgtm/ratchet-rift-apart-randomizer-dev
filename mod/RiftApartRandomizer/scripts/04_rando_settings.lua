-- Rift Apart Randomizer 8.4: your seed and settings.
-- Change, save, then restart the game (or press Pause to reload the scripts before you play).
-- A different seed or different randomization options make a NEW seed with its own progress;
-- start it with NEW GAME. Keys/logging can change any time.
-- Every option is explained in docs\CONFIGURATION.md. Wrong values are reported in rivet.log
-- (RANDO-SETTINGS) and the preset's value is used instead.
--
-- Always true, whatever you set:
--   * every one of the 25 Gold Bolts gives exactly ONE item, the moment you pick it up
--   * you start with the Hoverboots and the Map-O-Matic
--   * every weapon has exactly one route: a slot of Ms. Zurkon's shop, the start, or a reward
--     (docs\WEAPONS.md). Ammo and upgrades work as usual
--   * a mission, side activity or armor pod with no item gives Bolts or Raritanium
--   * the solver proves every seed can be finished (in the game's own mission order too)
RANDO_SETTINGS = {
  seed = "random",            -- any text, e.g. "lombax-ryno-2026"; "random" = the companion picks one and remembers it
  preset = "hub",             -- hub | hub_chaos | balanced | chaos | full | campaign | everything (docs\CONFIGURATION.md)
                              --   hub         8.0 (EXPERIMENTAL, docs\HUB.md): NEW GAME starts at Zurkie's Battleplex
                              --               with two random Coordinates; every destination you finish
                              --               opens the next ones; balanced items
                              --   hub_chaos   the hub with chaos' currency and prices
                              --   balanced    every item system, the game's own level order (7.0)
                              --   chaos       wide currency swings, random prices, locked levels (fewest open)
                              --   full        every item system + Coordinates as items (rewards wait for them)
                              --   campaign    LOCKED LEVELS: flying to a planet needs its Coordinates
                              --   everything  locked levels + random prices + start currency + more currency
                              -- experimental mission order (docs\CAMPAIGN.md): planet_shuffle | mission_shuffle |
                              --   full_campaign | campaign_chaos (played in the game's own order until verified)

  -- 8.0 hub (hub presets; leave a line out to use the default)
  -- hub_start_coordinates = 2,        -- Coordinates open at the start (2 to 4, all different planets)
  -- hub_unlocks = 1,                  -- Coordinates each finished destination opens (1 to 3)
  -- hub_finale = "all",               -- all | half: finished destinations before the finale opens
  -- hub_revisits = true,              -- second visits (Zurkie's 2, Sargasso 2, Savali 2) are destinations

  -- toggles (leave a line out to use the preset's value)
  -- weapons = true,                   -- shuffle the weapon pool over the shop, the start and the rewards
  restored_weapons = "auto",           -- ARSENAL_RESTORED's 9 weapons: "auto" = in the pool when the companion
                                       -- finds the mod installed; true = always (ONLY with the mod); false = never
  -- gadgets = true,                   -- Box Breaker, Omniglove, Glitch
  -- armor = true,                     -- armor pieces are rewards; armor pods give random items
  -- levels = false,                   -- true: each planet's travel needs its Coordinates (the campaign preset)
  -- mission_order = "vanilla",        -- experimental: planet_shuffle | mission_shuffle | full | chaos
  -- shop = "shuffle",                 -- shuffle: her 15 slots sell the seed's weapons | vanilla: her own
  -- bolts = true,                     -- Bolts rewards
  -- raritanium = true,                -- Raritanium rewards

  -- currency (per reward; later planets give more with currency_scaling)
  -- bolts_min = 1000, bolts_max = 10000,         -- 100 to 100000
  -- raritanium_min = 20, raritanium_max = 150,   -- 1 to 5000
  -- bolts_budget = 150000,            -- the most all Bolts rewards give together (0 = no limit)
  -- raritanium_budget = 2000,         -- the most all Raritanium rewards give together (0 = no limit)
  -- bolts_percent = 60,               -- with both on: % of currency rewards that are Bolts
  -- currency_scaling = true,

  -- shop prices
  -- shop_prices = "weapon",           -- vanilla | weapon (a slot costs what its weapon costs normally) | percent | random
  -- shop_price_percent = 100,         -- percent: this % of each slot's price; random: the lowest %
  -- shop_price_max_percent = 150,     -- random: the highest %

  -- where rewards are (the 25 Gold Bolts always are)
  -- story_milestones = true,          -- second story mission of each planet
  -- side_locations = true,            -- Zurkie's cups, Trudi, Blizar chef, Ardolis

  -- start (Hoverboots + Map-O-Matic are always added)
  -- start_weapons = 2,                -- 0 to 4 random weapons (the shop's 15 slots come first)
  -- start_gadgets = 1,                -- 0 to 2 random gadgets
  -- start_items = "",                 -- items you always start with, e.g. "weapon:enforcer,glitch"
  -- start_bolts = 0,                  -- 0 to 100000
  -- start_raritanium = 0,             -- 0 to 5000
  -- start_coordinates = "first_two",  -- start_only | first_two | random_extra (levels / Coordinates only)

  -- logic
  -- weapon_logic = "none",            -- none | light | standard
  -- accessibility = "full",           -- full | beatable
  -- exclude = "",                     -- e.g. "weapon:ryno_8,armor:pirate_head"

  -- in-game options (change any time)
  -- 8.3 KEYS: ordinary keyboard keys. A key is one character ("]", "/", "K", "7"), NUMPAD0-NUMPAD9,
  -- INSERT, DELETE, HOME, END, PAGEUP, PAGEDOWN, or F1-F24. Ctrl + the key does the second action.
  -- rivet.log lists them at start (RANDO-KEYS) and logs every press (RANDO-KEY).
  key_status = ";",                  -- ; status; Ctrl+; twice opens a planet you were sent back from (levels)
  key_campaign = "'",                -- experimental mission order only
  legacy_f_keys = true,              -- the old F5 / F6 / F7 / F8 / F9 keys keep working as well (false: off)
  real_items = true,                 -- put rewards into the real inventory
  real_weapons = true,
  armor_intercept = true,            -- armor pods give the seed's item instead of their own piece
  shop_runtime = true,               -- change the vendor's slots and prices in memory (false: her usual weapons;
                                     -- the seed's other shop weapons are then given to you directly)
  levels_runtime = true,             -- levels: send you back from a locked planet (false: its rewards wait instead)
  new_game_reset = true,             -- New Game starts the seed's randomizer progress over
  -- 8.0 hub, in the game (change any time)
  key_hub = "]",                     -- ] next destination, Ctrl+] go there (before the hub starts: go to Zurkie's)
  key_hub_return = "[",              -- [ twice back to Zurkie's; Ctrl+[ twice finish this destination by hand
  -- THE STORY ON ARRIVAL (8.3) and its hero (8.4)
  story_on_arrival = true,           -- landing on a planet (test travel, the ship's menu, a hub trip) starts that
                                     -- planet's story, even if the story before it is not finished
  story_prime_before_travel = true,  -- a hub trip (and a test-travel warp) switches to the story's hero and starts
                                     -- the story BEFORE it travels, so the planet loads with it running
  story_reload_stuck = true,         -- a story still at "go to <planet>" 20 s after its start is reloaded once:
                                     -- out to Zurkie's and straight back
  key_story = "/",                   -- / start the story of the planet you are on; Ctrl+/ twice: start it again
  hub_runtime = true,                -- false: a hub seed does nothing hub-specific (no warps, no mission calls)
  hub_trigger = "wrench",            -- New Game: leave the parade once Ratchet has the wrench | "control" | "cinematic"
  hub_intro = "force",               -- "force": mark the skipped prologue complete in the save | "leave" it active
  hub_force_missions = true,         -- an inactive story mission of a destination is made available, then started
  hub_replay = true,                 -- if starting fails, try the game's replay call
  hub_levels = "all",                -- "all": set every level bit (1-10) at Zurkie's | "off"
  hub_travel_flag = true,            -- turn the ship's planetary travel on at Zurkie's
  hub_fly = true,                    -- leave Zurkie's with the ship's flight when a ship answers (else the warp)
  hub_auto_return = true,            -- a finished destination takes you back to Zurkie's
  hub_return_delay = 12,             -- seconds before that ([ cancels)
  hub_hero_swap = true,              -- each destination is played as its own hero (checked with the game);
                                     -- Ratchet again at Zurkie's. A story only starts with its own hero
  -- 8.2 TEST TRAVEL (docs\TEST_TRAVEL.md): go to any planet, whatever Coordinates you hold. A testing aid,
  -- OFF for a real playthrough (8.4); set it to true to use it (written into the history as [TEST TRAVEL]).
  test_travel = false,               -- true: the keys below work, and nothing sends you back from a planet
  key_test_travel = ".",             -- . next planet, Ctrl+. warp there
  key_test_point = ",",              -- , next landing point on that planet, Ctrl+, fly there with the ship
  discovery = true,                  -- log the game events the randomizer listens to
  log_notifications = true,
}
