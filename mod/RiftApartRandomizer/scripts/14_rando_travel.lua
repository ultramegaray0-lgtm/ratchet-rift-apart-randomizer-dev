-- Randomizer 7.0: locked levels (rivet_hook, Lua 5.4). Loaded after 10_rando_runtime.lua.
--
-- With levels = true (seed.travel_lock) each planet's travel is locked behind its Coordinates.
-- What your game allows, and what this script does with it:
--   * Your game's mission system cannot open a mission out of order (rounds 14-15, CAMPAIGN.md),
--     so the STORY keeps the game's own mission order. The seed's solver proves that whenever the
--     story needs a planet, its Coordinates were findable on planets already open.
--   * The game cannot be stopped from flying (events cannot be vetoed), so a locked planet is
--     enforced AFTER the landing: if you chose it in the ship's planet menu (PlanetMenuAcceptEvent,
--     seen in rounds 14 and 16) and hold no Coordinates for it, rivet_hook's warp takes you back
--     to the planet you came from, to the checkpoint you last landed on there.
--   * Planet changes the game makes by itself are NEVER blocked: the parade's rifts, the rift
--     jumps inside missions (round 16: Nefarious City -> Savali -> Nefarious City), the story's own
--     travel (Nefarious City -> Sargasso) and loading a save all come without a planet-menu event.
--   * If no checkpoint to go back to is known, or the warp fails, the planet stays playable and
--     its rewards wait for its Coordinates instead (the 6.0 "banked" rule) - said on screen.
--   * Escape hatch: Ctrl+F9 twice opens the planet you were last sent back from (its Coordinates
--     are given, marked [OPENED BY HAND] in the history). The solver makes it unnecessary; it is
--     there in case the game's story differs from the model somewhere.
--   * levels_runtime = false in 04_rando_settings.lua turns the warp off (rewards wait instead).
-- Nothing here changes the game's files, missions or saves; a warp moves the save's checkpoint to
-- the planet you came from, which is where you were anyway.

RANDO_TRAVEL = RANDO_TRAVEL or {}
local T = RANDO_TRAVEL
local DB = RANDO_DATA
local function log(...) pcall(rivet.log, "[rando]", "RANDO-TRAVEL", ...) end
local function R() return RANDO end
local function S() return RANDO and RANDO.state end
local function SEED() return RANDO_SEED end
local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) end end
local function now() return (rivet.time and rivet.time()) or 0 end

T.MENU_WINDOW = 180          -- seconds a planet-menu choice waits for its landing (rift transitions are long)
T.SETTLE_FRAMES = 180        -- frames after the landing (scene and hero ready) before the warp
T.HATCH_WINDOW = 4           -- seconds between the two Ctrl+F9 presses
T.pending = nil              -- the last planet-menu choice not landed yet
T.warp = nil                 -- { to, planet, from, at_frame }
T.frame = 0

function T.active()
  local seed, s = SEED(), S()
  if not (seed and s and seed.travel_lock) then return false end
  if RANDO and RANDO.config and RANDO.config.levels_runtime == false then return false end
  return true
end

local function state()
  local s = S()
  s.travel = s.travel or { landed = {}, sent_back = 0, banked_planets = {} }
  s.travel.landed = s.travel.landed or {}
  s.travel.banked_planets = s.travel.banked_planets or {}
  return s.travel
end

-- which planet a checkpoint name belongs to: a name token starting with one of the planet's codes
-- (CHK_ZURK_00_DEFAULT -> scarstu, CHK_TRANSITION_TO_ZURKIES -> scarstu); the longest code wins
function T.planet_of_checkpoint(name)
  if type(name) ~= "string" then return nil end
  local up = name:upper()
  local best, blen = nil, 0
  for _, p in ipairs(DB.planets) do
    for _, code in ipairs((p.checkpoints and p.checkpoints.codes) or {}) do
      for tok in up:gmatch("[^_]+") do
        if tok:sub(1, #code) == code and #code > blen then best, blen = p.id, #code end
      end
    end
  end
  return best
end

-- 8.1: the checkpoint catalog. rivet.checkpoints(filter) lists the level's checkpoints whose name
-- contains filter, each with the top-level area it is in (round 17: "Zurkons", "Sargasso (open
-- world)", "Blizar_Destroyed", "interplanetary_space" for the planet tunnels). Torren IV and
-- Cordelion have no LANDING / SHIP / DEFAULT checkpoint, so 8.0 found nothing there: the catalog
-- now places every listed checkpoint on its planet by its area (the planet's "areas" fragments)
-- or else by its name (the planet's codes), and scores them, landing pads first, cinematics,
-- bosses and planet tunnels last. It is filled one filter per frame (T.catalog_step) so no
-- single callback lists the whole level.
T.PREFER = { "LANDINGPAD", "LANDING", "SHIP", "00_DEFAULT", "DEFAULT" }
T.SCORE = {
  { "LANDINGPAD", 100 }, { "LANDING", 90 }, { "_SHIP", 80 }, { "00_DEFAULT", 75 }, { "DEFAULT", 70 },
  { "ARRIVAL", 45 }, { "ARRIVE", 45 }, { "ENTRANCE", 40 }, { "_START", 35 }, { "_00_", 25 }, { "_01_", 20 },
}
T.AVOID = { "TRANSITION_TO", "CINE", "BOSS", "FINALE", "DEBUG", "TEST", "ARENA", "CHALLENGE", "_END",
            "DEATH", "RETURN", "ESCAPE", "PSHIFT", "REVISIT", "POSTMISSION", "WARPBACK", "TELEPORTER" }
T.CATALOG_SLICE = 128
T.catalog = nil              -- { planets = { [pid] = { [name] = area } }, filters = {...}, next = i, done = bool }

function T.score_checkpoint(name)
  local up = tostring(name):upper()
  local score = 0
  for _, s in ipairs(T.SCORE) do if up:find(s[1], 1, true) then score = math.max(score, s[2]) end end
  for _, a in ipairs(T.AVOID) do if up:find(a, 1, true) then score = score - 60 end end
  return score
end

-- which planet an area name belongs to (nil for interplanetary_space and unknown areas)
function T.planet_of_area(area)
  if type(area) ~= "string" or area == "" then return nil end
  local low = area:lower()
  if low:find("interplanetary", 1, true) then return nil end
  for _, p in ipairs(DB.planets) do
    for _, frag in ipairs((p.checkpoints and p.checkpoints.areas) or {}) do
      if low:find(frag, 1, true) then return p.id end
    end
  end
  return nil
end

-- the planet a listed checkpoint is on: its area first, its name second
function T.place(name, area)
  if type(name) ~= "string" then return nil end
  if name:upper():find("TRANSITION_TO", 1, true) then return nil end
  return T.planet_of_area(area) or T.planet_of_checkpoint(name)
end

local function entry_of(c)
  if type(c) == "table" then return c.name or c[1], c.area or c[4] or "" end
  return c, ""
end

function T.catalog_filters()
  local out, seen = {}, {}
  local function add(f) if f and not seen[f] then seen[f] = true; out[#out + 1] = f end end
  for _, f in ipairs({ "LANDING", "SHIP", "DEFAULT", "START" }) do add(f) end
  for _, p in ipairs(DB.planets) do
    for _, code in ipairs((p.checkpoints and p.checkpoints.codes) or {}) do add(code) end
  end
  add("CHK_")                                -- last: everything the level lists (2048 at most)
  return out
end

-- add one rivet.checkpoints() answer to the catalog (entries first..last); returns how many it placed
function T.catalog_add(list, first, last)
  local cat = T.catalog
  local n = 0
  list = list or {}
  for i = first or 1, math.min(last or #list, #list) do
    local name, area = entry_of(list[i])
    local pid = T.place(name, area)
    if pid then
      cat.planets[pid] = cat.planets[pid] or {}
      if cat.planets[pid][name] == nil then n = n + 1 end
      cat.planets[pid][name] = area or ""
    end
  end
  return n
end

function T.catalog_reset()
  T.catalog = { planets = {}, filters = T.catalog_filters(), next = 1, done = false, errors = 0 }
end

-- one filter per call (call it once a frame). Returns true when the catalog is complete.
function T.catalog_step()
  if not T.catalog then T.catalog_reset() end
  local cat = T.catalog
  if cat.done then return true end
  local f = cat.filters[cat.next]
  if not f and not cat.pending then
    cat.done = true
    local parts = {}
    for _, p in ipairs(DB.planets) do
      local best = T.best_in_catalog(p.id)
      local count = 0
      for _ in pairs(cat.planets[p.id] or {}) do count = count + 1 end
      parts[#parts + 1] = string.format("%s %d%s", p.id, count, best and ("=" .. best) or "")
    end
    log("checkpoint catalog:", table.concat(parts, ", "))
    return true
  end
  if cat.pending then                        -- a long answer is placed T.CATALOG_SLICE entries a frame
    local pd = cat.pending
    T.catalog_add(pd.list, pd.at, pd.at + T.CATALOG_SLICE - 1)
    pd.at = pd.at + T.CATALOG_SLICE
    if pd.at > #pd.list then cat.pending = nil end
    return false
  end
  cat.next = cat.next + 1
  local ok, list = pcall(rivet.checkpoints, f)
  if ok and type(list) == "table" then
    if #list > T.CATALOG_SLICE then cat.pending = { list = list, at = 1 } else T.catalog_add(list) end
  else
    cat.errors = cat.errors + 1
    if cat.errors <= 3 then log("checkpoints", f, "not listed:", tostring(list)) end
  end
  return false
end

-- every checkpoint of a planet the catalog holds, best first
function T.ranked(pid)
  local cat = T.catalog
  local names = {}
  for name in pairs((cat and cat.planets[pid]) or {}) do names[#names + 1] = name end
  table.sort(names, function(a, b)
    local sa, sb = T.score_checkpoint(a), T.score_checkpoint(b)
    if sa ~= sb then return sa > sb end
    if #a ~= #b then return #a < #b end
    return a < b
  end)
  return names
end
function T.best_in_catalog(pid)
  return T.ranked(pid)[1]
end

-- the whole catalog of one planet, for rivet.log (what the next round should name)
function T.describe_planet(pid, limit)
  local names = T.ranked(pid)
  local out = {}
  for i = 1, math.min(#names, limit or 24) do
    out[#out + 1] = string.format("%s(%d)", names[i], T.score_checkpoint(names[i]))
  end
  return string.format("%d: %s", #names, table.concat(out, " "))
end

-- a checkpoint on planet pid to warp to: where you last landed there, then the ones seen in your
-- logs, then the catalog, then rivet.checkpoints() searched by the planet's codes right now
function T.checkpoint_for(pid)
  local tr = state()
  if tr.landed[pid] then return tr.landed[pid], "where you last landed" end
  local p
  for _, x in ipairs(DB.planets) do if x.id == pid then p = x end end
  if not p then return nil end
  local known = p.checkpoints and p.checkpoints.known
  if known and known[1] then return known[1], "seen in your logs" end
  local best = T.best_in_catalog(pid)
  if best then return best, "checkpoint catalog" end
  if not T.catalog then T.catalog_reset() end
  for _, code in ipairs((p.checkpoints and p.checkpoints.codes) or {}) do
    local ok, list = pcall(rivet.checkpoints, code)
    if ok and type(list) == "table" then T.catalog_add(list) end
  end
  best = T.best_in_catalog(pid)
  if best then return best, "rivet.checkpoints" end
  return nil
end

-- PlanetMenuAcceptEvent { DestinationCheckpointName, InterplanetaryCheckpointName }
function T.on_menu_accept(f)
  if not (SEED() and S()) then return end
  local dest = f.DestinationCheckpointName
  local cur = RANDO and RANDO.state and RANDO.state.current_planet
  T.pending = { dest = dest, planet = T.planet_of_checkpoint(dest) or T.planet_of_checkpoint(f.InterplanetaryCheckpointName),
                from = cur, at = now() }
  log("planet menu:", tostring(dest), "->", tostring(T.pending.planet), "from", tostring(cur))
end

-- a planet arrival the runtime has processed (scene ready). Returns true when the arrival is
-- locked and handled here (sent back, or its rewards banked).
function T.on_arrival(pid, from)
  if not T.active() then T.pending = nil; return false end
  local s, tr = S(), state()
  local p = T.pending
  if p and now() - p.at > T.MENU_WINDOW then p = nil; T.pending = nil end
  if p and p.planet and p.planet ~= pid then
    return false                       -- a planet passed on the way (keep waiting for the landing)
  end
  T.pending = nil
  if not p then
    log("arrived on", pid, "without the planet menu (the story, a rift or a load): never blocked")
    return false
  end
  if s.access[pid] then
    if p.dest then tr.landed[pid] = p.dest end
    log("arrived on", pid, "(open) at", tostring(p.dest))
    return false
  end
  local back_to = p.from or from
  if not back_to or back_to == pid or not s.access[back_to] then
    -- where you came from is unknown or locked too: the nearest open planet in story order
    back_to = nil
    for _, x in ipairs(DB.planets) do if s.access[x.id] and x.id ~= pid then back_to = back_to or x.id end end
  end
  local cp, how = nil, nil
  if back_to then cp, how = T.checkpoint_for(back_to) end
  local name = RANDO.planet_name(pid)
  tr.last_locked = pid
  if not cp then
    T.bank(pid, "no checkpoint known to send you back to " .. tostring(back_to))
    return true
  end
  T.warp = { to = cp, planet = pid, from = back_to, at_frame = T.frame + T.SETTLE_FRAMES, how = how }
  log("locked:", pid, "- warping back to", back_to, "at", cp, "(" .. tostring(how) .. ") in", T.SETTLE_FRAMES, "frames")
  say(string.format("Randomizer: no Coordinates for %s yet - back to %s", name, RANDO.planet_name(back_to)),
      { type = "center", duration = 6 })
  return true
end

-- the planet stays playable; its rewards wait for its Coordinates (the 6.0 rule)
function T.bank(pid, why)
  local tr = state()
  tr.banked_planets[pid] = true
  if RANDO.mark_changed then RANDO.mark_changed() end
  log("locked:", pid, "- not sent back (" .. why .. "): its rewards wait for its Coordinates")
  say(string.format("Randomizer: no Coordinates for %s yet - rewards here wait for them", RANDO.planet_name(pid)),
      { type = "center", duration = 6 })
end
-- does a location on this planet wait for Coordinates? (10_rando_runtime.lua asks)
function T.banks(pid)
  local s = S()
  if not (s and pid) or s.access[pid] then return false end
  if not T.active() then return true end           -- levels off at runtime: rewards wait instead
  return state().banked_planets[pid] == true
end

-- where a planet was landed on (the planet menu's destination, a warp that landed): the first
-- choice next time. Used by the hub too (15_rando_hub.lua).
function T.remember(pid, cp)
  if not (pid and type(cp) == "string" and cp ~= "") then return end
  if cp:upper():find("TRANSITION_TO", 1, true) then return end
  local s = S()
  if not s then return end
  local tr = state()
  if tr.landed[pid] ~= cp then
    tr.landed[pid] = cp
    log("landing on", pid, "remembered:", cp)
    if RANDO and RANDO.mark_changed then RANDO.mark_changed() end
  end
end

function T.catalog_wanted()
  if T.catalog and T.catalog.done then return false end
  if type(rivet.checkpoints) ~= "function" then return false end
  return T.active() or (SEED() and SEED().hub ~= nil)
end

function T.tick(frame, ready)
  T.frame = frame
  -- the catalog: one filter every 4 frames, every frame while a hub trip waits for it
  local every = (RANDO_HUB and RANDO_HUB.wait_catalog) and 1 or 4
  if ready and frame % every == 0 and T.catalog_wanted() and frame >= (T.catalog_from or 600) then T.catalog_step() end
  local w = T.warp
  if not (w and ready) or frame < w.at_frame then return end
  T.warp = nil
  local s, tr = S(), state()
  if s.access[w.planet] then log("Coordinates for", w.planet, "arrived meanwhile: staying"); return end
  local ok, res = pcall(rivet.warp, w.to)
  if ok and res ~= false then
    tr.sent_back = (tr.sent_back or 0) + 1
    if RANDO.mark_changed then RANDO.mark_changed() end
    log("warped back to", w.from, "at", w.to, "(" .. tostring(res) .. ")")
  else
    log("warp to", w.to, "failed:", tostring(res))
    T.bank(w.planet, "the warp failed")
  end
end

-- Ctrl+F9 twice: open the planet you were last sent back from
local hatch_at = -100
function T.hatch()
  local tr = state()
  local pid = tr.last_locked
  if not pid or S().access[pid] then say("Randomizer: no locked planet to open", { type = "corner", duration = 4 }); return false end
  local t = now()
  if t - hatch_at > T.HATCH_WINDOW then
    hatch_at = t
    say(string.format("Randomizer: press Ctrl+F9 again to open %s by hand (it is recorded in the history)", RANDO.planet_name(pid)),
        { type = "center", duration = 5 })
    return false
  end
  hatch_at = -100
  tr.opened_by_hand = (tr.opened_by_hand or 0) + 1
  log("[OPENED BY HAND]", pid)
  if RANDO.history then RANDO.history("[OPENED BY HAND] Coordinates for " .. pid .. " (Ctrl+F9)") end
  RANDO.grant("access:" .. pid, false, "[OPENED BY HAND] ")
  return true
end

function T.status_text()
  local seed, s = SEED(), S()
  if not (seed and s and seed.travel_lock) then return nil end
  local n = 0
  for _ in pairs(s.access) do n = n + 1 end
  return string.format("planets open %d/%d%s", n, #DB.planets, T.active() and "" or " (warp off)")
end

function T.new_game() T.pending, T.warp = nil, nil end

pcall(rivet.on_event, "PlanetMenuAcceptEvent", function(ev)
  local ok, err = pcall(T.on_menu_accept, ev.fields or {})
  if not ok then log("RANDO-ERROR menu", tostring(err)) end
end)
log("loaded")
