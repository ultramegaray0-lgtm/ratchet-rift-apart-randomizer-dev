-- Randomizer 3.0 campaign layer: the mission registry, campaign sequence generation for every
-- mode, and the campaign constraints the progression solver (02_rando_generator.lua) uses.
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
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["03_rando_campaign"] = "8.5.0"   -- the kit check (10_rando_runtime.lua)
RANDO_CAMPAIGN = {}
local C = RANDO_CAMPAIGN
C.VERSION = "7.0.0"

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

C.MODES = {
  vanilla = "the game's own order; rewards randomized (2.0 behaviour)",
  planet_shuffle = "planets in a random order; each planet's visits keep their order",
  mission_shuffle = "every visit (including revisits) placed anywhere the dependencies allow",
  full = "mission shuffle with a random starting visit",
  chaos = "full, plus random story-ability order checks only (no soft ordering), more starting variety",
}
-- what the runtime must be able to do in the game for a mode (see 11_rando_campaign.lua)
C.NEEDS = {
  vanilla = {},
  planet_shuffle = { "mission_control", "travel" },
  mission_shuffle = { "mission_control", "travel" },
  full = { "mission_control", "travel", "new_game_init" },
  chaos = { "mission_control", "travel", "new_game_init" },
}

-- ---------------------------------------------------------------------------------------------
-- sequence generation
-- ---------------------------------------------------------------------------------------------
local function contains(t, v) for _, x in ipairs(t) do if x == v then return true end end return false end

-- hard rules every mode keeps:
--   * a revisit comes after the first visit of its planet (its scripts continue that story)
--   * the finale is last; with a fixed start, the intro is first
--   * a visit needing a story ability comes after the visit that grants it
function C.hard_ok(order, start_fixed)
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
  if start_fixed and order[1] ~= "corson_intro" then return false, "intro not first" end
  return true
end

-- a visit that can begin a campaign: no gadget or ability needs beyond the starting kit, not a
-- revisit, not the finale
function C.can_start(seg)
  return seg.kind ~= "finale" and seg.visit == 1 and #seg.requires == 0
end

-- builds a valid order by random topological insertion. rng: RANDO_GEN.rng
function C.sequence(mode, rng, random_start)
  local ids = {}
  for _, seg in ipairs(C.SEGMENTS) do ids[#ids + 1] = seg.id end
  if mode == "vanilla" then return ids, "corson_intro" end
  for _ = 1, 500 do
    local order
    if mode == "planet_shuffle" then
      -- shuffle planets by their first visit; revisits keep their vanilla slot relative to the
      -- shuffled first visits (inserted right after a random later point)
      local firsts, rest = {}, {}
      for _, seg in ipairs(C.SEGMENTS) do
        if seg.kind ~= "intro" and seg.kind ~= "finale" then
          if seg.visit == 1 then firsts[#firsts + 1] = seg.id else rest[#rest + 1] = seg.id end
        end
      end
      rng.shuffle(firsts)
      order = { "corson_intro" }
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
        if seg.kind ~= "finale" and not (seg.kind == "intro" and not random_start) then pool[#pool + 1] = seg.id end
      end
      rng.shuffle(pool)
      order = {}
      if not random_start then order[1] = "corson_intro" else
        local starts = {}
        for _, id in ipairs(pool) do if C.can_start(C.BY_ID[id]) then starts[#starts + 1] = id end end
        table.sort(starts)
        local first = rng.pick(starts)
        order[1] = first
        for i, id in ipairs(pool) do if id == first then table.remove(pool, i); break end end
      end
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
          if pos[seg.id] and pos[seg.id] < need and seg.kind ~= "finale" then
            table.remove(order, pos[seg.id])
            table.insert(order, math.min(need, #order), seg.id)   -- right after the last dependency
          end
        end
      end
    end
    local ok = C.hard_ok(order, not random_start)
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
  if order[1] ~= "corson_intro" then
    L[#L + 1] = "  Random start: a new game always opens with the intro. The randomizer completes it for you"
    L[#L + 1] = "  (its reward is paid then) and passes over its later slot. Needs the new_game_init capability."
  end
  local vanilla = true
  for i, id in ipairs(order) do if C.SEGMENTS[i].id ~= id then vanilla = false end end
  if not vanilla then
    L[#L + 1] = "  The order is followed only when the runtime's mission control is verified in your game"
    L[#L + 1] = "  (docs/CAMPAIGN.md). Until then you play the game's own order with these rewards; the seed"
    L[#L + 1] = "  is checked to be finishable in that order too."
  end
  return table.concat(L, "\n")
end

-- =============================================================================================
-- 8.0: ZURKIE'S BATTLEPLEX AS THE CAMPAIGN HUB
--
-- A hub seed starts at Zurkie's (the runtime, 15_rando_hub.lua, takes Ratchet there from the
-- parade). Every other visit of the registry is a DESTINATION. The player picks any open one;
-- finishing it gives the next Coordinates of the seed's unlock queue. Two Coordinates are open
-- at the start, on two different planets.
--
-- What decides "open" (the custom randomized progression table):
--   * a planet destination needs its planet's Coordinates (start pair, then the queue: every
--     finished destination gives the next `per_completion` of them);
--   * Zurkie's own visits (kind "hub") are played at the hub and need no Coordinates;
--   * a revisit needs its first visit (`after`), and a visit needing a story ability needs the
--     visit whose story grants it (Viceron: the Phantom Dash of Nefarious City and the Hurlshot
--     of Torren IV) - the game's own dependencies, kept because the missions' scripts expect them;
--   * the finale needs every other destination (or half of them, hub_finale = "half"); its
--     Coordinates (Corson V) are given when it opens.
-- C.hub_check explores EVERY order a player could choose (all subsets of finished destinations,
-- 2^12 states) and accepts a plan only if no reachable state leaves nothing to do before the
-- finale. So whatever the player picks, the campaign goes on.
-- =============================================================================================
C.HUB_PLANET = "scarstu"
C.HUB_CHECKPOINTS = { "CHK_ZURK_00_DEFAULT", "CHK_ZURK_LANDING_SHIP" }   -- round 14 line 171; round 13/16
C.FINALE_PLANET = "corson_v"

-- the destinations of a hub campaign, in registry order
function C.hub_destinations(revisits)
  local out = {}
  for _, seg in ipairs(C.SEGMENTS) do
    if seg.kind ~= "intro" and (revisits ~= false or seg.visit == 1 or seg.kind == "finale") then
      local abilities = {}
      for _, r in ipairs(seg.requires) do
        local ab = r:match("^ability:(.+)$")
        if ab then abilities[#abilities + 1] = ab end
      end
      local after = {}
      for _, a in ipairs(seg.after) do
        if revisits ~= false or C.BY_ID[a].visit == 1 then after[#after + 1] = a end
      end
      out[#out + 1] = {
        id = seg.id, planet = seg.planet, visit = seg.visit, hero = seg.hero, title = seg.title, boss = seg.boss,
        missions = seg.missions, entry = seg.entry, after = after, abilities = abilities, grants = seg.grants,
        kind = (seg.kind == "finale") and "finale" or ((seg.planet == C.HUB_PLANET) and "hub" or "planet"),
      }
    end
  end
  return out
end

-- planets a destination can start on: its first visit needs nothing but the starting kit
local function hub_start_candidates(dests)
  local ok, seen = {}, {}
  for _, d in ipairs(dests) do
    if d.kind == "planet" and d.visit == 1 and #d.abilities == 0 and #d.after == 0 and not seen[d.planet] then
      seen[d.planet] = true; ok[#ok + 1] = d.planet
    end
  end
  table.sort(ok)
  return ok
end

-- which destinations are open after `done` (set of ids) with `n` finished
function C.hub_open_planets(plan, n)
  local open = {}
  for _, pid in ipairs(plan.start) do open[pid] = true end
  local k = math.min(#plan.queue, n * plan.per_completion)
  for i = 1, k do open[plan.queue[i]] = true end
  return open
end
function C.hub_available(plan, done, n)
  local open = C.hub_open_planets(plan, n)
  local granted = {}
  for id in pairs(done) do
    local seg = C.BY_ID[id]
    for _, g in ipairs(seg and seg.grants or {}) do granted[g] = true end
  end
  local total, fin = 0, nil
  for _, d in ipairs(plan.destinations) do if d.kind ~= "finale" then total = total + 1 else fin = d end end
  local out = {}
  for _, d in ipairs(plan.destinations) do
    if not done[d.id] then
      local ok
      if d.kind == "finale" then
        ok = n >= (plan.finale_after or total)
      else
        ok = (d.kind == "hub") or open[d.planet] == true
        for _, a in ipairs(d.after) do if not done[a] then ok = false end end
        for _, ab in ipairs(d.abilities) do if not granted[ab] then ok = false end end
      end
      if ok then out[#out + 1] = d.id end
    end
  end
  return out
end

-- explores every order: true, or false and the first dead end found. yield (optional) is the
-- in-game generator's slice point: the check gives the frame back every 64 situations
function C.hub_check(plan, yield)
  local ids = {}
  for _, d in ipairs(plan.destinations) do if d.kind ~= "finale" then ids[#ids + 1] = d.id end end
  local bit = {}
  for i, id in ipairs(ids) do bit[id] = 1 << (i - 1) end
  local full = (1 << #ids) - 1
  local seen = {}
  local stack = { 0 }
  local states = 0
  while #stack > 0 do
    local mask = table.remove(stack)
    if not seen[mask] then
      seen[mask] = true
      states = states + 1
      if yield and states % 64 == 0 then yield() end
      local done, n = {}, 0
      for i, id in ipairs(ids) do if mask & (1 << (i - 1)) ~= 0 then done[id] = true; n = n + 1 end end
      local avail = C.hub_available(plan, done, n)
      if #avail == 0 then
        local list = {}
        for _, id in ipairs(ids) do if done[id] then list[#list + 1] = id end end
        return false, "dead end after " .. (#list > 0 and table.concat(list, ", ") or "nothing"), states
      end
      if mask == full then
        local fin = false
        for _, id in ipairs(avail) do if C.BY_ID[id].kind == "finale" then fin = true end end
        if not fin then return false, "the finale does not open after everything", states end
      else
        for _, id in ipairs(avail) do
          if bit[id] then stack[#stack + 1] = mask | bit[id] end
        end
      end
    end
  end
  return true, nil, states
end

-- the plan of one seed. rng: RANDO_GEN.rng (its own stream, so hub settings never change the
-- item placement of the same seed text). s: normalized settings.
function C.hub_plan(s, rng, yield)
  local dests = C.hub_destinations(s.hub_revisits)
  local planets = {}
  local seen = {}
  for _, d in ipairs(dests) do
    if d.kind == "planet" and not seen[d.planet] then seen[d.planet] = true; planets[#planets + 1] = d.planet end
  end
  local cands = hub_start_candidates(dests)
  local want = math.min(s.hub_start_coordinates or 2, #cands)
  local total = 0
  for _, d in ipairs(dests) do if d.kind ~= "finale" then total = total + 1 end end
  local finale_after = (s.hub_finale == "half") and math.ceil(total / 2) or total
  for attempt = 1, 200 do
    local pool = {}
    for _, p in ipairs(cands) do pool[#pool + 1] = p end
    rng.shuffle(pool)
    local start = {}
    for i = 1, want do start[i] = pool[i] end
    table.sort(start)
    local rest = {}
    local in_start = {}
    for _, p in ipairs(start) do in_start[p] = true end
    for _, p in ipairs(planets) do if not in_start[p] then rest[#rest + 1] = p end end
    rng.shuffle(rest)
    local plan = {
      version = 1, planet = C.HUB_PLANET, checkpoints = C.HUB_CHECKPOINTS, finale_planet = C.FINALE_PLANET,
      start = start, queue = rest, per_completion = s.hub_unlocks or 1, finale_after = finale_after,
      destinations = dests, finale = "finale", attempt = attempt,
    }
    local ok, why, states = C.hub_check(plan, yield)
    if ok then
      plan.states_checked = states
      -- one way through, for the spoiler (always the first open destination in registry order)
      local done, n, path = {}, 0, {}
      while true do
        local av = C.hub_available(plan, done, n)
        if #av == 0 then break end
        local pick = av[1]
        path[#path + 1] = pick
        done[pick] = true
        n = n + 1
        if C.BY_ID[pick].kind == "finale" then break end
      end
      plan.example = path
      return plan
    end
    plan.last_error = why
  end
  return nil, "no hub plan without a dead end"
end

-- what finishing the n-th destination opens
function C.hub_unlocks_at(plan, n)
  local out = {}
  local a = (n - 1) * plan.per_completion + 1
  for i = a, math.min(#plan.queue, n * plan.per_completion) do out[#out + 1] = plan.queue[i] end
  return out
end

function C.hub_describe(plan, planet_name)
  local L = {}
  local name = planet_name or function(p) return p end
  L[#L + 1] = string.format("  Start: Zurkie's Battleplex (%s). Starting Coordinates: %s and %s.", plan.checkpoints[1],
                            name(plan.start[1] or "?"), name(plan.start[2] or "?"))
  if #plan.start > 2 then
    local extra = {}
    for i = 3, #plan.start do extra[#extra + 1] = name(plan.start[i]) end
    L[#L + 1] = "  More starting Coordinates: " .. table.concat(extra, ", ")
  end
  L[#L + 1] = plan.per_completion == 1 and "  Each finished destination gives the next Coordinates in this order:"
              or string.format("  Each finished destination gives the next %d Coordinates in this order:", plan.per_completion)
  for i, pid in ipairs(plan.queue) do
    L[#L + 1] = string.format("    %2d. %s (after your %s destination)", i, name(pid),
                              ({ "1st", "2nd", "3rd" })[math.ceil(i / plan.per_completion)] or (math.ceil(i / plan.per_completion) .. "th"))
  end
  L[#L + 1] = string.format("  The finale (%s) opens after %d finished destinations; its Coordinates come then.",
                            name(plan.finale_planet), plan.finale_after)
  L[#L + 1] = "  Destinations (any order the rules allow):"
  for _, d in ipairs(plan.destinations) do
    local rule = {}
    if d.kind == "hub" then rule[#rule + 1] = "at the hub" end
    if d.kind == "planet" then rule[#rule + 1] = "needs " .. name(d.planet) .. " Coordinates" end
    for _, a in ipairs(d.after) do rule[#rule + 1] = "after " .. a end
    for _, ab in ipairs(d.abilities) do rule[#rule + 1] = "needs the story's " .. ab end
    if d.kind == "finale" then rule[#rule + 1] = "last" end
    L[#L + 1] = string.format("    %-13s %-34s %-7s %s", d.id, name(d.planet), d.hero or "", table.concat(rule, "; "))
  end
  L[#L + 1] = "  One way through: " .. table.concat(plan.example or {}, " > ")
  L[#L + 1] = string.format("  Checked: every order you could choose (%d situations) leaves something to do until the finale.",
                            plan.states_checked or 0)
  return table.concat(L, "\n")
end
