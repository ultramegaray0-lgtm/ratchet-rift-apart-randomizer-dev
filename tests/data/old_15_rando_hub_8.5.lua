-- Randomizer 8.0: Zurkie's Battleplex as the campaign hub (rivet_hook, Lua 5.4).
-- Loaded after 10_rando_runtime.lua, 11_rando_campaign.lua and 14_rando_travel.lua. Active only
-- for a seed made with hub = true (the "hub" preset, the 8.0 default).
--
-- EXPERIMENTAL. Nothing here has run in the game yet. What it does, step by step, and what each
-- step rests on (docs/HUB.md and docs/RESEARCH_8.0.md have the details):
--
--  1. NEW GAME -> ZURKIE'S. The game itself always begins a new save with the parade (the
--     mission graph's NewGameLoadInfo; it cannot be changed from a script). The runtime watches
--     the parade's objectives (seen in rounds 14 and 15) and, once Ratchet has his wrench
--     (OBJ_INTRO_PARADE_PICKUP_WRENCH done), warps him with rivet_hook's checkpoint warp (the
--     engine's own, the one level scripts use) to CHK_ZURK_00_DEFAULT, the checkpoint the ship's
--     planet menu lands on at Zurkie's (round 14 line 171). Fallbacks: CHK_ZURK_LANDING_SHIP,
--     then any ZURK checkpoint rivet.checkpoints() lists. The save's current checkpoint moves to
--     Zurkie's with the warp. If the parade comes back on a later load, the runtime takes you
--     back to Zurkie's.
--  2. THE PROLOGUE. hub_intro = "force" writes "Complete Finished" (4) into MIS_INTRO's saved
--     state record through rando_give.dll v6 (the walk State() itself makes, byte-checked), so
--     the save no longer holds an active prologue. Its randomizer reward is paid at once.
--  3. TWO COORDINATES. The seed's two starting Coordinates (two different planets) open on
--     arrival. F6 lists the destinations you can play now, Ctrl+F6 goes there: the ship's own
--     flight (rivet.fly) when a ship is near, otherwise the checkpoint warp. The ship's planet
--     menu works too: a planet without Coordinates sends you back to Zurkie's.
--  4. A DESTINATION'S STORY. On arrival the runtime asks the game for the visit's missions
--     (rando_give.dll, the game's own State()) and tries, in order: start an available mission
--     (exactly what StartMissionAction does); hub_force_missions: write "Available" (1) into an
--     inactive mission's record, then start it; replay it (ReplayMissionAction's call). If none
--     of that makes the mission active, the destination is played as EXPLORE: its Gold Bolts,
--     armor pods and side activities pay as always, and Ctrl+F5 twice finishes it by hand.
--     Rivet's visits swap the hero to Rivet first (rivet.hero_play_as, the game's own swap).
--  5. FINISHING. A destination finishes when the last of its missions completes
--     (MissionStateChangedEvent 3/4 or MissionCompleteEvent), or by hand. Its randomizer rewards
--     are paid (the planet's story-mission and side locations of that visit), the next
--     Coordinates of the seed's queue open, and after hub_return_delay seconds the warp takes
--     you back to Zurkie's (F5 cancels). The finale opens when every destination is finished.
--  6. THE SHIP'S MENU AND THE LEVEL MASK. At Zurkie's the runtime turns planetary travel on
--     (SetPlanetaryTravelAction's byte) and, with hub_levels = "all", sets every bit
--     UnlockLevelAction can set (levels 1-10), in case the planet menu reads them. Both are logged
--     before and after (RANDO-HUB levels), with the mask on every planet, to learn what they are.
--  7. RESEARCH. Once per session at Zurkie's, read-only: the helper's v6 report, every
--     destination mission's state, MIS_INTRO's record, the LANDING / ZURK / MEGA checkpoints and
--     the loaded Mission* configs go into rivet.log (RANDO-HUB research).
--
-- Keys (8.3 defaults; the old F keys still work with legacy_f_keys): ] next destination, Ctrl+] go,
-- [ twice back to Zurkie's (cancels an automatic return), Ctrl+[ twice finish this destination by
-- hand, / start the story of the planet you are on, Ctrl+/ twice start it again. Before the hub
-- has started (a save from before 8.0, or the warp failed), Ctrl+] goes to Zurkie's and starts it.
--
-- 8.3 THE STORY ON ARRIVAL: landing on a planet (test travel, the ship's menu, a hub trip) starts
-- that planet's first unfinished story, whatever came before it (H.story_here).
--
-- 8.4 (round 20) THE HERO DECIDES WHETHER A STORY STARTS. A story's first step ("go to <planet>")
-- finished at once when the visit's own hero was on the planet (Ardolis, Savali, Zurkie's 1 as
-- Ratchet) and never with the other hero (Torren IV and Viceron as Ratchet, Nefarious City as
-- Rivet in round 17). Round 20 played those as the wrong hero because the save's remembered hero
-- ("rivet") was trusted while the game had Ratchet: every swap was skipped or refused with
-- "already playing as that hero". Now:
--   * the hero is never taken from the save: rivet.hero_play_as answers "already playing as that
--     hero" exactly when the hero is the one asked for, and that answer is the check (H.ensure_hero);
--   * a story is started only after its hero is confirmed (H.activate);
--   * a hub trip (and a test-travel warp) gets the hero and starts the story BEFORE it travels
--     (story_prime_before_travel), so the planet loads with its story active, as Savali did;
--   * a story whose first step is still waiting after the start is reloaded once: out to Zurkie's
--     (or, for Zurkie's own visits, another planet) and straight back (story_reload_stuck). Round
--     20's Viceron finished that step on its reload. The 8.3 restart of an active mission is gone
--     from the automatic path: in round 20 it changed the state but never moved the story.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["15_rando_hub"] = "8.5.0"   -- the kit check (10_rando_runtime.lua)
RANDO_HUB = RANDO_HUB or {}
local H = RANDO_HUB
local C = RANDO_CAMPAIGN
local DB = RANDO_DATA
H.VERSION = "8.5.0"

local function log(...) pcall(rivet.log, "[rando]", "RANDO-HUB", ...) end
local function S() return RANDO and RANDO.state end
local function SEED() return RANDO_SEED end
local function D() return RANDO_CAMPAIGN_RT end
local function cfg(k, default)
  local c = RANDO and RANDO.config
  if c and c[k] ~= nil then return c[k] end
  return default
end
local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) else pcall(rivet.notify, text, opts) end end
local function pname(pid) return (RANDO and RANDO.planet_name and RANDO.planet_name(pid)) or tostring(pid) end
local function changed() if RANDO and RANDO.mark_changed then RANDO.mark_changed() end end
-- 8.3: the key a setting names, for on-screen text ("]", "Ctrl+]")
local function K(setting, ctrl) return (RANDO and RANDO.key and RANDO.key(setting, ctrl)) or setting end
local function history(msg) if RANDO and RANDO.history then RANDO.history(msg) else log(msg) end end
local function now() return (rivet.time and rivet.time()) or 0 end

-- timings (frames at 60 per second)
H.CATALOG_WAIT = 1800       -- frames a trip waits for the checkpoint catalog
H.SETTLE = 180              -- after a landing, before acting (scene, hero, HUD)
H.ARRIVE_TIMEOUT = 3600     -- a travel that has not landed after this is tried another way
H.MENU_WINDOW = 180         -- seconds a planet-menu choice waits for its landing
H.NEXT_MISSION_WAIT = 600   -- after a visit's mission completes, before acting on the next one
H.STARTUP_GUARD = 7200      -- after the hub starts, unexpected travel is undone (the story's own)
H.TRIGGER_TIMEOUT = 5400    -- New Game seen but the trigger objective never came: go anyway
H.CONFIRM = 4               -- seconds for the second press of F5 / Ctrl+F5
H.KEEPER_MAX = 3            -- parade-on-load corrections per session
H.STUCK_WAIT = 1200         -- 8.3: after a start, frames before a story still at "go to <planet>" is reported
H.HERO_EVERY = 60           -- 8.4: frames between hero checks while a swap is under way
H.HERO_TRIES = 15           -- 8.4: checks before a swap counts as failed (about 15 s)
H.PRIME_TIMEOUT = 900       -- 8.4: a trip waits at most this long for its story to be primed
H.BOUNCE_TIMEOUT = 7200     -- 8.4: a reload trip that has not come back by then is forgotten

H.frame = 0
H.session = H.session or { new_game = nil, control = nil, wrench = nil, researched = false, keeper = 0, started = {} }
H.session.started = H.session.started or {}   -- 8.3: missions this session started (name -> frame)
H.session.reloaded = H.session.reloaded or {} -- 8.4: destinations reloaded this session (id -> frame)
H.bounce = nil              -- 8.4: a reload trip in flight: { dest, via, at }
H.force_restart = {}        -- 8.3: destination id -> true (Ctrl+story key twice)
H.expect = nil              -- our own travel in flight: { planet, dest, at, how, cp, tries }
H.menu = nil                -- the last planet-menu choice: { planet, dest, at }
H.pending = nil             -- something to do after a settle: { at, fn, why }
H.ladder = nil              -- the mission ladder running for a destination
H.sel = 0                   -- F6 selection (not saved)

-- ---------------------------------------------------------------------------------------------
-- state
-- ---------------------------------------------------------------------------------------------
function H.plan() local sd = SEED(); return sd and sd.hub end
function H.enabled()
  return H.plan() ~= nil and cfg("hub_runtime", true) ~= false
end
function H.state()
  local s = S()
  if not s then return nil end
  local h = s.hub
  if type(h) ~= "table" then h = {}; s.hub = h end
  h.open = h.open or {}
  h.done = h.done or {}
  h.n_done = h.n_done or 0
  h.attempts = h.attempts or {}
  h.by_hand = h.by_hand or {}
  h.level_seen = h.level_seen or {}
  h.phase = h.phase or "pre"
  h.hero = h.hero or "ratchet"
  h.obj = h.obj or {}               -- 8.3: mission -> { o = last objective, s = its state }
  return h
end
local function dest_by_id(id)
  local p = H.plan()
  for _, d in ipairs((p and p.destinations) or {}) do if d.id == id then return d end end
  return nil
end
H.dest = dest_by_id
function H.home_checkpoint()
  local p = H.plan()
  local h = H.state()
  if h and h.home_cp then return h.home_cp end
  return p and p.checkpoints and p.checkpoints[1]
end

-- the planets open now: start pair, the queue up to what finished destinations unlocked, the
-- finale's planet once enough is done. Newly opened ones are announced.
function H.sync_open(quiet)
  local p, h, s = H.plan(), H.state(), S()
  if not (p and h) then return {} end
  local opened = {}
  local want = C.hub_open_planets(p, h.n_done)
  local total = 0
  for _, d in ipairs(p.destinations) do if d.kind ~= "finale" then total = total + 1 end end
  if h.n_done >= (p.finale_after or total) then want[p.finale_planet] = true end
  for pid in pairs(want) do
    if not h.open[pid] then
      h.open[pid] = true
      s.access[pid] = true
      opened[#opened + 1] = pid
    end
  end
  table.sort(opened)
  if #opened > 0 then
    changed()
    local names = {}
    for _, pid in ipairs(opened) do names[#names + 1] = pname(pid); history("Coordinates: " .. pid .. " (hub)") end
    log("Coordinates opened:", table.concat(opened, ", "))
    if not quiet then
      say("Coordinates: " .. table.concat(names, " and ") .. " - " .. K("key_hub") .. " to choose, " .. K("key_hub", true) .. " to go", { type = "center", duration = 7 })
    end
  end
  return opened
end

-- destinations playable now (ids, registry order)
function H.available()
  local p, h = H.plan(), H.state()
  if not (p and h) then return {} end
  local done = {}
  for id in pairs(h.done) do done[id] = true end
  return C.hub_available(p, done, h.n_done)
end

function H.status_text()
  if not H.plan() then return nil end
  local h = H.state()
  if not h then return nil end
  if not h.started then return "hub: not started (" .. K("key_hub", true) .. " to go to Zurkie's)" end
  local p = H.plan()
  local total = #p.destinations
  local cur = h.current and dest_by_id(h.current)
  return string.format("hub %d/%d done%s%s", h.n_done, total, cur and (" | at " .. cur.id) or "",
                       H.enabled() and "" or " (hub_runtime off)")
end

-- ---------------------------------------------------------------------------------------------
-- travel
-- ---------------------------------------------------------------------------------------------
-- the checkpoint for a destination: its registry entry, then 14's learned / known / searched one
function H.checkpoint_for(d_or_pid)
  local pid, entry = d_or_pid, nil
  if type(d_or_pid) == "table" then pid, entry = d_or_pid.planet, d_or_pid.entry end
  local p = H.plan()
  if p and pid == p.planet then return H.home_checkpoint(), "the hub" end
  if entry then return entry, "registry" end
  if RANDO_TRAVEL and RANDO_TRAVEL.checkpoint_for then
    local ok, cp, how = pcall(RANDO_TRAVEL.checkpoint_for, pid)
    if ok and cp then return cp, how end
  end
  return nil, "no checkpoint known"
end

-- go somewhere: fly when asked and a ship answers, else warp. Returns true when the game took it.
function H.travel(pid, dest, prefer_fly, why)
  local cp, how = H.checkpoint_for(dest or pid)
  local T = RANDO_TRAVEL
  if not cp and T and T.catalog_wanted and T.catalog_wanted() then
    -- the catalog is still being filled (one filter every few frames): the trip waits for it
    H.wait_catalog = { pid = pid, dest = dest and dest.id, prefer_fly = prefer_fly, why = why, at = H.frame }
    T.catalog_from = 0
    log("travel to", pid, "waits for the checkpoint catalog")
    say("Randomizer: looking for a landing point on " .. pname(pid) .. "...", { type = "corner", duration = 3 })
    return true
  end
  if not cp then
    -- 8.1: every planet is in the ship's menu (the level bits), and a menu landing on a planet you
    -- hold Coordinates for starts its destination and teaches the hub that landing checkpoint
    local cat = T and T.catalog
    log("travel to", pid, "impossible:", how, cat and ("(catalog " .. (cat.done and "complete" or "still filling") .. ")") or "")
    if T and T.describe_planet then log("catalog for", pid, T.describe_planet(pid)) end
    say("Randomizer: no warp point known for " .. pname(pid) .. " yet - fly there from the ship's planet menu",
        { type = "center", sub = "the landing is remembered for next time", duration = 8 })
    return false
  end
  local method, ok, res = nil, false, nil
  if prefer_fly and cfg("hub_fly", true) then
    ok, res = pcall(rivet.fly, cp)
    method = "fly"
    if not ok then log("fly to", cp, "refused:", tostring(res), "- warping instead") end
  end
  if not ok then
    ok, res = pcall(rivet.warp, cp)
    method = "warp"
  end
  if not ok or res == false then
    log("travel to", pid, "at", cp, "failed:", tostring(res))
    say("Randomizer: the trip to " .. pname(pid) .. " failed (" .. tostring(res) .. ")", { type = "center", duration = 6 })
    return false
  end
  H.expect = { planet = pid, dest = dest and dest.id or nil, at = H.frame, how = method, cp = cp, why = why, how_found = how,
               tries = ((H.expect and H.expect.planet == pid) and H.expect.tries or 0) + 1 }
  log("travel:", method, "to", cp, "(" .. tostring(how) .. ") for", pid, dest and dest.id or "", why or "", tostring(res))
  return true
end

-- the warp to Zurkie's (start, return, keeper). A ZURK checkpoint the game lists is the last resort.
function H.zurk_candidates()
  local p = H.plan()
  local out, seen = {}, {}
  local function add(cp) if cp and not seen[cp] then seen[cp] = true; out[#out + 1] = cp end end
  local h = H.state()
  add(h and h.home_cp)
  for _, cp in ipairs((p and p.checkpoints) or {}) do add(cp) end
  local ok, list = pcall(rivet.checkpoints, "ZURK")
  if ok and type(list) == "table" then
    local names = {}
    for _, c in ipairs(list) do
      local n = type(c) == "table" and (c.name or c[1]) or c
      if type(n) == "string" and not n:find("TRANSITION", 1, true) then names[#names + 1] = n end
    end
    table.sort(names)
    for _, want in ipairs({ "LANDING", "DEFAULT", "SHIP" }) do
      for _, n in ipairs(names) do if n:find(want, 1, true) then add(n) end end
    end
  end
  return out
end
function H.go_home(why)
  local p, h = H.plan(), H.state()
  if not (p and h) then return false end
  if S().current_planet == p.planet and h.phase ~= "pre" and h.phase ~= "to_hub" then
    log("already at Zurkie's (" .. tostring(why) .. ")")
    H.at_hub("already there")
    return true
  end
  local cands = H.zurk_candidates()
  local start = (H.expect and H.expect.planet == p.planet and H.expect.cand or 0) + 1
  for i = start, #cands do
    local ok, res = pcall(rivet.warp, cands[i])
    if ok and res ~= false then
      H.expect = { planet = p.planet, at = H.frame, how = "warp", cp = cands[i], cand = i, why = why, tries = i }
      log("warp to Zurkie's at", cands[i], "(" .. tostring(why) .. ")", tostring(res))
      return true
    end
    log("warp to", cands[i], "failed:", tostring(res))
  end
  H.expect = nil
  return false
end

-- ---------------------------------------------------------------------------------------------
-- the hub
-- ---------------------------------------------------------------------------------------------
-- New Game (10_rando_runtime.lua calls this after starting the seed over)
function H.new_game()
  H.expect, H.menu, H.pending, H.ladder, H.sel = nil, nil, nil, nil, 0
  H.bounce, H.priming, H.watching, H.hero_job = nil, nil, nil, nil
  H.return_at, H.wait_catalog, H.force_restart = nil, nil, {}
  -- 8.5: this session's record of the old run must not steer the new one (a destination reloaded
  -- in the old run could not be reloaded again; the old start's guard window). The parade's own
  -- markers (new_game, control, wrench) were just set by the objective that started this.
  local ss = H.session
  ss.started, ss.reloaded, ss.keeper, ss.started_frame, ss.researched = {}, {}, 0, nil, false
  local h = H.state()
  if h then h.phase = "pre" end
  log("new game: waiting for the parade's", cfg("hub_trigger", "wrench") == "wrench" and "wrench" or "first control", "to go to Zurkie's")
end

-- the parade's objectives (every ObjectiveStateChangedEvent, also before the seed is ready)
function H.on_objective(mission, objective, state)
  -- 8.3: every mission's latest objective (a story waiting at "go to <planet>" is restarted)
  if type(mission) == "string" and type(objective) == "string" and H.plan() and S() then
    local h = H.state()
    if h then h.obj[mission] = { o = objective, s = state, f = H.frame } end
  end
  if mission ~= "MIS_INTRO" then return end
  if objective == "OBJ_INTRO_PARADE_START_CINE" and state == 1 then
    H.session.new_game, H.session.control, H.session.wrench = H.frame, nil, nil
  elseif objective == "OBJ_INTRO_PARADE_START" and state == 1 then
    H.session.control = H.session.control or H.frame
  elseif objective == "OBJ_INTRO_PARADE_PICKUP_WRENCH" and state == 2 then
    H.session.wrench = H.session.wrench or H.frame
  end
end

local function trigger_met()
  local ss = H.session
  if not ss.new_game then return false end
  local t = cfg("hub_trigger", "wrench")
  if t == "cinematic" then return true end
  if t == "control" and ss.control then return true end
  if ss.wrench then return true end
  return H.frame - ss.new_game >= H.TRIGGER_TIMEOUT, "the trigger objective did not come"
end

function H.begin_hub(why)
  local h = H.state()
  if not h or h.started then return end
  h.phase = "to_hub"
  changed()
  log("going to Zurkie's:", why)
  say("Randomizer: to Zurkie's Battleplex - the randomized campaign starts there", { type = "center", duration = 6 })
  if not H.go_home("hub start") then
    H.start_failed("no Zurkie's checkpoint could be warped to")
  end
end

-- the warp never landed: the hub still opens (travel keys work from anywhere)
function H.start_failed(why)
  local h = H.state()
  log("could not reach Zurkie's:", why)
  say("Randomizer: could not reach Zurkie's (" .. why .. ") - your Coordinates are open; " .. K("key_hub") .. " / " .. K("key_hub", true) .. " travel from anywhere",
      { type = "center", duration = 9 })
  H.hub_started("unreached")
  h.phase = "hub_unreached"
end

-- first arrival: the start of the hub campaign
function H.hub_started(how)
  local h, p, s = H.state(), H.plan(), S()
  if h.started then return end
  h.started, h.started_how = true, how
  h.started_frame = H.frame
  h.phase = "hub"
  H.session.started_frame = H.frame
  history("HUB: the campaign starts at Zurkie's (" .. tostring(how) .. ")")
  H.sync_open(true)
  local names = {}
  for _, pid in ipairs(p.start) do names[#names + 1] = pname(pid) end
  -- the prologue's reward: it is skipped
  if SEED().locations["planet:corson_v"] and RANDO and RANDO.collect then
    RANDO.collect("planet:corson_v", "the prologue (the hub starts at Zurkie's)")
  end
  say("Zurkie's Battleplex: Coordinates for " .. table.concat(names, " and ") .. " - " .. K("key_hub") .. " to choose, " .. K("key_hub", true) .. " to go",
      { type = "planet", sub = "Finish a destination to open the next Coordinates", duration = 10 })
  changed()
  H.after(H.SETTLE, function() H.intro_done(); H.apply_world(); H.research() end, "hub start")
end

-- every arrival at Zurkie's
function H.at_hub(how)
  local h, p = H.state(), H.plan()
  if not h.started then return H.hub_started(how) end
  h.phase = "hub"
  -- back at the hub: a planet destination you left stays open (F6 / the menu take you back)
  local cur = h.current and dest_by_id(h.current)
  if cur and cur.kind ~= "hub" then h.current = nil; H.ladder = nil; cur = nil end
  -- 8.4: Ratchet at the hub, unless one of Zurkie's own visits is in progress (its hero is the
  -- ladder's); checked with the game, never from the save
  if not (cur and not h.done[cur.id]) and cfg("hub_hero_swap", true) then
    H.after(60, function()
      if H.priming or H.expect or H.bounce then return end      -- a trip is being prepared: its hero wins
      H.ensure_hero("ratchet", nil, "back at Zurkie's")
    end, "back to Ratchet")
  end
  local opened = h.unannounced or {}
  h.unannounced = nil
  local av = H.available()
  if #opened > 0 then
    local names = {}
    for _, pid in ipairs(opened) do names[#names + 1] = pname(pid) end
    say("New Coordinates: " .. table.concat(names, ", "), { type = "planet", sub = #av .. " destination(s) open - " .. K("key_hub") .. " to choose", duration = 8 })
  else
    say(string.format("Zurkie's: %d destination(s) open - " .. K("key_hub") .. " to choose, " .. K("key_hub", true) .. " to go", #av), { type = "corner", duration = 5 })
  end
  changed()
  H.after(H.SETTLE, function() H.apply_world(); H.research() end, "at the hub")
end

-- ---------------------------------------------------------------------------------------------
-- the game's state: MIS_INTRO, planetary travel, the level mask (rando_give.dll v6)
-- ---------------------------------------------------------------------------------------------
local function call(kind, name, cb, flag, value)
  local d = D()
  if not d then if cb then cb({ code = -2, why = "11_rando_campaign.lua is missing" }) end; return end
  d.mission_call(kind, name, cb, flag, value)
end
local function describe(r)
  local d = D()
  local names = d and d.STATE_NAMES or {}
  if d and d.NAMELESS and d.NAMELESS[r.kind] then
    return string.format("%s (0x%X -> 0x%X)", d.RESULT[r.code] or tostring(r.code), r.before or 0, r.after or 0)
  end
  return string.format("%s (%s -> %s)", d and d.RESULT[r.code] or tostring(r.code),
                       r.before and (names[r.before] or tostring(r.before)) or "?", r.after and (names[r.after] or tostring(r.after)) or "?")
end
H.describe = describe

function H.intro_done()
  local mode = cfg("hub_intro", "force")
  local h = H.state()
  if mode ~= "force" or h.intro then return end
  call("query", "MIS_INTRO", function(r)
    if r.code ~= 11 then h.intro = "unknown: " .. describe(r); log("MIS_INTRO:", describe(r)); return end
    if r.after == 3 or r.after == 4 then h.intro = "already complete"; log("MIS_INTRO already complete"); return end
    call("set_state", "MIS_INTRO", function(w)
      h.intro = (w.code == 11) and ("forced " .. tostring(w.before) .. " -> " .. tostring(w.after)) or ("not forced: " .. describe(w))
      changed()
      log("MIS_INTRO set to Complete Finished:", describe(w), w.object and string.format("record at %X", w.object) or "")
    end, 4)
  end)
end

-- the level bits again (a save load cleared them), and planetary travel with them
function H.relevel(pid)
  log("level bits were reset (a save load?) on", pid, "- unlocking again")
  H.apply_world()
end

function H.apply_world()
  local h = H.state()
  if cfg("hub_travel_flag", true) then
    call("travel_set", nil, function(r)
      h.travel_flag = r.code == 11 and r.after or nil
      log("planetary travel:", describe(r))
    end, 1)
  end
  local mode = cfg("hub_levels", "all")
  call("level_read", nil, function(r)
    if r.code ~= 11 then log("levels:", describe(r)); return end
    log(string.format("levels at the hub: unlocked 0x%X, other 0x%X, current %s", r.after or 0, r.ret or 0, tostring(r.index)))
    if mode ~= "all" then return end
    local want = 0x7FE                        -- bits 1..10
    if ((r.after or 0) & want) == want then return end
    for level = 1, 10 do
      if ((r.after or 0) >> level) & 1 == 0 then
        call("level_set", nil, function(w)
          log(string.format("level %d unlocked: %s, mask 0x%X", level, describe(w), w.after or 0))
        end, 1, level)
      end
    end
  end)
end

-- read-only research, once per session at the hub (rivet.log RANDO-HUB research)
function H.research()
  if H.session.researched then return end
  H.session.researched = true
  local d = D()
  local bits = d and d.v6_bits and d.v6_bits() or 0
  log(string.format("research: rando_give.dll v6 paths 0x%X (1 mission records, 2 level mask, 4 travel)", bits))
  local names, seen = { "MIS_INTRO" }, { MIS_INTRO = true }
  for _, dd in ipairs(H.plan().destinations) do
    for _, m in ipairs(dd.missions or {}) do if not seen[m] then seen[m] = true; names[#names + 1] = m end end
  end
  for _, m in ipairs({ "MIS_ZURK_ARENA_BRONZE_CUP", "MIS_ZURK_ARENA_SILVER_CUP", "MIS_ZURK_ARENA_GOLD_CUP" }) do
    if not seen[m] then seen[m] = true; names[#names + 1] = m end
  end
  for _, m in ipairs(names) do
    call("query", m, function(r) log("research: mission", m, describe(r), "system", tostring(r.system)) end)
  end
  call("probe", "MIS_INTRO", function(r)
    log("research: MIS_INTRO record", describe(r), r.object and string.format("at %X", r.object) or "")
  end)
  for _, f in ipairs({ "LANDING", "ZURK", "MEGA", "TRANSITION_TO" }) do
    local ok, list = pcall(rivet.checkpoints, f)
    if ok and type(list) == "table" then
      local n = {}
      for _, c in ipairs(list) do
        local name = type(c) == "table" and (c.name or c[1]) or c
        local area = type(c) == "table" and c.area or ""
        if type(name) == "string" and #n < 60 then n[#n + 1] = name .. (area ~= "" and ("@" .. tostring(area)) or "") end
      end
      log("research: checkpoints " .. f .. " (" .. #list .. "): " .. table.concat(n, " "))
    else
      log("research: checkpoints " .. f .. " not listed:", tostring(list))
    end
  end
  local okc, cfgs = pcall(rivet.configs, "Mission", 40)
  if okc and type(cfgs) == "table" then
    local n = {}
    for _, c in ipairs(cfgs) do n[#n + 1] = tostring(c.type) .. ":" .. tostring(c.id) end
    log("research: Mission configs (" .. #cfgs .. "): " .. table.concat(n, " "))
  end
end

-- ---------------------------------------------------------------------------------------------
-- a destination's story: the mission ladder
-- ---------------------------------------------------------------------------------------------
-- 8.4: the hero, checked with the game. rivet.hero_play_as(hero) answers "already playing as that
-- hero" exactly when the hero is that one (rivet_hook hero_look.cpp play_as: transform_state), so
-- asking again after a swap is the confirmation. "applied" / "loading" mean the swap is under way.
-- cb(ok, how): ok when the game confirmed the hero (or hub_hero_swap is off).
function H.is_already(res) return tostring(res):find("already playing", 1, true) ~= nil end
function H.ensure_hero(hero, cb, why)
  cb = cb or function() end
  if not hero or not cfg("hub_hero_swap", true) then return cb(true, "no swap") end
  local tries, asked = 0, false
  -- one swap at a time: a newer request (another hero, or the same one again) takes over, and the
  -- older one stops without answering (its caller has a timeout or was replaced as well)
  local job = { hero = hero }
  H.hero_job = job
  local function try()
    if H.hero_job ~= job then log("hero:", hero, "request replaced by a newer one (" .. tostring(H.hero_job and H.hero_job.hero) .. ")"); return end
    tries = tries + 1
    local ok, res = pcall(rivet.hero_play_as, hero)
    if not ok and H.is_already(res) then
      local hh = H.state()
      if hh and hh.hero ~= hero then hh.hero = hero; changed() end
      log("hero:", hero, asked and ("confirmed after the swap (" .. tries .. " checks)") or "confirmed", why and ("(" .. why .. ")") or "")
      H.hero_job = nil
      return cb(true, asked and "swapped" or "already")
    end
    if ok then
      if not asked then log("hero: swapping to", hero, "-", tostring(res), why and ("(" .. why .. ")") or "") end
      asked = true
    else
      log("hero: swap to", hero, "refused:", tostring(res), "(check " .. tries .. ")")
    end
    if tries >= H.HERO_TRIES then
      log("hero:", hero, "NOT confirmed after", tries, "checks - the story is started anyway")
      H.hero_job = nil
      say(string.format("Randomizer: could not switch to %s (%s) - the story may wait at its first step", hero, tostring(res)),
          { type = "center", duration = 8 })
      return cb(false, tostring(res))
    end
    H.after(H.HERO_EVERY, try, "hero " .. hero)
  end
  try()
end
-- kept for older callers: a confirmed swap, nothing waits for it
function H.play_as(hero) H.ensure_hero(hero, nil, "play_as") end

local function set_attempt(d, what, detail)
  local h = H.state()
  h.attempts[d.id] = { what = what, detail = detail, frame = H.frame }
  changed()
  log("destination", d.id .. ":", what, detail or "")
end

-- explore: the story could not be started here
function H.explore(d, why)
  set_attempt(d, "explore", why)
  say(string.format("%s: explore - Gold Bolts, armor pods and side activities pay. " .. K("key_hub_return", true) .. " twice finishes it, " .. K("key_hub_return") .. " twice goes back",
                    pname(d.planet)), { type = "center", duration = 9 })
end

-- the visit's mission to act on: the first one the game knows that is not complete
local function next_mission(d, answers)
  local real = {}
  for _, m in ipairs(d.missions or {}) do
    local r = answers[m]
    if r and r.code == 11 then real[#real + 1] = { name = m, state = r.after } end
  end
  for _, x in ipairs(real) do
    if x.state ~= 3 and x.state ~= 4 then return x, real end
  end
  return nil, real
end
H.next_mission = next_mission

-- Every story mission starts with an objective "go to <planet>" (OBJ_ZURK_01_GO_TO_ZURKONS,
-- OBJ_NEFCITY_GO_TO_NEFCITY, OBJ_MOL_GO_TO_MOLONOTH, OBJ_ZORD_01_GO_TO_ZORDOOM, OBJ_ARD_GO_TO_ARDOLIS).
function H.goto_step(objective)
  return type(objective) == "string" and (objective:find("_GO_TO_", 1, true) ~= nil or objective:find("_GOTO_", 1, true) ~= nil)
end
-- 8.4: is this mission known to wait at its first step? (the last objective seen is "go to" and not done)
function H.waiting_goto(name)
  local h = H.state()
  local last = h and h.obj[name]
  return last ~= nil and H.goto_step(last.o) and last.s ~= 2
end
-- 8.3 compatibility (tests, tools): stuck = waiting at "go to", or nothing seen of it yet
function H.stuck(name)
  local h = H.state()
  if H.session.started[name] then return false, "started this session" end
  local last = h and h.obj[name]
  if not last then return true, "no step of it seen yet" end
  if H.goto_step(last.o) and last.s ~= 2 then return true, "waiting at " .. last.o end
  return false, "at " .. tostring(last.o)
end

-- 8.3: the story of a planet, whatever came before it: its first destination (registry order)
-- that is not finished. The prologue is never one.
function H.story_dest(pid)
  local p, h = H.plan(), H.state()
  if not (p and h) then return nil end
  for _, d in ipairs(p.destinations or {}) do
    if d.planet == pid and not h.done[d.id] and d.kind ~= "intro" then return d end
  end
  return nil
end

-- 8.3: landing on a planet starts its story (story_on_arrival). Returns true when a story was
-- looked for. Zurkie's is the hub: its story starts with the story key or the hub's own key.
function H.story_here(pid, how)
  local p, h = H.plan(), H.state()
  if not (p and h) or not H.enabled() then return false end
  if not cfg("story_on_arrival", true) then return false end
  if pid == p.planet then return false end
  local d = H.story_dest(pid)
  if not d then
    say(pname(pid) .. ": its story is finished for the randomizer - explore", { type = "corner", duration = 5 })
    return false
  end
  log("story on arrival:", pid, "->", d.id, "(" .. tostring(how) .. ")")
  H.arrive(d, how)
  return true
end

-- 8.4: before a trip, the destination's hero and its story: the planet then loads with the story
-- active (round 20: MIS_SAV_01, active before the warp, finished "go to" on the landing). Only a
-- mission that is inactive or available is started; nothing here can stop the trip: cb() always
-- comes, at the latest after H.PRIME_TIMEOUT frames.
function H.prime(d, cb, why)
  local done = false
  local function go(what)
    if done then return end
    done = true
    log("prime", d.id .. ":", what)
    cb()
  end
  local dd = D()
  if not (d and cfg("story_prime_before_travel", true) and cfg("hub_runtime", true) ~= false) then return go("off") end
  if not (dd and dd.native_ok("query")) then return go("no mission calls") end
  H.after(H.PRIME_TIMEOUT, function() go("timed out") end, "prime timeout " .. d.id)
  H.ensure_hero(d.hero, function(okh)
    dd.refresh(d.missions or {}, function(answers)
      if done then return end
      local m = next_mission(d, answers)
      if not m then return go("no mission to start") end
      local function start()
        call("start", m.name, function(r)
          if r.code == 11 and r.after == 2 then H.session.started[m.name] = H.frame end
          go(string.format("hero %s %s, %s start: %s", tostring(d.hero), okh and "confirmed" or "not confirmed", m.name, describe(r)))
        end)
      end
      if m.state == 1 then return start() end
      if m.state == 0 and cfg("hub_force_missions", true) and dd.native_ok("set_state") then
        return call("set_state", m.name, function(w)
          if w.code == 11 and w.after == 1 then return start() end
          go("forcing " .. m.name .. " available: " .. describe(w))
        end, 1)
      end
      go(string.format("%s is %s - left as it is", m.name, dd.STATE_NAMES[m.state] or tostring(m.state)))
    end)
  end, "before the trip to " .. d.id .. (why and (", " .. why) or ""))
end

-- try to get the visit's story running. Every step is the game's own call (or the v6 record
-- write); the result of each is logged. 8.4: the hero is confirmed before a story is started, or
-- when an active story still waits at its first step. cb(ok, how)
function H.activate(d, cb)
  cb = cb or function() end
  local dd = D()
  if not dd then H.explore(d, "11_rando_campaign.lua is missing"); return cb(false, "no campaign script") end
  local ok, why = dd.native_ok("query")
  if not ok then H.explore(d, why); return cb(false, why) end
  local token = {}
  H.ladder = { d = d.id, token = token }
  local function live() return H.ladder and H.ladder.token == token end
  dd.refresh(d.missions or {}, function(answers)
    if not live() then return end
    local m, real = next_mission(d, answers)
    local h = H.state()
    h.real = h.real or {}
    local names = {}
    for _, x in ipairs(real) do names[#names + 1] = x.name end
    h.real[d.id] = names
    changed()
    if #real == 0 then H.ladder = nil; H.explore(d, "none of " .. table.concat(d.missions or {}, ", ") .. " is a mission in your game"); return cb(false, "unknown") end
    if not m then H.ladder = nil; H.finish(d, "its missions were already complete"); return cb(true, "complete") end
    local function running(how)
      H.ladder = nil
      set_attempt(d, "story", m.name .. " " .. how)
      say(string.format("%s: %s - the story is running (%s)", pname(d.planet), d.title or m.name, how), { type = "corner", duration = 6 })
      if how ~= "already active" then H.session.started[m.name] = H.frame end
      H.watch_story(d, m.name)
      cb(true, how)
    end
    local function replay_then_explore(why2)
      call("replay", m.name, function(rr)
        if not live() then return end
        log("replay", m.name, describe(rr))
        if rr.code == 11 and rr.after == 2 then return running("replayed") end
        H.ladder = nil
        H.explore(d, why2 .. "; replay: " .. describe(rr))
        cb(false, "explore")
      end)
    end
    local function start(how)
      call("start", m.name, function(r)
        if not live() then return end
        log("start", m.name, describe(r))
        if r.code == 11 and r.after == 2 then return running(how or "started") end
        if r.code == 11 and (r.after == 3 or r.after == 4) then H.ladder = nil; return H.on_mission_state(m.name, r.after) end
        if cfg("hub_replay", true) then return replay_then_explore("start: " .. describe(r)) end
        H.ladder = nil; H.explore(d, "start: " .. describe(r)); cb(false, "explore")
      end)
    end
    log("destination", d.id, "mission", m.name, "is", dd.STATE_NAMES[m.state] or tostring(m.state))
    -- the steps that follow need the visit's hero first
    local function with_hero(fn)
      H.ensure_hero(d.hero, function() if live() then fn() end end, d.id)
    end
    if m.state == 2 then
      local forced = H.force_restart[d.id]
      H.force_restart[d.id] = nil
      if not forced then
        -- running: an active story is left to the game. Only one known to wait at "go to" gets
        -- its hero checked (a story in the middle may have swapped the hero itself)
        if H.waiting_goto(m.name) or not h.obj[m.name] then return with_hero(function() running("already active") end) end
        return running("already active")
      end
      -- Ctrl + story key twice (experimental): available, then the game's start; if the game
      -- refuses, the record goes back to active and the replay call is tried
      local okv, whyv = dd.native_ok("set_state")
      if not okv then return replay_then_explore("active, restart asked, and " .. whyv) end
      log("restart", m.name, "(asked)")
      return with_hero(function()
        call("set_state", m.name, function(w)
          if not live() then return end
          log("restart: available", m.name, describe(w))
          if not (w.code == 11 and w.after == 1) then return replay_then_explore("restart: " .. describe(w)) end
          call("start", m.name, function(r)
            if not live() then return end
            log("restart: start", m.name, describe(r))
            if r.code == 11 and r.after == 2 then return running("restarted") end
            call("set_state", m.name, function(b)
              log("restart: back to active", m.name, describe(b))
              if cfg("hub_replay", true) then return replay_then_explore("restart refused: " .. describe(r)) end
              H.ladder = nil; running("already active")
            end, 2)
          end)
        end, 1)
      end)
    end
    if m.state == 1 then return with_hero(function() start() end) end
    if m.state == 0 and cfg("hub_force_missions", true) then
      local okv, whyv = dd.native_ok("set_state")
      if not okv then return replay_then_explore("inactive and " .. whyv) end
      return with_hero(function()
        call("set_state", m.name, function(w)
          if not live() then return end
          log("force available", m.name, describe(w))
          if w.code == 11 and w.after == 1 then return start() end
          replay_then_explore("forcing it available: " .. describe(w))
        end, 1)
      end)
    end
    replay_then_explore("it is " .. (dd.STATE_NAMES[m.state] or tostring(m.state)))
  end)
end

-- a story should leave its "go to <planet>" step within seconds once its hero is there. If it
-- has not after H.STUCK_WAIT frames, 8.4 reloads the destination once (story_reload_stuck).
function H.watch_story(d, name)
  local token = {}
  H.watching = H.watching or {}
  H.watching[d.id] = token
  H.after(H.STUCK_WAIT, function()
    if H.watching[d.id] ~= token then return end
    H.watching[d.id] = nil
    local h = H.state()
    if h.done[d.id] then return end
    local last = h.obj[name]
    if H.waiting_goto(name) then
      log("story still waiting at", last.o, "for", name, "after", H.STUCK_WAIT, "frames")
      H.session.started[name] = nil
      local cur = S().current_planet
      if cur ~= d.planet then
        log("story", name, "waits for", d.planet, "- you are on", tostring(cur))
        return
      end
      H.reload_story(d, "its first step " .. last.o .. " did not finish")
    elseif last then
      log("story", name, "is at", last.o, "(state " .. tostring(last.s) .. ")")
    else
      log("story", name, "reported no step yet")
    end
  end, "watch " .. name)
end

-- 8.4: reload a destination whose story waits at its first step: out to another planet and
-- straight back, so the planet loads with the story active and its hero there. Once per
-- destination per session; after that the story key (/) is the way.
function H.reload_story(d, why)
  local p, h = H.plan(), H.state()
  if not cfg("story_reload_stuck", true) then
    say(string.format("%s: the story waits at its first step - leave the planet and come back to start it", pname(d.planet)),
        { type = "center", duration = 8 })
    return false
  end
  if H.session.reloaded[d.id] then
    log("reload of", d.id, "already tried this session -", why)
    say(string.format("%s: the story still waits at its first step - press %s to try again, or leave and come back",
                      pname(d.planet), K("key_story")), { type = "center", duration = 8 })
    return false
  end
  local via, cp
  if d.planet ~= p.planet then
    via = p.planet
    cp = H.zurk_candidates()[1]
  else
    -- Zurkie's own visit: out to an open planet with a known checkpoint
    local list = {}
    for pid in pairs(h.open) do if pid ~= p.planet then list[#list + 1] = pid end end
    table.sort(list)
    for _, pid in ipairs(list) do
      local c = H.checkpoint_for(pid)
      if c then via, cp = pid, c; break end
    end
  end
  if not (via and cp) then
    log("reload of", d.id, "impossible: no checkpoint to go out to")
    say(string.format("%s: the story waits at its first step - leave the planet and come back to start it", pname(d.planet)),
        { type = "center", duration = 8 })
    return false
  end
  local ok, res = pcall(rivet.warp, cp)
  if not ok or res == false then
    log("reload of", d.id, "- the warp to", cp, "failed:", tostring(res))
    return false
  end
  H.session.reloaded[d.id] = H.frame
  H.ladder = nil
  H.bounce = { dest = d.id, via = via, at = H.frame }
  H.expect = { planet = via, at = H.frame, how = "warp", cp = cp, why = "reload " .. d.id, tries = 1 }
  history(string.format("[STORY RELOAD] %s (%s) - out to %s and back", d.id, why, via))
  log("reload:", d.id, why, "- out to", via, "at", cp, tostring(res))
  say(string.format("Randomizer: %s - the story did not start; reloading it (out to %s and straight back)", pname(d.planet), pname(via)),
      { type = "center", duration = 8 })
  return true
end

-- the reload trip landed on its way-out planet: straight back to the destination
function H.bounce_back(b)
  local d = dest_by_id(b.dest)
  H.bounce = nil
  if not d then return end
  log("reload: back to", d.id)
  if d.kind == "hub" then
    if H.go_home("reload " .. d.id) and H.expect then H.expect.dest = d.id end
  elseif not H.travel(d.planet, d, false, "reload " .. d.id) then
    say(string.format("Randomizer: the way back to %s failed - press %s to go there", pname(d.planet), K("key_hub", true)),
        { type = "center", duration = 8 })
  end
end

-- arrived for a destination (our travel, the menu, or a load): settle, then the ladder (which
-- confirms the hero first)
function H.arrive(d, how)
  local h = H.state()
  h.current = d.id
  h.phase = "away"
  changed()
  log("arrived for", d.id, "(" .. how .. ")")
  say(string.format("%s: %s", pname(d.planet), d.title or d.id), { type = "planet", sub = "Randomized destination", duration = 6 })
  H.after(H.SETTLE, function() H.activate(d) end, "arrive " .. d.id)
end

-- ---------------------------------------------------------------------------------------------
-- finishing a destination
-- ---------------------------------------------------------------------------------------------
-- the randomizer locations of one visit: its story-mission and side locations (Gold Bolts,
-- armor and collectibles pay through their own events)
function H.locations_of(d)
  local out = {}
  local sd = SEED()
  for _, lid in ipairs(RANDO_GEN.sorted_keys(sd.locations)) do
    local loc = DB.locations[lid]
    if loc and (loc.kind == "planet" or loc.kind == "story" or loc.kind == "side") then
      if C.location_segment(lid, loc.planet) == d.id then out[#out + 1] = lid end
    end
  end
  return out
end

function H.finish(d, how)
  local h, p = H.state(), H.plan()
  if not (h and d) or h.done[d.id] then return false end
  h.n_done = h.n_done + 1
  h.done[d.id] = h.n_done
  if how == "by hand" then h.by_hand[d.id] = true end
  history(string.format("HUB: %s finished (%s) - %d/%d", d.id, how, h.n_done, #p.destinations))
  changed()
  for _, lid in ipairs(H.locations_of(d)) do
    if RANDO and RANDO.collect then RANDO.collect(lid, "destination " .. d.id .. " finished") end
  end
  local opened = H.sync_open(true)
  h.unannounced = h.unannounced or {}
  for _, pid in ipairs(opened) do h.unannounced[#h.unannounced + 1] = pid end
  if d.kind == "finale" then
    h.phase = "done"
    if RANDO and RANDO.on_finale then RANDO.on_finale("hub finale (" .. how .. ")") end
    return true
  end
  local names = {}
  for _, pid in ipairs(opened) do names[#names + 1] = pname(pid) end
  local msg = string.format("Destination complete (%d/%d)%s", h.n_done, #p.destinations,
                            #names > 0 and (" - new Coordinates: " .. table.concat(names, ", ")) or "")
  if d.kind ~= "hub" and cfg("hub_auto_return", true) and h.current == d.id then
    local delay = cfg("hub_return_delay", 12)
    H.return_at = H.frame + math.max(1, delay) * 60
    say(msg, { type = "planet", sub = string.format("Back to Zurkie's in %d s (" .. K("key_hub_return") .. " to stay)", delay), duration = 8 })
  else
    say(msg, { type = "planet", sub = K("key_hub") .. " to choose the next destination", duration = 8 })
    if d.kind == "hub" then h.unannounced = nil end
  end
  if h.current == d.id and d.kind == "hub" then
    h.current = nil
    H.after(300, function()
      if H.priming or H.expect or H.bounce then return end
      local hh = H.state()
      local now_cur = hh and hh.current and dest_by_id(hh.current)
      if now_cur and not hh.done[now_cur.id] then return end   -- another visit started meanwhile
      H.ensure_hero("ratchet", nil, "Zurkie's visit finished")
    end, "back to Ratchet")
  end
  return true
end

-- missions completing anywhere (10_rando_runtime.lua passes every MissionStateChanged/Complete)
function H.on_mission_state(name, state)
  if not (H.plan() and type(name) == "string") then return end
  local h = H.state()
  if not h then return end
  if state ~= 3 and state ~= 4 then return end
  local cur = h.current and dest_by_id(h.current)
  local order = {}
  if cur then order[1] = cur end
  for _, d in ipairs(H.plan().destinations) do if d ~= cur then order[#order + 1] = d end end
  for _, d in ipairs(order) do
    if not h.done[d.id] then
      for i, m in ipairs(d.missions or {}) do
        if m == name then
          local real = (h.real and h.real[d.id]) or d.missions
          local last = real[#real] or d.missions[#d.missions]
          if name == last or i == #d.missions then
            H.finish(d, "story: " .. name)
          elseif d == cur and H.enabled() then
            log(name, "complete; the next mission of", d.id, "is looked at in", H.NEXT_MISSION_WAIT, "frames")
            H.after(H.NEXT_MISSION_WAIT, function()
              local hh = H.state()                      -- 8.5: the state then, not now (a restore may replace it)
              if hh and not hh.done[d.id] then H.activate(d) end
            end, "next mission " .. d.id)
          end
          return
        end
      end
    end
  end
end

-- ---------------------------------------------------------------------------------------------
-- arrivals (10_rando_runtime.lua calls this from process_planet). Returns true when handled.
-- ---------------------------------------------------------------------------------------------
local function first_dest_on(pid)
  for _, id in ipairs(H.available()) do
    local d = dest_by_id(id)
    if d.planet == pid and d.kind ~= "hub" then return d end
  end
  return nil
end

local function test_travel_on()
  local TT = RANDO_TEST_TRAVEL
  return TT ~= nil and TT.on ~= nil and TT.on()
end

-- the level mask on this planet (research), put back when a load cleared it
function H.check_levels(pid)
  local h = H.state()
  if not (h and D() and D().native_ok and D().native_ok("level_read")) then return end
  call("level_read", nil, function(r)
    if r.code == 11 then
      log(string.format("levels on %s: unlocked 0x%X, other 0x%X, current %s", pid, r.after or 0, r.ret or 0, tostring(r.index)))
      h.level_seen[pid] = r.index
      -- 8.1: a save load resets the mask (round 17: 0x7FE before a reload, 0x0 after it), and the
      -- planet menu lists only unlocked planets: put the bits back on every planet once the hub
      -- runs (8.2: or test travel is on)
      local want = 0x7FE
      if (h.started or test_travel_on()) and cfg("hub_levels", "all") == "all" and ((r.after or 0) & want) ~= want then
        H.after(H.SETTLE, function() H.relevel(pid) end, "level bits after a load")
      end
    end
  end)
end

function H.on_arrival(pid, from)
  local p, h = H.plan(), H.state()
  if not (p and h) or not H.enabled() then return false end
  H.check_levels(pid)
  local exp = H.expect
  H.expect = nil
  -- 8.4: a story reload on its way out: straight back, nothing else happens here
  local b = H.bounce
  if b and pid == b.via and h.started then
    log("reload: out on", pid, "- going back for", b.dest)
    H.after(H.SETTLE, function() H.bounce_back(b) end, "reload back " .. b.dest)
    return true
  end
  if not h.started then
    if pid == p.planet and (h.phase == "to_hub" or (exp and exp.planet == pid)) then
      H.hub_started(exp and exp.cp or "arrived")
      if exp and exp.cp then h.home_cp = exp.cp end
      return true
    end
    if exp then H.expect = exp end           -- still waiting for Zurkie's (a planet on the way)
    return false
  end
  if pid == p.planet then
    if exp and exp.cp and exp.planet == pid then h.home_cp = exp.cp end
    H.at_hub(exp and exp.how or "arrived")
    if exp and exp.dest then
      local d = dest_by_id(exp.dest)
      if d and d.kind == "hub" then H.arrive(d, "at the hub") end
    end
    return true
  end
  -- our own trip
  if exp and exp.planet == pid then
    -- (8.4: a warp's checkpoint is not remembered as the planet's landing: round 20's Torren IV
    -- trip used a mid-mission checkpoint a test trip had left there)
    local d = exp.dest and dest_by_id(exp.dest)
    if d then H.arrive(d, exp.how) else h.phase = "away"; h.current = nil end
    return true
  end
  -- the ship's planet menu
  local m = H.menu
  if m and now() - m.at <= H.MENU_WINDOW and m.planet == pid then
    H.menu = nil
    if h.open[pid] then
      if RANDO_TRAVEL and RANDO_TRAVEL.remember then RANDO_TRAVEL.remember(pid, m.dest) end
      -- 8.3: with story_on_arrival, the planet's story whatever came before it
      local d = cfg("story_on_arrival", true) and H.story_dest(pid) or first_dest_on(pid)
      if d then H.arrive(d, "planet menu") else
        h.phase, h.current = "away", nil
        say(pname(pid) .. ": nothing left to play here for the hub - explore, " .. K("key_hub_return") .. " twice to go back", { type = "corner", duration = 6 })
      end
    elseif test_travel_on() then
      -- 8.2: test travel lets every planet stay; its landing is learned like an open planet's
      if RANDO_TRAVEL and RANDO_TRAVEL.remember then RANDO_TRAVEL.remember(pid, m.dest) end
      h.phase, h.current = "away", nil
      RANDO_TEST_TRAVEL.stayed(pid, "planet menu")
      H.story_here(pid, "planet menu (test travel)")
    else
      log("no Coordinates for", pid, "- back to Zurkie's")
      say(string.format("Randomizer: no Coordinates for %s yet - back to Zurkie's", pname(pid)), { type = "center", duration = 6 })
      h.sent_back = (h.sent_back or 0) + 1
      H.after(H.SETTLE, function() H.go_home("no Coordinates for " .. pid) end, "sent back")
    end
    return true
  end
  -- the parade on a load, or the game's own travel right after the hub started
  -- (8.2: neither the keeper nor the startup guard moves you while test travel is on)
  local testing = test_travel_on()
  local guard = not testing and H.session.started_frame and (H.frame - H.session.started_frame) < H.STARTUP_GUARD
  local cur = h.current and dest_by_id(h.current)
  if not testing and pid == p.finale_planet and not (cur and cur.planet == pid) and not h.open[pid] and H.session.keeper < H.KEEPER_MAX then
    H.session.keeper = H.session.keeper + 1
    log("Corson V without the finale open (a load into the parade?) - back to Zurkie's")
    say("Randomizer: back to Zurkie's - the parade is behind you", { type = "center", duration = 6 })
    H.after(H.SETTLE, function() H.go_home("keeper") end, "keeper")
    return true
  end
  if guard and not (cur and cur.planet == pid) then
    log("the game took you to", pid, "right after the hub started - back to Zurkie's")
    H.after(H.SETTLE, function() H.go_home("startup guard") end, "startup guard")
    return true
  end
  -- a load (or the story's own travel) onto the destination in progress: carry on there
  if cur and cur.planet == pid and not h.done[cur.id] then
    log("back on", pid, "for", cur.id, "- asking the game where its story is")
    H.after(H.SETTLE, function() H.activate(cur) end, "resume " .. cur.id)
    return true
  end
  log("arrived on", pid, "by the game's own travel - never blocked")
  return true
end

-- PlanetMenuAcceptEvent { DestinationCheckpointName, InterplanetaryCheckpointName }
function H.on_menu_accept(f)
  if not (H.plan() and H.state()) then return end
  local dest = f.DestinationCheckpointName
  local pid = RANDO_TRAVEL and RANDO_TRAVEL.planet_of_checkpoint and
              (RANDO_TRAVEL.planet_of_checkpoint(dest) or RANDO_TRAVEL.planet_of_checkpoint(f.InterplanetaryCheckpointName))
  H.menu = { planet = pid, dest = dest, at = now() }
  log("planet menu:", tostring(dest), "->", tostring(pid))
end

-- ---------------------------------------------------------------------------------------------
-- keys
-- ---------------------------------------------------------------------------------------------
local function ctrl_down()
  if RANDO and RANDO.ctrl_down then return RANDO.ctrl_down() end
  local ctrl = false
  pcall(function() ctrl = rivet.is_key_down(rivet.key("CONTROL")) end)
  return ctrl
end
local function describe_dest(d)
  local where = d.kind == "hub" and "at Zurkie's" or pname(d.planet)
  return string.format("%s: %s (%s)", where, d.title or d.id, d.hero or "?")
end

function H.key_select()
  local h = H.state()
  if not h.started then
    say("Randomizer: " .. K("key_hub", true) .. " goes to Zurkie's and starts the hub campaign", { type = "center", duration = 6 })
    return
  end
  local av = H.available()
  if #av == 0 then say("Randomizer: no destination open", { type = "corner", duration = 4 }); return end
  H.sel = (H.sel % #av) + 1
  local d = dest_by_id(av[H.sel])
  say(string.format("Destination %d/%d - %s - " .. K("key_hub", true) .. " to go", H.sel, #av, describe_dest(d)), { type = "center", duration = 6 })
end

function H.key_go()
  local h, p = H.state(), H.plan()
  if not h.started then
    if h.phase == "to_hub" and H.expect then return end
    return H.begin_hub(K("key_hub", true))
  end
  local av = H.available()
  if #av == 0 then say("Randomizer: no destination open", { type = "corner", duration = 4 }); return end
  if H.sel < 1 or H.sel > #av then H.sel = 1 end
  local d = dest_by_id(av[H.sel])
  H.return_at = nil
  if d.kind == "hub" then
    if S().current_planet == p.planet then H.arrive(d, "at the hub")
    else
      if H.priming then return end
      H.priming = true
      H.prime(d, function()
        H.priming = nil
        if H.go_home("for " .. d.id) and H.expect then H.expect.dest = d.id end
      end, K("key_hub", true))
    end
    return
  end
  local at_hub = S().current_planet == p.planet
  if H.priming then return say("Randomizer: getting the story ready...", { type = "corner", duration = 3 }) end
  -- (no landing point known and none coming: the trip cannot happen, so nothing is changed first)
  local T = RANDO_TRAVEL
  if not H.checkpoint_for(d) and not (T and T.catalog_wanted and T.catalog_wanted()) then
    H.travel(d.planet, d, at_hub, K("key_hub", true))
    return
  end
  H.priming = true
  say("Randomizer: off to " .. describe_dest(d), { type = "corner", duration = 5 })
  -- 8.4: the hero and the story first, then the trip (the planet loads with its story active)
  H.prime(d, function()
    H.priming = nil
    if not H.travel(d.planet, d, at_hub, K("key_hub", true)) then return end
  end, K("key_hub", true))
end

local confirm = { ["return"] = -100, finish = -100, restart = -100 }

-- 8.3 the story key: start the story of the planet you are on (whatever came before it).
-- Ctrl + the key twice: start it again from its first step, even if it is running.
function H.key_story(ctrl)
  local h = H.state()
  local pid = S().current_planet
  if not pid then return say("Randomizer: the planet is not known yet", { type = "corner", duration = 4 }) end
  local d = H.story_dest(pid)
  if not d then return say(pname(pid) .. ": its story is finished for the randomizer", { type = "corner", duration = 5 }) end
  if ctrl then
    local t = now()
    if t - confirm.restart > H.CONFIRM then
      confirm.restart = t
      say(string.format("Randomizer: press %s again to start %s again from its first step", K("key_story", true), d.title or d.id),
          { type = "center", duration = 5 })
      return
    end
    confirm.restart = -100
    H.force_restart[d.id] = true
    log("[STORY RESTART BY HAND]", d.id)
    history("[STORY RESTART BY HAND] " .. d.id)
  end
  h.current = d.id
  if pid ~= H.plan().planet then h.phase = "away" end
  changed()
  log("story key:", pid, "->", d.id, ctrl and "(restart)" or "")
  say(string.format("%s: %s - starting the story", pname(pid), d.title or d.id), { type = "corner", duration = 5 })
  -- 8.4: the ladder confirms the hero; a story already known to wait at its first step is
  -- reloaded right away (the story key may reload again: it is the player's own choice)
  if not ctrl then
    local m
    for _, name in ipairs(d.missions or {}) do if H.waiting_goto(name) then m = name; break end end
    if m and pid == d.planet then
      H.session.reloaded[d.id] = nil
      H.ensure_hero(d.hero, function() H.reload_story(d, "story key: " .. m .. " waits at its first step") end, "story key")
      return
    end
  end
  H.after(60, function() H.activate(d) end, "story key " .. d.id)
end
function H.key_return()
  local h, p = H.state(), H.plan()
  if H.return_at then
    H.return_at = nil
    say("Randomizer: staying here - " .. K("key_hub_return") .. " twice goes back to Zurkie's", { type = "corner", duration = 5 })
    return
  end
  if not h.started then return say("Randomizer: the hub has not started - " .. K("key_hub", true) .. " goes to Zurkie's", { type = "corner", duration = 5 }) end
  if S().current_planet == p.planet then return say("Randomizer: you are at Zurkie's", { type = "corner", duration = 3 }) end
  local t = now()
  if t - confirm["return"] > H.CONFIRM then
    confirm["return"] = t
    local cur = h.current and dest_by_id(h.current)
    say("Randomizer: press " .. K("key_hub_return") .. " again to go back to Zurkie's" .. ((cur and not h.done[cur.id]) and " (this destination stays open)" or ""),
        { type = "center", duration = 5 })
    return
  end
  confirm["return"] = -100
  local cur = h.current and dest_by_id(h.current)
  if cur and not h.done[cur.id] then h.current = nil end
  H.ladder = nil
  if not H.go_home(K("key_hub_return")) then say("Randomizer: the warp to Zurkie's failed (see rivet.log)", { type = "center", duration = 6 }) end
end

function H.key_finish()
  local h = H.state()
  local d = h.current and dest_by_id(h.current)
  if not d or h.done[d.id] then return say("Randomizer: no destination in progress", { type = "corner", duration = 4 }) end
  local t = now()
  if t - confirm.finish > H.CONFIRM then
    confirm.finish = t
    say(string.format("Randomizer: press " .. K("key_hub_return", true) .. " again to finish %s by hand (it is recorded)", d.id), { type = "center", duration = 5 })
    return
  end
  confirm.finish = -100
  log("[FINISHED BY HAND]", d.id)
  H.finish(d, "by hand")
end

-- ---------------------------------------------------------------------------------------------
-- the frame
-- ---------------------------------------------------------------------------------------------
function H.after(frames, fn, why)
  H.pending = H.pending or {}
  H.pending[#H.pending + 1] = { at = H.frame + frames, fn = fn, why = why }
end

function H.tick(frame, ready)
  H.frame = frame
  if not (H.plan() and S()) then return end
  local h = H.state()
  if not H.enabled() then return end
  -- deferred actions (only with the scene up)
  if ready and H.pending and #H.pending > 0 then
    local due, keep = {}, {}
    for _, a in ipairs(H.pending) do if frame >= a.at then due[#due + 1] = a else keep[#keep + 1] = a end end
    H.pending = keep
    for _, a in ipairs(due) do
      local ok, err = pcall(a.fn)
      if not ok then log("RANDO-ERROR hub", tostring(a.why), tostring(err)) end
    end
  end
  -- New Game -> Zurkie's
  if not h.started and h.phase == "pre" and S().started and ready then
    local ok, why = trigger_met()
    if ok then H.begin_hub(why or ("parade " .. cfg("hub_trigger", "wrench"))) end
  end
  -- a trip waiting for the checkpoint catalog (8.1)
  local w = H.wait_catalog
  if w and ready then
    local T = RANDO_TRAVEL
    if not (T and T.catalog_wanted and T.catalog_wanted()) or frame - w.at > H.CATALOG_WAIT then
      H.wait_catalog = nil
      H.travel(w.pid, w.dest and dest_by_id(w.dest), w.prefer_fly, w.why)
    end
  end
  -- a trip that has not landed
  local e = H.expect
  if e and ready and frame - e.at > H.ARRIVE_TIMEOUT then
    local p = H.plan()
    if e.planet == p.planet then
      log("no arrival at Zurkie's after", H.ARRIVE_TIMEOUT, "frames from", e.cp)
      if not H.go_home(e.why or "retry") then
        H.expect = nil
        if not h.started then H.start_failed("the warp did not land") end
      end
    elseif e.how == "fly" then
      log("the ship did not land on", e.planet, "- warping")
      H.expect = nil
      H.travel(e.planet, e.dest and dest_by_id(e.dest), false, "fly timed out")
    else
      log("no arrival on", e.planet, "after the warp to", e.cp)
      H.expect = nil
      say("Randomizer: the trip to " .. pname(e.planet) .. " did not land (see rivet.log)", { type = "center", duration = 6 })
    end
  end
  -- 8.4: a reload trip that never came back is forgotten
  if H.bounce and frame - H.bounce.at > H.BOUNCE_TIMEOUT then
    log("reload of", H.bounce.dest, "never came back - forgotten")
    H.bounce = nil
  end
  -- automatic return after a finished destination
  if H.return_at and ready and frame >= H.return_at then
    H.return_at = nil
    h.current = nil
    if not H.go_home("destination finished") then
      say("Randomizer: the warp to Zurkie's failed - " .. K("key_hub_return") .. " twice to try again", { type = "center", duration = 6 })
    end
  end
end

-- persistence: the companion's restore replaces the state; a hub started in this session before
-- the restore (a new game while the companion connected) is kept
function H.on_restore(live)
  local s = S()
  if not s then return end
  if live and live.hub and (not s.hub or not s.hub.started) and live.hub.started then
    s.hub = live.hub
    log("kept this session's hub start over the restored state")
  end
  -- the restored hub, on the planet this session is on: put the hub's world back (Zurkie's), or
  -- take you back to Zurkie's from the parade
  local h = s.hub
  if not (H.plan() and h and h.started and H.enabled()) then return end
  local p = H.plan()
  if s.current_planet == p.planet then
    H.after(H.SETTLE, function() H.apply_world() end, "restored at the hub")
  elseif s.current_planet == p.finale_planet and not (h.open and h.open[p.finale_planet]) and H.session.keeper < H.KEEPER_MAX
         and not test_travel_on() then
    H.session.keeper = H.session.keeper + 1
    log("restored on Corson V without the finale open - back to Zurkie's")
    H.after(H.SETTLE, function() H.go_home("keeper (restore)") end, "keeper")
  end
end

-- ---------------------------------------------------------------------------------------------
-- wiring
-- ---------------------------------------------------------------------------------------------
pcall(rivet.on_event, "PlanetMenuAcceptEvent", function(ev)
  local ok, err = pcall(H.on_menu_accept, ev.fields or {})
  if not ok then log("RANDO-ERROR menu", tostring(err)) end
end)

-- 8.3: keys through the runtime's binder (keyboard keys; legacy_f_keys keeps the old F key too)
local function bind(setting, legacy, fn)
  if not (RANDO and RANDO.bind_setting) then return end
  RANDO.bind_setting(setting, legacy, function()
    if not (H.plan() and S()) then return end
    if not H.enabled() then return say("Randomizer: hub_runtime is off", { type = "corner", duration = 3 }) end
    local ready = false
    pcall(function() ready = rivet.scene_ready() and rivet.hero() ~= nil end)
    if not ready then return say("Randomizer: wait until the game has loaded", { type = "corner", duration = 3 }) end
    fn(ctrl_down())
  end)
end
bind("key_hub", "F6", function(ctrl) if ctrl then H.key_go() else H.key_select() end end)
bind("key_hub_return", "F5", function(ctrl) if ctrl then H.key_finish() else H.key_return() end end)
bind("key_story", nil, function(ctrl) H.key_story(ctrl) end)

log("loaded (" .. H.VERSION .. ")")
