-- Rift Apart Randomizer 10.0: your seed and settings.
-- Change, save, then restart the game (or press Pause to reload the scripts before you play).
-- A different seed or different randomization options make a NEW seed with its own progress;
-- start it with NEW GAME. Keys/logging can change any time.
-- Every option is explained in docs\CONFIGURATION.md. Wrong values are reported in rivet.log
-- (RANDO-SETTINGS) and the preset's value is used instead.
--
-- Always true, whatever you set:
--   * 10.0 (hub = true): NEW GAME takes you to Zurkie's Battleplex once Ratchet has his wrench. Choose
--     the Prologue, the Battle Arena or Nefarious City there (] next, Ctrl+] go); every other planet
--     opens when you find its Coordinates. Finishing a destination brings you back to Zurkie's.
--   * every Gold Bolt you pick up is a real Gold Bolt, and the randomizer adds a reward to it
--   * you start with the Hoverboots and the Map-O-Matic
--   * every weapon has exactly one route: a slot of Ms. Zurkon's shop, the start, or a reward
--     (docs\WEAPONS.md). A weapon you can find is never also for sale. Ammo and upgrades as usual
--   * a mission, side activity or armor pod with no item gives Bolts or Raritanium
--   * the solver proves every seed can be finished (in the game's own mission order too)
--   * hub = false gives 9.0's start instead: the prologue, then Nefarious City, then Sargasso
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["04_rando_settings"] = "10.0.0"   -- the kit check (10_rando_runtime.lua)
RANDO_SETTINGS = {
  seed = "random",            -- any text, e.g. "lombax-ryno-2026"; "random" = the companion picks one and remembers it
  preset = "balanced",        -- balanced | chaos | full | campaign | everything (docs\CONFIGURATION.md)
                              --   balanced    every item system with your defaults (02's G.DEFAULTS: Coordinates
                              --               as items, planet_shuffle, weapon prices); travel is free
                              --   chaos       wide currency swings, random prices, locked levels (fewest open)
                              --   full        every item system + Coordinates as items (rewards wait for them)
                              --   campaign    LOCKED LEVELS: flying to a planet needs its Coordinates
                              --   everything  locked levels + random prices + start currency + more currency
                              -- experimental mission order (docs\CAMPAIGN.md): planet_shuffle | mission_shuffle |
                              --   full_campaign | campaign_chaos (played in the game's own order until verified;
                              --   9.0: every order starts with the prologue, Nefarious City, Sargasso)

  -- 10.0 (leave a line out to use the default shown)
  -- hub = true,                       -- Zurkie's hub + planet shuffle (false: 9.0's story start)
  -- distribution = "spread",          -- spread: items over Gold Bolts, missions, side activities and armor pods
                                       -- goldbolts_first: 4.0-9.0 (every Gold Bolt an item, the rest mostly currency)
  -- shop_weapons = 8,                 -- 0-15 different weapons Ms. Zurkon sells; her other slots are closed and
                                       -- those weapons become rewards instead
  -- early_weapons = 2,                -- 0-6 weapons at locations you can reach right at the start

  -- toggles (leave a line out to use the preset's value)
  -- weapons = true,                   -- shuffle the weapon pool over the shop, the start and the rewards
  restored_weapons = "auto",           -- ARSENAL_RESTORED's 9 weapons: "auto" = in the pool when the companion
                                       -- finds the mod installed; true = always (ONLY with the mod); false = never
  -- gadgets = true,                   -- Box Breaker, Omniglove, Glitch
  -- armor = true,                     -- armor pieces are rewards; armor pods give random items
  -- levels = true,                   -- true: each planet's travel needs its Coordinates (the campaign preset)
  -- mission_order = "planet_shuffle",        -- experimental: planet_shuffle | mission_shuffle | full | chaos
  -- shop = "shuffle",                 -- shuffle: her 15 slots sell the seed's weapons | vanilla: her own
  -- bolts = true,                     -- Bolts rewards
  -- raritanium = true,                -- Raritanium rewards

  -- currency (per reward; later planets give more with currency_scaling)
  -- bolts_min = 1000, bolts_max = 10000,         -- 1000 to 100000
  -- raritanium_min = 150, raritanium_max = 300,   -- 150 to 5000
  -- bolts_budget = 150000,            -- the most all Bolts rewards give together (0 = no limit)
  -- raritanium_budget = 2000,         -- the most all Raritanium rewards give together (0 = no limit)
  -- bolts_percent = 60,               -- with both on: % of currency rewards that are Bolts
  -- currency_scaling = true,

  -- shop prices
  -- shop_prices = "random",           -- vanilla | weapon (a slot costs what its weapon costs normally) | percent | random
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
  -- start_raritanium = 1000,             -- 1000 to 5000
  -- start_coordinates = "first_two",  -- start_only | first_two | random_extra (levels / Coordinates only)

  -- logic
  -- weapon_logic = "none",            -- none | light | standard
  -- accessibility = "full",           -- full | beatable
  -- exclude = "",                     -- e.g. "weapon:ryno_8,armor:pirate_head"

  -- in-game options (change any time)
  -- 10.0 the hub (only with hub = true)
  key_hub = "]",                     -- ] next destination, Ctrl+] go
  key_hub_return = "[",              -- [ twice back to Zurkie's, Ctrl+[ twice finish a destination by hand
  key_story = "/",                   -- / start the story of the planet you are on
  hub_return_delay = 12,             -- seconds after a finished destination before you go back to Zurkie's
  hub_follow_story = false,          -- true: when the game's own story takes you to an open destination, play it
  shop_close_slots = true,           -- closed shop slots show the Burst Pistol (false: their own weapon)
  -- 8.3 KEYS: ordinary keyboard keys. A key is one character ("]", "/", "K", "7"), NUMPAD0-NUMPAD9,
  -- INSERT, DELETE, HOME, END, PAGEUP, PAGEDOWN, or F1-F24. Ctrl + the key does the second action.
  -- rivet.log lists them at start (RANDO-KEYS) and logs every press (RANDO-KEY).
  key_status = ";",                  -- ; status; Ctrl+; twice opens a planet you were sent back from (levels)
  key_campaign = "'",                -- experimental mission order only
  legacy_f_keys = true,              -- the old F7 / F8 / F9 / F12 keys keep working as well (false: off)
  real_items = true,                 -- put rewards into the real inventory
  real_weapons = true,
  armor_intercept = true,            -- armor pods give the seed's item instead of their own piece
  shop_runtime = true,               -- change the vendor's slots and prices in memory (false: her usual weapons;
                                     -- the seed's other shop weapons are then given to you directly)
  levels_runtime = true,             -- levels: send you back from a locked planet (false: its rewards wait instead)
  new_game_reset = true,             -- New Game starts the seed's randomizer progress over
  -- 8.2 TEST TRAVEL (docs\TEST_TRAVEL.md): go to any planet, whatever Coordinates you hold. A testing aid,
  -- OFF for a real playthrough (8.4); set it to true to use it (written into the history as [TEST TRAVEL]).
  test_travel = false,               -- true: the keys below work, and nothing sends you back from a planet
                                     -- (9.0: a test trip only moves you; it starts no story)
  key_test_travel = ".",             -- . next planet, Ctrl+. warp there
  key_test_point = ",",              -- , next landing point on that planet, Ctrl+, fly there with the ship
  discovery = true,                  -- log the game events the randomizer listens to
  log_notifications = true,
}
