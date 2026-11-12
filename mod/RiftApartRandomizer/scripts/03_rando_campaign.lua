-- Randomizer 3.0 campaign layer: the mission registry, campaign sequence generation for every
-- mode, and the campaign constraints the progression solver (02_rando_generator.lua) uses.
--
-- 9.0: THE STORY STARTS AS IN THE GAME. A new game plays the prologue (the parade on Corson V),
-- then Nefarious City, then Sargasso: the visits the game itself takes you to (arrival =
-- "story", C.STORY_START). Every campaign order of every mode begins with them, in that order;
-- only the visits after them are reordered. The Zurkie's hub of 8.0-8.5 (and random_start, a
-- campaign that began somewhere else) is gone.
--
-- 7.0: the same registry drives the LEVEL-LOCKED campaign (levels = true). The story keeps the
-- game's own mission order (your game cannot open a mission out of order, docs/CAMPAIGN.md), but
-- each planet's travel is locked behind its Coordinates, which are items of the seed. A visit
-- marked arrival = "story" is one the game itself takes you to (no planet menu): those planets
-- are open from the start, because the randomizer never blocks the story's own travel.
--
-- A campaign is an ordered list of SEGMENTS. A segment is one visit to a planet: the game's
-- missions for that visit, in their own order (a mission's scripts expect the missions before it
-- on the same visit, so a visit is never split). Modes reorder the segments; the solver proves
-- the order can be played with the items the seed hands out.
--
-- Provenance of every entry (field `src`):
--   game   mission name seen in your rivet.log (MissionStateChangedEvent)
--   dag    name found in your game's dag (Phase 1 research: story-mission overlay regions)
--   guide  public walkthrough (gamepressure mission list, vulkk gear guide); NOT verified in the
--          game files. The research kit (companion/research/Research-Campaign.bat) replaces these
--          with the real names; tools/build_campaign_registry.py merges them.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["03_rando_campaign"] = "9.0.0"   -- the kit check (10_rando_runtime.lua)
RANDO_CAMPAIGN = {}
local C = RANDO_CAMPAIGN
C.VERSION = "9.0.0"

-- story abilities: no item config exists, so only the story itself hands them out
C.STORY_ABILITIES = { phantom_dash = true, hurlshot = true, speetle = true, dragon_mount = true, wallrun = true }

-- src "game": a mission name of the visit was seen in your game (round 14: the level scripts'
-- mission variables, MissionStateChanged / devstats events). A visit may list more than one
-- name: the director uses the first and the last name the game's mission table holds, so a
-- guessed name that does not exist does no harm (lab Ctrl+F12 lists which exist).
C.SEGMENTS = {
  { id = "corson_intro", planet = "corson_v", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_INTRO" }, entry = nil, kind = "intro", arrival = "story",
    title = "Parade, pursue Dr. Nefarious" },
  { id = "nefcity_1", planet = "nefarious_city", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_NEFCITY_01" }, entry = "CHK_NEFCITY_SHIP", arrival = "story",
    grants = { "phantom_dash" }, title = "Market, Club Nefarious, follow the Phantom, the statue" },
  { id = "sargasso_1", planet = "sargasso", visit = 1, hero = "rivet", src = "game",
    missions = { "MIS_SARG_01_FIRST_VISIT", "MIS_SARG_01_CLANKPUZZLE" }, boss = "Seekerpede", arrival = "story",
    title = "Reach the Morts, Rivet's hideout, Seekerpede" },
  { id = "scarstu_1", planet = "scarstu", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_ZURK_01_VISIT_01" }, entry = "CHK_ZURK_LANDING_SHIP", boss = "Francois (arena)",
    title = "Zurkie's Gastropub, defeat Francois" },
  { id = "savali_1", planet = "savali", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_SAV_01" }, entry = "CHK_SAV_01_LANDING",
    title = "Village attack, Lombax lore, three temples, the Archives" },
  { id = "blizar_1", planet = "blizar_prime", visit = 1, hero = "rivet", src = "game",
    missions = { "MIS_BLIZAR" }, entry = "CHK_BLIZAR_A_LANDINGPAD",
    title = "Blockade, the miners, the drill, Phase Quartz" },
  { id = "torren_1", planet = "torren_iv", visit = 1, hero = "rivet", src = "game",
    missions = { "MIS_MOL_01_FIRST_VISIT" }, requires = { "hoverboots" },
    grants = { "hurlshot" }, boss = "the Fixer (chase)", title = "Find the Fixer, the Hurlshot, escape" },
  { id = "cordelion_1", planet = "cordelion", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_CORD_01_FIRST_VISIT" }, entry = "CHK_CORD_A_START", boss = "Cordelion boss",
    title = "Kedaro Station, the Rubion Forge, a new Dimensionator" },
  { id = "scarstu_2", planet = "scarstu", visit = 2, hero = "rivet", src = "game",
    missions = { "MIS_ZURK_02B_VISIT_02B" }, after = { "scarstu_1" }, title = "Meet Ratchet in the Gastropub" },
  { id = "ardolis_1", planet = "ardolis", visit = 1, hero = "ratchet", src = "game",
    missions = { "MIS_ARD_01_FIRST_VISIT" }, entry = "CHK_ARD_START", requires = { "hoverboots" },
    title = "Pierre Le Fer, treasure hunt, Pirate Trials, Captain Quantum" },
  { id = "sargasso_2", planet = "sargasso", visit = 2, hero = "rivet", src = "game",
    missions = { "MIS_SARG_02_REVISIT_SHIPS" }, entry = "CHK_SARG_02_MININGPLATFORM_LANDINGPAD", after = { "sargasso_1" },
    title = "Protect the Morts, free the Seekerpede, Nefarious' ships" },
  { id = "savali_2", planet = "savali", visit = 2, hero = "ratchet", src = "game",
    missions = { "MIS_SVALI_02_SECOND_VISIT" }, after = { "savali_1" }, title = "The Archives' machines, the catacombs" },
  { id = "viceron_1", planet = "viceron", visit = 1, hero = "rivet", src = "game",
    missions = { "MIS_ZORD_01" }, entry = "CHK_ZORDOOM_START", requires = { "ability:phantom_dash", "ability:hurlshot" },
    boss = "Zordoom Prison warden", title = "Find Ratchet and Kit, reactor shutdown, follow the cell" },
  { id = "finale", planet = "corson_v", visit = 2, hero = "ratchet", src = "game",
    missions = { "MIS_MEGA_FINALE" }, entry = "CHK_MEGA_FINALE_START", kind = "finale", boss = "Emperor Nefarious",
    title = "The final battle" },
}
-- 8.4 (round 20): the hero of each visit, checked against the walkthroughs (Ratchet & Clank wiki
-- plot; gamepressure; thegamer) and against round 17/20: a story's first "go to <planet>" step
-- finished only when the visit's own hero was there (Ardolis, Savali, Zurkie's 1 as Ratchet: at
-- once; Torren IV, Viceron as Ratchet and Nefarious City as Rivet: never). Four heroes were wrong
-- and are fixed: nefcity_1 Ratchet ("Ratchet awakens in Nefarious City"), sargasso_2 Rivet ("Rivet
-- and Kit fly to Sargasso"), ardolis_1 Ratchet ("Ratchet and Clank fly to Ardolis"), viceron_1
-- Rivet ("Rivet flies to Zordoom Prison"). Entries: CHK_ARD_START (round 20: the story ran from
-- it), CHK_CORD_A_START and CHK_ZORDOOM_START (listed by rivet.checkpoints() in round 19).
-- 8.1 (round 17 research, rando_give.dll v6 queries): MIS_BLIZAR_01, MIS_CORD_BOSS, MIS_ZURK_02,
-- MIS_SARG_02_REVISIT and MIS_MEGA_01_RIVET are "not a mission in your game"; the names above all
-- exist (MIS_BLIZAR from MissionStateChanged events). Entries CHK_SARG_02_MININGPLATFORM_LANDINGPAD
-- and CHK_MEGA_FINALE_START are listed by rivet.checkpoints() in your game (not warped to yet).
-- 7.0 arrival = "story" evidence (round 16 rivet.log): the parade's rifts end on Nefarious City
-- (lines 200-221, no PlanetMenuAcceptEvent), and when MIS_NEFCITY_01 completes the game starts
-- MIS_SARG_01_FIRST_VISIT and changes the planet to Sargasso by itself (lines 338-344). The first
-- planet-menu travel in every log is the one to Zurkie's (round 14 line 171, round 16 line 390).
function C.story_arrival_planets()
  local out, seen = {}, {}
  for _, seg in ipairs(C.SEGMENTS) do
    if seg.arrival == "story" and not seen[seg.planet] then seen[seg.planet] = true; out[#out + 1] = seg.planet end
  end
  return out
end
C.BY_ID = {}
for i, seg in ipairs(C.SEGMENTS) do seg.index = i; seg.requires = seg.requires or {}; seg.grants = seg.grants or {}; seg.after = seg.after or {}; C.BY_ID[seg.id] = seg end

-- 9.0: the start every campaign has, in this order: the prologue, then the visits the story itself
-- travels to next (the parade's rifts end on Nefarious City; finishing MIS_NEFCITY_01 takes you to
-- Sargasso, round 16 lines 338-344). Built from the registry: the leading run of arrival = "story".
C.STORY_START = {}
for _, seg in ipairs(C.SEGMENTS) do
  if seg.arrival ~= "story" then break end
  C.STORY_START[#C.STORY_START + 1] = seg.id
end
C.IN_STORY_START = {}
for i, id in ipairs(C.STORY_START) do C.IN_STORY_START[id] = i end

-- where each 2.0 location sits in the campaign (the visit whose content holds it)
C.LOCATION_SEGMENT = {
  ["planet:corson_v"] = "corson_intro", ["story2:corson_v"] = "finale",
  ["planet:nefarious_city"] = "nefcity_1", ["story2:nefarious_city"] = "nefcity_1",
  ["planet:sargasso"] = "sargasso_1", ["story2:sargasso"] = "sargasso_2",
  ["planet:scarstu"] = "scarstu_1", ["story2:scarstu"] = "scarstu_2",
  ["planet:savali"] = "savali_1", ["story2:savali"] = "savali_2",
  ["planet:blizar_prime"] = "blizar_1", ["story2:blizar_prime"] = "blizar_1",
  ["planet:torren_iv"] = "torren_1", ["story2:torren_iv"] = "torren_1",
  ["planet:cordelion"] = "cordelion_1", ["story2:cordelion"] = "cordelion_1",
  ["planet:ardolis"] = "ardolis_1", ["story2:ardolis"] = "ardolis_1",
  ["planet:viceron"] = "viceron_1",
  ["side:zurkies_bronze"] = "scarstu_1", ["side:zurkies_silver"] = "scarstu_1", ["side:zurkies_gold"] = "scarstu_2",
  ["side:sargasso_trudi"] = "sargasso_2", ["side:blizar_chef"] = "blizar_1", ["side:ardolis_mapomatic"] = "ardolis_1",
}
-- Gold Bolts: the first visit of their planet (open-world content of that planet)
function C.location_segment(lid, planet)
  local s = C.LOCATION_SEGMENT[lid]
  if s then return s end
  if planet then
    for _, seg in ipairs(C.SEGMENTS) do if seg.planet == planet and seg.visit == 1 then return seg.id end end
  end
  return nil
end

-- (the default mode is campaign_mode in 02_rando_generator.lua's G.DEFAULTS: planet_shuffle)
-- 9.0: every mode starts with the prologue, Nefarious City and Sargasso (C.STORY_START)
C.MODES = {
  vanilla = "the game's own order; rewards randomized (2.0 behaviour)",
  planet_shuffle = "after the story's start, planets in a random order; each planet's visits keep their order",
  mission_shuffle = "after the story's start, every visit (including revisits) placed anywhere the dependencies allow",
  full = "mission shuffle (9.0: the same start as every mode)",
  chaos = "mission shuffle with story-ability order checks only (9.0: the same start as every mode)",
}
-- what the runtime must be able to do in the game for a mode (see 11_rando_campaign.lua). 9.0: no
-- mode skips the prologue any more, so none needs new_game_init
C.NEEDS = {
  vanilla = {},
  planet_shuffle = { "mission_control", "travel" },
  mission_shuffle = { "mission_control", "travel" },
  full = { "mission_control", "travel" },
  chaos = { "mission_control", "travel" },
}

-- ---------------------------------------------------------------------------------------------
-- sequence generation
-- ---------------------------------------------------------------------------------------------
local function contains(t, v) for _, x in ipairs(t) do if x == v then return true end end return false end

-- hard rules every mode keeps:
--   * 9.0: the order begins with the story's start (prologue, Nefarious City, Sargasso)
--   * a revisit comes after the first visit of its planet (its scripts continue that story)
--   * the finale is last
--   * a visit needing a story ability comes after the visit that grants it
-- (the second argument of 3.0-8.5, start_fixed, is ignored: the start is always fixed)
function C.hard_ok(order)
  local pos = {}
  for i, id in ipairs(order) do pos[id] = i end
  for _, seg in ipairs(C.SEGMENTS) do
    local p = pos[seg.id]
    if not p then return false, "missing " .. seg.id end
    for _, a in ipairs(seg.after) do if pos[a] > p then return false, seg.id .. " before " .. a end end
    for _, r in ipairs(seg.requires) do
      local ab = r:match("^ability:(.+)$")
      if ab then
        local granted = false
        for _, other in ipairs(C.SEGMENTS) do
          if contains(other.grants, ab) and pos[other.id] < p then granted = true end
        end
        if not granted then return false, seg.id .. " needs " .. ab .. " before it" end
      end
    end
  end
  if order[#order] ~= "finale" then return false, "finale not last" end
  for i, id in ipairs(C.STORY_START) do
    if order[i] ~= id then return false, "the story's start is not " .. table.concat(C.STORY_START, " > ") end
  end
  if #order ~= #C.SEGMENTS then return false, "visits twice or missing" end
  return true
end

-- builds a valid order by random topological insertion. rng: RANDO_GEN.rng. 9.0: the order always
-- begins with C.STORY_START; the third argument of 3.0-8.5 (random_start) is ignored.
function C.sequence(mode, rng)
  local ids = {}
  for _, seg in ipairs(C.SEGMENTS) do ids[#ids + 1] = seg.id end
  if mode == "vanilla" then return ids, ids[1] end
  for _ = 1, 500 do
    local order
    if mode == "planet_shuffle" then
      -- shuffle planets by their first visit; revisits keep their vanilla slot relative to the
      -- shuffled first visits (inserted right after a random later point)
      local firsts, rest = {}, {}
      for _, seg in ipairs(C.SEGMENTS) do
        if seg.kind ~= "finale" and not C.IN_STORY_START[seg.id] then
          if seg.visit == 1 then firsts[#firsts + 1] = seg.id else rest[#rest + 1] = seg.id end
        end
      end
      rng.shuffle(firsts)
      order = {}
      for _, id in ipairs(C.STORY_START) do order[#order + 1] = id end
      for _, id in ipairs(firsts) do order[#order + 1] = id end
      for _, id in ipairs(rest) do
        local first = C.BY_ID[C.BY_ID[id].after[1]]
        local at
        for i, x in ipairs(order) do if x == first.id then at = i end end
        local slot = rng.int(at + 1, #order + 1)
        table.insert(order, slot, id)
      end
      order[#order + 1] = "finale"
    else
      local pool = {}
      for _, seg in ipairs(C.SEGMENTS) do
        if seg.kind ~= "finale" and not C.IN_STORY_START[seg.id] then pool[#pool + 1] = seg.id end
      end
      rng.shuffle(pool)
      order = {}
      for _, id in ipairs(C.STORY_START) do order[#order + 1] = id end
      for _, id in ipairs(pool) do order[#order + 1] = id end
      order[#order + 1] = "finale"
      -- repair: move each revisit after its first visit, and ability needs after their grant
      for _ = 1, 3 do
        for _, seg in ipairs(C.SEGMENTS) do
          local deps = {}
          for _, a in ipairs(seg.after) do deps[#deps + 1] = a end
          for _, r in ipairs(seg.requires) do
            local ab = r:match("^ability:(.+)$")
            if ab then for _, o in ipairs(C.SEGMENTS) do if contains(o.grants, ab) then deps[#deps + 1] = o.id end end end
          end
          local pos = {}
          for i, id in ipairs(order) do pos[id] = i end
          local need = 0
          for _, d in ipairs(deps) do if pos[d] and pos[d] > need then need = pos[d] end end
          if pos[seg.id] and pos[seg.id] < need and seg.kind ~= "finale" and not C.IN_STORY_START[seg.id] then
            table.remove(order, pos[seg.id])
            table.insert(order, math.min(need, #order), seg.id)   -- right after the last dependency
          end
        end
      end
    end
    local ok = C.hard_ok(order)
    if ok then return order, order[1] end
  end
  return nil, "no valid order"
end

-- the campaign constraint object the solver uses
-- returns { order = {...}, index = {seg_id = n}, loc_segment = {lid = n}, segments = {...} }
function C.build(order, s, db_locations)
  local camp = { order = order, index = {}, loc_segment = {}, segments = {}, vanilla = true }
  for i, id in ipairs(order) do if not C.SEGMENTS[i] or C.SEGMENTS[i].id ~= id then camp.vanilla = false end end
  for i, id in ipairs(order) do
    camp.index[id] = i
    local seg = C.BY_ID[id]
    camp.segments[i] = { id = id, planet = seg.planet, requires = seg.requires, grants = seg.grants, boss = seg.boss }
  end
  for lid, loc in pairs(db_locations) do
    local sid = C.location_segment(lid, loc.planet)
    if sid and camp.index[sid] then camp.loc_segment[lid] = camp.index[sid] end
  end
  camp.planet_locks = s.planet_locks
  return camp
end

-- how far the campaign gets with what is owned: the number of visits that can be played in
-- order. owned: item key -> count (randomizer items + start); weapons_needed(i) per visit index
function C.reach(camp, owned, start_kit, wcount, weapons_needed)
  local abilities = {}
  for k in pairs(start_kit or {}) do abilities[k] = true end
  for i, seg in ipairs(camp.segments) do
    for _, r in ipairs(seg.requires) do
      local ab = r:match("^ability:(.+)$")
      if ab then
        if not abilities[ab] then return i - 1, "needs " .. ab end
      elseif not start_kit[r] and (owned[r] or 0) == 0 then
        return i - 1, "needs " .. r
      end
    end
    -- (with levels = true the story-arrival planets are open from the start: 02's start rules)
    if camp.planet_locks and (owned["access:" .. seg.planet] or 0) == 0 then return i - 1, "needs Coordinates for " .. seg.planet end
    if seg.boss and weapons_needed and wcount < weapons_needed(i) then return i - 1, "needs weapons for " .. seg.boss end
    for _, g in ipairs(seg.grants) do abilities[g] = true end
  end
  return #camp.segments
end

-- spoiler text for the campaign
function C.describe(order)
  local L = {}
  for i, id in ipairs(order) do
    local seg = C.BY_ID[id]
    local need = (#seg.requires > 0) and ("  needs " .. table.concat(seg.requires, ", ")) or ""
    local gives = (#seg.grants > 0) and ("  story gives " .. table.concat(seg.grants, ", ")) or ""
    L[#L + 1] = string.format("  %2d. %-13s %-15s %-8s %s%s%s%s", i, id, seg.planet, seg.hero,
                              seg.title or "", seg.boss and ("  [boss: " .. seg.boss .. "]") or "", need, gives)
  end
  L[#L + 1] = "  A new game plays the prologue, then Nefarious City, then Sargasso, as in the game; only the"
  L[#L + 1] = "  visits after them are reordered."
  local vanilla = true
  for i, id in ipairs(order) do if C.SEGMENTS[i].id ~= id then vanilla = false end end
  if not vanilla then
    L[#L + 1] = "  The order is followed only when the runtime's mission control is verified in your game"
    L[#L + 1] = "  (docs/CAMPAIGN.md). Until then you play the game's own order with these rewards; the seed"
    L[#L + 1] = "  is checked to be finishable in that order too."
  end
  return table.concat(L, "\n")
end
