-- Randomizer 8.2: test travel - go to any planet, whatever Coordinates you hold (rivet_hook, Lua 5.4).
-- Loaded after 14_rando_travel.lua and 15_rando_hub.lua. Off unless test_travel = true in
-- 04_rando_settings.lua (a runtime option: it never changes the seed or its fingerprint).
--
-- Keys (test_travel = true):
--   F7          next planet (all 10, in story order, starting after the one you are on)
--   F8          next landing point on that planet
--   Ctrl+F7     warp there (rivet_hook's checkpoint warp, the one level scripts use)
--   Ctrl+F8     fly there with the ship (rivet.fly; needs the ship's planet menu nearby, e.g. at
--               a landing pad - round 17: Zurkie's -> CHK_NEFCITY_SHIP worked)
--
-- While it is on:
--   * a test trip's landing is only reported and remembered as that planet's landing point; the hub
--     does not start or finish destinations because of it (Zurkie's itself is the hub's as always)
--   * the ship's planet menu takes you anywhere: neither the hub nor locked levels send you back
--   * the hub's Corson V keeper and its startup guard do not move you
--   * the level bits (the planet menu's list) are put back after a load, as the hub does
--   * rewards follow the usual rules: test travel opens no Coordinates and pays nothing by itself
-- Every trip is written to the randomizer history as [TEST TRAVEL], so a run that used it shows it.
--
-- Landing points of a planet, best first: where you last landed there, the hub's own entry
-- points, the ones seen in your logs, then the checkpoint catalog (14_rando_travel.lua: every
-- checkpoint rivet.checkpoints() lists, placed on its planet and scored, landing pads first).
-- rivet.log lines start with RANDO-TEST.

RANDO_TEST_TRAVEL = RANDO_TEST_TRAVEL or {}
local TT = RANDO_TEST_TRAVEL
local DB = RANDO_DATA
local function log(...) pcall(rivet.log, "[rando]", "RANDO-TEST", ...) end
local function S() return RANDO and RANDO.state end
local function SEED() return RANDO_SEED end
local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) else pcall(rivet.notify, text, opts) end end
local function pname(pid) return (RANDO and RANDO.planet_name and RANDO.planet_name(pid)) or tostring(pid) end
local function now() return (rivet.time and rivet.time()) or 0 end
local function history(msg) if RANDO and RANDO.history then RANDO.history(msg) else log(msg) end end

TT.VERSION = "8.2.0"
TT.WINDOW = 180              -- seconds a trip waits for its landing
TT.POINTS = 12               -- landing points offered per planet (catalog)
TT.sel = TT.sel or 0         -- selected planet (index into DB.planets; not saved)
TT.point = TT.point or {}    -- pid -> selected landing point index (not saved)
TT.trip = nil                -- { planet, cp, how, at, from }

function TT.on()
  local c = RANDO and RANDO.config
  return c ~= nil and c.test_travel == true
end

local function planet_index(pid)
  for i, p in ipairs(DB.planets) do if p.id == pid then return i end end
  return nil
end

-- every landing point we know for a planet, best first (no duplicates, no planet tunnels)
function TT.points(pid)
  local out, seen = {}, {}
  local function add(cp, why)
    if type(cp) ~= "string" or cp == "" or seen[cp] then return end
    if cp:upper():find("TRANSITION_TO", 1, true) then return end
    seen[cp] = true
    out[#out + 1] = { cp = cp, why = why }
  end
  local s = S()
  local landed = s and s.travel and s.travel.landed
  if landed then add(landed[pid], "where you last landed") end
  local plan = SEED() and SEED().hub
  if plan then
    if pid == plan.planet then
      local h = s and s.hub
      add(h and h.home_cp, "the hub's landing")
      for _, cp in ipairs(plan.checkpoints or {}) do add(cp, "the hub's landing") end
    end
    for _, d in ipairs(plan.destinations or {}) do
      if d.planet == pid and d.entry then add(d.entry, "a hub destination's entry") end
    end
  end
  local i = planet_index(pid)
  local known = i and DB.planets[i].checkpoints and DB.planets[i].checkpoints.known
  for _, cp in ipairs(known or {}) do add(cp, "seen in your logs") end
  local T = RANDO_TRAVEL
  if T and T.ranked then
    for _, cp in ipairs(T.ranked(pid, TT.POINTS)) do add(cp, "checkpoint catalog") end
  end
  return out
end

-- how far the checkpoint catalog is (for the on-screen line)
local function catalog_note()
  local T = RANDO_TRAVEL
  local cat = T and T.catalog
  if not cat then return "the checkpoint list has not started yet" end
  if cat.done then return "the checkpoint list is complete" end
  return string.format("the checkpoint list is still being read (%d/%d)", math.min(cat.next - 1, #cat.filters), #cat.filters)
end

-- ask the catalog to hurry (one filter every frame, starting now)
local function hurry()
  local T = RANDO_TRAVEL
  if T then T.catalog_from = 0 end
  TT.want_catalog = true
end

function TT.selected()
  if TT.sel < 1 or TT.sel > #DB.planets then return nil end
  return DB.planets[TT.sel].id
end

local function show(pid)
  local pts = TT.points(pid)
  local n = #DB.planets
  local head = string.format("Test travel %d/%d: %s", TT.sel, n, pname(pid))
  if #pts == 0 then
    hurry()
    say(head .. " - no landing point known yet", { type = "center", duration = 7,
        sub = catalog_note() .. "; press F7 again in a few seconds, or use the ship's planet menu" })
    log("selected", pid, "- no landing point yet:", catalog_note())
    return
  end
  local k = TT.point[pid] or 1
  if k > #pts then k = 1 end
  TT.point[pid] = k
  local pt = pts[k]
  say(head, { type = "center", duration = 7,
      sub = string.format("%s (%d/%d, %s) - Ctrl+F7 warp, Ctrl+F8 fly, F8 next landing point", pt.cp, k, #pts, pt.why) })
  log("selected", pid, pt.cp, string.format("(%d/%d, %s)", k, #pts, pt.why))
end

local function off_message()
  say("Randomizer: test travel is off - set test_travel = true in 04_rando_settings.lua, then press Pause",
      { type = "center", duration = 6 })
end

-- F7: next planet
function TT.key_next()
  if not TT.on() then return off_message() end
  if TT.sel < 1 then
    local cur = S() and S().current_planet
    TT.sel = (cur and planet_index(cur)) or 0
  end
  TT.sel = (TT.sel % #DB.planets) + 1
  show(TT.selected())
end

-- F8: next landing point of the selected planet
function TT.key_point()
  if not TT.on() then return off_message() end
  local pid = TT.selected()
  if not pid then return TT.key_next() end
  local pts = TT.points(pid)
  if #pts > 0 then TT.point[pid] = ((TT.point[pid] or 1) % #pts) + 1 end
  show(pid)
end

-- Ctrl+F7 (warp) / Ctrl+F8 (fly)
function TT.go(how)
  if not TT.on() then return off_message() end
  local pid = TT.selected()
  if not pid then
    say("Randomizer: press F7 first to choose a planet", { type = "corner", duration = 4 })
    return false
  end
  local pts = TT.points(pid)
  local pt = pts[TT.point[pid] or 1]
  if not pt then show(pid); return false end
  local fn = (how == "fly") and rivet.fly or rivet.warp
  local ok, res = pcall(fn, pt.cp)
  if not ok or res == false then
    log(how, "to", pt.cp, "for", pid, "failed:", tostring(res))
    local hint = (how == "fly") and " - the ship's flight needs its planet menu nearby (a landing pad); Ctrl+F7 warps instead"
                 or " - F8 picks another landing point"
    say(string.format("Test travel: %s to %s failed (%s)%s", how, pt.cp, tostring(res), hint), { type = "center", duration = 8 })
    return false
  end
  local cur = S() and S().current_planet
  TT.trip = { planet = pid, cp = pt.cp, how = how, at = now(), from = cur }
  log(how, "to", pt.cp, "for", pid, "(" .. pt.why .. ") from", tostring(cur), tostring(res))
  history(string.format("[TEST TRAVEL] %s to %s (%s)", how, pid, pt.cp))
  say(string.format("Test travel: %s to %s", how == "fly" and "flying" or "warping", pname(pid)),
      { type = "corner", duration = 5, sub = pt.cp })
  return true
end

-- a landing (10_rando_runtime.lua's process_planet asks first). true = handled here.
function TT.on_arrival(pid, from)
  local trip = TT.trip
  if not trip then return false end
  if now() - trip.at > TT.WINDOW then
    log("the", trip.how, "to", trip.cp, "did not land within", TT.WINDOW, "s - forgotten")
    TT.trip = nil
    return false
  end
  if trip.planet ~= pid then
    log("passing", pid, "on the way to", trip.planet)
    return false
  end
  TT.trip = nil
  if RANDO_TRAVEL and RANDO_TRAVEL.remember then RANDO_TRAVEL.remember(pid, trip.cp) end
  log("arrived on", pid, "by", trip.how, "at", trip.cp)
  local plan = SEED() and SEED().hub
  if plan and pid == plan.planet then
    return false                       -- Zurkie's: the hub's own arrival (Ratchet, the level bits, F6)
  end
  if plan and RANDO_HUB and RANDO_HUB.check_levels and RANDO_HUB.enabled and RANDO_HUB.enabled() then
    pcall(RANDO_HUB.check_levels, pid)
  end
  local s = S()
  local open = s and s.access and s.access[pid]
  say(string.format("Test travel: %s", pname(pid)), { type = "planet", duration = 6,
      sub = open and "you hold its Coordinates" or "no Coordinates here - rewards follow the usual rules" })
  return true
end

-- the planet menu took you to a planet you hold no Coordinates for (14 / 15 call this)
function TT.stayed(pid, how)
  log("no Coordinates for", pid, "- staying (" .. tostring(how) .. ", test_travel is on)")
  history(string.format("[TEST TRAVEL] %s without Coordinates (%s)", pid, tostring(how)))
  say(string.format("Test travel: %s - no Coordinates, but you stay (test_travel is on)", pname(pid)),
      { type = "corner", duration = 6 })
end

function TT.status_text()
  if not TT.on() then return nil end
  return "TEST TRAVEL on (F7 / Ctrl+F7)"
end

-- keys
local function ctrl_down()
  local ctrl = false
  pcall(function() ctrl = rivet.is_key_down(rivet.key("CONTROL")) end)
  return ctrl
end
local function bind(setting, default, fn)
  local name = (RANDO and RANDO.config and RANDO.config[setting]) or default
  local okk, vk = pcall(rivet.key, name)
  if not okk then log("RANDO-ERROR key", tostring(name), tostring(vk)); return end
  pcall(rivet.on_key, vk, function()
    if not (SEED() and S()) then return end
    if not TT.on() then return off_message() end
    local ready = false
    pcall(function() ready = rivet.scene_ready() and rivet.hero() ~= nil end)
    if not ready then return say("Randomizer: wait until the game has loaded", { type = "corner", duration = 3 }) end
    local ok, err = pcall(fn, ctrl_down())
    if not ok then log("RANDO-ERROR key", tostring(name), tostring(err)) end
  end)
end
bind("key_test_travel", "F7", function(ctrl) if ctrl then TT.go("warp") else TT.key_next() end end)
bind("key_test_point", "F8", function(ctrl) if ctrl then TT.go("fly") else TT.key_point() end end)

log("loaded (" .. TT.VERSION .. ")" .. (TT.on() and " - test travel is ON: F7 planet, F8 landing point, Ctrl+F7 warp, Ctrl+F8 fly" or " - off"))
