-- Ratchet & Clank: Rift Apart Randomizer - your settings.
--
-- Edit with Notepad, save, then restart the game. Changing the seed or any option below makes a
-- NEW seed with its own progress: start it with New Game. Lines starting with -- are notes; to
-- change an option, remove the -- in front of it and edit the value. A wrong value is reported in
-- rivet.log (search RANDO-SETTINGS) and the default is used instead.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["04_rando_settings"] = "10.0.51"   -- version check (do not edit)
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
  collectibles = true,                 -- DEV DEFAULT (v0.71-DEV1): the 10 Spybots and 12 Lorbs hold rewards, paid by
                                       -- their pickup events (bound, not seen in a log yet). F2 / F3 show them;
                                       -- Ctrl+F2 / Ctrl+F3 twice pay a pickup the game did not report (dev(keys).lua)

  -- WHAT IS RANDOMIZED
  -- weapons = true,                   -- weapons are shuffled over the shop, your start and the rewards
  restored_weapons = "auto",           -- ARSENAL_RESTORED's 9 weapons: "auto" = only when that mod is installed,
                                       -- false = never (true = always: ONLY if you have that mod)
  -- gadgets = true,                   -- Box Breaker, Omniglove and Glitch are rewards
  -- armor = true,                     -- armor pieces are rewards; armor pods give random items
  shop = "shuffle",                    -- DEV DEFAULT (v0.71-DEV1): Ms. Zurkon sells the seed's weapons. The vendor's slots
                                       -- are now also looked for as POINTERS to the weapons' configs (docs/SHOP.md);
                                       -- if they are still not found, the shop's extra weapons are given directly and
                                       -- rivet.log shows RANDO-SHOP EVIDENCE. "vanilla": her usual weapons, none a reward
  -- shop_bonus = true,               -- v0.71-DEV3: six of Ms. Zurkon's open weapon slots ALSO pay a bonus when you buy the weapon in
                                       -- them: 2 Omega versions, 2 gadgets, 2 armor pieces (a vendor screen can only list weapons). The
                                       -- items come from other locations (never one the logic needs). Key \\ shows which slot pays what
  shop_show_items = "notify",          -- v0.71-DEV5: "notify" = the bonus items ride on the weapon you buy and are announced on screen and in
                                       -- rivet.log | "try" = EXPERIMENT: each gadget / armor bonus is ALSO written into a closed vendor slot by
                                       -- its own item id, so the vendor screen may list it (UNTESTED, may stop the game when the vendor
                                       -- opens: then set "notify" again) | "off"
  shop_note_when = "vendor",           -- v0.71-DEV7: when the bonus notes show (one short message per bonus): "vendor" = when you talk to
                                       -- Ms. Zurkon (after a purchase if the game never reports the vendor opening) | "load" = a while into
                                       -- each of the first loads | "both"
  shop_rename = "off",                 -- v0.71-DEV7: her screen: the weapon of a bonus slot gets the bonus item's text as its DESCRIPTION
                                       -- ("desc") or NAME ("name"); "probe" = only log the config fields | "off"
  shop_pay_owned = true,               -- v0.71-DEV9: a bonus slot selling a weapon you ALREADY OWN cannot be bought (her screen shows it
                                       -- owned), so its bonus is given to you directly (~10 s after the weapon reads as yours). false = it
                                       -- waits for a purchase, as in DEV8
  -- exclude = "",                     -- items never randomized, e.g. "weapon:ryno_8,armor:pirate_head"
  start_omega = 1,                     -- DEV DEFAULT (v0.62-DEV5): start with this many random Omega versions (0-20),
                                       -- so every new game tests the Omega route (its weapon is given with it)
  omega_weapons = true,                -- DEV DEFAULT ON: CHALLENGE MODE (New Game+), 20 Omega versions are rewards
                                       -- of their own ("omega:burst_pistol" ...). An Omega found first also gives
                                       -- its weapon; the weapon found later never undoes the Omega (docs/OMEGA.md)
  omega_early = true,                  -- DEV DEFAULT (v0.71-DEV2, TEST): the Omega versions go on the locations the start can
                                       -- reach first (missions, pods, chests that would give Bolts or Raritanium). false = anywhere
  omega_test = 0,                      -- v0.71-DEV3: OFF (Omega weapons, Spybots and Lorbs passed their rounds). The test: every
                                       -- weapon reward - Gold Bolts, pods, missions, the start - arrives as its Omega version
                                       -- until you hold this many Omega weapons (0 = off, up to 20; it was 6 in v0.71-DEV2)

  weapon_xp = true,                    -- DEV DEFAULT (v0.71-DEV8): weapon XP joins the rewards - weapon_xp_percent of the
                                       -- locations that would give Bolts or Raritanium give weapon XP instead
  -- weapon_xp_percent = 25,           -- 0-100
  -- weapon_xp_min = 2000, weapon_xp_max = 20000,  -- XP per reward (later planets give more)
  weapon_xp_target = "smart",          -- "smart": an Omega weapon you hold gets the XP first (the one with the least XP),
                                       -- otherwise the weapon you hold with the least XP | "lowest": always the weapon
                                       -- you hold with the least XP

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

  -- ENEMIES AND BOSSES (the save remembers changes made with the in-game keys).
  -- These only decide the start of a save that has never used the keys; they do not change the seed.
  enemy_randomizer = true,             -- V4 DEFAULT ON: maximum-coverage regular enemy replacement starts before entering a level.
                                       -- become other regular enemies loaded on the same level (needs rando_give.dll v7)
  boss_randomizer = false,              -- boss-tier enemies are shuffled among themselves (story bosses never)
  enemy_notify = true,                 -- dev 10.29: a corner note "[ENEMY RANDOMIZER] SUCCESS - Original: X -> Replacement: Y"
                                       -- for every changed spawner's first spawn (false: only rivet.log)
  enemy_compat = "max",                -- v0.71-DEV8 DEV DEFAULT: "max" = as many enemies changed as possible: every regular enemy
                                       -- can become every other loaded on the level (walkers, flyers and turrets mixed), no
                                       -- pair is held back by earlier evidence, and a replacement that seems not to die is
                                       -- only logged. If an encounter makes you die or reload 5 times it keeps its original
                                       -- enemies for this seed. "all" = 10.31's rules (pairs that could not be killed are put
                                       -- back). "verified": only replacements with in-game proof they die.
                                       -- "trial": also untested ones of the same bot class, one spawner per level at a time.
  enemy_mix_movement = true,           -- v0.71-DEV8: true (the dev default) mixes walkers, flyers and turrets; false keeps
                                       -- them apart (round42: a walker at a flyer's spawn stood where it was hard to reach).
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
-- The - key turns the ENEMY RANDOMIZER on or off, the = key the BOSS RANDOMIZER (both OFF by default; remembered).
-- BACKSPACE turns the CHAOS RANDOMIZER on or off (off by default; remembered; no protection at all).
-- Ctrl+0 pressed twice sends your randomizer items again if some went missing.
