-- Ratchet & Clank: Rift Apart Randomizer - your settings.
--
-- Edit with Notepad, save, then restart the game. Changing the seed or any option below makes a
-- NEW seed with its own progress: start it with New Game. Lines starting with -- are notes; to
-- change an option, remove the -- in front of it and edit the value. A wrong value is reported in
-- rivet.log (search RANDO-SETTINGS) and the default is used instead.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["04_rando_settings"] = "10.0.9"   -- version check (do not edit)
RANDO_SETTINGS = {
  -- THE SEED: "random" = the companion picks one and remembers it. Any other text is a fixed seed
  -- (the same text and settings give the same seed on every PC), e.g. "lombax-ryno-2026".
  seed = "random",

  -- PRESET: the starting point for every option below.
  --   balanced    the defaults shown below
  --   full        bigger Bolts rewards (up to 15,000), smaller Raritanium rewards (up to 250)
  --   chaos       1 starting weapon, no starting gadget, shop prices 25-300%, wide currency swings
  --   everything  shop prices 50-200%, start with 2,500 Bolts and 25 Raritanium, bigger rewards
  preset = "balanced",

  -- WHERE ITEMS GO
  distribution = "goldbolts_first",    -- "goldbolts_first": every Gold Bolt gives one item
                                       -- "spread": items spread over Gold Bolts, missions, side activities, armor pods
  -- shop_weapons = 8,                 -- 0-15: weapons Ms. Zurkon sells; her other slots close and those weapons become rewards
  -- early_weapons = 2,                -- 0-6: weapons placed where you can reach them right at the start
  -- story_milestones = true,          -- each planet's second story mission gives a reward
  -- side_locations = true,            -- Zurkie's cups, Trudi, the Blizar chef and Ardolis give rewards
  -- collectibles = true,              -- the 10 Spybots and 12 Lorbs give rewards (they pay once their pickup is bound)

  -- WHAT IS RANDOMIZED
  -- weapons = true,                   -- weapons are shuffled over the shop, your start and the rewards
  restored_weapons = "auto",           -- ARSENAL_RESTORED's 9 weapons: "auto" = only when that mod is installed,
                                       -- false = never (true = always: ONLY if you have that mod)
  -- gadgets = true,                   -- Box Breaker, Omniglove and Glitch are rewards
  -- armor = true,                     -- armor pieces are rewards; armor pods give random items
  -- shop = "shuffle",                 -- "shuffle": Ms. Zurkon sells the seed's weapons | "vanilla": her usual ones
  -- exclude = "",                     -- items never randomized, e.g. "weapon:ryno_8,armor:pirate_head"

  -- YOUR START (Hoverboots and Map-O-Matic are always included)
  -- start_weapons = 2,                -- 0-4 random weapons
  -- start_gadgets = 1,                -- 0-2 random gadgets
  -- start_items = "",                 -- items you always start with, e.g. "weapon:enforcer,glitch"
  -- start_bolts = 0,                  -- 0-100000
  -- start_raritanium = 0,             -- 0-5000

  -- BOLTS AND RARITANIUM (a reward location without an item gives one of these)
  -- bolts = true,
  -- raritanium = true,
  -- bolts_min = 1000, bolts_max = 10000,         -- per reward (100-100000)
  -- raritanium_min = 120, raritanium_max = 1000,  -- per reward (1-5000)
  -- bolts_budget = 150000,            -- the most all Bolts rewards give together (0 = no limit)
  -- raritanium_budget = 2000,         -- the most all Raritanium rewards give together (0 = no limit)

  -- SHOP PRICES
  -- shop_prices = "weapon",           -- "vanilla" | "weapon": a slot costs its new weapon's price
                                       -- | "percent": shop_price_percent of it | "random": between the two percents
  -- shop_price_percent = 100,
  -- shop_price_max_percent = 150,

  -- LOGIC
  -- weapon_logic = "none",            -- "none" | "light" | "standard": weapons expected before later planets
  -- accessibility = "full",           -- "full": every location reachable | "beatable": only what finishing needs
  -- coords_first_visit = true,        -- planet shuffle: Coordinates always open a planet's first visit
                                       -- (never on a revisit; Viceron's come from Torren IV's story)

  -- ENEMIES AND BOSSES (enemy.lua, boss.lua; both OFF by default, no preset turns them on). Use the keys
  -- in the game instead of editing this: the save remembers your choice. These only decide the start
  -- of a save that never used the keys. They do not change the seed.
  -- enemy_randomizer = false,         -- regular enemies of combat encounters become other regular enemies
  -- boss_randomizer = false,          -- boss-tier enemies are shuffled among themselves (story bosses never)
  -- key_enemies = "-",                -- the Enemy Randomizer's key (Ctrl+key: what it changed here)
  -- key_bosses = "=",                 -- the Boss Randomizer's key
  -- CHAOS (chaos.lua, OFF by default): ANY enemy or boss can become ANY other, from any planet, with NO
  -- protection: doors may never open, bosses may be unbeatable, a run may become impossible. While it is
  -- ON the two above change nothing. Its key turns it off again (docs/CHAOS.md).
  -- chaos_randomizer = false,
  -- key_chaos = "BACKSPACE",          -- the Chaos Randomizer's key
  -- chaos_cross_planet = true,        -- false: only this planet's enemies
}
-- In the game, the 0 key turns PLANET SHUFFLE on or off (off by default; it is remembered).
-- The - key turns the ENEMY RANDOMIZER on or off, the = key the BOSS RANDOMIZER (off by default; remembered).
-- BACKSPACE turns the CHAOS RANDOMIZER on or off (off by default; remembered; no protection at all).
-- Ctrl+0 pressed twice sends your randomizer items again if some went missing.
