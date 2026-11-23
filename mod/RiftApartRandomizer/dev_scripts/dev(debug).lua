-- DEVELOPER TOOL - not part of a release. dev(debug).lua: EVERY developer tool of the kit in ONE file (v0.62-DEV5).
-- Copy ONLY this file from dev_scripts\ into <game>\scripts (delete every other dev(*).lua there: this file holds them).
-- Built by tools/build_dev_debug.py from the single dev(*).lua files - edit those (or tools/dev_debug_core.lua), then
-- run the tool; never edit dev(debug).lua by hand.
--
-- ALWAYS ON (this file's own section, "warp" below): WARP ANYWHERE and UNSTUCK
--   HOME             next planet            Ctrl+HOME      previous planet
--   PAGEDOWN         next room (checkpoint) of that planet          Ctrl+PAGEDOWN  10 rooms on
--   PAGEUP           previous room                                  Ctrl+PAGEUP    10 rooms back
--   END              WARP to the selected room (the game's checkpoint warp; works from anywhere, no Coordinates needed)
--   Ctrl+END         fly there with the ship instead (rivet.fly; needs the ship's planet menu nearby)
--   INSERT           UNSTUCK: warp to the last checkpoint you passed (press again within 5 s: the one before it)
--   Ctrl+INSERT      UNSTUCK: warp to this planet's landing point
--   DELETE           where am I (planet, last checkpoint, rooms known)  Ctrl+DELETE  every room of the selected planet
--                                                                                    to rivet.log (RANDO-DEBUG rooms)
--   NUMPAD1          Omega: read every weapon record (17_rando_omega.lua must be installed)
--   NUMPAD2          Omega: compare the records with the NUMPAD1 read - bytes that went 0 -> 1 are Omega candidates
--                    (buy an Omega at Ms. Zurkon in Challenge Mode, or level a weapon, between the two presses)
--   Ctrl+NUMPAD2     Omega: take the single candidate byte as the Omega flag for this save (state.omega_cal)
-- Rooms: every checkpoint rivet.checkpoints() lists for the planet (14_rando_travel.lua's catalog, landing pads first).
-- The catalog fills over the first seconds after the game loads; the first HOME asks it to hurry.
-- Every warp is written to the randomizer history as [DEBUG WARP]; rewards follow the usual rules.
--
-- THE OTHER SECTIONS (switches in RANDO_DEV_DEBUG.sections below; true = on):
--   keys        the developer keys ; ] [ / ' (status, hub destinations, story, campaign director)
--   testtravel  test travel . and , (needs test_travel = true in 04_rando_settings.lua)
--   testmode    F10 / F11 fake progress, Ctrl+F10 x2 reset, the mission lab
--   omega_probe read-only hero component listing (RANDO-OMEGA-PROBE lines)
--   probe       script-node probe (NUMPAD3-9) with its data (vtables, item ids)              OFF: research only
--   spawnprobe  read-only spawner evidence (RANDO-SPAWNPROBE)            OFF: it can exceed the 8 ms frame budget
--   spawnproof  controlled enemy replacements on Zurkon (RANDO-SPAWNPROOF) OFF: stands down while the Enemy Randomizer is on
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(debug)"] = "10.0.39"   -- the kit check (10_rando_runtime.lua)

RANDO_DEV_DEBUG = RANDO_DEV_DEBUG or {}
local DBG = RANDO_DEV_DEBUG
DBG.sections = DBG.sections or {
  warp = true, keys = true, testtravel = true, testmode = true, omega_probe = true,
  probe = false, spawnprobe = false, spawnproof = false,
}
DBG.ran = DBG.ran or {}
local function dlog(...) pcall(rivet.log, "[rando]", "RANDO-DEBUG", ...) end
DBG.log = dlog
-- one section: run unless switched off; an error stays inside it (logged), the others still load
function DBG.section(name, fn)
  if not DBG.sections[name] then dlog("section", name, "off"); return end
  local ok, err = pcall(fn)
  if ok then DBG.ran[name] = true else dlog("RANDO-ERROR section", name, tostring(err)) end
end

-- ==== section: warp (WARP ANYWHERE and UNSTUCK) ==========================================================================
DBG.section("warp", function()
  local R = RANDO
  local DB = RANDO_DATA
  if not (R and R.bind_key and DB and DB.planets) then dlog("warp: 10_rando_runtime.lua is not loaded"); return end
  local W = {}
  DBG.warp = W
  W.sel = 0                      -- index into DB.planets
  W.room = {}                    -- pid -> selected room index
  W.recent = {}                  -- the last checkpoints passed (newest last), for UNSTUCK
  W.RECENT = 8
  W.unstuck_at, W.unstuck_n = -100, 0

  local function say(text, opts) if R.say then R.say(text, opts) else pcall(rivet.notify, text, opts) end end
  local function S() return R.state end
  local function now() return (rivet.time and rivet.time()) or 0 end
  local function pname(pid) return (R.planet_name and R.planet_name(pid)) or tostring(pid) end
  local function history(msg) if R.history then pcall(R.history, msg) end; dlog(msg) end
  local function ready()
    local ok = false
    pcall(function() ok = rivet.scene_ready() and rivet.hero() ~= nil end)
    return ok
  end
  local function T() return RANDO_TRAVEL end

  -- remember every checkpoint passed (14_rando_travel.lua's T.on_checkpoint keeps only the last one)
  local TR = T()
  if TR and TR.on_checkpoint and not TR.debug_wrapped then
    local orig = TR.on_checkpoint
    TR.on_checkpoint = function(hash, loaded, ...)
      local r = orig(hash, loaded, ...)
      local lc = TR.last_checkpoint
      if lc and lc.name then
        local last = W.recent[#W.recent]
        if not (last and last.name == lc.name) then
          W.recent[#W.recent + 1] = { name = lc.name, planet = lc.planet, at = now() }
          if #W.recent > W.RECENT then table.remove(W.recent, 1) end
        end
      end
      return r
    end
    TR.debug_wrapped = true
  end

  local function hurry()
    local t = T()
    if t then t.catalog_from = 0 end
    if RANDO_TEST_TRAVEL then RANDO_TEST_TRAVEL.want_catalog = true end
    W.want_catalog = true
  end
  local function catalog_note()
    local t = T()
    local cat = t and t.catalog
    if not cat then return "the checkpoint list has not started yet" end
    if cat.done then return "the checkpoint list is complete" end
    return string.format("the checkpoint list is still being read (%d/%d)", math.min(cat.next - 1, #cat.filters), #cat.filters)
  end
  -- every room of a planet: where you last landed, the ones seen in your logs, then the whole catalog (best first)
  function W.rooms(pid)
    local out, seen = {}, {}
    local function add(cp)
      if type(cp) ~= "string" or cp == "" or seen[cp] then return end
      if cp:upper():find("TRANSITION_TO", 1, true) then return end
      seen[cp] = true
      out[#out + 1] = cp
    end
    local t = T()
    local s = S()
    local tr = (t and t.state and s) and t.state() or nil
    if tr and tr.landed then add(tr.landed[pid]) end
    for _, p in ipairs(DB.planets) do
      if p.id == pid then for _, cp in ipairs((p.checkpoints and p.checkpoints.known) or {}) do add(cp) end end
    end
    if t and t.ranked then for _, cp in ipairs(t.ranked(pid)) do add(cp) end end
    return out
  end
  function W.selected() return DB.planets[W.sel] and DB.planets[W.sel].id end
  local function planet_index(pid)
    for i, p in ipairs(DB.planets) do if p.id == pid then return i end end
    return nil
  end
  function W.show()
    local pid = W.selected()
    if not pid then return end
    local rooms = W.rooms(pid)
    local head = string.format("[DEBUG] %d/%d %s", W.sel, #DB.planets, pname(pid))
    if #rooms == 0 then
      hurry()
      say(head .. " - no room known yet", { type = "center", duration = 6, sub = catalog_note() .. "; press HOME again in a few seconds" })
      return
    end
    local k = W.room[pid] or 1
    if k > #rooms then k = 1 end
    if k < 1 then k = #rooms end
    W.room[pid] = k
    say(head, { type = "center", duration = 6,
        sub = string.format("room %d/%d: %s - END warp, Ctrl+END fly, PAGEUP/PAGEDOWN other rooms", k, #rooms, rooms[k]) })
    dlog("selected", pid, string.format("room %d/%d", k, #rooms), rooms[k])
  end
  function W.next_planet(step)
    if W.sel < 1 then
      local cur = S() and S().current_planet
      W.sel = (cur and planet_index(cur)) or 0
      if step < 0 and W.sel == 0 then W.sel = 1 end
    end
    W.sel = ((W.sel - 1 + step) % #DB.planets) + 1
    hurry()
    W.show()
  end
  function W.next_room(step)
    local pid = W.selected()
    if not pid then return W.next_planet(1) end
    local rooms = W.rooms(pid)
    if #rooms == 0 then return W.show() end
    W.room[pid] = (((W.room[pid] or 1) - 1 + step) % #rooms) + 1
    W.show()
  end
  -- warp (or fly) to a checkpoint name
  function W.go(cp, how, why)
    local fn = (how == "fly") and rivet.fly or rivet.warp
    if not fn then say("[DEBUG] this rivet_hook has no " .. how); return false end
    local ok, res = pcall(fn, cp)
    if not ok or res == false then
      dlog(how, "to", cp, "failed:", tostring(res))
      say(string.format("[DEBUG] %s to %s failed (%s)", how, cp, tostring(res)), { type = "center", duration = 7,
          sub = how == "fly" and "the ship's flight needs its planet menu nearby - END warps instead" or "pick another room (PAGEUP / PAGEDOWN)" })
      return false
    end
    local t = T()
    local pid = t and t.planet_of_checkpoint and t.planet_of_checkpoint(cp)
    -- a trip test travel knows (its arrival is never sent back by locked travel)
    if RANDO_TEST_TRAVEL and pid then
      RANDO_TEST_TRAVEL.trip = { planet = pid, cp = cp, how = how, at = now(), from = S() and S().current_planet }
    end
    history(string.format("[DEBUG WARP] %s to %s (%s)%s", how, tostring(pid or "?"), cp, why and (" - " .. why) or ""))
    say(string.format("[DEBUG] %s to %s", how == "fly" and "flying" or "warping", pid and pname(pid) or cp), { type = "corner", duration = 5, sub = cp })
    return true
  end
  function W.go_selected(how)
    local pid = W.selected()
    -- v0.62-DEV9: round49 pressed END five times before any HOME and only got "press HOME first": END alone now
    -- chooses the planet you are on and shows its room; END again warps there
    if not pid then
      local cur = S() and S().current_planet
      W.sel = (cur and planet_index(cur)) or 1
      dlog("END before HOME: chose", tostring(W.selected()), "- END again warps to the room shown")
      hurry()
      return W.show()
    end
    local rooms = W.rooms(pid)
    local cp = rooms[W.room[pid] or 1]
    if not cp then return W.show() end
    W.go(cp, how)
  end
  -- UNSTUCK: the last checkpoint passed; pressed again within 5 s, the one before it, and so on
  function W.unstuck()
    local t = now()
    if t - W.unstuck_at > 5 then W.unstuck_n = 0 end
    W.unstuck_at = t
    W.unstuck_n = W.unstuck_n + 1
    local entry = W.recent[#W.recent - W.unstuck_n + 1]
    local lc = T() and T().last_checkpoint
    if not entry and W.unstuck_n == 1 and lc and lc.name then entry = { name = lc.name, planet = lc.planet } end
    if not entry then
      local cur = S() and S().current_planet
      local cp = cur and T() and T().checkpoint_for and T().checkpoint_for(cur)
      if cp then return W.go(cp, "warp", "unstuck: no checkpoint passed yet, this planet's landing point") end
      say("[DEBUG] no checkpoint known to go back to - choose a room with HOME / PAGEDOWN, then END", { type = "center", duration = 6 })
      return
    end
    W.go(entry.name, "warp", string.format("unstuck (%d back)", W.unstuck_n))
  end
  function W.landing()
    local cur = S() and S().current_planet
    local cp, how = nil, nil
    if cur and T() and T().checkpoint_for then cp, how = T().checkpoint_for(cur) end
    if not cp then say("[DEBUG] no landing point known for " .. pname(cur)); return end
    W.go(cp, "warp", "unstuck: landing point (" .. tostring(how) .. ")")
  end
  function W.where()
    local s = S()
    local cur = s and s.current_planet
    local lc = T() and T().last_checkpoint
    local rooms = cur and W.rooms(cur) or {}
    local text = string.format("[DEBUG] on %s - last checkpoint %s - %d room(s) known here", pname(cur), tostring(lc and lc.name or "-"), #rooms)
    dlog(text, "| recent:", (function()
      local t = {}
      for _, e in ipairs(W.recent) do t[#t + 1] = e.name end
      return table.concat(t, ", ")
    end)())
    say(text, { type = "center", duration = 6, sub = catalog_note() })
  end
  function W.dump_rooms()
    local pid = W.selected() or (S() and S().current_planet)
    if not pid then return end
    local rooms = W.rooms(pid)
    dlog("rooms", pid, #rooms, table.concat(rooms, " "))
    say(string.format("[DEBUG] %d room(s) of %s written to rivet.log", #rooms, pname(pid)), { type = "corner", duration = 4 })
  end

  -- Omega helpers (17_rando_omega.lua): read every weapon record, compare later
  W.omega_snap = nil
  function W.omega_read(compare)
    local O = RANDO_OMEGA
    if not (O and O.start_job and O.find_records and O.read) then
      say("[DEBUG] 17_rando_omega.lua is not installed", { type = "corner", duration = 4 }); return
    end
    O.start_job("debug_" .. (compare and "compare" or "read"), function()
      local inv, why = O.find_records()
      if not inv then dlog("omega: no weapon records -", tostring(why)); say("[DEBUG] Omega: no weapon records (" .. tostring(why) .. ")"); return end
      local snap = {}
      for w, rec in pairs(inv.records) do snap[w] = O.read(rec.id_at, O.SPAN) end
      if not compare then
        W.omega_snap = snap
        dlog(string.format("omega: %d weapon record(s) read in %s (array at +0x%X)", inv.count, inv.class, inv.array_at))
        say(string.format("[DEBUG] Omega: %d weapon records read - make one weapon Omega, then NUMPAD2", inv.count), { type = "corner", duration = 6 })
        return
      end
      if not W.omega_snap then say("[DEBUG] Omega: press NUMPAD1 first"); return end
      local cands, lines = {}, 0
      for w, after in pairs(snap) do
        local before = W.omega_snap[w]
        if before then
          local diff = {}
          for i = 9, math.min(#before, #after) do
            if before[i] ~= after[i] then
              diff[#diff + 1] = string.format("+0x%X:%02X>%02X", i - 1, before[i], after[i])
              if before[i] == 0 and after[i] == 1 then cands[#cands + 1] = { w = w, off = i - 1 } end
            end
          end
          if #diff > 0 then lines = lines + 1; dlog("omega diff", w, table.concat(diff, " ")) end
        end
      end
      W.omega_cands = cands
      local t = {}
      for _, c in ipairs(cands) do t[#t + 1] = string.format("%s +0x%X", c.w, c.off) end
      dlog("omega candidates (0 -> 1):", #cands, table.concat(t, ", "))
      say(string.format("[DEBUG] Omega: %d record(s) changed, %d candidate byte(s) - see rivet.log", lines, #cands),
          { type = "center", duration = 6, sub = #cands == 1 and "Ctrl+NUMPAD2 takes it as the Omega flag" or "one candidate is needed to take it" })
      W.omega_snap = snap
    end)
  end
  function W.omega_take()
    local c = W.omega_cands
    local s = S()
    if not (c and #c == 1 and s) then say("[DEBUG] Omega: exactly one candidate byte is needed (NUMPAD1, change, NUMPAD2)"); return end
    s.omega_cal = { off = c[1].off, from = "debug " .. c[1].w, at = math.floor(now()) }
    if R.mark_changed then R.mark_changed() end
    dlog(string.format("omega: the Omega flag is taken as +0x%X (from %s) for this save", c[1].off, c[1].w))
    say(string.format("[DEBUG] Omega flag set to +0x%X for this save", c[1].off), { type = "center", duration = 6 })
  end

  local function bind(name, fn)
    R.bind_key(name, function()
      if not ready() then return say("[DEBUG] wait until the game has loaded", { type = "corner", duration = 3 }) end
      local ok, err = pcall(fn, R.ctrl_down())
      if not ok then dlog("RANDO-ERROR", name, tostring(err)) end
    end, "debug " .. name)
  end
  bind("HOME", function(ctrl) W.next_planet(ctrl and -1 or 1) end)
  bind("PAGEDOWN", function(ctrl) W.next_room(ctrl and 10 or 1) end)
  bind("PAGEUP", function(ctrl) W.next_room(ctrl and -10 or -1) end)
  bind("END", function(ctrl) W.go_selected(ctrl and "fly" or "warp") end)
  bind("INSERT", function(ctrl) if ctrl then W.landing() else W.unstuck() end end)
  bind("DELETE", function(ctrl) if ctrl then W.dump_rooms() else W.where() end end)
  bind("NUMPAD1", function() W.omega_read(false) end)
  bind("NUMPAD2", function(ctrl) if ctrl then W.omega_take() else W.omega_read(true) end end)
  dlog("warp loaded: HOME planet, PAGEUP/PAGEDOWN room, END warp (Ctrl fly), INSERT unstuck (Ctrl landing point), DELETE where am I, NUMPAD1/2 Omega")
end)

-- ==== section: keys (dev(keys).lua) =================================================================================
DBG.section("keys", function()
-- ---- dev(keys).lua ----
-- DEVELOPER TOOL - not part of a release. The developer keys. A release answers only the player's
-- key (0, 10_rando_runtime.lua); with this file installed these work too, and on-screen messages
-- mention them (RANDO_DEV_KEYS):
--   ;  (F9)   status line              Ctrl+; twice  open the planet you were last sent back from
--   ]  (F6)   next hub destination     Ctrl+]        go there
--   [  (F5)   cancel the automatic return after a finished destination
--             Ctrl+[ twice  finish the current destination by hand
--   /         start the story of the planet you are on (hub)
--   '  (F12)  campaign director: travel to the next visit (experimental mission orders only)
--   F2        Spybots: paid / total and the next reward   Ctrl+F2 twice  pay a Spybot pickup the game did not report
--   F3        Lorbs: the same                             Ctrl+F3 twice  pay a Lorb pickup the game did not report
--   \         Ms. Zurkon's shop bonus: slots and bonuses  Ctrl+\ twice  pay the next shop bonus without buying (v0.71-DEV3)
-- The F keys in brackets work as well while legacy_f_keys = true. Key names are settings
-- (key_status, key_hub, key_hub_return, key_story, key_campaign in 04_rando_settings.lua).
-- (dev(keys).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["keys"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it

local R = RANDO
if not (R and R.bind_setting) then return end
RANDO_DEV_KEYS = true
local function say(text, opts) R.say(text, opts) end
local function log(...) pcall(rivet.log, "[rando]", ...) end
local function ready()
  local ok = false
  pcall(function() ok = rivet.scene_ready() and rivet.hero() ~= nil end)
  return ok
end

-- status; Ctrl: the locked-travel escape hatch (14_rando_travel.lua)
R.bind_setting("key_status", "F9", function()
  if not (RANDO_SEED and R.state) then say("Randomizer: the seed is still being prepared"); return end
  if R.ctrl_down() and RANDO_TRAVEL and RANDO_SEED.travel_lock then RANDO_TRAVEL.hatch(); return end
  say(R.status_text(), { type = "corner", duration = 6 })
end)

-- the campaign director (11_rando_campaign.lua); Ctrl+ is the lab (dev(testmode).lua)
R.bind_setting("key_campaign", "F12", function()
  if R.ctrl_down() or not RANDO_CAMPAIGN_RT then return end
  RANDO_CAMPAIGN_RT.go()
end)

-- v0.71-DEV1: Spybots and Lorbs (10_rando_runtime.lua R.claim_collectible). Their pickup events are bound but have not been
-- seen in a log yet; if you pick one up and rivet.log shows no "RANDO-COLLECTIBLE" line, Ctrl+key twice pays it.
local claim_armed = {}
local function collectible_key(setting, legacy, kind, label)
  R.bind_setting(setting, legacy, function()
    if not (RANDO_SEED and R.state) then say("Randomizer: the seed is still being prepared"); return end
    if not R.ctrl_down() then say(R.collectible_status(kind), { type = "corner", duration = 6 }); return end
    local t = (rivet.time and rivet.time()) or 0
    if not claim_armed[kind] or t - claim_armed[kind] > 4 then
      claim_armed[kind] = t
      say(string.format("Randomizer: press Ctrl+%s again to pay a %s pickup the game did not report", R.config[setting], label),
          { type = "center", duration = 4 })
      return
    end
    claim_armed[kind] = nil
    local ok, why = R.claim_collectible(kind)
    if not ok then say("Randomizer: " .. label .. " not paid - " .. tostring(why), { type = "corner", duration = 5 }) end
  end)
end
collectible_key("key_spybot", nil, "spybot", "Spybot")
collectible_key("key_lorb", nil, "lorb", "Lorb")

-- v0.71-DEV3: Ms. Zurkon's shop bonus (12_rando_shop.lua). Key: the shop's slots, what each sells now and the bonus it pays
-- ([paid] once collected). Ctrl+key twice pays the next unpaid bonus without a purchase - a test of the grant itself.
local shop_armed = nil
R.bind_setting("key_shop", nil, function()
  if not (RANDO_SEED and R.state) then say("Randomizer: the seed is still being prepared"); return end
  local H = RANDO_SHOP
  if not (H and H.bonus_lines) then return end
  if not R.ctrl_down() then
    local lines = H.bonus_lines()
    if #lines == 0 then say("Randomizer: this seed has no shop bonus (shop_bonus = false, or no open weapon slot)", { type = "corner", duration = 5 }); return end
    log("RANDO-SHOP BONUS (key):", table.concat(lines, " | "))
    say("Shop bonus (" .. #lines .. "): " .. table.concat(lines, "; ") .. " [" .. tostring(H.status_text() or "vendor not changed yet") .. "]", { type = "corner", duration = 12 })
    return
  end
  local t = (rivet.time and rivet.time()) or 0
  if not shop_armed or t - shop_armed > 4 then
    shop_armed = t
    say(string.format("Randomizer: press Ctrl+%s again to pay the next shop bonus without buying anything", R.config.key_shop), { type = "center", duration = 4 })
    return
  end
  shop_armed = nil
  local ok, why = H.claim_next()
  if not ok then say("Randomizer: no shop bonus paid - " .. tostring(why), { type = "corner", duration = 5 }) end
end)

-- the hub (15_rando_hub.lua)
local function hub_key(setting, legacy, fn)
  R.bind_setting(setting, legacy, function()
    local H = RANDO_HUB
    if not (H and R.hub_loaded() and R.state) then return end
    if not R.planet_shuffle_on() then
      return say("Randomizer: planet shuffle is off - " .. R.key("key_shuffle") .. " turns it on", { type = "corner", duration = 4 })
    end
    if not H.enabled() then return say("Randomizer: hub_runtime is off", { type = "corner", duration = 3 }) end
    if not ready() then return say("Randomizer: wait until the game has loaded", { type = "corner", duration = 3 }) end
    fn(H, R.ctrl_down())
  end)
end
hub_key("key_hub", "F6", function(H, ctrl) if ctrl then H.key_go() else H.key_select() end end)
hub_key("key_hub_return", "F5", function(H, ctrl) if ctrl then H.key_finish() else H.key_return() end end)
hub_key("key_story", nil, function(H) H.key_story() end)

log("RANDO-KEYS developer keys:", string.format("status %s | hub %s | stay %s | story %s | campaign %s%s",
    R.key("key_status"), R.key("key_hub"), R.key("key_hub_return"), R.key("key_story"), R.key("key_campaign"),
    R.config.legacy_f_keys and " | old F keys too" or ""))
end)

-- ==== section: testtravel (dev(testtravel).lua) =====================================================================
DBG.section("testtravel", function()
-- ---- dev(testtravel).lua ----
-- DEVELOPER TOOL - not part of a release. TEST TRAVEL: go to any planet, whatever Coordinates
-- you hold (rivet_hook, Lua 5.4). The randomizer never needs this file. Its keys work only with
-- test_travel = true in 04_rando_settings.lua (a runtime option: it never changes the seed).
-- A test trip only moves you; it starts no story.
--
-- Keys (key_test_travel / key_test_point; legacy_f_keys = true: F7 / F8 as well):
--   .           next planet (all 10, in story order, starting after the one you are on)
--   ,           next landing point on that planet
--   Ctrl+.      warp there (rivet_hook's checkpoint warp, the one level scripts use)
--   Ctrl+,      fly there with the ship (rivet.fly; needs the ship's planet menu nearby)
--
-- While it is on:
--   * a test trip's landing is remembered as that planet's test landing point
--   * the ship's planet menu takes you anywhere: locked travel does not send you back
--   * rewards follow the usual rules: test travel opens no Coordinates and pays nothing by itself
-- Every trip is written to the randomizer history as [TEST TRAVEL], so a run that used it shows it.
--
-- Landing points of a planet, best first: where you last landed there, where a test trip went,
-- the ones seen in your logs, then the checkpoint catalog (14_rando_travel.lua: every checkpoint
-- rivet.checkpoints() lists, placed on its planet and scored, landing pads first).
-- rivet.log lines start with RANDO-TEST.
-- (dev(testtravel).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["testtravel"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it

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

TT.VERSION = "10.0.39"
local function K(setting, ctrl) return (RANDO and RANDO.key and RANDO.key(setting, ctrl)) or setting end
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
  local tr = (RANDO_TRAVEL and RANDO_TRAVEL.state and s) and RANDO_TRAVEL.state() or (s and s.travel)
  -- real landings first, then where a test trip last went
  if tr and tr.landed then add(tr.landed[pid], "where you last landed") end
  if tr and tr.test_landed then add(tr.test_landed[pid], "where a test trip went") end
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
        sub = catalog_note() .. "; press " .. K("key_test_travel") .. " again in a few seconds, or use the ship's planet menu" })
    log("selected", pid, "- no landing point yet:", catalog_note())
    return
  end
  local k = TT.point[pid] or 1
  if k > #pts then k = 1 end
  TT.point[pid] = k
  local pt = pts[k]
  say(head, { type = "center", duration = 7,
      sub = string.format("%s (%d/%d, %s) - %s warp, %s fly, %s next landing point", pt.cp, k, #pts, pt.why,
                          K("key_test_travel", true), K("key_test_point", true), K("key_test_point")) })
  log("selected", pid, pt.cp, string.format("(%d/%d, %s)", k, #pts, pt.why))
end

local function off_message()
  say("Randomizer: test travel is off - set test_travel = true in 04_rando_settings.lua, then press Pause",
      { type = "center", duration = 6 })
end

-- next planet
function TT.key_next()
  if not TT.on() then return off_message() end
  if TT.sel < 1 then
    local cur = S() and S().current_planet
    TT.sel = (cur and planet_index(cur)) or 0
  end
  TT.sel = (TT.sel % #DB.planets) + 1
  show(TT.selected())
end

-- next landing point of the selected planet
function TT.key_point()
  if not TT.on() then return off_message() end
  local pid = TT.selected()
  if not pid then return TT.key_next() end
  local pts = TT.points(pid)
  if #pts > 0 then TT.point[pid] = ((TT.point[pid] or 1) % #pts) + 1 end
  show(pid)
end

-- go: warp or fly
function TT.go(how)
  if not TT.on() then return off_message() end
  local pid = TT.selected()
  if not pid then
    say("Randomizer: press " .. K("key_test_travel") .. " first to choose a planet", { type = "corner", duration = 4 })
    return false
  end
  local pts = TT.points(pid)
  local pt = pts[TT.point[pid] or 1]
  if not pt then show(pid); return false end
  return TT.travel(pid, pt, how)
end

function TT.travel(pid, pt, how)
  local fn = (how == "fly") and rivet.fly or rivet.warp
  local ok, res = pcall(fn, pt.cp)
  if not ok or res == false then
    log(how, "to", pt.cp, "for", pid, "failed:", tostring(res))
    local hint = (how == "fly") and (" - the ship's flight needs its planet menu nearby (a landing pad); " .. K("key_test_travel", true) .. " warps instead")
                 or (" - " .. K("key_test_point") .. " picks another landing point")
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
  if RANDO_TRAVEL and RANDO_TRAVEL.remember_test then RANDO_TRAVEL.remember_test(pid, trip.cp) end
  log("arrived on", pid, "by", trip.how, "at", trip.cp)
  local s = S()
  local open = s and s.access and s.access[pid]
  say(string.format("Test travel: %s", pname(pid)), { type = "planet", duration = 6,
      sub = open and "you hold its Coordinates" or "no Coordinates here - rewards follow the usual rules" })
  return true
end

-- the planet menu took you to a planet you hold no Coordinates for (14 calls this)
function TT.stayed(pid, how)
  log("no Coordinates for", pid, "- staying (" .. tostring(how) .. ", test_travel is on)")
  history(string.format("[TEST TRAVEL] %s without Coordinates (%s)", pid, tostring(how)))
  say(string.format("Test travel: %s - no Coordinates, but you stay (test_travel is on)", pname(pid)),
      { type = "corner", duration = 6 })
end

function TT.status_text()
  if not TT.on() then return nil end
  return "TEST TRAVEL on (" .. K("key_test_travel") .. " / " .. K("key_test_travel", true) .. ")"
end

-- keys
local function bind(setting, legacy, fn)
  if not (RANDO and RANDO.bind_setting) then return end
  RANDO.bind_setting(setting, legacy, function()
    if not (SEED() and S()) then return end
    if not TT.on() then return off_message() end
    local ready = false
    pcall(function() ready = rivet.scene_ready() and rivet.hero() ~= nil end)
    if not ready then return say("Randomizer: wait until the game has loaded", { type = "corner", duration = 3 }) end
    fn(RANDO.ctrl_down())
  end)
end
bind("key_test_travel", "F7", function(ctrl) if ctrl then TT.go("warp") else TT.key_next() end end)
bind("key_test_point", "F8", function(ctrl) if ctrl then TT.go("fly") else TT.key_point() end end)

log("loaded (" .. TT.VERSION .. ")" .. (TT.on() and string.format(" - test travel is ON: %s planet, %s landing point, %s warp, %s fly",
    K("key_test_travel"), K("key_test_point"), K("key_test_travel", true), K("key_test_point", true)) or " - off"))
end)

-- ==== section: testmode (dev(testmode).lua) =========================================================================
DBG.section("testmode", function()
-- ---- dev(testmode).lua ----
-- DEVELOPER TOOL - not part of a release. Randomizer TEST MODE: shortcuts that fake progress on a
-- spare save. Everything done with them is marked [TEST] in the history and the status line.
--   F10            a story mission on the current planet (or the first one not done)
--   F11            pick up one Gold Bolt on the current planet
--   Ctrl+F10 x2    reset this seed's randomizer progress (press twice within 5 seconds)
--   Ctrl+'  (Ctrl+F12 with legacy_f_keys)   the mission lab: read every mission's state (read only)
--   Ctrl+F11       the mission lab: start / complete / replay a mission on this spare save
-- Delete this file for normal play.
-- (dev(testmode).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["testmode"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_TEST_MODE = true

local R = RANDO
if not (R and R.on_key and RANDO_DATA) then return end
local DB = RANDO_DATA
local function log(...) pcall(rivet.log, "[rando]", ...) end
local function S() return R.state end
local function say(text, opts) R.say(text, opts) end

function R.test_planet()
  local s = S()
  if s.current_planet then return s.current_planet end
  for _, p in ipairs(DB.planets) do if not s.planets_detected[p.id] then return p.id end end
  return DB.planets[#DB.planets].id
end
function R.test_story()
  local s, pid = S(), R.test_planet()
  s.test_used = true
  local n = 0
  for _ in pairs(s.story_missions[pid] or {}) do n = n + 1 end
  R.history("[TEST] story mission " .. (n + 1) .. " on " .. pid)
  R.on_story_mission(pid, "TEST_" .. pid .. "_" .. (n + 1))
  return pid
end
function R.test_gold_bolt()
  local s, pid = S(), R.test_planet()
  s.test_used = true
  local n = 1
  while s.bolts_seen["TEST " .. pid .. " " .. n] do n = n + 1 end
  local lid = R.pick_bolt_location(pid)
  s.bolts_seen["TEST " .. pid .. " " .. n] = lid or "none"
  R.history("[TEST] Gold Bolt on " .. pid)
  if lid then R.collect(lid, "[TEST] Gold Bolt") else say("[TEST] no Gold Bolt left on " .. R.planet_name(pid)) end
  return lid
end
local reset_armed_at = -100
function R.test_reset()
  local now = (rivet.time and rivet.time()) or 0
  if now - reset_armed_at > 5 then
    reset_armed_at = now
    say("[TEST] Press Ctrl+F10 again within 5 seconds to RESET this seed's progress", { type = "center", duration = 5 })
    return false
  end
  reset_armed_at = -100
  local old = S()
  local keep = { real = old.real, real_nodes = old.real_nodes, real_mode = old.real_mode, weapon_types = old.weapon_types,
                 armor_baseline = old.armor_baseline, planet_shuffle = old.planet_shuffle }
  local s = R.fresh_state()
  for k, v in pairs(keep) do s[k] = v end
  s.test_used = true
  R.set_state(s)
  R.begin()
  R.history("[TEST] progress reset")
  say("[TEST] Randomizer progress reset: " .. R.status_text(), { type = "center", duration = 5 })
  return true
end

R.on_key("F10", function()
  if R.ctrl_down() then R.test_reset() else R.test_story() end
end)
R.on_key("F11", function()
  if not R.ctrl_down() then R.test_gold_bolt() end        -- Ctrl+F11 is the lab experiment below
end)

-- the mission lab (11_rando_campaign.lua's D.lab_read / D.lab_try)
local D = RANDO_CAMPAIGN_RT
if D and D.lab_read and D.lab_try then
  local function on_ctrl(name, fn, what)
    local vk = R.vk(name)
    if not vk then return end
    pcall(rivet.on_key, vk, function()
      if not R.ctrl_down() then return end
      local ok, res, msg = pcall(fn)
      if not ok then log("RANDO-ERROR " .. what, tostring(res)) end
      if what == "lab try" then say("[LAB] mission experiment: " .. tostring(msg or res), { type = "center", duration = 6 }) end
    end)
  end
  on_ctrl(R.config.key_campaign, D.lab_read, "lab read")
  if R.config.legacy_f_keys and R.config.key_campaign ~= "F12" then on_ctrl("F12", D.lab_read, "lab read") end
  on_ctrl("F11", D.lab_try, "lab try")
end

log("RANDO-STATUS TEST MODE on: F10 story mission, F11 Gold Bolt, Ctrl+F10 twice resets, Ctrl+" ..
    tostring(R.config.key_campaign) .. " lab read, Ctrl+F11 lab try")
end)

-- ==== section: omega_probe (dev(omega_inventory_probe).lua) =========================================================
DBG.section("omega_probe", function()
-- ---- dev(omega_inventory_probe).lua ----
-- DEVELOPER TOOL - not part of a release. Safe Omega inventory discovery (dev(debug).lua holds it too).
-- Copy this file to GAME_FOLDER/scripts/ for one diagnostic run, then remove it.
-- It only inspects the live hero's component class names and metadata. No game state is mutated,
-- and event ItemHandle values are never treated as scene-actor handles.
-- (dev(omega_inventory_probe).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["omega_probe"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_OMEGA_PROBE = RANDO_OMEGA_PROBE or {}
local P = RANDO_OMEGA_PROBE

local function log(...)
  pcall(rivet.log, "[rando]", "RANDO-OMEGA-PROBE", ...)
end

local function relevant(name)
  local n = tostring(name or ""):lower()
  return n:find("item", 1, true) or n:find("invent", 1, true)
      or n:find("weapon", 1, true) or n:find("equip", 1, true)
      or n:find("loadout", 1, true)
end

local function dump()
  if not (rivet.scene_ready and rivet.scene_ready()) then return false end
  local hero = rivet.hero and rivet.hero()
  if not hero then return false end

  local ok, classes = pcall(rivet.components, hero)
  if not ok or type(classes) ~= "table" then
    P.failures = (P.failures or 0) + 1
    if P.failures == 1 then log("hero component enumeration failed:", tostring(classes)) end
    return P.failures >= 5
  end

  table.sort(classes)
  log("hero handle", tostring(hero), "component count", #classes)
  log("hero components:", table.concat(classes, ", "))

  local found = 0
  for _, class in ipairs(classes) do
    if relevant(class) then
      found = found + 1
      local okc, c = pcall(rivet.component, hero, class)
      if not okc or type(c) ~= "table" then
        log("component", class, "metadata unavailable:", tostring(c))
      else
        log(string.format(
          "component %s address=%s size=%s handle=%s prius=%s prius_size=%s prius_behavior=%s shared=%s",
          tostring(class), tostring(c.address), tostring(c.size), tostring(c.handle),
          tostring(c.prius), tostring(c.prius_size), tostring(c.prius_behavior), tostring(c.shared)))
        local size = math.tointeger(tonumber(c.prius_size)) or 0
        if c.prius and size > 0 then
          local n = math.min(size, 0x80, 512)
          local okr, bytes = pcall(rivet.read, tostring(c.prius), n)
          if okr and bytes then
            log("PRIUS", class, "first", n, "bytes:", tostring(bytes))
          else
            log("PRIUS", class, "read unavailable:", tostring(bytes))
          end
        end
      end
    end
  end
  log("relevant hero components:", found, "(item / inventory / weapon / equip / loadout)")
  log("diagnostic complete - read-only; no memory writes were attempted")
  return true
end

rivet.on_frame(function()
  if P.done then return end
  local ok, finished = pcall(dump)
  if not ok then
    P.failures = (P.failures or 0) + 1
    if P.failures == 1 then log("probe error:", tostring(finished)) end
    if P.failures >= 5 then P.done = true end
  elseif finished then
    P.done = true
  end
end)

log("loaded - waiting for the live hero; read-only")
end)

-- ==== section: probe (dev(item_ids).lua, dev(probe).lua, dev(vtables).lua) ==========================================
DBG.section("probe", function()
-- ---- dev(item_ids).lua ----
do
-- DEVELOPER TOOL - not part of a release (data for dev(probe).lua).
-- generated by tools/gen_item_ids.py from your dag: asset id (hex) -> config path.
-- Used by the probe to recognise item ids inside script nodes. Data only.
-- (dev(item_ids).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["probe"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_ITEM_IDS = {
  ["B44F9479BE5C766B"] = "configs/equipment/equip_loadout_allweapons.config",
  ["B3ECB318D034E7F8"] = "configs/equipment/equip_loadout_allweapons_v5.config",
  ["BE7D6581C0BE4C28"] = "configs/equipment/equip_loadout_ardolis.config",
  ["9A77C7466EB7D4BE"] = "configs/equipment/equip_loadout_arena_a2.config",
  ["99103C8E83BCBF8A"] = "configs/equipment/equip_loadout_blizar.config",
  ["80C5D853386BB8CD"] = "configs/equipment/equip_loadout_challenge_c3_random_burstpistol.config",
  ["B46AFF43CD6ADF6F"] = "configs/equipment/equip_loadout_challenge_c3_random_carpetbomber.config",
  ["9F150830D0DF2D02"] = "configs/equipment/equip_loadout_challenge_c3_random_enforcer.config",
  ["882A7BD4E37AA82A"] = "configs/equipment/equip_loadout_challenge_c3_random_gloveofdoom.config",
  ["BC13C437C6A59ED0"] = "configs/equipment/equip_loadout_challenge_c3_random_mrfunguy.config",
  ["B007A91397E44CE3"] = "configs/equipment/equip_loadout_challenge_c3_random_pixelizer.config",
  ["899A9F927019D4EE"] = "configs/equipment/equip_loadout_challenge_c3_random_ricochet.config",
  ["9C3FD8B665BD4E6E"] = "configs/equipment/equip_loadout_challenge_c3_random_tunneler.config",
  ["BD9F825B8AFA8A0D"] = "configs/equipment/equip_loadout_challenge_c3_random_warprifle.config",
  ["8F6446DEEFE636DA"] = "configs/equipment/equip_loadout_challenge_hover_boots_race.config",
  ["ABA73A9FBAB00EEC"] = "configs/equipment/equip_loadout_challenge_ice_blaster.config",
  ["BFFB017EB22F825A"] = "configs/equipment/equip_loadout_challenge_portal_short_range.config",
  ["856761912047A045"] = "configs/equipment/equip_loadout_challenge_portal_sniper.config",
  ["8EA0D44306F85F34"] = "configs/equipment/equip_loadout_challenge_portal_warmonger.config",
  ["8A70C6A52687FE0F"] = "configs/equipment/equip_loadout_challenge_rando_weap_blaster.config",
  ["836D981EC4ECB5EE"] = "configs/equipment/equip_loadout_challenge_rando_weap_carpetbomb.config",
  ["BC6CDA68792D781A"] = "configs/equipment/equip_loadout_challenge_rando_weap_doom.config",
  ["9DCC2CB8CD594E51"] = "configs/equipment/equip_loadout_challenge_rando_weap_mrfunguy.config",
  ["8179381E75780C6D"] = "configs/equipment/equip_loadout_challenge_rando_weap_pixel.config",
  ["A845771D7BE5046F"] = "configs/equipment/equip_loadout_challenge_rando_weap_ricochet.config",
  ["BDE030396E419EEF"] = "configs/equipment/equip_loadout_challenge_rando_weap_tunneler.config",
  ["8F81FE7DBAFB768A"] = "configs/equipment/equip_loadout_challenge_rando_weap_warprifle.config",
  ["BCDCF0B2492D8ACA"] = "configs/equipment/equip_loadout_challenge_topiary.config",
  ["B5BB2F97C978346B"] = "configs/equipment/equip_loadout_clank.config",
  ["AC17DE3789724940"] = "configs/equipment/equip_loadout_cordelion.config",
  ["9EBDC103966FF508"] = "configs/equipment/equip_loadout_defaultrachette.config",
  ["B69380793EC0DA5A"] = "configs/equipment/equip_loadout_defaultratchet.config",
  ["84E5E884ED3B2717"] = "configs/equipment/equip_loadout_demo.config",
  ["920E95ED8DEE777A"] = "configs/equipment/equip_loadout_empty.config",
  ["811021FE69C01837"] = "configs/equipment/equip_loadout_empty_complete.config",
  ["A0BB27681322DDAC"] = "configs/equipment/equip_loadout_finale.config",
  ["A324B1863644E33A"] = "configs/equipment/equip_loadout_game_start.config",
  ["BCEBFAA2702E0114"] = "configs/equipment/equip_loadout_intro_rooftop.config",
  ["AA1367A7C81461C0"] = "configs/equipment/equip_loadout_jetpack.config",
  ["980E5D968E46F24D"] = "configs/equipment/equip_loadout_magboot_only.config",
  ["8D5DD727E62E6CFA"] = "configs/equipment/equip_loadout_mega_boss.config",
  ["BEBEC15429C095D0"] = "configs/equipment/equip_loadout_mega_progression_01.config",
  ["81F80522D0216A01"] = "configs/equipment/equip_loadout_mega_progression_02.config",
  ["B757A04921C0BDD1"] = "configs/equipment/equip_loadout_mega_progression_03.config",
  ["8F749A0F81CB38E0"] = "configs/equipment/equip_loadout_molonoth.config",
  ["AB003719EA0C9AA4"] = "configs/equipment/equip_loadout_molonoth_complete.config",
  ["8C681E41A7666104"] = "configs/equipment/equip_loadout_nef_burst.config",
  ["A7631F39C1264FAB"] = "configs/equipment/equip_loadout_nef_city.config",
  ["B320D9129E637FE8"] = "configs/equipment/equip_loadout_nef_city_no_glove.config",
  ["BBC484082770C267"] = "configs/equipment/equip_loadout_nef_city_train.config",
  ["AEAA9520F33E3F30"] = "configs/equipment/equip_loadout_nef_slums.config",
  ["BA01EEA0C6C56064"] = "configs/equipment/equip_loadout_nef_tower.config",
  ["9A515D68239F946E"] = "configs/equipment/equip_loadout_parade.config",
  ["B3485BA5D69EBC22"] = "configs/equipment/equip_loadout_parade_wrenchonly.config",
  ["B4DC0F14CFB88835"] = "configs/equipment/equip_loadout_prisonpark.config",
  ["AB3D1EDC7640E926"] = "configs/equipment/equip_loadout_rachette_blasteronly.config",
  ["92D12B00D71CBC89"] = "configs/equipment/equip_loadout_rachette_empty.config",
  ["9815FA08031397CC"] = "configs/equipment/equip_loadout_ratchet_actone.config",
  ["82F249EEA3CB8FF1"] = "configs/equipment/equip_loadout_ratchet_actone_nojetboots.config",
  ["838C29827674A544"] = "configs/equipment/equip_loadout_ratchet_allweapons.config",
  ["BFB032BCE83717F5"] = "configs/equipment/equip_loadout_ratchet_ardolis_piratechallenge.config",
  ["B2DB4371964977D6"] = "configs/equipment/equip_loadout_ratchet_blasteronly.config",
  ["B2EF5789A907E247"] = "configs/equipment/equip_loadout_ratchet_earlygame.config",
  ["AF8A08FAD4C9CD61"] = "configs/equipment/equip_loadout_ratchet_earlygame_plus_topiary.config",
  ["A58A260B246C9B10"] = "configs/equipment/equip_loadout_ratchet_endgame.config",
  ["97F445C220A5FE51"] = "configs/equipment/equip_loadout_ratchet_midgame.config",
  ["869F32A19BEB6CB7"] = "configs/equipment/equip_loadout_ratchet_parade_buzzblades.config",
  ["A47A084F644FDC18"] = "configs/equipment/equip_loadout_ratchet_parade_gloveofdoom.config",
  ["864CD47C4A5A8F96"] = "configs/equipment/equip_loadout_ratchet_parade_tutorial.config",
  ["BCC4657106DEAC4F"] = "configs/equipment/equip_loadout_ratchet_parade_warmonger.config",
  ["84D168E8DD127129"] = "configs/equipment/equip_loadout_ratchet_vs2.config",
  ["9C8719D79F2275E2"] = "configs/equipment/equip_loadout_ratchet_wrenchonly.config",
  ["A8DE24B46D599679"] = "configs/equipment/equip_loadout_ratchet_zurkons_visit1_default.config",
  ["B0D2001AB4CD11C6"] = "configs/equipment/equip_loadout_ratchette_actone_weapon_01.config",
  ["8F94C46C4D2CEE17"] = "configs/equipment/equip_loadout_ratchette_actone_weapon_02.config",
  ["882AF9E773D4251A"] = "configs/equipment/equip_loadout_ratchette_allweapons.config",
  ["B825F2B948FDDEB5"] = "configs/equipment/equip_loadout_ratchette_endgame.config",
  ["AEEB44F7F8CED2D3"] = "configs/equipment/equip_loadout_ratchette_hammeronly.config",
  ["8A5B91704C34BBF4"] = "configs/equipment/equip_loadout_ratchette_midgame.config",
  ["AA55B13F4223856A"] = "configs/equipment/equip_loadout_rivet_intro.config",
  ["ABFAFA83A989A9D1"] = "configs/equipment/equip_loadout_rivet_invasion.config",
  ["99944468111B078A"] = "configs/equipment/equip_loadout_sargasso_1.config",
  ["A6D2801EE8FAF85B"] = "configs/equipment/equip_loadout_sargasso_2.config",
  ["9B30397D9310589C"] = "configs/equipment/equip_loadout_savali.config",
  ["BDFE884965ED3B41"] = "configs/equipment/equip_loadout_savali_2.config",
  ["861FE890FF5876C7"] = "configs/equipment/equip_loadout_savali_boots.config",
  ["B4F5281C105E72FB"] = "configs/equipment/equip_loadout_savali_hboots_newweps.config",
  ["94DAC65350262C97"] = "configs/equipment/equip_loadout_shared.config",
  ["96A7C4B3841BB28D"] = "configs/equipment/equip_loadout_spaceship.config",
  ["B7EACC21D619068A"] = "configs/equipment/equip_loadout_train.config",
  ["90F525E1AD124FD0"] = "configs/equipment/equip_loadout_wrench_magboots.config",
  ["A98ABB74F73F3046"] = "configs/equipment/equip_loadout_zordoom.config",
  ["A46C0A83AA6A7C65"] = "configs/equipment/equip_loadout_zurkons_1.config",
  ["BC7036D3291E3058"] = "configs/equipment/equip_loadout_zurkons_1_plus_topiary.config",
  ["9B2ACEF5538B83B4"] = "configs/equipment/equip_loadout_zurkons_2.config",
  ["8BBB05C05E9BB58B"] = "configs/equipment/equip_zoom_clank_default.config",
  ["A13BFBE1015EC5FB"] = "configs/equipment/equip_zoom_default.config",
  ["9F2848B647CA611F"] = "configs/equipment/equip_zoom_lobbed.config",
  ["AA13D82E37811145"] = "configs/equipment/equip_zoom_ryno.config",
  ["8FFF822180F7E61F"] = "configs/equipment/equip_zoom_shotgun.config",
  ["9F87252AB8F3CF6C"] = "configs/equipment/gdgt_boxbreaker_item.config",
  ["BDF624AF87896CE9"] = "configs/equipment/gdgt_glitchprojector_item.config",
  ["A37A7A2CBD0DF9B4"] = "configs/equipment/gdgt_grindboots_item.config",
  ["87E5325BFD92E3C2"] = "configs/equipment/gdgt_helipack_item.config",
  ["9C998F86A3974C88"] = "configs/equipment/gdgt_hoverboard_rocket.config",
  ["842E8D8EFE349E00"] = "configs/equipment/gdgt_hoverboots_item.config",
  ["B405E27E44753A20"] = "configs/equipment/gdgt_magbootlaunch_item.config",
  ["9D2B016270140D8D"] = "configs/equipment/gdgt_magnetboots_item.config",
  ["9AB06529F129A923"] = "configs/equipment/gdgt_mapomatic_item.config",
  ["942D86888FE97CF0"] = "configs/equipment/gdgt_portalzip_item.config",
  ["9CC557575CA487D8"] = "configs/equipment/gdgt_slingshot_item.config",
  ["BB2D719850EE70AB"] = "configs/equipment/gdgt_swingshot_item.config",
  ["A653844E3C3E67BC"] = "configs/equipment/gdgt_swingshot_weapon.config",
  ["98F2996246EB8469"] = "configs/equipment/gdgt_versaglove_item.config",
  ["8687C1BB32C3A509"] = "configs/equipment/proj_protogrenade_shot.config",
  ["B7C2FEC85DA0681D"] = "configs/equipment/proj_ryno_portal_spawnedshot.config",
  ["A84A4DBF3531219F"] = "configs/equipment/proj_topiarysprinkler_emitter.config",
  ["813A6533FE8EA9FF"] = "configs/equipment/proj_topiarysprinkler_shot.config",
  ["967F6B3BD5A728AD"] = "configs/equipment/proj_topiarysprinkler_shot_nosound.config",
  ["BEFA0BD3E352361C"] = "configs/equipment/proj_topiarysprinkler_targeting.config",
  ["8C8CCC6E3495E1E4"] = "configs/equipment/test/hmiller/test_wpn_arachno_predator_item.config",
  ["9E6B864413C7C4FC"] = "configs/equipment/test/hmiller/test_wpn_arachno_predator_weapon.config",
  ["93AB1D5FA17500FB"] = "configs/equipment/test/hmiller/test_wpn_charge_zapper_item.config",
  ["BEE43981897670CF"] = "configs/equipment/test/hmiller/test_wpn_charge_zapper_weapon.config",
  ["A30BFD24A041D5B0"] = "configs/equipment/test/hmiller/test_wpn_fling_bomb_item.config",
  ["91ABCA33E484BAA1"] = "configs/equipment/test/hmiller/test_wpn_fling_bomb_weapon.config",
  ["B69BAB27A5590DE3"] = "configs/equipment/test/hmiller/test_wpn_stun_web_item.config",
  ["B1DD52B0048635F0"] = "configs/equipment/test/hmiller/test_wpn_stun_web_weapon.config",
  ["A936755D49F329E9"] = "configs/equipment/test/test_gpark_equip_loadout_empty.config",
  ["9CF573AB81FD52CE"] = "configs/equipment/wpn_arachno_predator.config",
  ["8A67A81AEB4604BC"] = "configs/equipment/wpn_arachnodroid_gun_triggereffect.config",
  ["89789E05B4F32AED"] = "configs/equipment/wpn_arachnodroid_gun_triggereffect_light.config",
  ["9AF527D0B0F57FFA"] = "configs/equipment/wpn_arachnodroid_missile_triggereffect.config",
  ["9B5556A231A82AD3"] = "configs/equipment/wpn_arachnodroid_missile_triggereffect_light.config",
  ["B3A6DB13FC84212E"] = "configs/equipment/wpn_blaster_grid.config",
  ["A348B82E699E1784"] = "configs/equipment/wpn_blaster_item.config",
  ["B096CE6A56F894A0"] = "configs/equipment/wpn_blaster_mod.config",
  ["991C5B488C2ACC0C"] = "configs/equipment/wpn_blaster_triggereffect_fire.config",
  ["A21C248799DB0DCA"] = "configs/equipment/wpn_blaster_triggereffect_fire_light.config",
  ["8A5CAE2261550EE1"] = "configs/equipment/wpn_blaster_weapon.config",
  ["BA2C4AD864E09ECD"] = "configs/equipment/wpn_blunderbuster_grid.config",
  ["AAC229E5F1FAA867"] = "configs/equipment/wpn_blunderbuster_item.config",
  ["A6A7B59C43D04377"] = "configs/equipment/wpn_blunderbuster_mod.config",
  ["B72490C139D05178"] = "configs/equipment/wpn_blunderbuster_weapon.config",
  ["9114481B9B674967"] = "configs/equipment/wpn_bouncer_grid.config",
  ["81FA2B260E7D7FCD"] = "configs/equipment/wpn_bouncer_item.config",
  ["B1649C8CF2D13FB6"] = "configs/equipment/wpn_bouncer_minibomb_shot.config",
  ["8C8C4A663EE656E6"] = "configs/equipment/wpn_bouncer_mod.config",
  ["9CCD4C957FB96DB5"] = "configs/equipment/wpn_bouncer_triggereffect_fire.config",
  ["92254BBFC7BDC18E"] = "configs/equipment/wpn_bouncer_triggereffect_fire_light.config",
  ["A00809B9A1226BE0"] = "configs/equipment/wpn_bouncer_weapon.config",
  ["A3D1D0A4DA444869"] = "configs/equipment/wpn_burstpistol_grid.config",
  ["B33FB3994F5E7EC3"] = "configs/equipment/wpn_burstpistol_item.config",
  ["BFDB6C0DC06000A5"] = "configs/equipment/wpn_burstpistol_mod.config",
  ["BA3DDF7E0F1F59D5"] = "configs/equipment/wpn_burstpistol_triggereffect_fire.config",
  ["8FEA419F9B3B9B88"] = "configs/equipment/wpn_burstpistol_triggereffect_fire_light.config",
  ["A2C7A7FF9FC4E9A2"] = "configs/equipment/wpn_burstpistol_weapon.config",
  ["9BEFC57C655ACD70"] = "configs/equipment/wpn_buzzblades_grid.config",
  ["8B01A641F040FBDA"] = "configs/equipment/wpn_buzzblades_item.config",
  ["AAA6E86BC72ACF9A"] = "configs/equipment/wpn_buzzblades_mod.config",
  ["A2259663DAC9FF8E"] = "configs/equipment/wpn_buzzblades_triggereffect_fire.config",
  ["9BD579851E1DA84B"] = "configs/equipment/wpn_buzzblades_triggereffect_fire_light.config",
  ["B6560D60B92AEE64"] = "configs/equipment/wpn_buzzblades_weapon.config",
  ["829E3AA2C75F7191"] = "configs/equipment/wpn_carpetbomber_grid.config",
  ["9270599F5245473B"] = "configs/equipment/wpn_carpetbomber_item.config",
  ["9265EFB9D9B441AB"] = "configs/equipment/wpn_carpetbomber_mod.config",
  ["A2910BBAC3D9B67D"] = "configs/equipment/wpn_carpetbomber_triggereffect_fire.config",
  ["860A6BD89B74CFC5"] = "configs/equipment/wpn_carpetbomber_triggereffect_fire_light.config",
  ["864E41E96413E176"] = "configs/equipment/wpn_carpetbomber_weapon.config",
  ["88DEF4D7C6ABEBD7"] = "configs/equipment/wpn_clank_melee_item.config",
  ["AF74F8F748BFE008"] = "configs/equipment/wpn_clank_melee_melee.config",
  ["91C867072F8C5CB9"] = "configs/equipment/wpn_clank_melee_streak.config",
  ["8717F50CFA0031DF"] = "configs/equipment/wpn_clank_melee_weapon.config",
  ["857A99EFAEA80722"] = "configs/equipment/wpn_clank_puzzle_accel_item.config",
  ["9E79130CB637C3F1"] = "configs/equipment/wpn_clank_puzzle_decel_item.config",
  ["868BD0623910B371"] = "configs/equipment/wpn_clank_puzzle_energy_item.config",
  ["92AD96F341F6B533"] = "configs/equipment/wpn_clank_puzzle_gravity_item.config",
  ["BFC8934F20134E54"] = "configs/equipment/wpn_clank_puzzle_slowdown_item.config",
  ["BD61FB7E3A7EFFB6"] = "configs/equipment/wpn_clank_puzzle_speedup_item.config",
  ["9B89CF2071C443D0"] = "configs/equipment/wpn_clankpuzzle_decel_weapon.config",
  ["868250349D151376"] = "configs/equipment/wpn_clankpuzzlegravity_weapon.config",
  ["BB86E83D17A903FA"] = "configs/equipment/wpn_clankpuzzles_accel_weapon.config",
  ["B0EABEAC35C34A0A"] = "configs/equipment/wpn_clankpuzzles_energy_weapon.config",
  ["A4B0CA7A991FEB51"] = "configs/equipment/wpn_default_beamin.config",
  ["926155D47164C8A5"] = "configs/equipment/wpn_default_triggereffect_empty.config",
  ["B166653B7848A89D"] = "configs/equipment/wpn_default_triggereffect_fire.config",
  ["AAAD3555C0F847D7"] = "configs/equipment/wpn_detcord_grid.config",
  ["BA43566855E2717D"] = "configs/equipment/wpn_detcord_item.config",
  ["96F27AECDA7F8570"] = "configs/equipment/wpn_detcord_mod.config",
  ["8510C12BEFD0A235"] = "configs/equipment/wpn_detcord_weapon.config",
  ["B5365EF057EB223F"] = "configs/equipment/wpn_flyerbreath_item.config",
  ["A8ACEB76A1CCC0A6"] = "configs/equipment/wpn_flyerbreath_weapon.config",
  ["B887FFB58475EBB6"] = "configs/equipment/wpn_flyerfireball_item.config",
  ["BFBDD850730DFA4B"] = "configs/equipment/wpn_flyerfireball_weapon.config",
  ["96A4963BD5233A15"] = "configs/equipment/wpn_fossilizer_grid.config",
  ["864AF50640390CBF"] = "configs/equipment/wpn_fossilizer_item.config",
  ["815E52678260C7D6"] = "configs/equipment/wpn_fossilizer_mod.config",
  ["8A574FA5E17842B5"] = "configs/equipment/wpn_fossilizer_triggereffect_aim.config",
  ["983D709B82F19498"] = "configs/equipment/wpn_fossilizer_triggereffect_aim_light.config",
  ["89D17BC1FEEC7A9A"] = "configs/equipment/wpn_fossilizer_triggereffect_fire.config",
  ["B3E65D56AE758979"] = "configs/equipment/wpn_fossilizer_triggereffect_fire_light.config",
  ["84DB7BC76F85BDD8"] = "configs/equipment/wpn_fossilizer_weapon.config",
  ["9A40416A85455699"] = "configs/equipment/wpn_fossilizer_zoomconfig.config",
  ["B7AC55921C372D94"] = "configs/equipment/wpn_fusion_grenade_grid.config",
  ["A74236AF892D1B3E"] = "configs/equipment/wpn_fusion_grenade_item.config",
  ["8F7F55CD7F5978B9"] = "configs/equipment/wpn_fusion_grenade_mod.config",
  ["B9C868F9888356DA"] = "configs/equipment/wpn_fusion_grenade_weapon.config",
  ["8221F07AB2C82C9D"] = "configs/equipment/wpn_fusiongrenade_subshotconfig.config",
  ["B6201ACFD6F47CC3"] = "configs/equipment/wpn_glove_of_doom_grid.config",
  ["A6CE79F243EE4A69"] = "configs/equipment/wpn_glove_of_doom_item.config",
  ["91E8A72C130631BC"] = "configs/equipment/wpn_glove_of_doom_mod.config",
  ["A4AC4488FA5B9B48"] = "configs/equipment/wpn_glove_of_doom_weapon.config",
  ["9376D5843B248119"] = "configs/equipment/wpn_groovitron_grid.config",
  ["8398B6B9AE3EB7B3"] = "configs/equipment/wpn_groovitron_item.config",
  ["9014732F5BBB04AB"] = "configs/equipment/wpn_groovitron_mod.config",
  ["803BFF6DB9A1BCC4"] = "configs/equipment/wpn_groovitron_weapon.config",
  ["AC8C2336AAA959CB"] = "configs/equipment/wpn_hammer_item.config",
  ["838ACB87802B81A0"] = "configs/equipment/wpn_hammer_weapon.config",
  ["829F7887BE324660"] = "configs/equipment/wpn_hexapodgun__left_item.config",
  ["8F0DA6D438D2A457"] = "configs/equipment/wpn_hexapodgun_buffed_item.config",
  ["AA77DC8904D7F0EC"] = "configs/equipment/wpn_hexapodgun_item.config",
  ["8990274291A6693D"] = "configs/equipment/wpn_hexapodgun_weapon.config",
  ["A1DABCDB4412D3C7"] = "configs/equipment/wpn_hexapodgun_weaponbuffed.config",
  ["84A1A83C092268A8"] = "configs/equipment/wpn_hexapodmortar_aimcontext.config",
  ["92CDEE2DD3F048D1"] = "configs/equipment/wpn_hexapodmortar_item.config",
  ["B03D869C7578584D"] = "configs/equipment/wpn_hexapodmortar_weapon.config",
  ["A26BBAC2D8383394"] = "configs/equipment/wpn_hexapodmortar_zoom.config",
  ["82BE6A72B314A861"] = "configs/equipment/wpn_icicleblast_grid.config",
  ["9BBBD160F7F394F6"] = "configs/equipment/wpn_icicleblast_icicle_shotconfig.config",
  ["9250094F260E9ECB"] = "configs/equipment/wpn_icicleblast_item.config",
  ["B2353FCD926DB1EB"] = "configs/equipment/wpn_icicleblast_mod.config",
  ["BFF04C36FE3AAC00"] = "configs/equipment/wpn_icicleblast_weapon.config",
  ["9456B11735397846"] = "configs/equipment/wpn_icicleblaster_triggereffect_fire.config",
  ["91BBD03E9A92DF15"] = "configs/equipment/wpn_icicleblaster_triggereffect_fire_light.config",
  ["B5119946EA1C0200"] = "configs/equipment/wpn_kamehameha_camstick.config",
  ["AE12232DA2662E87"] = "configs/equipment/wpn_kamehameha_grid.config",
  ["BEFC4010377C182D"] = "configs/equipment/wpn_kamehameha_item.config",
  ["B1596496E2FF0BCA"] = "configs/equipment/wpn_kamehameha_mod.config",
  ["8DCC8D5CDC2E058A"] = "configs/equipment/wpn_kamehameha_triggereffect.config",
  ["A8660FA8365CC509"] = "configs/equipment/wpn_kamehameha_triggereffect_light.config",
  ["B18964361A999F40"] = "configs/equipment/wpn_kamehameha_weapon.config",
  ["8E5A14FF3CB46368"] = "configs/equipment/wpn_kamehameha_zoom.config",
  ["8BEFF5CB76E59885"] = "configs/equipment/wpn_kit_warbot_gun_item.config",
  ["B8B4BD2CE7527515"] = "configs/equipment/wpn_kit_warbot_gun_weapon.config",
  ["ADDF65F667A434D8"] = "configs/equipment/wpn_lightningrod_grid.config",
  ["BD3106CBF2BE0272"] = "configs/equipment/wpn_lightningrod_item.config",
  ["90C2B691A97E6642"] = "configs/equipment/wpn_lightningrod_mod.config",
  ["8EE613790E769BFE"] = "configs/equipment/wpn_lightningrod_triggereffect_detonate.config",
  ["B0816A5868531798"] = "configs/equipment/wpn_lightningrod_triggereffect_fire.config",
  ["86628C8A9FA1CE88"] = "configs/equipment/wpn_lightningrod_triggereffect_fire_light.config",
  ["B424A83389DB01C6"] = "configs/equipment/wpn_lightningrod_weapon.config",
  ["A601D823A7D4659C"] = "configs/equipment/wpn_magnamissile_grid.config",
  ["B6EFBB1E32CE5336"] = "configs/equipment/wpn_magnamissile_item.config",
  ["ACDA75D68E2D3A18"] = "configs/equipment/wpn_magnamissile_mod.config",
  ["972794263A3EF5FA"] = "configs/equipment/wpn_magnamissile_weapon.config",
  ["AA53A5EEA61DB0F9"] = "configs/equipment/wpn_magshield_grid.config",
  ["BABDC6D333078653"] = "configs/equipment/wpn_magshield_item.config",
  ["A10E961FE80FA4B2"] = "configs/equipment/wpn_magshield_mod.config",
  ["AB1F3AD1A40AE27B"] = "configs/equipment/wpn_magshield_triggereffect.config",
  ["A746553818414108"] = "configs/equipment/wpn_magshield_triggereffect_light.config",
  ["806D2B76E65503B9"] = "configs/equipment/wpn_magshield_weapon.config",
  ["8E75D350A703D752"] = "configs/equipment/wpn_mrfunguy_bot_awareness.config",
  ["ACE6EFEE94CC28A4"] = "configs/equipment/wpn_mrfunguy_bot_melee.config",
  ["A7A72C4ABEFD1095"] = "configs/equipment/wpn_mrfunguy_bot_movement.config",
  ["977B516DEE7FD53D"] = "configs/equipment/wpn_mrfunguy_bot_targeting.config",
  ["9D8D496BB74B29AA"] = "configs/equipment/wpn_mrfunguy_grid.config",
  ["935447A3DD14AAA9"] = "configs/equipment/wpn_mrfunguy_hitreact.config",
  ["8D632A5622511F00"] = "configs/equipment/wpn_mrfunguy_item.config",
  ["834843176AF66FCE"] = "configs/equipment/wpn_mrfunguy_mod.config",
  ["8258FEAA62D9282B"] = "configs/equipment/wpn_mrfunguy_triggereffect_fire.config",
  ["8452E615B84569F5"] = "configs/equipment/wpn_mrfunguy_triggereffect_fire_light.config",
  ["ABD5FF3E14067369"] = "configs/equipment/wpn_mrfunguy_weapon.config",
  ["A3DBFABE617E34A0"] = "configs/equipment/wpn_nailgun_grid.config",
  ["B3359983F464020A"] = "configs/equipment/wpn_nailgun_item.config",
  ["B5F176B6FA1CC925"] = "configs/equipment/wpn_nailgun_mod.config",
  ["B3F94DF5A20D4016"] = "configs/equipment/wpn_nailgun_weapon.config",
  ["8835A67840B30875"] = "configs/equipment/wpn_pitofdeath_grid.config",
  ["98DBC545D5A93EDF"] = "configs/equipment/wpn_pitofdeath_item.config",
  ["80E8DB071A46ACB6"] = "configs/equipment/wpn_pitofdeath_mod.config",
  ["9AB0D4DEDA6C5A8F"] = "configs/equipment/wpn_pitofdeath_weapon.config",
  ["9B9F49E0947C368E"] = "configs/equipment/wpn_pixelizer_grid.config",
  ["8B712ADD01660024"] = "configs/equipment/wpn_pixelizer_item.config",
  ["BE9C5F500A12B6FB"] = "configs/equipment/wpn_pixelizer_mod.config",
  ["B614646342BB26DD"] = "configs/equipment/wpn_pixelizer_weapon.config",
  ["AAB5026EB0764BF2"] = "configs/equipment/wpn_plasma_striker_grid.config",
  ["BA5B6153256C7D58"] = "configs/equipment/wpn_plasma_striker_item.config",
  ["8EC5419C5473A0F0"] = "configs/equipment/wpn_plasma_striker_mod.config",
  ["92BFD5F5C31A4BE9"] = "configs/equipment/wpn_plasma_striker_weapon.config",
  ["89FFCEE246B53616"] = "configs/equipment/wpn_plasmastriker_zoomconfig.config",
  ["90DA8CA29466E5BB"] = "configs/equipment/wpn_predator_launcher_grid.config",
  ["8034EF9F017CD311"] = "configs/equipment/wpn_predator_launcher_item.config",
  ["B42677887B8713C2"] = "configs/equipment/wpn_predator_launcher_mod.config",
  ["9A65E33F75221B90"] = "configs/equipment/wpn_predator_launcher_weapon.config",
  ["90E14CDA8DD9D960"] = "configs/equipment/wpn_predatorlauncher_minimissileconfig.config",
  ["BC89F736535DE5B7"] = "configs/equipment/wpn_protogrenade_grid.config",
  ["AC67940BC647D31D"] = "configs/equipment/wpn_protogrenade_item.config",
  ["8114B09095144CE1"] = "configs/equipment/wpn_protogrenade_mod.config",
  ["A8301EE6B3F4001A"] = "configs/equipment/wpn_protogrenade_triggereffect.config",
  ["A313C4E08A26BDFC"] = "configs/equipment/wpn_protogrenade_triggereffect_light.config",
  ["8256EC7512E9A2BF"] = "configs/equipment/wpn_protogrenade_weapon.config",
  ["8B687178AAA3D139"] = "configs/equipment/wpn_protoshotgun_grid.config",
  ["9B8612453FB9E793"] = "configs/equipment/wpn_protoshotgun_item.config",
  ["9C38AE70BF405A5D"] = "configs/equipment/wpn_protoshotgun_mod.config",
  ["BBE30873B2C084DB"] = "configs/equipment/wpn_protoshotgun_triggereffect.config",
  ["A5BB440C022B89B1"] = "configs/equipment/wpn_protoshotgun_triggereffect_light.config",
  ["8266535EAB64A053"] = "configs/equipment/wpn_protoshotgun_weapon.config",
  ["A0931A4CEABE25A3"] = "configs/equipment/wpn_pyrocitor_grid.config",
  ["B07D79717FA41309"] = "configs/equipment/wpn_pyrocitor_item.config",
  ["BC16F1A08FD270CE"] = "configs/equipment/wpn_pyrocitor_mod.config",
  ["931885DA00CF3068"] = "configs/equipment/wpn_pyrocitor_sub_shot.config",
  ["954D77E9622EDDA4"] = "configs/equipment/wpn_pyrocitor_weapon.config",
  ["AAFC2CC7CF31B364"] = "configs/equipment/wpn_revolver_grid.config",
  ["BA124FFA5A2B85CE"] = "configs/equipment/wpn_revolver_item.config",
  ["A35DC329F848B191"] = "configs/equipment/wpn_revolver_mod.config",
  ["A9369F5FF87321A5"] = "configs/equipment/wpn_revolver_weapon.config",
  ["A5FF2343A1FDF02A"] = "configs/equipment/wpn_ricochet_grid.config",
  ["B511407E34E7C680"] = "configs/equipment/wpn_ricochet_item.config",
  ["BEFC1C122E23BE10"] = "configs/equipment/wpn_ricochet_mod.config",
  ["9600C7D2A2475B86"] = "configs/equipment/wpn_ricochet_triggereffect_fire.config",
  ["9C953559C5E8FA19"] = "configs/equipment/wpn_ricochet_triggereffect_fire_light.config",
  ["AFE0A05639B4C889"] = "configs/equipment/wpn_ricochet_weapon.config",
  ["85B714913F2FBDC5"] = "configs/equipment/wpn_ricochet_zoom.config",
  ["A19A6D6355B88929"] = "configs/equipment/wpn_ryno_grid.config",
  ["B1740E5EC0A2BF83"] = "configs/equipment/wpn_ryno_item.config",
  ["8A630D6B1A346C68"] = "configs/equipment/wpn_ryno_mod.config",
  ["89C87AF2D7D364A0"] = "configs/equipment/wpn_ryno_triggereffect_fire.config",
  ["88DDC8A2DC72619F"] = "configs/equipment/wpn_ryno_triggereffect_fire_light.config",
  ["90F8067A9D096609"] = "configs/equipment/wpn_ryno_weapon.config",
  ["92EA8866106E4216"] = "configs/equipment/wpn_schrodinger_grid.config",
  ["8204EB5B857474BC"] = "configs/equipment/wpn_schrodinger_item.config",
  ["9E913E2FBE76156E"] = "configs/equipment/wpn_schrodinger_mod.config",
  ["9A790F8C1DFAB119"] = "configs/equipment/wpn_schrodinger_weapon.config",
  ["95B3028C9B672088"] = "configs/equipment/wpn_seismicshock_grid.config",
  ["855D61B10E7D1622"] = "configs/equipment/wpn_seismicshock_item.config",
  ["B37BBB7E986667DC"] = "configs/equipment/wpn_seismicshock_mod.config",
  ["ABDA447478EB7929"] = "configs/equipment/wpn_seismicshock_weapon.config",
  ["AAD5EF22B0D0F35A"] = "configs/equipment/wpn_sheepinator_grid.config",
  ["BA3B8C1F25CAC5F0"] = "configs/equipment/wpn_sheepinator_item.config",
  ["8A9E265619088F91"] = "configs/equipment/wpn_sheepinator_mod.config",
  ["B17794BA3892355A"] = "configs/equipment/wpn_sheepinator_weapon.config",
  ["945F76575122CB45"] = "configs/equipment/wpn_stickyblaster_grid.config",
  ["84B1156AC438FDEF"] = "configs/equipment/wpn_stickyblaster_item.config",
  ["A961E455994033F8"] = "configs/equipment/wpn_stickyblaster_mod.config",
  ["BDD63E39D0D94C78"] = "configs/equipment/wpn_stickyblaster_weapon.config",
  ["AFD600E08BA5C72A"] = "configs/equipment/wpn_thumper_grid.config",
  ["BF3863DD1EBFF180"] = "configs/equipment/wpn_thumper_item.config",
  ["83142D5E65DB3F6E"] = "configs/equipment/wpn_thumper_mod.config",
  ["B8EC8C05816E61EE"] = "configs/equipment/wpn_thumper_weapon.config",
  ["89E4CCD061254310"] = "configs/equipment/wpn_topiary_healthdrop.config",
  ["8B9709EBB90D4C52"] = "configs/equipment/wpn_topiaryblaster_grid.config",
  ["9B796AD62C177AF8"] = "configs/equipment/wpn_topiaryblaster_item.config",
  ["AA2C6AF6C65A3EDF"] = "configs/equipment/wpn_topiaryblaster_mod.config",
  ["B7DA9C5DC372E3BE"] = "configs/equipment/wpn_topiaryblaster_weapon.config",
  ["AD402AEDB9ACD97A"] = "configs/equipment/wpn_triggereffect_warprifle.config",
  ["AA15DE0379861E6A"] = "configs/equipment/wpn_tunneler_grid.config",
  ["BAFBBD3EEC9C28C0"] = "configs/equipment/wpn_tunneler_item.config",
  ["83C3500A9862B053"] = "configs/equipment/wpn_tunneler_mod.config",
  ["8DF607D21C1566C2"] = "configs/equipment/wpn_tunneler_triggereffect.config",
  ["A7200F2F9B57094B"] = "configs/equipment/wpn_tunneler_triggereffect_light.config",
  ["927D92CBCBB28593"] = "configs/equipment/wpn_tunneler_weapon.config",
  ["8A5DE9D1E7545385"] = "configs/equipment/wpn_tunneler_zoom.config",
  ["804AB15269EC1EBE"] = "configs/equipment/wpn_turret_shot.config",
  ["B2D72C40E6C3CA25"] = "configs/equipment/wpn_tutorializer_grid.config",
  ["A2394F7D73D9FC8F"] = "configs/equipment/wpn_tutorializer_item.config",
  ["81A3DBC4AE39AB75"] = "configs/equipment/wpn_tutorializer_weapon.config",
  ["9D80B73301250E29"] = "configs/equipment/wpn_volcaniceruptor_grid.config",
  ["8D6ED40E943F3883"] = "configs/equipment/wpn_volcaniceruptor_item.config",
  ["8EB61BA104D1EC4E"] = "configs/equipment/wpn_volcaniceruptor_mod.config",
  ["BBECBB36071F2FFD"] = "configs/equipment/wpn_volcaniceruptor_subshot.config",
  ["86F63FC43D59EB15"] = "configs/equipment/wpn_volcaniceruptor_weapon.config",
  ["A277F0E7B24B6C9C"] = "configs/equipment/wpn_warmonger_grid.config",
  ["B29993DA27515A36"] = "configs/equipment/wpn_warmonger_item.config",
  ["908EE6BA58761CAA"] = "configs/equipment/wpn_warmonger_microrocket_shot.config",
  ["8B23804E604AEBA0"] = "configs/equipment/wpn_warmonger_mod.config",
  ["8BF8D2D8421A98FD"] = "configs/equipment/wpn_warmonger_triggereffect_fire.config",
  ["81B4DCA5BFF4E584"] = "configs/equipment/wpn_warmonger_triggereffect_fire_light.config",
  ["88509280BCDCC008"] = "configs/equipment/wpn_warmonger_weapon.config",
  ["974523ABD8BC5B70"] = "configs/equipment/wpn_warprifle_grid.config",
  ["AF9CD8D64C6B035A"] = "configs/equipment/wpn_warprifle_hightemp_camstick.config",
  ["B54D315BB0086F19"] = "configs/equipment/wpn_warprifle_implosionshotconfig.config",
  ["87AB40964DA66DDA"] = "configs/equipment/wpn_warprifle_item.config",
  ["A8CB03475F44E61A"] = "configs/equipment/wpn_warprifle_lowtemp_camstick.config",
  ["9EA32668673C5A4E"] = "configs/equipment/wpn_warprifle_mediumtemp_camstick.config",
  ["9685468B59CC3B72"] = "configs/equipment/wpn_warprifle_mod.config",
  ["92E7EB38F3DB4821"] = "configs/equipment/wpn_warprifle_triggereffect_fire.config",
  ["B8D63C8DD9CDEE3A"] = "configs/equipment/wpn_warprifle_triggereffect_fire_light.config",
  ["B2BBE01937DA8024"] = "configs/equipment/wpn_warprifle_weapon.config",
  ["B70D1479466E169F"] = "configs/equipment/wpn_warprifle_zoom.config",
  ["A178983A0CCBEC09"] = "configs/equipment/wpn_wrench_item.config",
  ["AA338D795C97A448"] = "configs/equipment/wpn_wrench_melee.config",
  ["8027BEC8CB618B30"] = "configs/equipment/wpn_wrench_streak.config",
  ["96F82CC31EEDE656"] = "configs/equipment/wpn_wrench_weapon.config",
  ["AA14752001E5F995"] = "configs/equipment/wpn_zurkon_emergentvo.config",
  ["BB67D73D260EA133"] = "configs/equipment/wpn_zurkon_grid.config",
  ["AB89B400B3149799"] = "configs/equipment/wpn_zurkon_item.config",
  ["B68EA860D566ACF0"] = "configs/equipment/wpn_zurkon_mod.config",
  ["BABE76C945B681B8"] = "configs/equipment/wpn_zurkon_shot.config",
  ["8274AC7EE91C8B1D"] = "configs/equipment/wpn_zurkon_weapon.config",
  ["8BE8CDA154FC1B77"] = "configs/hero/ally_accessibility_highlight.config",
  ["97273A97EC446362"] = "configs/hero/hero_accessibility_highlight.config",
  ["94AABCE76E15BD2A"] = "configs/hero/hero_aimassist_crate.config",
  ["A4FE496E5E1E068E"] = "configs/hero/hero_aimassist_curve_friction.config",
  ["B6AA23AD161437C3"] = "configs/hero/hero_aimassist_curve_magnetism.config",
  ["99DFE089337C69F6"] = "configs/hero/hero_aimassist_user_casual.config",
  ["9A9A78CD8C3FCEBE"] = "configs/hero/hero_aimassist_user_default.config",
  ["9A6DA4239397FE26"] = "configs/hero/hero_aimassist_user_fossilizer_zoom00.config",
  ["B2E1C4C9F1AF79B3"] = "configs/hero/hero_aimassist_user_fossilizer_zoom00_casual.config",
  ["ACC20148627629F6"] = "configs/hero/hero_aimassist_user_fossilizer_zoom01.config",
  ["8EFCBDE2662E16CC"] = "configs/hero/hero_aimassist_user_fossilizer_zoom01_casual.config",
  ["9384C53E9B97D627"] = "configs/hero/hero_aimassist_user_fossilizer_zoom02.config",
  ["AE6D1D54356E20ED"] = "configs/hero/hero_aimassist_user_fossilizer_zoom02_casual.config",
  ["936131E32E3722E3"] = "configs/hero/hero_aimassist_user_strafe.config",
  ["A818F1B7F5C7F6F6"] = "configs/hero/hero_aimassist_user_strafe_casual.config",
  ["AD558850758AD0F8"] = "configs/hero/hero_aimassist_user_zoom.config",
  ["B45A5C26C1A83DAE"] = "configs/hero/hero_aimassist_user_zoom_casual.config",
  ["95619D97C5DAD768"] = "configs/hero/hero_battlebrew_armor.config",
  ["B83C92EADC633781"] = "configs/hero/hero_battlebrew_boltiplier.config",
  ["A18B3F635C4126DF"] = "configs/hero/hero_battlebrew_float.config",
  ["995D4EA6C728F2BE"] = "configs/hero/hero_battlebrew_nanotech_drain.config",
  ["9B1D5B95FDE66DCF"] = "configs/hero/hero_battlebrew_overdrive.config",
  ["8AAB6A82B0B79A23"] = "configs/hero/hero_battlebrew_scale.config",
  ["BAFC108897CBD935"] = "configs/hero/hero_battlebrew_time_dilation.config",
  ["AA345CBFB812BB9B"] = "configs/hero/hero_battlebrew_vampire.config",
  ["B51D4B439B6271B3"] = "configs/hero/hero_beamin.config",
  ["B6B481C01EDEA3CE"] = "configs/hero/hero_beamout.config",
  ["91C6109E86AB306B"] = "configs/hero/hero_character_list.config",
  ["9BFB80447C896FDD"] = "configs/hero/hero_clank_grind.config",
  ["ACB1CADE18654E7C"] = "configs/hero/hero_clank_level.config",
  ["965C67E9C44B634B"] = "configs/hero/hero_clank_mover.config",
  ["806C37EF6071F2B1"] = "configs/hero/hero_clank_shared.config",
  ["BBAFB8E8E06B0EA0"] = "configs/hero/hero_clank_slide.config",
  ["A499834D0EE776D9"] = "configs/hero/hero_clank_traversal.config",
  ["B7A5E7D4A0F13E4D"] = "configs/hero/hero_clank_traversal_puzzle_accel.config",
  ["A489C5D31E9E9F91"] = "configs/hero/hero_clank_traversal_puzzle_decel.config",
  ["9D19E765E821DE4B"] = "configs/hero/hero_clank_traversal_puzzle_rise.config",
  ["BCEC9F0392798E11"] = "configs/hero/hero_clankaimassisttargetconfig.config",
  ["B603CC1C7FFAA5A1"] = "configs/hero/hero_clankpack.config",
  ["BC2C027295A2A39F"] = "configs/hero/hero_clankpack_classic.config",
  ["9439911989273BC0"] = "configs/hero/hero_clankpack_loadout_default.config",
  ["B381276A2B565431"] = "configs/hero/hero_clankpack_loadout_none.config",
  ["8B6666CC8903C62D"] = "configs/hero/hero_clankpack_loadout_ratchet_clank.config",
  ["B6213BD3F274CAFE"] = "configs/hero/hero_clankpack_loadout_ratchet_clank_parade.config",
  ["B36A5F549C063CFD"] = "configs/hero/hero_clankpack_loadout_ratchet_kit.config",
  ["96A13233DF98EBF4"] = "configs/hero/hero_clankpack_loadout_rivet_clank.config",
  ["9C629F084720D12E"] = "configs/hero/hero_clankpack_loadout_rivet_kit.config",
  ["851B52191AE925A3"] = "configs/hero/hero_clankpack_loadout_rivet_kit_ratchet_clank.config",
  ["AB164975278024A3"] = "configs/hero/hero_clankpack_ratchette.config",
  ["BCED9E471124548E"] = "configs/hero/hero_clarkpack.config",
  ["BEC57F1DC4DD8403"] = "configs/hero/hero_fasttravel.config",
  ["973E6B23C1807074"] = "configs/hero/hero_grind.config",
  ["8116293D855932E4"] = "configs/hero/hero_grind_override_intro_passive_shift.config",
  ["883006289BBF5CF2"] = "configs/hero/hero_grind_override_zurk_boss_pshift.config",
  ["9DA73C4DD9DD7926"] = "configs/hero/hero_hoverboot.config",
  ["B41F9980DC9251F6"] = "configs/hero/hero_hoverboot_kick_triggereffect.config",
  ["96CC1C4FCDC7D62B"] = "configs/hero/hero_hoverboot_warp1.config",
  ["A98AD839342629FA"] = "configs/hero/hero_hoverboot_warp2.config",
  ["9F257D52C5C7FE2A"] = "configs/hero/hero_hoverboot_warp3.config",
  ["8B9DB97E2FDB33FA"] = "configs/hero/hero_hoverboot_zordoomhoverbootsequence.config",
  ["8E09CC6D9E0E7EE4"] = "configs/hero/hero_kitpack.config",
  ["A07421B9A56C51D5"] = "configs/hero/hero_level.config",
  ["8FA1542A03052FE9"] = "configs/hero/hero_micronship_missile_shot.config",
  ["9A998C8E79427CE2"] = "configs/hero/hero_mover.config",
  ["AFA9B7AEC46B79D0"] = "configs/hero/hero_openpocketdim.config",
  ["94CB49ECA10EB6F8"] = "configs/hero/hero_playerxp_item.config",
  ["B6EB9D9CBA8BA136"] = "configs/hero/hero_portalzip.config",
  ["BE6F6570D1CBAEEB"] = "configs/hero/hero_prop.config",
  ["AC116761AFFDC401"] = "configs/hero/hero_prop_gallery.config",
  ["97057693272278B7"] = "configs/hero/hero_ratchet_level.config",
  ["B6D4B3B442297C6B"] = "configs/hero/hero_respawn.config",
  ["BD094FC96E4AFAD9"] = "configs/hero/hero_rivet_prop_gallery.config",
  ["BEC994B3E5BE8B0D"] = "configs/hero/hero_shared.config",
  ["B610C326BA7270F3"] = "configs/hero/hero_ship_bullet_emitter_lt.config",
  ["8623B0615726E410"] = "configs/hero/hero_ship_bullet_emitter_rt.config",
  ["9DE7DE3FE0958E70"] = "configs/hero/hero_ship_bullet_shot.config",
  ["801CFECBFB4A9F96"] = "configs/hero/hero_ship_bullet_targeting.config",
  ["B0F9CC4B05B0EF11"] = "configs/hero/hero_ship_missile_emitter.config",
  ["BE493227913DE18A"] = "configs/hero/hero_ship_missile_rt_emitter.config",
  ["9447D5770B0111D2"] = "configs/hero/hero_ship_missile_shot.config",
  ["A9D7574E7C76874F"] = "configs/hero/hero_ship_missile_targeting.config",
  ["8000C3BFEAE73385"] = "configs/hero/hero_ship_teslablast_shot.config",
  ["B1875FE3C546B352"] = "configs/hero/hero_skin_clank.config",
  ["8CD6B82DE095EEA3"] = "configs/hero/hero_skin_ratchet.config",
  ["8A5C01C8CEB08F32"] = "configs/hero/hero_skin_ratchette.config",
  ["B76A538F5D621109"] = "configs/hero/hero_slide.config",
  ["AD3D6E155BE6411C"] = "configs/hero/hero_slide_molonoth.config",
  ["9288E94B9D95D994"] = "configs/hero/hero_slide_override_pshift.config",
  ["937BA2763A64CFE1"] = "configs/hero/hero_spaceship_flight_default.config",
  ["8B14FBFFD6A629C9"] = "configs/hero/hero_spaceship_level.config",
  ["9C026D1836E4E0E2"] = "configs/hero/hero_spaceship_magnet.config",
  ["A2EBC6FE0E26AAB8"] = "configs/hero/hero_spaceship_magnettow_cameracurve.config",
  ["B2018BFFDB374DBA"] = "configs/hero/hero_spaceship_movecurve.config",
  ["9F992A4EDA815E2D"] = "configs/hero/hero_spaceship_thrust.config",
  ["B0D50B22AC513D00"] = "configs/hero/hero_spaceship_thrustcurve.config",
  ["84C4866FF74F7F64"] = "configs/hero/hero_traversal.config",
  ["956568D54D829B99"] = "configs/hero/hero_unique_clank.config",
  ["9FAB9B08EB29266A"] = "configs/hero/hero_unique_ratchet.config",
  ["850633250F73152C"] = "configs/hero/hero_unique_ratchette.config",
  ["B2B721F92E1D5246"] = "configs/hero/hero_unique_spaceship.config",
  ["82D14B30DDEA8818"] = "configs/hero/hero_weapon_level.config",
  ["998B1D0E0037811E"] = "configs/hero/test/jusher/hero_grind_override_blizar_double_loop_slow.config",
  ["B0F3A691EA70AB09"] = "configs/hero/test/jusher/hero_grind_override_float_drag_fast.config",
  ["A2FA4023022723A0"] = "configs/hero/test/jusher/hero_grind_override_float_drag_medium.config",
  ["8963A6137DEC5DEF"] = "configs/hero/test/jusher/hero_grind_override_float_drag_slow.config",
  ["93DC54F7A17C2EB8"] = "configs/hero/test/jusher/hero_grind_override_kalebo_float.config",
  ["8197498CB4D277ED"] = "configs/hero/test/jusher/hero_grind_override_zordoom.config",
  ["B33274CCB0A9CE3E"] = "configs/hero/test/jusher/test_hero_grind_override.config",
  ["9A3B33E46D963518"] = "configs/hero/test/jyednock/test_hero_grind_override.config",
  ["9B7601041789BF85"] = "configs/hero/test/jyednock/test_hero_hoverboot_override.config",
  ["AFF58BE8DD12F92A"] = "configs/hero/test/jyednock/test_hero_slide_override.config",
  ["AAC36DF1894813C2"] = "configs/hero/vanity/vanitybundles/android_armor/hero_vanity_bundle_head_android_armor.config",
  ["BABA5C38A243DEAB"] = "configs/hero/vanity/vanitybundles/android_armor/hero_vanity_bundle_legs_android_armor.config",
  ["A97016E53C96D07F"] = "configs/hero/vanity/vanitybundles/android_armor/hero_vanity_bundle_torso_android_armor.config",
  ["9827564FE7B8F06F"] = "configs/hero/vanity/vanitybundles/beginning_armor/hero_vanity_bundle_head_beginning_armor.config",
  ["8FF06EEE40BD44F3"] = "configs/hero/vanity/vanitybundles/beginning_armor/hero_vanity_bundle_legs_beginning_armor.config",
  ["A518FE7359C380A0"] = "configs/hero/vanity/vanitybundles/beginning_armor/hero_vanity_bundle_torso_beginning_armor.config",
  ["B527A1F98E5E7D35"] = "configs/hero/vanity/vanitybundles/carbonox_armor/hero_vanity_bundle_head_carbonox_armor.config",
  ["A7552D5025EED180"] = "configs/hero/vanity/vanitybundles/carbonox_armor/hero_vanity_bundle_legs_carbonox_armor.config",
  ["85EAD7CCFB74AE51"] = "configs/hero/vanity/vanitybundles/carbonox_armor/hero_vanity_bundle_torso_carbonox_armor.config",
  ["A88B07E8ECCAFBF5"] = "configs/hero/vanity/vanitybundles/carbonox_preorder_armor/hero_vanity_bundle_head_carbonox_preorder_armor.config",
  ["A2E70A0C663B372A"] = "configs/hero/vanity/vanitybundles/carbonox_preorder_armor/hero_vanity_bundle_legs_carbonox_preorder_armor.config",
  ["A4E59E596CAC765A"] = "configs/hero/vanity/vanitybundles/carbonox_preorder_armor/hero_vanity_bundle_torso_carbonox_preorder_armor.config",
  ["B37FF2A19EAC4C7C"] = "configs/hero/vanity/vanitybundles/clank_armor/hero_vanity_bundle_head_clank_armor.config",
  ["9F176042DA9FD87B"] = "configs/hero/vanity/vanitybundles/clank_armor/hero_vanity_bundle_legs_clank_armor.config",
  ["8013B4EF20904B35"] = "configs/hero/vanity/vanitybundles/clank_armor/hero_vanity_bundle_torso_clank_armor.config",
  ["9C5E667630BA2398"] = "configs/hero/vanity/vanitybundles/commando_armor/hero_vanity_bundle_head_commando_armor.config",
  ["8E2CEADF9B0A8F2D"] = "configs/hero/vanity/vanitybundles/commando_armor/hero_vanity_bundle_legs_commando_armor.config",
  ["B1E7F7E6C7FF8BE2"] = "configs/hero/vanity/vanitybundles/commando_armor/hero_vanity_bundle_torso_commando_armor.config",
  ["8CB04B79806C291F"] = "configs/hero/vanity/vanitybundles/emperor_armor/hero_vanity_bundle_head_emperor_armor.config",
  ["9CC97AB0AB67E476"] = "configs/hero/vanity/vanitybundles/emperor_armor/hero_vanity_bundle_legs_emperor_armor.config",
  ["9F17B3947C5A5B5B"] = "configs/hero/vanity/vanitybundles/emperor_armor/hero_vanity_bundle_torso_emperor_armor.config",
  ["93E712D2F21D0DD0"] = "configs/hero/vanity/vanitybundles/galactic ranger/hero_vanity_bundle_head_galactic_ranger.config",
  ["84302A735518B94C"] = "configs/hero/vanity/vanitybundles/galactic ranger/hero_vanity_bundle_legs_galactic_ranger.config",
  ["BCE27F601A79EDF3"] = "configs/hero/vanity/vanitybundles/galactic ranger/hero_vanity_bundle_torso_galactic_ranger.config",
  ["A51DC633DAF006FE"] = "configs/hero/vanity/vanitybundles/handondemo/hero_vanity_bundle_legs_grind_boots_demo.config",
  ["81B5107741397A3A"] = "configs/hero/vanity/vanitybundles/handondemo/hero_vanity_bundle_torso_demo.config",
  ["A52883C49F25024B"] = "configs/hero/vanity/vanitybundles/holoflux_armor/hero_vanity_bundle_head_holoflux_armor.config",
  ["B75A0F6D3495AEFE"] = "configs/hero/vanity/vanitybundles/holoflux_armor/hero_vanity_bundle_legs_holoflux_armor.config",
  ["8C53BB00623348B5"] = "configs/hero/vanity/vanitybundles/holoflux_armor/hero_vanity_bundle_torso_holoflux_armor.config",
  ["9F39769F9BF0351D"] = "configs/hero/vanity/vanitybundles/lombax_armor/hero_vanity_bundle_head_lombax_armor.config",
  ["9E4EAAF5C6CC8F98"] = "configs/hero/vanity/vanitybundles/lombax_armor/hero_vanity_bundle_legs_lombax_armor.config",
  ["A656A4D56398A996"] = "configs/hero/vanity/vanitybundles/lombax_armor/hero_vanity_bundle_torso_lombax_armor.config",
  ["8AA9D4114F5AD58E"] = "configs/hero/vanity/vanitybundles/marauder_armor/hero_vanity_bundle_head_marauder_armor.config",
  ["98DB58B8E4EA793B"] = "configs/hero/vanity/vanitybundles/marauder_armor/hero_vanity_bundle_legs_marauder_armor.config",
  ["A16C9E0D5A9B491F"] = "configs/hero/vanity/vanitybundles/marauder_armor/hero_vanity_bundle_torso_marauder_armor.config",
  ["8001C43CEBA5E2FA"] = "configs/hero/vanity/vanitybundles/pirate/hero_vanity_bundle_head_pirate.config",
  ["9CBC9C624BF57A98"] = "configs/hero/vanity/vanitybundles/pirate/hero_vanity_bundle_legs_pirate.config",
  ["BFC94E73B01DD256"] = "configs/hero/vanity/vanitybundles/pirate/hero_vanity_bundle_torso_pirate.config",
  ["910E71B1479875DA"] = "configs/hero/vanity/vanitybundles/punk_armor/hero_vanity_bundle_head_punk_armor.config",
  ["9FD5C12AA19F2179"] = "configs/hero/vanity/vanitybundles/punk_armor/hero_vanity_bundle_legs_punk_armor.config",
  ["A427A6596E4B5048"] = "configs/hero/vanity/vanitybundles/punk_armor/hero_vanity_bundle_torso_punk_armor.config",
  ["86161C6E3C6B2FB7"] = "configs/hero/vanity/vanitybundles/qforce_armor/hero_vanity_bundle_head_qforce_armor.config",
  ["8761C00461579532"] = "configs/hero/vanity/vanitybundles/qforce_armor/hero_vanity_bundle_legs_qforce_armor.config",
  ["86418C62F94DF704"] = "configs/hero/vanity/vanitybundles/qforce_armor/hero_vanity_bundle_torso_qforce_armor.config",
  ["854C0C6E8AB94C6F"] = "configs/hero/vanity/vanitybundles/quest_armor/hero_vanity_bundle_head_quest_armor.config",
  ["A9249E8DCE8AD868"] = "configs/hero/vanity/vanitybundles/quest_armor/hero_vanity_bundle_legs_quest_armor.config",
  ["A2A9CA4690EA166E"] = "configs/hero/vanity/vanitybundles/quest_armor/hero_vanity_bundle_torso_quest_armor.config",
  ["B39AC2A317F84B4D"] = "configs/hero/vanity/vanitybundles/reaver_armor/hero_vanity_bundle_head_reaver_armor.config",
  ["B2ED1EC94AC4F1C8"] = "configs/hero/vanity/vanitybundles/reaver_armor/hero_vanity_bundle_legs_reaver_armor.config",
  ["80AA4A570C54DFE2"] = "configs/hero/vanity/vanitybundles/reaver_armor/hero_vanity_bundle_torso_reaver_armor.config",
  ["B649CA1B42FC150E"] = "configs/hero/vanity/vanitybundles/rebellion_armor/hero_vanity_bundle_head_rebellion_armor.config",
  ["A19EF2BAE5F9A192"] = "configs/hero/vanity/vanitybundles/rebellion_armor/hero_vanity_bundle_legs_rebellion_armor.config",
  ["8516DEBFE3350B85"] = "configs/hero/vanity/vanitybundles/rebellion_armor/hero_vanity_bundle_torso_rebellion_armor.config",
  ["A080A54E2B9F5FCB"] = "configs/hero/vanity/vanitybundles/starshield_armor/hero_vanity_bundle_head_starshield_armor.config",
  ["9811C0560C1DD121"] = "configs/hero/vanity/vanitybundles/starshield_armor/hero_vanity_bundle_legs_starshield_armor.config",
  ["8EF7D02726FF8B89"] = "configs/hero/vanity/vanitybundles/starshield_armor/hero_vanity_bundle_torso_starshield_armor.config",
  ["92F57A025043DA23"] = "configs/hero/vanity/vanitybundles/warmachine_armor/hero_vanity_bundle_head_warmachine_armor.config",
  ["AA641F1A77C154C9"] = "configs/hero/vanity/vanitybundles/warmachine_armor/hero_vanity_bundle_legs_warmachine_armor.config",
  ["B2D5A6077667B224"] = "configs/hero/vanity/vanitybundles/warmachine_armor/hero_vanity_bundle_torso_warmachine_armor.config",
  ["B44E3C3FE297A72D"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_boots_ratchet_android_armor.config",
  ["AEC0D25B9449D2A8"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_boots_rivet_android_armor.config",
  ["B62A6D5A570FE5FC"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_glove_left_ratchet_android_armor.config",
  ["968E09C2068A0DD3"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_glove_left_rivet_android_armor.config",
  ["869E8AF332B245A2"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_glove_right_ratchet_android_armor.config",
  ["A517E91A37C24335"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_glove_right_rivet_android_armor.config",
  ["A69A0E38E0F5FF80"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_helmet_ratchet_android_armor.config",
  ["841A920712A39B54"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_helmet_rivet_android_armor.config",
  ["8E571D0419D5B12E"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_legs_ratchet_android_armor.config",
  ["AADEE60A684D8CB1"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_legs_rivet_android_armor.config",
  ["A7C1BC9C4C9A985A"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_torso_ratchet_android_armor.config",
  ["82468010FC685CD4"] = "configs/hero/vanity/vanityitems/android_armor/hero_vanity_torso_rivet_android_armor.config",
  ["9A7B3D91A84B782B"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_boots_ratchet_beginning_armor.config",
  ["95DF1BDF41AFAAA3"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_boots_rivet_beginning_armor.config",
  ["AE05184DFBCA9AC6"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_glove_left_ratchet_beginning_armor.config",
  ["ACD69C1B5F2771DF"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_glove_left_rivet_beginning_armor.config",
  ["82238B183D506F03"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_glove_right_ratchet_beginning_armor.config",
  ["A8CA0325F13C4A2E"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_glove_right_rivet_beginning_armor.config",
  ["91FDA36A62D87C13"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_head_ratchet_beginning_armor.config",
  ["B5C3E0AFB84C99C0"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_head_rivet_beginning_armor.config",
  ["B77A8666DBAC3F89"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_helmet_ratchet_beginning_armor.config",
  ["A93A64C174EE49A4"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_helmet_rivet_beginning_armor.config",
  ["9B91AE8EE829B0CC"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_legs_ratchet_beginning_armor.config",
  ["86C7D6E56A50694E"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_legs_rivet_beginning_armor.config",
  ["A74D2FADB86387B3"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_torso_ratchet_beginning_armor.config",
  ["86509B7CEFA295D4"] = "configs/hero/vanity/vanityitems/beginning_armor/hero_vanity_torso_rivet_beginning_armor.config",
  ["8DE7E952E1478D51"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_boots_ratchet_carbonox_armor.config",
  ["AB6ED7E96D0764B2"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_boots_rivet_carbonox_armor.config",
  ["BCBB90D19CDB57D6"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_glove_left_ratchet_carbonox_armor.config",
  ["9C692F6B08D8C2D5"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_glove_left_rivet_carbonox_armor.config",
  ["A12F8DE0BD126540"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_glove_right_ratchet_carbonox_armor.config",
  ["B02E0297DB56D6BA"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_glove_right_rivet_carbonox_armor.config",
  ["88307D3288681A35"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_head_ratchet_carbonox_armor.config",
  ["B2DD408B8177536C"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_head_rivet_carbonox_armor.config",
  ["BBD492ABE0A48B83"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_helmet_ratchet_carbonox_armor.config",
  ["ADF3DD6870157488"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_helmet_rivet_carbonox_armor.config",
  ["9440201481A8C36A"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_legs_ratchet_carbonox_armor.config",
  ["B64A179204CD1C0B"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_legs_rivet_carbonox_armor.config",
  ["9AF840A8D9900351"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_torso_ratchet_carbonox_armor.config",
  ["B07568C4BF52F27F"] = "configs/hero/vanity/vanityitems/carbonox_armor/hero_vanity_torso_rivet_carbonox_armor.config",
  ["932F8AAFAC1302B2"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_boots_ratchet_carbonox_preorder_armor.config",
  ["9906E038A41B3BD9"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_boots_rivet_carbonox_preorder_armor.config",
  ["8AC34B2331D24598"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_glove_left_ratchet_carbonox_preorder_armor.config",
  ["B0574D9B5B4F834B"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_glove_left_rivet_carbonox_preorder_armor.config",
  ["9148C3695A678DF4"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_glove_right_ratchet_carbonox_preorder_armor.config",
  ["9C5A261AA553D9A8"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_glove_right_rivet_carbonox_preorder_armor.config",
  ["95DD4522930771AB"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_head_ratchet_carbonox_preorder_armor.config",
  ["A36A21AA67AC8945"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_head_rivet_carbonox_preorder_armor.config",
  ["A6C5B9623FC36E87"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_helmet_ratchet_carbonox_preorder_armor.config",
  ["88094CF3BA295752"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_helmet_rivet_carbonox_preorder_armor.config",
  ["8534F7DB6E9B4462"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_legs_ratchet_carbonox_preorder_armor.config",
  ["93F584C2645CAFE3"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_legs_rivet_carbonox_preorder_armor.config",
  ["805BACA5C471F9CC"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_torso_ratchet_carbonox_preorder_armor.config",
  ["89B178E152BB6F66"] = "configs/hero/vanity/vanityitems/carbonox_preorder_armor/hero_vanity_torso_rivet_carbonox_preorder_armor.config",
  ["89C3B0BA31043858"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_boots_ratchet_clank_armor.config",
  ["B45DD5FD7E872EF6"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_boots_rivet_clank_armor.config",
  ["B3A5683EC8E7F93F"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_glove_left_ratchet_clank_armor.config",
  ["AC587DB540149532"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_glove_left_rivet_clank_armor.config",
  ["9BFACE777403B400"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_glove_right_ratchet_clank_armor.config",
  ["B29D20434B5E9B1A"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_glove_right_rivet_clank_armor.config",
  ["82732F49CA2CC721"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_helmet_ratchet_clank_armor.config",
  ["9F8DCBCEEC885C4D"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_helmet_rivet_clank_armor.config",
  ["8556AE3F0D5B5A0F"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_legs_ratchet_clank_armor.config",
  ["837CBD18E5BF74BE"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_legs_rivet_clank_armor.config",
  ["A545E2F15925B624"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_torso_ratchet_clank_armor.config",
  ["AF3E6D3238D31C6A"] = "configs/hero/vanity/vanityitems/clank_armor/hero_vanity_torso_rivet_clank_armor.config",
  ["AD73F0C7EB551C13"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_boots_ratchet_commando_armor.config",
  ["82171066D3E33A1F"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_boots_rivet_commando_armor.config",
  ["8F71F77EB89CD101"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_glove_left_ratchet_commando_armor.config",
  ["B40AF2B12E1FA651"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_glove_left_rivet_commando_armor.config",
  ["AC81AE9953B522E3"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_glove_right_ratchet_commando_armor.config",
  ["87AA5385BA278886"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_glove_right_rivet_commando_armor.config",
  ["BC3D5D18B4E33F86"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_head_ratchet_commando_armor.config",
  ["9318E1B1D1672A29"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_head_rivet_commando_armor.config",
  ["AED6BDF1A57276C1"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_helmet_ratchet_commando_armor.config",
  ["99FEFD424C9E513B"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_helmet_rivet_commando_armor.config",
  ["A04D003EBD23E6D9"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_legs_ratchet_commando_armor.config",
  ["978FB6A854DD654E"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_legs_rivet_commando_armor.config",
  ["BA6C593DD3829213"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_torso_ratchet_commando_armor.config",
  ["990CAF4B01B6ACD2"] = "configs/hero/vanity/vanityitems/commando_armor/hero_vanity_torso_rivet_commando_armor.config",
  ["8BE1D73DEC65E7D3"] = "configs/hero/vanity/vanityitems/default/hero_vanity_boots_ratchet_default.config",
  ["93FFBB84D0E15685"] = "configs/hero/vanity/vanityitems/default/hero_vanity_boots_rivet_default.config",
  ["AA34DC883030B672"] = "configs/hero/vanity/vanityitems/default/hero_vanity_glove_left_ratchet_default.config",
  ["B352415DBAC8A67C"] = "configs/hero/vanity/vanityitems/default/hero_vanity_glove_left_rivet_default.config",
  ["9C0489D5BC843577"] = "configs/hero/vanity/vanityitems/default/hero_vanity_glove_right_ratchet_default.config",
  ["BEDA98DC7C110B4C"] = "configs/hero/vanity/vanityitems/default/hero_vanity_glove_right_rivet_default.config",
  ["95C04BE75F4244DC"] = "configs/hero/vanity/vanityitems/default/hero_vanity_head_ratchet_default.config",
  ["BD10CE8B0DECB2A8"] = "configs/hero/vanity/vanityitems/default/hero_vanity_head_rivet_default.config",
  ["82177346F847F040"] = "configs/hero/vanity/vanityitems/default/hero_vanity_legs_ratchet_default.config",
  ["AD69FF4226E77FC1"] = "configs/hero/vanity/vanityitems/default/hero_vanity_legs_rivet_default.config",
  ["996A81236D6B463E"] = "configs/hero/vanity/vanityitems/default/hero_vanity_torso_ratchet_default.config",
  ["ACA2E744FC98DA0E"] = "configs/hero/vanity/vanityitems/default/hero_vanity_torso_rivet_default.config",
  ["A5BD6188039055F3"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_boots_ratchet_emperor_armor.config",
  ["88B3F4D39D6DE875"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_boots_rivet_emperor_armor.config",
  ["A4ECFE42DF4B7D73"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_glove_left_ratchet_emperor_armor.config",
  ["B74A04162F336E8B"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_glove_left_rivet_emperor_armor.config",
  ["B8C3E228A721370E"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_glove_right_ratchet_emperor_armor.config",
  ["830FBD556A78A49B"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_glove_right_rivet_emperor_armor.config",
  ["A23CE4ABB50CD034"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_helmet_ratchet_emperor_armor.config",
  ["B27D3776526F1070"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_helmet_rivet_emperor_armor.config",
  ["B830B87559193A0A"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_legs_ratchet_emperor_armor.config",
  ["84DE074034EA1B08"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_legs_rivet_emperor_armor.config",
  ["B632E12BAD9D6A84"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_torso_ratchet_emperor_armor.config",
  ["A435A698F54C6609"] = "configs/hero/vanity/vanityitems/emperor_armor/hero_vanity_torso_rivet_emperor_armor.config",
  ["BF7DF22BAD05C07B"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_boots_ratchet_galactic.config",
  ["9A48B87B4C045ABE"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_boots_rivet_galactic.config",
  ["9C2167E7777D4BD8"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_glove_left_ratchet_galactic.config",
  ["80BDA45677BFC1CF"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_glove_left_rivet_galactic.config",
  ["83CEB8B44DAC7EE4"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_glove_right_ratchet_galactic.config",
  ["A837E532E8D7D7DD"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_glove_right_rivet_galactic.config",
  ["985D29D9828852E2"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_head_ratchet_galactic.config",
  ["8F950BEC910A3308"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_head_rivet_galactic.config",
  ["A7B92E69F1FD134A"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_helmet_ratchet_galactic.config",
  ["A022DAE9145E7B1B"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_helmet_rivet_galactic.config",
  ["A0CC4CC1A50ADC08"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_legs_ratchet_galactic.config",
  ["9DE787453ABA9FBD"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_legs_rivet_galactic.config",
  ["8F4A693E2F439826"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_torso_ratchet_galactic.config",
  ["BA87690D0E85C095"] = "configs/hero/vanity/vanityitems/galactic range/hero_vanity_torso_rivet_galactic.config",
  ["975A550E6DDD1AF7"] = "configs/hero/vanity/vanityitems/handsondemo/hero_vanity_glove_right_ratchet_demo_default.config",
  ["BE35A34B3CCFE616"] = "configs/hero/vanity/vanityitems/handsondemo/hero_vanity_grind_boots_demo_default.config",
  ["A36E05E98E3682EF"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_boots_ratchet_holoflux_armor.config",
  ["BB61F5D47C7C1BCC"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_boots_rivet_holoflux_armor.config",
  ["B4B27ABFD8E3CD9D"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_glove_left_ratchet_holoflux_armor.config",
  ["A3905F15C7DF461C"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_glove_left_rivet_holoflux_armor.config",
  ["BF4BADC979AEC471"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_glove_right_ratchet_holoflux_armor.config",
  ["827F2D5C1A5F1841"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_glove_right_rivet_holoflux_armor.config",
  ["818911FE112FFCD1"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_head_ratchet_holoflux_armor.config",
  ["94CC1DDB6030D621"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_head_rivet_holoflux_armor.config",
  ["8F72753C158D4F01"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_helmet_ratchet_holoflux_armor.config",
  ["A44AB1A4E952926C"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_helmet_rivet_holoflux_armor.config",
  ["9DF94CD818EF258E"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_legs_ratchet_holoflux_armor.config",
  ["905B4AC2E58A9946"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_legs_rivet_holoflux_armor.config",
  ["B471AC13B6E10CEF"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_torso_ratchet_holoflux_armor.config",
  ["A07A4AF9AE298D01"] = "configs/hero/vanity/vanityitems/holoflux_armor/hero_vanity_torso_rivet_holoflux_armor.config",
  ["B7743C33EEA34F91"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_boots_ratchet_lombax_armor.config",
  ["851F9A064F2A53D9"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_boots_rivet_lombax_armor.config",
  ["B91DEFA45815B2A4"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_glove_left_ratchet_lombax_armor.config",
  ["87B8E852FA984E59"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_glove_left_rivet_lombax_armor.config",
  ["B1689854CD29C735"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_glove_right_ratchet_lombax_armor.config",
  ["91F8EBDA4EFA605F"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_glove_right_rivet_lombax_armor.config",
  ["B7835AE68B0FB675"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_head_ratchet_lombax_armor.config",
  ["8B21A1C07FF5BA93"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_head_rivet_lombax_armor.config",
  ["B568CF255C9E6ABB"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_helmet_ratchet_lombax_armor.config",
  ["8EE6B7588093850D"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_helmet_rivet_lombax_armor.config",
  ["B3140DFF0EB5F912"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_legs_ratchet_lombax_armor.config",
  ["B69C301C14E34E50"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_legs_rivet_lombax_armor.config",
  ["AC6F831E3CF6D95C"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_torso_ratchet_lombax_armor.config",
  ["AC68D5246CB07378"] = "configs/hero/vanity/vanityitems/lombax_armor/hero_vanity_torso_rivet_lombax_armor.config",
  ["AF557C380D9F7AAD"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_boots_ratchet_marauder_armor.config",
  ["94E0A201AC03CC09"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_boots_rivet_marauder_armor.config",
  ["A5031A632A08EE8C"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_glove_left_ratchet_marauder_armor.config",
  ["9936C31D19BB0635"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_glove_left_rivet_marauder_armor.config",
  ["85EB44F58C619698"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_glove_right_ratchet_marauder_armor.config",
  ["906E918236247CC1"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_glove_right_rivet_marauder_armor.config",
  ["A3355EE7970E1195"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_helmet_ratchet_marauder_armor.config",
  ["897594A9D1FA93C6"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_helmet_rivet_marauder_armor.config",
  ["B0C669D520472424"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_legs_ratchet_marauder_armor.config",
  ["B6C13483133102CC"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_legs_rivet_marauder_armor.config",
  ["B84AD5C23548F4AD"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_torso_ratchet_marauder_armor.config",
  ["8FFB1D2C7E565AC4"] = "configs/hero/vanity/vanityitems/marauder_armor/hero_vanity_torso_rivet_marauder_armor.config",
  ["89A2191168106EDD"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_boots_ratchet_pirate.config",
  ["850BCF38B12ADE30"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_boots_rivet_pirate.config",
  ["A77FCA9E65442946"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_glove_left_ratchet_pirate.config",
  ["845533DFE4724139"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_glove_left_rivet_pirate.config",
  ["B0862FD431A44A7D"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_glove_right_ratchet_pirate.config",
  ["98E753503C5FBCFC"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_glove_right_rivet_pirate.config",
  ["BC4383018F1E88F8"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_head_ratchet_pirate.config",
  ["BBCA2A6099C92D40"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_head_rivet_pirate.config",
  ["B4F891EEA7B4FE9C"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_helmet_ratchet_pirate.config",
  ["B41445B96DE0AA15"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_helmet_rivet_pirate.config",
  ["AE310FA824AE244D"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_legs_ratchet_pirate.config",
  ["BABDF60AC4F597C5"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_legs_rivet_pirate.config",
  ["A96DC8672A91F4F6"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_torso_ratchet_pirate.config",
  ["875F3C17FE1B6FBD"] = "configs/hero/vanity/vanityitems/pirate/hero_vanity_torso_rivet_pirate.config",
  ["8F7DF3B58DEE4FA5"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_boots_ratchet_punk_armor.config",
  ["9E67405F61FC0EBF"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_boots_rivet_punk_armor.config",
  ["BA1C032EF4E70026"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_glove_left_ratchet_punk_armor.config",
  ["8076B302356FD408"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_glove_left_rivet_punk_armor.config",
  ["95EFAA06AD517C95"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_glove_right_ratchet_punk_armor.config",
  ["BE18A9A1D432E822"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_glove_right_rivet_punk_armor.config",
  ["86B786767C2B126A"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_head_ratchet_punk_armor.config",
  ["A62AF0758943E81F"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_head_rivet_punk_armor.config",
  ["B830FF9F8629A5CD"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_helmet_ratchet_punk_armor.config",
  ["A1381D33BD417EB1"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_helmet_rivet_punk_armor.config",
  ["BB0A17AA173DE6A9"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_legs_ratchet_punk_armor.config",
  ["9EBB956DAEC166F5"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_legs_rivet_punk_armor.config",
  ["A60ABC97AE746F04"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_torso_ratchet_punk_armor.config",
  ["AE50DB4AE3BA56E2"] = "configs/hero/vanity/vanityitems/punk_armor/hero_vanity_torso_rivet_punk_armor.config",
  ["82E1634DD5C3CE5B"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_boots_ratchet_qforce_armor.config",
  ["9C30F0F7E8B14973"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_boots_rivet_qforce_armor.config",
  ["B94BF439ACDA2A13"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_glove_left_ratchet_qforce_armor.config",
  ["949AE8FBEA0D2BE4"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_glove_left_rivet_qforce_armor.config",
  ["9BDFD87C0280462C"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_glove_right_ratchet_qforce_armor.config",
  ["94B2FD986200705D"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_glove_right_rivet_qforce_armor.config",
  ["9794725111DAE8E7"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_head_ratchet_qforce_armor.config",
  ["BE2602A11CAFD820"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_head_rivet_qforce_armor.config",
  ["8BC3DB6DBCDFDBB9"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_helmet_ratchet_qforce_armor.config",
  ["AEF19FEF1A46DB9F"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_helmet_rivet_qforce_armor.config",
  ["930325489460A780"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_legs_ratchet_qforce_armor.config",
  ["839B937D77B92CE3"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_legs_rivet_qforce_armor.config",
  ["99FADC6007965896"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_torso_ratchet_qforce_armor.config",
  ["B547BFD5CB2B69D2"] = "configs/hero/vanity/vanityitems/qforce_armor/hero_vanity_torso_rivet_qforce_armor.config",
  ["95A0970FCF43B97A"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_boots_ratchet_quest_armor.config",
  ["826E2B326A922EE5"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_boots_rivet_quest_armor.config",
  ["8CD4804719DFE50E"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_glove_left_ratchet_quest_armor.config",
  ["88F2185F04A10965"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_glove_left_rivet_quest_armor.config",
  ["9A3115C0F8737F55"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_glove_right_ratchet_quest_armor.config",
  ["9EB9B185A0C14082"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_glove_right_rivet_quest_armor.config",
  ["A806AF0BA187BEEE"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_head_ratchet_quest_armor.config",
  ["89C4483EBFB4EBD0"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_head_rivet_quest_armor.config",
  ["848B30759AB7C282"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_helmet_ratchet_quest_armor.config",
  ["BD37B5675CF20116"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_helmet_rivet_quest_armor.config",
  ["A7ECD096BD210754"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_legs_ratchet_quest_armor.config",
  ["B8827DE0852CB6B3"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_legs_rivet_quest_armor.config",
  ["B926C544A7623706"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_torso_ratchet_quest_armor.config",
  ["990D93FD2CC61C79"] = "configs/hero/vanity/vanityitems/quest_armor/hero_vanity_torso_rivet_quest_armor.config",
  ["9074E36FDEC83074"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_boots_ratchet_reaver_armor.config",
  ["A9BC2E3AC3222D89"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_boots_rivet_reaver_armor.config",
  ["BD08122FA4A4FD66"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_glove_left_ratchet_reaver_armor.config",
  ["8D23376B983208DC"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_glove_left_rivet_reaver_armor.config",
  ["B3792BAFD0A24681"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_glove_right_ratchet_reaver_armor.config",
  ["BE77F1D4DF7EA428"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_glove_right_rivet_reaver_armor.config",
  ["917FB464E4C3C001"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_head_ratchet_reaver_armor.config",
  ["88A512B3CFF9E65C"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_head_rivet_reaver_armor.config",
  ["95B0565B37B98433"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_helmet_ratchet_reaver_armor.config",
  ["A81A59DAEF5FF379"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_helmet_rivet_reaver_armor.config",
  ["95E8E37D61798F66"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_legs_ratchet_reaver_armor.config",
  ["B518836FA4EF129F"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_legs_rivet_reaver_armor.config",
  ["8B6F5C420C9DA6B9"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_torso_ratchet_reaver_armor.config",
  ["80CB6118E0B80D28"] = "configs/hero/vanity/vanityitems/reaver_armor/hero_vanity_torso_rivet_reaver_armor.config",
  ["89D606801E074F29"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_boots_ratchet_rebellion_armor.config",
  ["BBB1878BE4EB4FC2"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_boots_rivet_rebellion_armor.config",
  ["A18F5F3EA8F38052"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_glove_left_ratchet_rebellion_armor.config",
  ["BC3B109CED99B31D"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_glove_left_rivet_rebellion_armor.config",
  ["9902960D2E174A32"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_glove_right_ratchet_rebellion_armor.config",
  ["88577A85C7E17FA4"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_glove_right_rivet_rebellion_armor.config",
  ["B1F383A6D82EF736"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_head_ratchet_rebellion_armor.config",
  ["BE0B470FCDC768E7"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_head_rivet_rebellion_armor.config",
  ["BB2F2C5EFB9C2F2D"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_helmet_ratchet_rebellion_armor.config",
  ["8934440DCE18C281"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_helmet_rivet_rebellion_armor.config",
  ["BB9F8E4252DF3BE9"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_legs_ratchet_rebellion_armor.config",
  ["8D0F71451FDB9869"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_legs_rivet_rebellion_armor.config",
  ["B4E014BC0E2FB0B1"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_torso_ratchet_rebellion_armor.config",
  ["A83E07284AE670B5"] = "configs/hero/vanity/vanityitems/rebellion_armor/hero_vanity_torso_rivet_rebellion_armor.config",
  ["9A35CE4BDB9A45D8"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_boots_ratchet_starshield_armor.config",
  ["A8B63BF5C9C3FD96"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_boots_rivet_starshield_armor.config",
  ["8C2E0CCC143191BE"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_glove_left_ratchet_starshield_armor.config",
  ["B06C2E73A776A14F"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_glove_left_rivet_starshield_armor.config",
  ["820D88E0343D7BF1"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_glove_right_ratchet_starshield_armor.config",
  ["827BA2D5E2B8AD23"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_glove_right_rivet_starshield_armor.config",
  ["A6389A82F3792CF0"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_head_ratchet_starshield_armor.config",
  ["AECEC683CA86B559"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_head_rivet_starshield_armor.config",
  ["870554162237A69D"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_helmet_ratchet_starshield_armor.config",
  ["8C2D76AA2906B1EC"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_helmet_rivet_starshield_armor.config",
  ["808918193BE206E1"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_legs_ratchet_starshield_armor.config",
  ["B2BE9BA5C3466C06"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_legs_rivet_starshield_armor.config",
  ["AC023C8D1F1AC026"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_torso_ratchet_starshield_armor.config",
  ["BFA9920FF1147396"] = "configs/hero/vanity/vanityitems/starshield_armor/hero_vanity_torso_rivet_starshield_armor.config",
  ["A78B376DCC8636D7"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_boots_ratchet_warmachine_armor.config",
  ["9AC3E4B9B21F787E"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_boots_rivet_warmachine_armor.config",
  ["BF0D66BC353A239C"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_glove_left_ratchet_warmachine_armor.config",
  ["8D2503F7C2272D67"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_glove_left_rivet_warmachine_armor.config",
  ["91C08A048F485E8D"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_glove_right_ratchet_warmachine_armor.config",
  ["AFBC76BD10C7E64A"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_glove_right_rivet_warmachine_armor.config",
  ["9A1AECA2A3E1155D"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_head_ratchet_warmachine_armor.config",
  ["8E08D60F974725B7"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_head_rivet_warmachine_armor.config",
  ["A4E3DB2253B3C2DC"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_helmet_ratchet_warmachine_armor.config",
  ["B00F008A799E8841"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_helmet_rivet_warmachine_armor.config",
  ["BCAB6E396B7A3F4C"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_legs_ratchet_warmachine_armor.config",
  ["92788B299E87FCE8"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_legs_rivet_warmachine_armor.config",
  ["91BCC5AB0806B329"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_torso_ratchet_warmachine_armor.config",
  ["8DDC4D438AC8F67E"] = "configs/hero/vanity/vanityitems/warmachine_armor/hero_vanity_torso_rivet_warmachine_armor.config",
  ["B6059D3F8C559E85"] = "configs/hero/vanity/vanitysets/hero_vanity_set_android_armor.config",
  ["A696F40E71866892"] = "configs/hero/vanity/vanitysets/hero_vanity_set_beginning_armor.config",
  ["BE707A032DECDC9E"] = "configs/hero/vanity/vanitysets/hero_vanity_set_carbonox_armor.config",
  ["86D980EC2D69DFA9"] = "configs/hero/vanity/vanitysets/hero_vanity_set_carbonox_preorder_armor.config",
  ["9B82C3F4F09C8B72"] = "configs/hero/vanity/vanitysets/hero_vanity_set_clank_armor.config",
  ["B5AD2CF736C8C0DD"] = "configs/hero/vanity/vanitysets/hero_vanity_set_commando_armor.config",
  ["98B11B98B810582C"] = "configs/hero/vanity/vanitysets/hero_vanity_set_emperor_armor.config",
  ["A2B21002CB2EC326"] = "configs/hero/vanity/vanitysets/hero_vanity_set_galactic_ranger.config",
  ["992F66537AC9E54C"] = "configs/hero/vanity/vanitysets/hero_vanity_set_holoflux_armor.config",
  ["9A3F0B88A0671678"] = "configs/hero/vanity/vanitysets/hero_vanity_set_lombax_armor.config",
  ["B2F2A7083D76587E"] = "configs/hero/vanity/vanitysets/hero_vanity_set_marauder_armor.config",
  ["8BF2E4253C21F419"] = "configs/hero/vanity/vanitysets/hero_vanity_set_pirate.config",
  ["BED8E9713F86C4A0"] = "configs/hero/vanity/vanitysets/hero_vanity_set_punk_armor.config",
  ["926A7760BB41CB28"] = "configs/hero/vanity/vanitysets/hero_vanity_set_qforce_armor.config",
  ["BE5F333C9DB09DD3"] = "configs/hero/vanity/vanitysets/hero_vanity_set_quest_armor.config",
  ["9F920CB14008BCCA"] = "configs/hero/vanity/vanitysets/hero_vanity_set_reaver_armor.config",
  ["935C89833FF88B2A"] = "configs/hero/vanity/vanitysets/hero_vanity_set_rebellion_armor.config",
  ["A448BB158723C52C"] = "configs/hero/vanity/vanitysets/hero_vanity_set_starshield_armor.config",
  ["938DD89F9686875E"] = "configs/hero/vanity/vanitysets/hero_vanity_set_warmachine_armor.config",
  ["A6743C0897D6CDBF"] = "configs/hpz/pup_hpz_majorweaponupgrade.config",
  ["899B2E69E6DAC27C"] = "configs/hpz/pup_hpz_test_item.config",
  ["A6240C53D6009E42"] = "configs/hpz/pup_hpz_test_item02.config",
  ["9F1C324C41628430"] = "configs/hpz/pup_hpz_weaponupgrade.config",
  ["84B942BE54A8384A"] = "configs/pickup/pup_ammo_blaster_item.config",
  ["9B51A46E39E3ABC6"] = "configs/pickup/pup_ammo_blunderbuster_item.config",
  ["A60BD1B6334B5003"] = "configs/pickup/pup_ammo_bouncer_item.config",
  ["9E6980721F17EF72"] = "configs/pickup/pup_ammo_burstpistol_item.config",
  ["8479CDBAFF088F5F"] = "configs/pickup/pup_ammo_buzzblades_item.config",
  ["B6353EE0231E04D3"] = "configs/pickup/pup_ammo_carpetbomber_item.config",
  ["9DB2ACF868D45EB3"] = "configs/pickup/pup_ammo_detcord_item.config",
  ["89329EFD4F71783A"] = "configs/pickup/pup_ammo_fossilizer_item.config",
  ["898EA6FAF897318E"] = "configs/pickup/pup_ammo_fusiongrenade_item.config",
  ["98B40775F2285AFE"] = "configs/pickup/pup_ammo_generic_item.config",
  ["975DF4798BF749C8"] = "configs/pickup/pup_ammo_glove_of_doom_item.config",
  ["8CE0DD42A176C336"] = "configs/pickup/pup_ammo_groovitron_item.config",
  ["BF063AA476470F7A"] = "configs/pickup/pup_ammo_icicleblast_item.config",
  ["B1842BEB38346CA8"] = "configs/pickup/pup_ammo_kamehameha_item.config",
  ["997461B483E5419A"] = "configs/pickup/pup_ammo_lightningrod_item.config",
  ["92AADC61439510DE"] = "configs/pickup/pup_ammo_magnamissile_item.config",
  ["B8CE4D438A98C573"] = "configs/pickup/pup_ammo_magshield_item.config",
  ["BBB826F74A038F1F"] = "configs/pickup/pup_ammo_mr_zurkon_item.config",
  ["80ED1C069B87134D"] = "configs/pickup/pup_ammo_mrfunguy_item.config",
  ["94C46313C9522DC4"] = "configs/pickup/pup_ammo_nailgun_item.config",
  ["97A3AEBEDAE14A5A"] = "configs/pickup/pup_ammo_pitofdeath_item.config",
  ["8902A14DB8F94304"] = "configs/pickup/pup_ammo_pixelizer_item.config",
  ["96C5D7DAE4A67007"] = "configs/pickup/pup_ammo_plasma_striker_item.config",
  ["ACBB304B82F34F97"] = "configs/pickup/pup_ammo_predator_launcher_item.config",
  ["8822F374B71C90F5"] = "configs/pickup/pup_ammo_protogrenade_item.config",
  ["BFC3753A4EE2A47B"] = "configs/pickup/pup_ammo_protoshotgun_item.config",
  ["9097FAC9DB404B2B"] = "configs/pickup/pup_ammo_puzzle_accel_item.config",
  ["8B94702AC3DF8FF8"] = "configs/pickup/pup_ammo_puzzle_decel_item.config",
  ["8A6C4E5388F6E84E"] = "configs/pickup/pup_ammo_puzzle_energy_item.config",
  ["AE021A79CD67C505"] = "configs/pickup/pup_ammo_puzzle_melee_item.config",
  ["89021955B0A21FE5"] = "configs/pickup/pup_ammo_puzzlegravity_item.config",
  ["B20EF2E1C63B5029"] = "configs/pickup/pup_ammo_pyrocitor_item.config",
  ["B79C79AAE3FD8983"] = "configs/pickup/pup_ammo_revolver_item.config",
  ["B89F762E8D31CACD"] = "configs/pickup/pup_ammo_ricochet_item.config",
  ["B66A5392DA716EAF"] = "configs/pickup/pup_ammo_ryno_item.config",
  ["AF52D8B0D53DE50D"] = "configs/pickup/pup_ammo_schrodinger_item.config",
  ["A11806CE7F2655CA"] = "configs/pickup/pup_ammo_seismicshock_item.config",
  ["976DBFF475835441"] = "configs/pickup/pup_ammo_sheepinator_item.config",
  ["B52298E10C21FE4E"] = "configs/pickup/pup_ammo_stickyblaster_item.config",
  ["98C9994D2389DE4E"] = "configs/pickup/pup_ammo_thumper_item.config",
  ["B7E7DC5FEDDD77A7"] = "configs/pickup/pup_ammo_topiaryblaster_item.config",
  ["B7758B6E554A248D"] = "configs/pickup/pup_ammo_tunneler_item.config",
  ["87323701B106FE88"] = "configs/pickup/pup_ammo_volcaniceruptor_item.config",
  ["B0EA184A9ECE1916"] = "configs/pickup/pup_ammo_warmonger_item.config",
  ["85D8CB06F4392EFA"] = "configs/pickup/pup_ammo_warprifle_item.config",
  ["8B0198DF1491CDD0"] = "configs/pickup/pup_arachnodroid_health_item.config",
  ["891FDE9B5EC37BBB"] = "configs/pickup/pup_arachnodroid_shield_item.config",
  ["A2FF6C76128565CC"] = "configs/pickup/pup_arachnodroid_speed_boost_item.config",
  ["947DC517D343AD64"] = "configs/pickup/pup_bolt_item.config",
  ["99F4A1E340AA1D71"] = "configs/pickup/pup_gold_bolt_item.config",
  ["8C1D388F81D692B6"] = "configs/pickup/pup_health_item.config",
  ["95FFA4C1254A6F29"] = "configs/pickup/pup_raritanium_item.config",
  ["97CA612D98AAF94A"] = "configs/pickup/pup_ruintoken_item.config",
  ["B1E533414CD8D094"] = "configs/pickup/pup_ryno_plan_item.config",
  ["A45778F21343AE69"] = "configs/pickup/pup_saucer_missile_item.config",
  ["8A5A0862A77F07B6"] = "configs/pickup/pup_zerpstone_item.config",
}
end
-- ---- dev(probe).lua ----
do
-- DEVELOPER TOOL - not part of a release. Randomizer PROBE v7. Lets you inspect and test the game's own
-- level-script "give item" nodes by hand. Nothing happens unless you press one of these keys
-- (Num Lock on). The randomizer itself does not need this file; 09_rando_real.lua delivers
-- rewards automatically.
--
--   NUMPAD3  survey: list the grant-type script nodes on this planet and pre-select the
--            AddToInventoryAction node that is known to work (log: RANDO-PROBE node ...)
--   NUMPAD4  select the next node that can be fired
--   NUMPAD5  fire the selected node as it is
--   NUMPAD7  choose a test item (your seed's weapons first, then gadgets)
--   NUMPAD6  give the test item through the selected AddToInventoryAction node
--   NUMPAD9  census: find a node that is safe to borrow on this planet (log: RANDO-REAL census)
--   NUMPAD8  give the test item through that borrowed node
-- Removed in v7: the bolt-counter scan (the count is not stored where it searched), the
-- AmmoCost weapon lock (no effect) and the component-index search (exceeded the frame budget).

-- (dev(probe).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["probe"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_PROBE = RANDO_PROBE or {}
local P = RANDO_PROBE
P.version = 7
P.frame = P.frame or 0

local function log(...) pcall(rivet.log, "[rando]", "RANDO-PROBE", ...) end
-- every HUD message is also logged
local function say(t) log("HUD:", t); pcall(rivet.notify, "[PROBE] " .. t, { type = "center", duration = 5 }) end
P.log, P.say = log, say

-- ---- helpers -------------------------------------------------------------------------
local function hex_to_bin(h) return (h:gsub("%s", ""):gsub("%x%x", function(x) return string.char(tonumber(x, 16)) end)) end
local function bin_to_hex(b) return (b:gsub(".", function(c) return string.format("%02X ", c:byte()) end)):sub(1, -2) end
local function addr(n) return string.format("%X", n) end
-- 8 little-endian bytes -> "%016X" text (asset ids pass 2^63, so they stay text)
local function le_qword_hex(bin, i) local s = "" for k = i + 7, i, -1 do s = s .. string.format("%02X", bin:byte(k)) end return s end
-- "%016X" text -> "AA BB .." little-endian byte text for rivet.write
local function qword_hex_to_le(hex) local t = {} for k = 15, 1, -2 do t[#t + 1] = hex:sub(k, k + 1) end return table.concat(t, " ") end
P.hex_to_bin, P.bin_to_hex, P.le_qword_hex, P.qword_hex_to_le = hex_to_bin, bin_to_hex, le_qword_hex, qword_hex_to_le

-- ---- script-node grants -----------------------------------------------------------------
P.FILTERS = { "Inventory", "Currency", "Weapon", "Level", "Planetary", "Reward", "Pickup", "Bolt" }
P.FIRE_PLUG = { AddToInventoryAction = "In", AddCurrencyAction = "In", UnlockLevelAction = "Unlock",
                SetWeaponEquipableAction = "In" }
P.DETAIL = { AddToInventoryAction = true, AddCurrencyAction = true, UnlockLevelAction = true,
             SetWeaponEquipableAction = true, SubCurrencyAction = true, SetCurrencyAction = true,
             GetCurrencyAction = true, RemoveFromInventoryAction = true, SetPlanetaryTravelAction = true,
             EquipWeaponAction = true, PickupItemAction = true, SpawnRewardAction = true,
             IsLevelUnlockedAction = true, CheckPlanetaryTravelAction = true, UIArenaRewardAction = true }
P.DETAIL_PER_CLASS = 12
P.nodes, P.targets, P.sel = {}, {}, 0
P.survey = nil
P.pending = {}          -- { at = frame, fn = function } run later in on_frame
P.watch_until = 0

local function later(frames, fn) P.pending[#P.pending + 1] = { at = P.frame + frames, fn = fn } end

local function item_name(hex) return RANDO_ITEM_IDS and RANDO_ITEM_IDS[hex] end

-- decode the node's own fields, whose offsets come from the handlers in your exe
local function decode(info, bin)       -- bin = 0x20 bytes read from node+0x58
  local f = {}
  if info.class == "AddToInventoryAction" then
    f.item = le_qword_hex(bin, 0x60 - 0x58 + 1)
    f.item_name = item_name(f.item)
    f.count = string.unpack("<i4", bin, 0x68 - 0x58 + 1)
  elseif info.class == "SetWeaponEquipableAction" then
    f.weapon = string.unpack("<I4", bin, 0x6c - 0x58 + 1)
    f.equipable = bin:byte(0x70 - 0x58 + 1)
  elseif info.class == "UnlockLevelAction" then
    f.level = string.unpack("<i4", bin, 0x60 - 0x58 + 1)
  end
  return f
end

local function describe(info)
  local f, parts = info.fields or {}, {}
  if f.item then parts[#parts + 1] = "item=" .. f.item .. (f.item_name and (" (" .. f.item_name .. ")") or " (not a known item id)") end
  if f.count then parts[#parts + 1] = "count=" .. f.count end
  if f.weapon then parts[#parts + 1] = "weapon=" .. f.weapon .. " equipable=" .. f.equipable end
  if f.level then parts[#parts + 1] = "level=" .. f.level end
  for _, v in ipairs(info.vars or {}) do parts[#parts + 1] = v end
  return table.concat(parts, " ")
end
P.describe = describe

function P.inspect(node)
  local info = { component = node.component, actor = node.actor, class = node.class, uid = node.uid }
  local ok, c = pcall(rivet.component, node.actor, node.class)
  if ok and c and c.handle == node.component then
    info.addr = tonumber(c.address, 16)
    local okr, text = pcall(rivet.read, addr(info.addr + 0x58), 0x20)
    if okr and text then
      info.raw = text
      info.fields = decode(info, hex_to_bin(text))
    end
  else
    info.why = ok and "the actor holds another node of this class first" or tostring(c)
  end
  local okn, n = pcall(rivet.script_node, node.component, false)
  info.vars, info.outs = {}, {}
  if okn and type(n) == "table" then
    for _, v in ipairs(n.vars or {}) do
      local label = v.name or v.plug_name or string.format("0x%08X", v.plug or 0)
      if v.live then
        local val = v.value
        if type(val) == "table" then val = "{" .. tostring(val.count or #val) .. " actor(s)}" end
        info.vars[#info.vars + 1] = label .. "=" .. tostring(val)
      else
        info.vars[#info.vars + 1] = label .. "=(not live)"
      end
    end
    for _, o in ipairs(n.outputs or {}) do
      info.outs[#info.outs + 1] = (o.plug_name or string.format("0x%08X", o.plug or 0)) .. "->" .. tostring(o.to and o.to.class)
    end
  else
    info.vars[#info.vars + 1] = "script_node: " .. tostring(n)
  end
  log(string.format("node %s comp=%s actor=%s uid=%s %s %s out[%s] raw58=%s", info.class, tostring(info.component),
      tostring(info.actor), tostring(info.uid), info.addr and ("addr=" .. addr(info.addr)) or ("no address: " .. tostring(info.why)),
      describe(info), table.concat(info.outs, ","), tostring(info.raw)))
  return info
end

-- the node is still the same live instance (round 9: a node from before a reload was written to)
function P.still_valid(t)
  local ok, c = pcall(rivet.component, t.actor, t.class)
  return ok and c and c.handle == t.component and t.addr ~= nil and tonumber(c.address, 16) == t.addr
end

function P.start_survey()
  P.survey = { fi = 1, seen = {}, counts = {}, queue = {}, per_class = {} }
  P.nodes, P.targets, P.sel = {}, {}, 0
  say("surveying script nodes on this planet...")
end

function P.survey_step()
  local s = P.survey
  if not s then return end
  if s.fi <= #P.FILTERS then
    local filter = P.FILTERS[s.fi]; s.fi = s.fi + 1
    local ok, list = pcall(rivet.script_nodes, filter, 200)
    if not ok then log("script_nodes(" .. filter .. ") failed:", tostring(list)); return end
    for _, node in ipairs(list) do
      if not s.seen[node.component] then
        s.seen[node.component] = true
        s.counts[node.class] = (s.counts[node.class] or 0) + 1
        if P.DETAIL[node.class] and (s.per_class[node.class] or 0) < P.DETAIL_PER_CLASS then
          s.per_class[node.class] = (s.per_class[node.class] or 0) + 1
          s.queue[#s.queue + 1] = node
        end
      end
    end
    return
  end
  for _ = 1, 3 do
    local node = table.remove(s.queue, 1)
    if not node then break end
    local info = P.inspect(node)
    P.nodes[#P.nodes + 1] = info
    if P.FIRE_PLUG[info.class] then P.targets[#P.targets + 1] = info end
  end
  if #s.queue > 0 then return end
  P.survey = nil
  local names = {}
  for k, v in pairs(s.counts) do names[#names + 1] = k .. "=" .. v end
  table.sort(names)
  log("survey done:", #names == 0 and "no grant-type nodes loaded here" or table.concat(names, " "))
  log("survey fireable:", #P.targets)
  -- pre-select the node that granted Box Breaker + Hoverboots in round 7 (or the safest one)
  P.sel = 0
  local pref = {}
  for i, uid in ipairs((RANDO_DATA and RANDO_DATA.real_nodes and RANDO_DATA.real_nodes.preferred_nodes) or
                       { "98763a0c6fd24259", "b075049b0add2df3" }) do pref[uid] = i end
  local best
  for i, t in ipairs(P.targets) do
    if t.class == "AddToInventoryAction" and pref[t.uid] and (not best or pref[t.uid] < pref[P.targets[best].uid]) then best = i end
  end
  if best then P.sel = best end
  say(#P.targets .. " node(s) can be fired here" .. (best and (" - selected " .. P.targets[best].class .. " " .. P.targets[best].uid) or " - NUMPAD4 to pick one"))
end

function P.select_next()
  if #P.targets == 0 then say("nothing to fire - NUMPAD3 surveys this planet"); return nil end
  P.sel = P.sel % #P.targets + 1
  local t = P.targets[P.sel]
  say(string.format("%d/%d %s %s", P.sel, #P.targets, t.class, describe(t)))
  return t
end

function P.fire(t, what)
  t = t or P.targets[P.sel]
  if not t then say("pick a node first (NUMPAD3, then NUMPAD4)"); return false end
  local plug = P.FIRE_PLUG[t.class]
  local ok, err = pcall(rivet.signal, t.component, plug)
  log("fire", t.class, "comp=" .. tostring(t.component), "plug=" .. plug, what or describe(t), ok and "queued" or ("refused: " .. tostring(err)))
  P.watch_until = P.frame + 600
  say(ok and ("fired " .. t.class .. " - did anything change?") or ("refused: " .. tostring(err)))
  return ok
end

-- test items: every weapon and gadget item config in your dag, reachable through the id table.
-- Built on first use, so dev(item_ids).lua may load before or after this file.
P.test_items, P.test_i, P.item_id = {}, 0, {}
function P.build_test_items()
  if P.built then return end
  P.built = true
  for hex, path in pairs(RANDO_ITEM_IDS or {}) do P.item_id[path] = hex end
  -- the player's weapons and gadgets (from the seed export), weapons first; without a seed,
  -- every weapon/gadget item in the dag
  if RANDO_DATA and RANDO_DATA.real_items then
    for _, info in pairs(RANDO_DATA.real_items) do
      P.item_id[info.config] = info.id
      P.test_items[#P.test_items + 1] = info.config
    end
  else
    for path in pairs(P.item_id) do
      if path:match("^configs/equipment/wpn_.+_item%.config$") or path:match("^configs/equipment/gdgt_.+_item%.config$") then
        P.test_items[#P.test_items + 1] = path
      end
    end
  end
  table.sort(P.test_items, function(a, b)
    local wa, wb = a:find("/wpn_") ~= nil, b:find("/wpn_") ~= nil
    if wa ~= wb then return wa end
    return a < b
  end)
end

function P.next_test_item()
  P.build_test_items()
  if #P.test_items == 0 then say("no test items: dev(item_ids).lua and the seed file are missing"); return nil end
  P.test_i = P.test_i % #P.test_items + 1
  local path = P.test_items[P.test_i]
  local label = path:match("([^/]+)_item%.config$")
  if RANDO_DATA and RANDO_DATA.real_items then
    for item, info in pairs(RANDO_DATA.real_items) do
      if info.config == path then label = label .. " = " .. ((RANDO_DATA.items[item] and RANDO_DATA.items[item].name) or item) end
    end
  end
  say("test item " .. P.test_i .. "/" .. #P.test_items .. ": " .. label .. " - NUMPAD6 gives it")
  return path
end

-- point an AddToInventoryAction node at another item, fire it, then put the node back.
-- Refused unless the node's own +0x60 was recognised as an item id: that proves the layout.
function P.grant_via_node(path, amount)
  P.build_test_items()
  path = path or P.test_items[P.test_i]
  local t = P.targets[P.sel]
  if not path then say("choose a test item with NUMPAD7"); return false end
  if not t or t.class ~= "AddToInventoryAction" then say("select an AddToInventoryAction node with NUMPAD4"); return false end
  if not (t.addr and t.fields and t.fields.item_name) then
    say("this node's item field was not recognised - not writing to it"); log("grant refused: layout unproven", describe(t)); return false
  end
  if not P.still_valid(t) then
    P.targets, P.sel = {}, 0
    say("that node is gone (the level reloaded) - NUMPAD3 again"); return false
  end
  local hex = P.item_id[path]
  local at = addr(t.addr + 0x60)
  local ok0, original = pcall(rivet.read, at, 12)
  if not ok0 or not original then say("cannot read the node: " .. tostring(original)); return false end
  local bytes = qword_hex_to_le(hex) .. " " .. bin_to_hex(string.pack("<i4", amount or 1))
  local okw, err = pcall(rivet.write, at, bytes)
  if not okw then log("grant write failed", tostring(err)); say("write failed: " .. tostring(err)); return false end
  local _, now = pcall(rivet.read, at, 12)
  log("grant: node now holds", tostring(now), "(wanted " .. bytes .. ")")
  local fired = P.fire(t, "giving " .. path)
  later(90, function()
    if not P.still_valid(t) then log("grant: node gone before restore - nothing to put back"); return end
    local okr, e2 = pcall(rivet.write, at, original)
    log("grant: node restored", okr and "ok" or tostring(e2))
  end)
  log("grant", path, "x" .. (amount or 1), "via node comp=" .. tostring(t.component), fired and "fired" or "not fired")
  return fired
end

function P.donor_grant(path)
  P.build_test_items()
  path = path or P.test_items[P.test_i]
  if not path then say("choose a test item with NUMPAD7"); return false end
  if not RANDO_REAL then say("09_rando_real.lua is missing"); return false end
  local item
  for k, info in pairs((RANDO_DATA and RANDO_DATA.real_items) or {}) do if info.config == path then item = k end end
  if not item then say("not a randomizer item: " .. path); return false end
  local ok, err = RANDO_REAL.probe_donor_grant(item)
  P.watch_until = P.frame + 600
  log("donor grant", item, ok and "fired" or ("refused: " .. tostring(err)))
  say(ok and ("fired " .. item .. " through the borrowed node - check your inventory") or tostring(err))
  return ok
end

-- events seen after a fire, so the log shows what the game did with it
local function fields_text(ev)
  local parts = {}
  for k, v in pairs(ev.fields or {}) do
    if type(v) == "number" and math.abs(v) >= 1e15 then v = string.format("%.0f", v) end
    parts[#parts + 1] = tostring(k) .. "=" .. tostring(v)
  end
  table.sort(parts)
  return table.concat(parts, " ")
end
P.WATCH = { "GainBoltEvent", "WeaponAddedEvent", "GadgetItemAddedEvent", "PurchaseWeaponEvent",
            "VendorPurchaseEvent", "GainGoldBoltEvent", "MissionStateChangedEvent", "PlanetChangedEvent",
            "InventoryChangedEvent", "GainRaritaniumEvent" }

-- ---- wiring ------------------------------------------------------------------------------
local function on(class, fn) local ok, err = pcall(rivet.on_event, class, fn); if not ok then log("cannot subscribe", class, err) end; return ok end
local function forget_targets() P.targets, P.sel, P.nodes = {}, 0, {} end
on("PlanetChangedEvent", forget_targets)
on("LevelLoadedEvent", forget_targets)
for _, class in ipairs(P.WATCH) do
  on(class, function(ev) if P.frame <= P.watch_until then log("after fire:", class, fields_text(ev)) end end)
end

local function key(name, fn) pcall(rivet.on_key, rivet.key(name), function()
  local ok, err = pcall(fn); if not ok then log(name, "failed:", tostring(err)) end end) end
key("NUMPAD3", function() P.start_survey() end)
key("NUMPAD4", function() P.select_next() end)
key("NUMPAD5", function() P.fire() end)
key("NUMPAD6", function() P.grant_via_node() end)
key("NUMPAD7", function() P.next_test_item() end)
key("NUMPAD9", function()
  if not RANDO_REAL or not RANDO_REAL.start_donor_search then say("09_rando_real.lua is missing"); return end
  if not RANDO_VTABLES then say("dev(vtables).lua is missing"); return end
  say("census of this planet's script nodes...")
  RANDO_REAL.start_donor_search(true)
end)
key("NUMPAD8", function() P.donor_grant() end)

function P.on_frame()
  P.frame = P.frame + 1
  for i = #P.pending, 1, -1 do
    local p = P.pending[i]
    if P.frame >= p.at then table.remove(P.pending, i); local ok, err = pcall(p.fn); if not ok then log("later:", tostring(err)) end end
  end
  if P.survey then
    local ok, err = pcall(P.survey_step)
    if not ok then log("survey step:", tostring(err)); P.survey = nil end
  end
end
pcall(rivet.on_frame, P.on_frame)
log("v7 loaded: NUMPAD3 survey, NUMPAD4 select, NUMPAD5 fire, NUMPAD7 item, NUMPAD6 give item, NUMPAD9 census, NUMPAD8 give via borrowed node")
end
-- ---- dev(vtables).lua ----
do
-- DEVELOPER TOOL - not part of a release (data for dev(probe).lua).
-- generated from your RiftApart.exe (3.0630.1.0) by tools/gen_action_vtables.py: script-action class
-- -> RVA of its primary vtable. Used by the probe to find the exe's load address from any live node.
-- (dev(vtables).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["probe"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_VTABLES = {
  AbandonMissionAction = 0x2FBD2E8,
  AccelLerpVecAction = 0x433A290,
  ActivateAtmosphereAction = 0x4605858,
  ActivateCameraAction = 0x45B3998,
  ActivateVendorScriptAction = 0x2F04CA0,
  ActorActivationQueryAction = 0x32B2E18,
  ActorAttachAction = 0x460C6B8,
  ActorBoundsAction = 0x32B31D0,
  ActorControlAction = 0x32B2DA0,
  ActorCountAction = 0x32B2E98,
  ActorDeleteAction = 0x2FCE340,
  ActorDetachAction = 0x460C730,
  ActorDrawAction = 0x32B3248,
  ActorGenderAction = 0x460C530,
  ActorGroupClearAction = 0x32B2FF8,
  ActorGroupControlAction = 0x32B2F80,
  ActorHeadAction = 0x2FD0268,
  ActorHighContrastShaderAction = 0x4589970,
  ActorInRangeAction = 0x460C898,
  ActorPickAction = 0x32B2F10,
  ActorPositionAction = 0x32B3158,
  ActorSaveCheckActorFlagAction = 0x4607BF0,
  ActorSaveCheckDeletedFlagAction = 0x4607CF0,
  ActorSaveSetActorFlagAction = 0x4607C70,
  ActorSelectAction = 0x460C498,
  ActorStretchAction = 0x2FD01F0,
  ActorSwapModelAction = 0x460C7A8,
  ActorToggleLookAction = 0x32B33B0,
  ActorToggleLookGroupAction = 0x32B3330,
  ActorVolumeAction = 0x32B30E0,
  ActorWarpAction = 0x32B3070,
  AddAction = 0x4339F68,
  AddCurrencyAction = 0x2FCEAE8,
  AddDialogPromptScriptAction = 0x2F9CA90,
  AddMapIconAction = 0x2FD1268,
  AddMissionStashAction = 0x45EDA80,
  AddPOI2Action = 0x4582800,
  AddToInventoryAction = 0x2FA4DE0,
  AddVectorsAction = 0x43395A0,
  AddXPAction = 0x2FCF480,
  AdvanceCurveAction = 0x460CB18,
  AdvanceMissionObjectiveAction = 0x45ED600,
  AirlockAction = 0x45E6690,
  AlarmAction = 0x2F45280,
  AmbientBarrageControlAction = 0x2FCEEA0,
  AndAction = 0x4337B10,
  AnimateAnimVarAction = 0x458DB08,
  AnimateNumberAction = 0x45EC918,
  AnimateShaderConstantAction = 0x4605AF8,
  AnimatedDismountScriptAction = 0x2F9FD70,
  AnyMissionActiveAction = 0x45EDD80,
  ApplyEaseAction = 0x433A378,
  ApplyLoadoutScriptAction = 0x3017A80,
  ApplyOverrideLoadoutScriptAction = 0x3017D10,
  ApplySimpleMaterialSplineToCurveAction = 0x45C3790,
  ArachnodroidPulseDamageAction = 0x2FB7AE0,
  ArachnodroidWeaponAction = 0x2FB7E30,
  AreaEnableAction = 0x45E6858,
  AttachActorAction = 0x2EFD9B0,
  AttachActorToViewportAction = 0x45B3728,
  AudioBusMaterialAction = 0x2FB1398,
  AutoCheckpointAction = 0x2F5D508,
  AutoUpdateStreamingSourceByProximityAction = 0x45E5D08,
  BattleBrewAutoFillScriptAction = 0x2F56738,
  BattleBrewSetFillMultiplierScriptAction = 0x2F56868,
  BeetleTrailScriptAction = 0x2EBA890,
  BitFlagsAction = 0x43377D8,
  BlendAtmospheresAction = 0x46061F8,
  BoltCrankSetStateAction = 0x2FA1430,
  BoltScriptAction = 0x2FAC9D0,
  BossAttackVolumeSetupScriptAction = 0x2E73830,
  BossCentipedeGetPilotActorScriptAction = 0x2E8D0C0,
  BossChaseControllerScriptAction = 0x2E73A20,
  BotAwarenessSetPriorityTargetsScriptAction = 0x2E7C960,
  BotCommandFaceScriptAction = 0x4598790,
  BotCommandFollowCurveScriptAction = 0x2E94818,
  BotCommandGotoScriptAction = 0x45988C0,
  BotCommandHoverFollowCurveToTargetScriptAction = 0x2E94C50,
  BotCommandIdleScriptAction = 0x4598AB0,
  BotCommandJuiceDistractionScriptAction = 0x2E91478,
  BotCommandJuiceEngageTargetScriptAction = 0x2E915C0,
  BotCommandJumpToScriptAction = 0x2E94FB8,
  BotCommandNefariousUseShieldScriptAction = 0x2E88088,
  BotCommandPlayAnimScriptAction = 0x4598D78,
  BotCommandQueueScriptAction = 0x45985A0,
  BotCommandScriptAction = 0x2E80628,
  BotCommandShooterAttackTargetScriptAction = 0x2E953C8,
  BotCommandUseAnimClueScriptAction = 0x2E95600,
  BotCommandUseComboAttackScriptAction = 0x2E95A28,
  BotCommandZordoomChaseAction = 0x2E806B0,
  BotCommandZordoomCisternJumpAction = 0x2E80908,
  BotCommandZordoomSlideAction = 0x2E807B8,
  BotCommandZordoomStunnedAction = 0x2E80860,
  BotGroupMustEngageScriptAction = 0x2EC5350,
  BotMultiTargetOverrideScriptAction = 0x2EC56E8,
  BreakableAction = 0x45AA640,
  BreakableChunkCleanupAction = 0x45AA730,
  BreakableSetManualDamageAction = 0x45AA6B0,
  BreakpointAction = 0x43365D0,
  CameraLookTargetAction = 0x2EE7B08,
  CameraPositionAction = 0x45B3640,
  CameraRaycastPositionAction = 0x45B37A8,
  CameraShakeAction = 0x45B3250,
  CanPickupScriptAction = 0x4602B20,
  CardSetBonusAction = 0x2FA4A00,
  CardSetCompleteAction = 0x2FA4F90,
  CentipedeClearShotsAction = 0x2E816E8,
  ChangeCritterDensityAction = 0x2E6D350,
  ChangeCurveSpeedAction = 0x45C91E8,
  ChangeDimensionCheckpointAction = 0x2F0A6B8,
  ChangeFlockDensityAction = 0x2E6F0A8,
  ChangeOpenCurveFollowModeAction = 0x45C9368,
  CharacterSwapAction = 0x2F5D130,
  CheckActorCombatStateAction = 0x2EEE4B8,
  CheckActorStatusEffectAction = 0x2FE9DD8,
  CheckAnimFilterAction = 0x458DBF8,
  CheckDimensionCompleteAction = 0x2F0A938,
  CheckHeroTypeAction = 0x2F5D0B8,
  CheckInventoryAction = 0x2FA4CF0,
  CheckMissionAction = 0x45EDD08,
  CheckMissionObjectiveAction = 0x45ED340,
  CheckMissionStashAction = 0x45EDC90,
  CheckMissionStateAction = 0x45F9950,
  CheckObjectiveFlagsAction = 0x2FBD1F0,
  CheckObjectiveStateAction = 0x45F9AC0,
  CheckPlanetaryTravelAction = 0x2F2BA20,
  CheckPoweredAction = 0x2E96B40,
  CheckPuzzleTargetTypeAction = 0x2FC9660,
  CheckPuzzleVolumeAction = 0x2FC99E8,
  CheckPuzzleVolumeTrackerAction = 0x2FC9968,
  CheckPuzzleVolumeTypeAction = 0x2FC91D0,
  CheckWorldCombatStateAction = 0x2EEE5B8,
  CheckpointAction = 0x45E5D98,
  CheckpointCompareAction = 0x45E5E30,
  CheckpointQueryAction = 0x45E5EB8,
  CheckpointWarpAction = 0x2F5D1A8,
  Cinematic2Action = 0x32C3270,
  Cinematic2ActorAction = 0x32C32F0,
  Cinematic2ListenerAction = 0x32C2F68,
  Cinematic2TriggerEventOnActorAction = 0x32C3EF0,
  CinematicPlayerStateAction = 0x2F5C918,
  ClampAction = 0x433A3E8,
  ClankPuzzleGetLastNavAction = 0x2FC9350,
  ClearAnimDamageAction = 0x458D9A0,
  ClearClankPuzzleRecalOrbAction = 0x2FC92D0,
  ClearCurveAction = 0x45C9170,
  ClearOverrideWeaponAction = 0x2FFDA48,
  ClearPlacedShotsAction = 0x2FFDD18,
  ClearShotsAction = 0x2FFDCA0,
  ClosestPointInVolumeAction = 0x460CA18,
  ClosestPointOnCurveAction = 0x460CA98,
  ClosestPointOnNavDeferredAction = 0x45F6218,
  CoherentDrawTextAction = 0x45833B8,
  CollectibleCollectAction = 0x45B4C08,
  CollectibleInstanceQueryAction = 0x45B4D08,
  CollectibleRegisterAction = 0x45B4D88,
  CollectibleTypeQueryAction = 0x45B4C88,
  CollisionCastBaseAction = 0x4609B70,
  ColorCorrectionSetBlendWeightAction = 0x32EBAA8,
  CombatMarkupSwapScriptAction = 0x2EEDB60,
  CommandFireAtAction = 0x2FCD188,
  CommandGoToAction = 0x2FCD670,
  CommandJumpToAction = 0x2FCD3F8,
  CommandSnapperIntroAction = 0x2FCD530,
  CommandStandStillAction = 0x2FCD2C0,
  CompareActorAction = 0x43380C0,
  CompareActorGroupAction = 0x4337048,
  CompareAllegianceScriptAction = 0x4625C18,
  CompareBooleanAction = 0x4337938,
  CompareNumberAction = 0x4337FD0,
  CompareStringAction = 0x4338048,
  CompleteCleanupMissionAction = 0x45F9A40,
  CompleteMissionAction = 0x45EDF40,
  CompleteMissionObjectiveAction = 0x45ED6B0,
  CompleteObjectiveAction = 0x45F9B40,
  ConduitAction = 0x460A1F8,
  ConduitEventAction = 0x460A268,
  ConduitVfxToggleAction = 0x460A2F8,
  ConversationAction = 0x45C6530,
  CopyBooleanAction = 0x43371A8,
  CopyVectorAction = 0x43373E8,
  CorpseCleanupScriptAction = 0x4609240,
  CorpseManagerSetLimitsScriptAction = 0x46094D0,
  CounterAction = 0x43394C0,
  CreateCurveFromPointListAction = 0x460A830,
  CustomDesignEventAction = 0x460B108,
  CycleSignalAction = 0x4337BF0,
  DamageAction = 0x45D8FD0,
  DamageSphereAction = 0x45D9040,
  DamageVolumeScriptAction = 0x45CEF90,
  DeactivateCameraAction = 0x45B3A10,
  DeactivateMissionAction = 0x45ED240,
  DeactivateMissionObjectiveAction = 0x45ED2B8,
  DebugActorAction = 0x45CFCF8,
  DebugAddAnimControllerAction = 0x4336648,
  DebugDrawArrowAction = 0x45D1260,
  DebugDrawCapsuleAction = 0x45D10F8,
  DebugDrawConeAction = 0x45D12D8,
  DebugDrawCurveAction = 0x45D0930,
  DebugDrawCylinderAction = 0x45D1170,
  DebugDrawLineAction = 0x45D11E8,
  DebugDrawSphereAction = 0x45D1080,
  DebugDrawVolumeAction = 0x45D1350,
  DebugImageAction = 0x45D7B60,
  DebugMessageAction = 0x43364E0,
  DebugPlotLinesAction = 0x45D7BD8,
  DebugPrintToTTYAction = 0x4336948,
  DebugProgressBarAction = 0x45D7AE8,
  DebugReportAction = 0x4336558,
  DebugResetTimeLocalAction = 0x43367C8,
  DebugScreenCaptureAction = 0x43369C0,
  DebugSetAnimVarScalarAction = 0x4336848,
  DebugSetFilterStateAction = 0x43368C8,
  DebugSetFixedFramerateAction = 0x43366C8,
  DebugSetToBindPoseAction = 0x4336748,
  DecomposeCombatMarkupCollectionScriptAction = 0x2EED7F0,
  DelayAction = 0x4337D58,
  DepthOfFieldAction = 0x2EE82E0,
  DetectChangeAction = 0x32CC808,
  DimensionCheckpointQueryAction = 0x2F0A738,
  DimensionPortalListenerAction = 0x2F0A838,
  DimensionPortalSourceAction = 0x2F0A7B8,
  DimensionalPulseAction = 0x2F0C858,
  DimensionalPulseTargetControlAction = 0x2F0C8D0,
  DimensionalPulseTargetListenerAction = 0x2F0C958,
  DimensionalPulseTargetSetTypeAction = 0x2F0C9E0,
  DisableAction = 0x2FCE4A0,
  DisableCoverSystemAction = 0x46095D0,
  DisablePOIAction = 0x4582870,
  DisablePostEffectsAction = 0x45D09A8,
  DisengageAction = 0x2FCDC78,
  DivideAction = 0x433A220,
  DoorScriptAction = 0x45DE758,
  DotProductAction = 0x4339808,
  DropshipScriptAction = 0x2EFF1B8,
  EconModifyAction = 0x2F0E288,
  EmergentDialogTriggerDisableScriptAction = 0x45B8F80,
  EmergentVOAction = 0x2FCED30,
  EmergentVOSetVoiceScriptAction = 0x2EF24E0,
  EnableAction = 0x2FCE5A8,
  EnableCurveFollowerAutoStopAction = 0x45C92E0,
  EnableDisableMagSurfaceEdgeDetectionScriptAction = 0x2FCE6A8,
  EndLevelDefeatAction = 0x45D5788,
  EndLevelLobbyAction = 0x45D5878,
  EndLevelMainMenuAction = 0x45D5800,
  EndLevelVictoryAction = 0x45D5710,
  EngageAction = 0x2FCDCE8,
  EnoughBoltsToBuyWeaponAction = 0x2F0E750,
  EnoughRareToUpgradeWeaponAction = 0x2F0E7D0,
  EquipWeaponAction = 0x2FFD740,
  ExitToFrontendAction = 0x2FAAEC0,
  ExponentAction = 0x433A838,
  ExpositionTokenAction = 0x45C64B8,
  FadeMasterVolumeAction = 0x43438C0,
  FadeModelAlphaAction = 0x4606088,
  FailMissionAction = 0x45EE058,
  FallRespawnAction = 0x2F5D580,
  FilterSignalAction = 0x4337E40,
  FinaleBossChaseEndSequenceScriptAction = 0x2E8C420,
  FinaleBossChaseStartSequenceScriptAction = 0x2E8C7E0,
  FinaleBossChaseUseLaserScriptAction = 0x2E8C870,
  FinaleBossDamageWeakspotScriptAction = 0x2E8A560,
  FinaleBossMechHeartAllowLaserPhaseScriptAction = 0x2E8B758,
  FinaleBossMechHeartScriptAction = 0x2E8B6D8,
  FinaleBossRetreatAction = 0x2E7F718,
  FinaleMechGetPilotScriptAction = 0x2E88C18,
  FlockControlScriptAction = 0x2E6F028,
  FlyerMountCollisionScriptAction = 0x2F9FDF0,
  FlyerPickupLaunchScriptAction = 0x2EBCE50,
  FlyingMountStickOptionScriptAction = 0x2F9FEF8,
  FollowCurveAction = 0x45C93E8,
  FollowCurveControlAction = 0x45C9460,
  FollowCurvePredictAction = 0x2FCFF60,
  ForEachActorAction = 0x32B34B8,
  ForceActorCombatStateEngagedAction = 0x2EEE430,
  ForceActorGroundTypeAction = 0x2FBB2B0,
  ForceClankbotDropAction = 0x2E96CB8,
  ForceGrindBoostAction = 0x2F5D958,
  FormatStringAction = 0x4337290,
  FormationAttackAction = 0x3063AE8,
  FullScreenMovieAction = 0x32DCB08,
  FullScreenMovieSyncedAction = 0x2EE9640,
  GalacticMapGetTriggeredLandingCineAction = 0x2FAE598,
  GalacticMapManualOpenMapAction = 0x2FAE7B8,
  GalacticMapManualTriggerLandingAction = 0x2FAE730,
  GalacticMapSetPreMapMovieAction = 0x2FAE6B0,
  GalacticMapSwitchToSetLevelAction = 0x2FAE628,
  GameIntentAction = 0x2FF0420,
  GameSpawnerAction = 0x2FE7DC0,
  GateAction = 0x4337B80,
  GatherAnimCluesAction = 0x458DA18,
  GetActiveWeaponAction = 0x2FFDB38,
  GetActorGroupByNameAction = 0x32B3438,
  GetActorInstanceInfoAction = 0x32B3530,
  GetActorsInVolumeScriptAction = 0x2FCFEE0,
  GetActorsWithAllegianceAction = 0x2FCE9D0,
  GetAmmoAction = 0x2FFD570,
  GetAngleBetweenVectorsAction = 0x43399F0,
  GetBreakablesInVolumesAction = 0x45AA7B0,
  GetCameraFOVAction = 0x45B3920,
  GetCameraFXProxyActorAction = 0x2EE7EF8,
  GetCharacterIdAction = 0x45DC3D0,
  GetClankPackActorAction = 0x2FCEE28,
  GetClientNameAction = 0x45DC2D0,
  GetClosestPointOnLineFromRayVectorAction = 0x4339B70,
  GetClosestPointOnLineSegmentFromPointAction = 0x4339C00,
  GetCurrencyAction = 0x2FCEB80,
  GetCurrentHeroShipAction = 0x2FAE518,
  GetCurrentLevelIDAction = 0x2FAE9A0,
  GetCurvePointAction = 0x460CC10,
  GetCurveTotalLengthAction = 0x460CB90,
  GetDifficultyAction = 0x2F09688,
  GetEulerAnglesAction = 0x4339E70,
  GetHPAction = 0x45D9940,
  GetItemCountAction = 0x2FA4D68,
  GetKickablesInVolumesAction = 0x45E4900,
  GetLevelIDAction = 0x2FAE928,
  GetLightingModeAction = 0x2FAAD40,
  GetMissionObjectiveVariableAction = 0x45ED970,
  GetMountActorScriptAction = 0x2F9FCF0,
  GetNumAliveAction = 0x2FCCAA0,
  GetOrthogonalNormalVectorAction = 0x4339788,
  GetPlanetMenuDestinationCheckpointAction = 0x2F2B990,
  GetPlanetMenuInterplanetaryCheckpointAction = 0x2F2B900,
  GetPlayerIndexAction = 0x45DC358,
  GetPuzzleHintTypeAction = 0x2E69AE8,
  GetPuzzleRecallVolumesAction = 0x2FC96E0,
  GetPuzzleVolumeInfoAction = 0x2FC95E0,
  GetSaveSlotAction = 0x2FAAFB0,
  GetScreenCoordinateAction = 0x45D7A00,
  GetSpaceshipMagnetStateAction = 0x2F5E108,
  GetStickInputAction = 0x2F5D6F8,
  GetTargetDataLocationAction = 0x4626028,
  GetTeamScriptAction = 0x45D59D8,
  GetTimeSincePlayerEventAction = 0x2FC7400,
  GetTriggerInputAction = 0x2F5D770,
  GetUIActorAction = 0x2FD09D8,
  GetVectorComponentsAction = 0x4337460,
  GetVectorDirectionAction = 0x4339970,
  GetVectorDistanceAction = 0x4339880,
  GetVectorPositionAction = 0x43398F8,
  GetVelocityAction = 0x460DA48,
  GetWeaponAction = 0x2FFDAC8,
  GetWeaponLevelAction = 0x2FFD920,
  GetXPAction = 0x2FCE818,
  GiveAmmoAction = 0x2FFD500,
  GiveCardAction = 0x2FA4A78,
  GlobalSaveTableCheckKeyAction = 0x46081A0,
  GlobalSaveTableQueryAction = 0x4608220,
  GlobalSaveTableSetKeyAction = 0x46082A0,
  GoldBoltCountAction = 0x2FCEF98,
  GrindPathFollowerAction = 0x2F45380,
  HUDCommunicatorAction = 0x2FD0B38,
  HUDControlAction = 0x2FD0960,
  HUDMessageAction = 0x2FD08C8,
  HUDVisibilityAction = 0x2FD11F0,
  HammerCrankSetStateAction = 0x2FA2330,
  HasVisitedLevelAction = 0x2FAE8B0,
  HealAction = 0x45D9128,
  HeroButtonPressListenerAction = 0x2F5D5F8,
  HeroButtonReleaseListenerAction = 0x2F5D678,
  HeroDeathDisableRespawnAction = 0x2F5D398,
  HeroDefaultVanityLoadedAction = 0x2FA93F8,
  HeroLockAction = 0x2F5CD00,
  HeroPlayScriptedAnimAction = 0x2F5E280,
  HeroSetupLevelLoadedAction = 0x45E6290,
  HeroTargetImmuneAction = 0x2F5F998,
  HeroWearBootsAction = 0x2F5E208,
  HexEnableAction = 0x45E67E8,
  HexStreamingSourceAction = 0x45E68D0,
  IgWindAction = 0x32E4DF0,
  IncomingDamageModifierAction = 0x45D95A0,
  InputIdleAction = 0x2FCF100,
  InstanceTransitionAction = 0x45E6390,
  InvalidateEnvProbesAction = 0x433CAF8,
  InvertMatrixAction = 0x433A050,
  IsActorCameraObstructedAction = 0x45B3828,
  IsAliveAction = 0x45D90B8,
  IsCustomCommandLineFlagSetAction = 0x460C910,
  IsDemoAction = 0x45D58F0,
  IsGoldBoltCollectedAction = 0x2FCF010,
  IsLevelUnlockedAction = 0x2FAEC98,
  IsMissionReplayAction = 0x45F9E30,
  IsNewLevelAction = 0x2FAE838,
  IsNumberInRangeAction = 0x4337A20,
  IsOpenWorldAction = 0x45E6020,
  IsPlayerUsingCasualModeAction = 0x2FC74F8,
  IsPlayerUsingInvertedControlsAction = 0x2FC7578,
  IsSwitchTriggeredAction = 0x4629DC0,
  IsVarConnectedAction = 0x4337848,
  IsWeaponActiveAction = 0x2FFDC28,
  IsWeaponOwnedAction = 0x2FFDBB0,
  KickableSetInteractableAction = 0x45E4880,
  KillAction = 0x45D98B0,
  LandingBirdSystemAction = 0x2E6B5C0,
  LaserBeamSpawnerAction = 0x2F454A0,
  LedgeBirdLedgeControlAction = 0x2E6B6B0,
  LedgeBirdSystemAction = 0x2E6B638,
  LedgePathAttachAction = 0x2F510E0,
  LerpFloatAction = 0x4339D08,
  LerpFloatOverTimeAction = 0x433A570,
  LerpVectorAction = 0x4339C90,
  LerpVectorOverTimeAction = 0x433A690,
  LightIntensityAction = 0x433C880,
  LoadLevelAction = 0x45D56A0,
  LockMapIconAction = 0x2FD12E0,
  LockUIMissionAction = 0x2FD1178,
  LogAimAssistStartAction = 0x2F57AE0,
  LogarithmAction = 0x433A8A8,
  LookAtHeroAction = 0x4609558,
  LoopSignalAction = 0x4337C68,
  MakeMissionAvailableAction = 0x45EDDF8,
  ManglerControlScriptAction = 0x2EB0788,
  ManualTargetingAction = 0x2FCDDD0,
  MaxMinAction = 0x433A500,
  ModAction = 0x433A308,
  ModifyNavAction = 0x32DDA20,
  ModifyProximitySpawnScriptAction = 0x2FE8230,
  MonitorPlayerIdlingAction = 0x2FC7600,
  MotionAction = 0x460D9D8,
  MountAbilityOverrideScriptAction = 0x2F9FE70,
  MountCameraControlToggleScriptAction = 0x2F9FFF8,
  MountCameraScriptAction = 0x2F9FC78,
  MountScriptAction = 0x2F9FC00,
  MoverRequestAction = 0x460E0B0,
  MoverVelocityQueryAction = 0x460E128,
  MovingLevelAttachActorsAction = 0x45F50B0,
  MovingLevelPlayAnimAction = 0x45F5030,
  MovingLevelSetSpeedAction = 0x45F4F30,
  MovingLevelSetTileListAction = 0x45F4FB0,
  MovingLevelTriggerAction = 0x45F4EB0,
  MultVectorByScalarAction = 0x4339690,
  MultiplyAction = 0x433A1B0,
  MultiplyMatricesAction = 0x433A138,
  MusicCueListenerAction = 0x4343848,
  MusicIntensityTrackerScriptAction = 0x2E70988,
  NavMeshObstructionSystemAction = 0x45F7610,
  NavMeshObstructionsAction = 0x45F7590,
  NavObstacleAction = 0x460C820,
  NefariousBlimpGetNefPilotActorScriptAction = 0x2E88760,
  NormalizeValueToRangeAction = 0x4339D78,
  NormalizeVectorAction = 0x4339710,
  NumberGenAction = 0x4339530,
  ObjectConveyorScriptAction = 0x45DF0E0,
  OfferEnableAction = 0x45BF2C0,
  OnActivatedAction = 0x32CC4D0,
  OnActivityInterplanetaryTravelAction = 0x2F2BB20,
  OnActorCombatStateChangedAction = 0x2EEE3B0,
  OnAwarenessChangedAction = 0x4609110,
  OnBaseEventAction = 0x460AED8,
  OnBlockAction = 0x45D9530,
  OnBooleanAction = 0x43379B0,
  OnBouncedAction = 0x2F5E380,
  OnButtonPressedAction = 0x32CC6A0,
  OnChildSpawnedAction = 0x2EC5168,
  OnClankPuzzleLockOnStatusChangeAction = 0x2FC9148,
  OnClankPuzzleSphereDeployedAction = 0x2FC90C0,
  OnClankPuzzleVolumeEndAction = 0x2FC9250,
  OnCustomDesignEventAction = 0x460B048,
  OnDamageCounterAction = 0x45D94B8,
  OnDamagedAction = 0x45D93D0,
  OnDeactivatedAction = 0x32CC548,
  OnDeadAction = 0x45D92B8,
  OnDestroyedAction = 0x32CC718,
  OnDialogEventAction = 0x32CBC30,
  OnDoneAction = 0x32CC880,
  OnDropObjectAction = 0x2F5D490,
  OnEnterVolumeAction = 0x460AD70,
  OnEquippedWeaponAction = 0x2FFD3E0,
  OnEventAction = 0x32CC460,
  OnFlyerPickupAction = 0x2F9FF80,
  OnFrameEventAction = 0x43376F0,
  OnGameplayRunningAction = 0x45E5FA8,
  OnGroupChangeAction = 0x32CC790,
  OnHPThresholdAction = 0x45D9440,
  OnHealthThresholdClampedScriptAction = 0x2EC6590,
  OnHeroRespawnAction = 0x2F5E470,
  OnHostMigratedAction = 0x45D5A50,
  OnInjuredAction = 0x45D9360,
  OnInventoryChangedAction = 0x2FA4F10,
  OnJukeboxRTTEventAction = 0x2F42F58,
  OnKilledSomethingAction = 0x460B180,
  OnLightingModeChangedAction = 0x2FAADB8,
  OnLobbyRTTEventAction = 0x2FD0BB0,
  OnLookAtActorAction = 0x45B32C8,
  OnLookAtActorByAngleAction = 0x45B3548,
  OnLookAtEachActorAction = 0x45B35C8,
  OnMissionEventAction = 0x45EDAF8,
  OnMissionObjectiveEventAction = 0x45EDB98,
  OnMissionStateChangeEventAction = 0x45F9BB8,
  OnNumAliveAction = 0x2FCCE10,
  OnNumDeadAction = 0x2FCCB18,
  OnObjectiveStateChangeEventAction = 0x45F9C38,
  OnOpenWorldChangeAction = 0x45E6098,
  OnPickupAction = 0x4602AB0,
  OnPickupClankbotAction = 0x2E96A58,
  OnPlanetMenuRTTEventAction = 0x2F2B880,
  OnPlayerEventAction = 0x2FC7480,
  OnPortalTransitionAction = 0x4604520,
  OnPoweredAction = 0x2E96AD0,
  OnProjectileHitAction = 0x460B1F8,
  OnReceiveEventAction = 0x460AF90,
  OnRuinTokenPickupAction = 0x2F0E658,
  OnRynoPlanPickupAction = 0x2F0E378,
  OnShotSpawnedEventAction = 0x460E640,
  OnSpaceshipReticleTargetChangeAction = 0x2F5DFF8,
  OnStashChangedAction = 0x45EDC18,
  OnStringMessageAction = 0x2FCE920,
  OnThrowObjectAction = 0x2F5D418,
  OnTouchedAction = 0x32CC5C0,
  OnTriggerAction = 0x4629E38,
  OnUsedAction = 0x32CC630,
  OnValueChangedEventAction = 0x460AE58,
  OnVendorEventAction = 0x2FF10D0,
  OnVendorRTTEventAction = 0x2FD0A50,
  OnVolumeHunterEnterVolumeAction = 0x460E4F0,
  OnWorldCombatStateChangedAction = 0x2EEE538,
  OnWrenchSlamScriptAction = 0x2F074A0,
  OnZerpStonePickupAction = 0x2F0E468,
  OnZoneLoadedAction = 0x45E6190,
  OnZurkieRTTEventAction = 0x2F42EE0,
  OpenClosePowerReceptorAction = 0x2E96BB8,
  OrderedListArrangeAction = 0x460B878,
  OrderedListBuildAction = 0x460B4F8,
  OrderedListGetCountAction = 0x460B7F8,
  OrderedListGetIndexAction = 0x460B678,
  OrderedListGetItemAction = 0x460B6F8,
  OrderedListIterateAction = 0x460B778,
  OrderedListRemoveAction = 0x460B570,
  OrderedListUIAction = 0x460B8F8,
  OscillatingMotionAction = 0x2EF80D0,
  OutgoingDamageModifierAction = 0x45D9830,
  OverlayAction = 0x45E6620,
  OverlayAlertAction = 0x2FD0840,
  OverlayFadeAction = 0x45D7910,
  OverlayFlashAction = 0x45D7988,
  OverrideBoltShowerSettingsAction = 0x2FADCC8,
  OverrideBotComboConfigScriptAction = 0x2EC5AE0,
  OverrideBotShootingConfigScriptAction = 0x2EC5B68,
  OverrideBotSpeedScriptAction = 0x2EC5E00,
  OverrideGrindConfigAction = 0x2F5D9D0,
  OverrideHeroBackpackAction = 0x2F5D8D8,
  OverrideHeroCameraAnimatorAction = 0x2EE7E70,
  OverrideHeroSpaceshipSpeedAction = 0x2F5DE68,
  OverrideHeroSpaceshipTurnRateAction = 0x2F5DDE0,
  OverrideHoverbootConfigAction = 0x2F5DAD0,
  OverrideOpenWorldLoadDistanceAction = 0x2FAAE38,
  OverridePlanetLandingCheckpointAction = 0x2FC6920,
  OverrideSlideConfigAction = 0x2F5DA50,
  PassThruAction = 0x4337768,
  PassiveShiftTransitionAction = 0x2F0B730,
  PauseMapForceOfflineAction = 0x2FD1358,
  PerfSpecGetAction = 0x2FCF170,
  PeriodicAction = 0x4337F60,
  PhotoModeControlAction = 0x2FD0E08,
  PhysicsCollisionAction = 0x45FEFF0,
  PhysicsImpulseAction = 0x45FEDB0,
  PhysicsMakeVeryStiffSpringConstraintAction = 0x433E040,
  PhysicsRemoveConstraintAction = 0x433E0D0,
  PhysicsSetFreebodyAction = 0x45FF2F0,
  PhysicsSetGameGravityAction = 0x45FF068,
  PhysicsSetVelocityAction = 0x45FEE28,
  PickupItemAction = 0x4602B98,
  PirateChallengeControllerScriptAction = 0x2FC6520,
  PlanetMenuCheckpointWarpAction = 0x2FC69A8,
  PlatformDestinationAction = 0x45DF278,
  PlatformOrientationAction = 0x45DF630,
  PlatformSetCurveAction = 0x45DF200,
  PlatformSpeedAction = 0x45DF758,
  PlayAnimAction = 0x45900E0,
  PlayDialogAction = 0x2FAC3F0,
  PointCameraAtTargetAction = 0x2EE7DF0,
  PortalActivateAction = 0x4604428,
  PortalZipCombatOverrideScriptAction = 0x2F98728,
  PortalZipScriptAction = 0x2F986B0,
  PostFXFor3DUIAction = 0x2FD0E80,
  PressStartLogoAction = 0x2FD0C28,
  PressurePlateEventListenerAction = 0x2FA2B78,
  PrintCurrentLoadingTimeAction = 0x45E6110,
  PrototypeMessageAction = 0x460C3D0,
  ProximitySpawnScriptAction = 0x2FE81B0,
  PushAnimSetAction = 0x458DA90,
  PuzzleBotRunDirectionAction = 0x2FC9868,
  PuzzleTargetLatestVolumeAction = 0x2FC98E8,
  QueryAnimVarAction = 0x458DB80,
  RandomNumberAction = 0x433A618,
  RandomPointInVolumeAction = 0x460C998,
  RandomSignalAction = 0x4337DC8,
  RayCastDeferredAction = 0x4609BF8,
  RaycastAction = 0x46007D0,
  RecallPuzzleVolumesAction = 0x2FC9760,
  RegionAction = 0x45E6318,
  RegisterUserControlSetAction = 0x2FD2160,
  ReloadAction = 0x45E6700,
  ReloadToObjectiveAction = 0x2FAAF38,
  RemoveFromInventoryAction = 0x2FA4E70,
  RemovePuzzleVolumeDataFromTargetAction = 0x2FC97E0,
  ReplayMissionAction = 0x45F9DB8,
  RequestHeroRespawnAction = 0x2F5E3F0,
  ResurrectAction = 0x45D99B0,
  ReverseCurveFollowerAction = 0x45C9260,
  RotateByEulerAnglesAction = 0x4339EE8,
  RotateByMatrixAction = 0x4339FD8,
  RotateVectorAroundAxisAction = 0x4339AF0,
  RotateVectorAroundYAction = 0x4339A70,
  RuinTokenCountAction = 0x2F0E5E0,
  RynoPlanCountAction = 0x2F0E300,
  SargassoCentipedeMineFiringAction = 0x2E81660,
  SaveMissionStateAction = 0x45EDFE0,
  ScaleActorAction = 0x32B32B8,
  ScreenFadeAction = 0x4609000,
  ScriptAction = 0x2E69A88,
  ScriptStartedAction = 0x45E6208,
  ScriptedBirdControlAction = 0x2E6B540,
  ScriptedDevstatsEventAction = 0x45D22D0,
  ScriptedMortarPickerAction = 0x2FCCB88,
  SendAnimDamageEventAction = 0x458D920,
  SendEventAction = 0x460ADE8,
  SetAbilityEnabledAction = 0x2FCDB80,
  SetActorAction = 0x43370C0,
  SetActorGroupAction = 0x4337130,
  SetActorGuiRenderAction = 0x4606100,
  SetAdditionalAttackersAction = 0x2F5E188,
  SetAllegianceScriptAction = 0x4625D48,
  SetAllowShaderHighlightsInCinematicsAction = 0x45898E0,
  SetAllowedClankbotsAction = 0x2E96C38,
  SetAmmoAction = 0x2FFD5E0,
  SetBooleanAction = 0x43378C0,
  SetBypassDistantLightingAction = 0x433CA78,
  SetCameraFOVAction = 0x45B38A8,
  SetCanDanceAction = 0x2FCDE48,
  SetCasualTargetingRangeMultiplierAction = 0x2FFDD90,
  SetCompositeShaderAction = 0x4605F90,
  SetCurrencyAction = 0x2FCEA50,
  SetCurveAction = 0x45C9100,
  SetCurveFromPointListAction = 0x460A8B0,
  SetDamageInvulnerableAction = 0x45D9238,
  SetDamageMultiplierAction = 0x45D91B8,
  SetDamagedOnlyByHeroAction = 0x2FCEDA8,
  SetDifficultyAction = 0x2F09700,
  SetDimensionCompleteAction = 0x2F0A8B8,
  SetFallingRespawnLocationScriptAction = 0x2F520A0,
  SetFlounderingScriptAction = 0x2EC61B0,
  SetHeroBackpackAction = 0x2F5D860,
  SetHeroCurrentShipAction = 0x2FAE498,
  SetHeroHackedShipAction = 0x2F5D2A0,
  SetHeroMaskAction = 0x2F5D7E8,
  SetHeroRailShooterAction = 0x2F5D318,
  SetHeroSpaceshipFlighConfigAction = 0x2F5DB50,
  SetHeroSpaceshipInputAction = 0x2F5DEF0,
  SetHeroSpaceshipMagnetModeAction = 0x2F5E080,
  SetHeroSpaceshipMissileCountAction = 0x2F5DF70,
  SetHighContrastShaderAction = 0x45899F0,
  SetHomeAreaAction = 0x2FCDD58,
  SetInfiniteAmmoAction = 0x2FFD650,
  SetKeyFrameModifierGlobalAction = 0x4606178,
  SetLevelOverrideAction = 0x2FAED10,
  SetLightGridFadeTimeAction = 0x433C9F8,
  SetLightGridPriorityAction = 0x433C978,
  SetLightingModeAction = 0x2FAACC8,
  SetLootModeAction = 0x2FADC50,
  SetMaterialAction = 0x433C670,
  SetMaterialGlobalAction = 0x433C7F8,
  SetMissionActiveAction = 0x45F99C8,
  SetMissionFailedAction = 0x45F9D40,
  SetMissionObjectiveVariableAction = 0x45ED9F8,
  SetModelAmbientAnimationAction = 0x433C8F8,
  SetModelCustomInputAction = 0x433C700,
  SetNumberAction = 0x4337308,
  SetObjectiveFailedAction = 0x45F9CC0,
  SetOfferVolumeAction = 0x45BF338,
  SetOneHitKillAction = 0x2FFD6C8,
  SetPlanetaryTravelAction = 0x2F2BAA0,
  SetPortalDestinationAction = 0x46044A0,
  SetRTCPAction = 0x4343938,
  SetRenderConstantAction = 0x4606010,
  SetSaveOnReloadAction = 0x45E5F30,
  SetSkirmishDesiresScriptAction = 0x2EAE930,
  SetStrandStateAction = 0x45EC810,
  SetStreamingVideoConfigAction = 0x4623C20,
  SetStringAction = 0x4337220,
  SetTargetTypeScriptAction = 0x4625E68,
  SetTargetableAction = 0x4625FB0,
  SetTeamScriptAction = 0x45D5960,
  SetTextureAction = 0x433C780,
  SetTrampolineParamsAction = 0x2F5E300,
  SetVectorAction = 0x4337378,
  SetVelocityScriptMotionAction = 0x460DAC0,
  SetWeaponEquipableAction = 0x2FCDBF8,
  SetWeaponLevelAction = 0x2FFD888,
  SetWeaponModCountAction = 0x2FFD9B8,
  SetXPAction = 0x2FCF3F0,
  SetupControllerAction = 0x2FAED88,
  SignalRelayAction = 0x4337A98,
  SimpleMoverAction = 0x460C5A8,
  SimpleRotatingChangeSpeedAction = 0x45C3C00,
  SkipObjectiveAction = 0x2FBD270,
  SkirmishScriptAction = 0x2EAEC70,
  SkuFilterAction = 0x2FCF090,
  SlerpVectorAction = 0x4339DF8,
  SlottedInteractScriptAction = 0x45E0688,
  SolveQuadraticEquationAction = 0x4339440,
  SpawnRewardAction = 0x2FCEF20,
  SpawnScaledActorScriptAction = 0x2FD06D0,
  SpawnScriptedBirdAction = 0x2E6B4C8,
  SpawnerBotSetupScriptAction = 0x2EC71B0,
  SpawnerFactoryScriptAction = 0x2EC7BC0,
  SpawnerScriptAction = 0x461CBE0,
  StartMissionAction = 0x45EDEA0,
  StartMissionObjectiveAction = 0x45ED550,
  StaticSphereCheckDeferredAction = 0x4609D10,
  StatusEmitterScriptAction = 0x4621E38,
  StopAllOscillatingMotionAction = 0x2EF7C78,
  StopPickupFallAction = 0x460C620,
  StructuredLogScriptAction = 0x433D2B0,
  StructuredLoggingActorLooksDumpAction = 0x433D800,
  StructuredLoggingActorPhysicsAction = 0x433D658,
  StructuredLoggingFinishTestAction = 0x460C210,
  StructuredLoggingLogAnimTreeAction = 0x433DAD0,
  StructuredLoggingLogAnimVarAction = 0x433DB90,
  StructuredLoggingLogJointsAction = 0x433DA48,
  StructuredLoggingNumberAction = 0x433D428,
  StructuredLoggingPhysicsBodyDumpAction = 0x433D778,
  StructuredLoggingPhysicsBreakableDiagnosticsAction = 0x433D920,
  StructuredLoggingScaleAction = 0x433D020,
  StructuredLoggingSetTraceAnimControllerAction = 0x433D9B8,
  StructuredLoggingStringAction = 0x433D310,
  StructuredLoggingTransformAction = 0x433CF98,
  StructuredLoggingVectorAction = 0x433D540,
  SubCurrencyAction = 0x2FCEBF8,
  SubtractAction = 0x433A0C8,
  SubtractVectorsAction = 0x4339618,
  SunsetSpawnerFactoryScriptAction = 0x2EC7B30,
  SweptSphereDeferredAction = 0x4609C80,
  SwitchSignalAction = 0x4337CE0,
  SyncValueAction = 0x45C4960,
  TextSelectScriptAction = 0x2F04C20,
  TimeScaleAction = 0x44CCBB0,
  TimedTriggerPadGroupSetupScriptAction = 0x45E1040,
  TimerAction = 0x4337EB8,
  ToggleAction = 0x460C348,
  ToggleCustomNavClueAction = 0x32DDA90,
  ToggleHeroMovesAction = 0x2F5CD70,
  TogglePortalRespawnSystemScriptAction = 0x2EF9050,
  TogglePostVolumesScriptAction = 0x460E760,
  TogglePressurePlateCompletedAction = 0x2FA2AF0,
  TogglePressurePlateLockedAction = 0x2FA2A70,
  ToggleStreamingVideoAction = 0x4623BA0,
  TrafficScriptAction = 0x2FEEAA8,
  TrainCarAction = 0x2EF7CF8,
  TriggerActorAction = 0x4629D48,
  TriggerBeamOutEffectAction = 0x2EF4F40,
  TriggerEmergentDialogAction = 0x45B9B80,
  TriggerPadScriptAction = 0x45E0FC8,
  TrigonometryAction = 0x433A740,
  TrigonometryInverseAction = 0x433A7B8,
  UIArenaRewardAction = 0x2FD0750,
  UIArenaWaveAction = 0x2FD1590,
  UICountDownAction = 0x2FD07C8,
  UICounterAction = 0x2FD13D8,
  UIExitFinaleAction = 0x2FD0D18,
  UIObjectiveAction = 0x2FD1100,
  UIProgressBarAction = 0x2FD1500,
  UIShowReticleAction = 0x2FD1488,
  UISkipMovieAction = 0x2FD0D90,
  UISkipPuzzleAction = 0x2FD0CA0,
  UITutorialAction = 0x32A0168,
  UITutorialMessageAction = 0x2FEFF90,
  UIViewRTTLoadAction = 0x4583450,
  UIViewRTTVisibilityAction = 0x4583338,
  UnequipWeaponAction = 0x2FFD7B8,
  UnlockLevelAction = 0x2FAEC20,
  UseSharedLoadoutScriptAction = 0x3017FA0,
  VanityEquipBundleAction = 0x2FA9308,
  VanityEquipSetAction = 0x2FA9380,
  VanityGiveBundleAction = 0x2FA9218,
  VanityGiveSetAction = 0x2FA9290,
  VanityHasBundleAction = 0x2FA9028,
  VanityHasSetAction = 0x2FA9120,
  VanityIsBundleEquippedAction = 0x2FA90A0,
  VanityIsSetEquippedAction = 0x2FA9198,
  VehicleFXControlAction = 0x2FEEB98,
  VehicleObstacleAction = 0x2FEEB20,
  VendorActivateScriptAction = 0x2FF1050,
  VendorRTTAction = 0x2FD0AC8,
  WaitForCheckpointWarpEndAction = 0x2F5D220,
  WarpToInteractScriptAction = 0x45E0708,
  WasRuinTokenCollectedAction = 0x2F0E6D0,
  WasRynoPlanCollectedAction = 0x2F0E4E0,
  WasZerpStoneCollectedAction = 0x2F0E560,
  WwiseGameSyncAction = 0x4343538,
  ZerpStoneCountAction = 0x2F0E3F0,
  ZoneVisibleAction = 0x45E6770,
  hclAction = 0x486B230,
  hclClothPickingAction = 0x487C7F0,
  hclSimpleWindAction = 0x486B360,
  hknpAction = 0x4954700,
  hknpArrayAction = 0x4956818,
  hknpBinaryAction = 0x4954BC8,
  hknpSpringAction = 0x4954F80,
  hknpUnaryAction = 0x49549E0,
}
RANDO_EXE = { add_to_inventory_vtable = 0x2FA4DE0, add_to_inventory_handler = 0x86CB90, handler_slot = 10 }
end
end)

-- ==== section: spawnprobe (dev(spawnprobe).lua) =====================================================================
DBG.section("spawnprobe", function()
-- ---- dev(spawnprobe).lua ----
-- DEVELOPER TOOL - not part of a release. SPAWN PROBE v1 (dev 10.20): READ-ONLY evidence for the Enemy /
-- Boss / Chaos Randomizers. It never writes game memory, never fires a node, never changes a setting.
--
-- WHY IT EXISTS. Your dev 10.19 rivet.log (2026-11-17, kept as tests/data/round30_rivet.log) proved:
--   * a SpawnerScriptAction node's u32 at +0x60 IS the handle of the "Spawner" component on the same
--     actor (6 of 6 dumped pairs: node +0x60 == Spawner +0x1C; both +0x10 point at the same Actor), and a
--     SpawnerStoppedEvent's SpawnerComponentHandle is that same handle (0x214EBC, Zurkon);
--   * neither the node nor its Spawner component keeps a Prius: ddlPriusData (+0x08) is 0 in both, and the
--     306 bytes of the Spawner that reached the log hold no pointer except the vtable and the actor.
-- So WHERE the encounter's Templates live at runtime is still unknown; every census since 10.12 read 0
-- nodes. Guessing more offsets would repeat 10.12-10.19. This file collects the missing facts in ONE play
-- session, automatically:
--   1. INDEX (after each level / planet / checkpoint load): every SpawnerScriptAction node, its Spawner
--      component (only if its handle equals the node's +0x60), a byte snapshot of that component, and a
--      histogram of the offsets where a Spawner holds a readable pointer.
--   2. SPAWNS (the first P.SPAWN_LOG of a level): what the game actually created - the spawned actor's
--      handle, uid, name, actor asset (id and name), Template flag and component classes - and the same
--      for SpawnFactory.
--   3. CHANGES: after spawns, every indexed Spawner is read again; the ones whose bytes changed are the
--      encounters that ran. Their changed offsets are logged, and the first ones are probed deeply.
--   4. DEEP PROBE of a node: the ComponentInfo of every component on its actor (class, size, Prius type,
--      Prius size, Prius behaviour), the node and Spawner bytes (whole, in short lines), the node's plug
--      block, every block one pointer away, and a UID SEARCH: each 8-byte value in those blocks is asked
--      rivet.find_uid; a hit names the loaded actor (name, Template flag, classes). A Templates list is a
--      list of template-actor uids, so a hit that is a template bot (or matches a spawned bot's actor
--      asset) shows exactly where the list is.
-- Output lines start with "RANDO-SPAWNPROBE". Remove this file to turn it off; the randomizer does not need it.
-- (dev(spawnprobe).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["spawnprobe"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_SPAWNPROBE = RANDO_SPAWNPROBE or {}
local P = RANDO_SPAWNPROBE
P.version = 1
P.frame = P.frame or 0

P.NODE_CLASS = "SpawnerScriptAction"
P.SPAWNER_CLASS = "Spawner"
P.HANDLE_AT = 0x60             -- node +0x60 = its Spawner component's handle (proved by the 10.19 log)
P.CHUNK = 96                   -- bytes per dump line (rivet.log keeps 1024 characters of a line)
P.READ_MAX = 512               -- rivet.read's limit per call (rivet_hook MAX_READ_BYTES)
P.INDEX_DELAY = 120            -- frames after a load before the level is indexed
P.INDEX_LIMIT = 512            -- nodes indexed per level
P.INDEX_PROBES = 2             -- deep probes right after an index (nodes whose Spawner holds a pointer first)
P.CHANGE_PROBES = 3            -- deep probes of Spawners that changed while playing, per level
P.SESSION_PROBES = { index = 8, change = 20 }   -- deep probes per session: after an index / of a Spawner that ran
P.SPAWN_LOG = 6                -- spawns per level whose actor is described
P.SWEEP_GAP = 240              -- frames between two re-reads of every indexed Spawner
P.SWEEPS_PER_LEVEL = 4
P.UID_CALLS = 240              -- rivet.find_uid calls per deep probe
P.SLICE = 0.002                -- seconds of work per frame (rivet_hook stops a script after 8 ms)

P.lvl = P.lvl or nil
P.job = nil
P.queue = P.queue or {}
P.spent = P.spent or { index = 0, change = 0 }
P.t0 = 0

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNPROBE", ...) end
P.log = log
local function clock() return (os and os.clock and os.clock()) or 0 end

-- ---- bytes -----------------------------------------------------------------------------------
local function bytes_of(text)
  local t = {}
  for x in tostring(text or ""):gmatch("%x%x") do t[#t + 1] = tonumber(x, 16) end
  return t
end
local function u16(b, i) if not b[i + 1] then return nil end return b[i] + b[i + 1] * 0x100 end
local function u32(b, i)
  if not b[i + 3] then return nil end
  return b[i] + b[i + 1] * 0x100 + b[i + 2] * 0x10000 + b[i + 3] * 0x1000000
end
local function s32(b, i) local v = u32(b, i); if v and v >= 0x80000000 then v = v - 0x100000000 end; return v end
local function hex64(b, i)
  if not b[i + 7] then return nil end
  return string.format("%02X%02X%02X%02X%02X%02X%02X%02X", b[i + 7], b[i + 6], b[i + 5], b[i + 4], b[i + 3], b[i + 2], b[i + 1], b[i])
end
local function ptr64(b, i)
  local h = hex64(b, i)
  if not h or h:sub(1, 1):match("[89A-F]") then return nil end
  return tonumber(h, 16)
end
local function valid_ptr(p) return p ~= nil and p > 0x10000 and p < 0x7FFFFFFFFFFF and p % 8 == 0 end
P.bytes_of, P.u32, P.hex64, P.ptr64, P.valid_ptr = bytes_of, u32, hex64, ptr64, valid_ptr

-- a rivet call; nil on failure. Inside the job a stop by the frame budget is raised again, so that
-- guarded() can retry the step on the next frame instead of taking the failure for an answer.
local function rcall(fn, ...)
  local ok, a, b = pcall(fn, ...)
  if ok then return a, b end
  if coroutine.isyieldable() and tostring(a):find("budget", 1, true) then error(a, 0) end
  return nil
end
P.rcall = rcall

-- rivet.read in pieces of at most P.READ_MAX bytes; nil when the first piece is unreadable
local function read(addr, len)
  if not valid_ptr(addr) and not (addr and addr > 0x10000) then return nil end
  local out = {}
  local at = 0
  while at < len do
    local n = math.min(P.READ_MAX, len - at)
    local text = rcall(rivet.read, string.format("%X", addr + at), n)
    if not text then break end
    local b = bytes_of(text)
    for _, v in ipairs(b) do out[#out + 1] = v end
    if #b < n then break end
    at = at + n
  end
  if #out == 0 then return nil end
  return out
end
P.read = read

local function hexrange(b, from, n)
  local t = {}
  for k = from, math.min(#b, from + n - 1) do t[#t + 1] = string.format("%02x", b[k]) end
  return table.concat(t, " ")
end
-- a block in lines of P.CHUNK bytes ("<head> +0x060: aa bb ...")
function P.dump(head, b)
  if not b then log(head .. ": unreadable"); return end
  for from = 1, #b, P.CHUNK do log(string.format("%s +0x%03X: %s", head, from - 1, hexrange(b, from, P.CHUNK))) end
end

-- a C string (printable ASCII only), or nil. Read 8 bytes at a time: a string can end just before
-- unreadable memory, and rivet.read answers nil for a block that runs into it.
local function cstr(p)
  if not (p and p > 0x10000 and p < 0x7FFFFFFFFFFF) then return nil end
  local t = {}
  for at = 0, 88, 8 do
    local b = read(p + at, 8)
    if not b then break end
    for _, c in ipairs(b) do
      if c == 0 then return #t > 0 and table.concat(t) or nil end
      if c < 32 or c > 126 then return nil end
      t[#t + 1] = string.char(c)
    end
  end
  return #t > 0 and table.concat(t) or nil
end
P.cstr = cstr

-- ---- engine structures (rivet_hook src/game/actor.hpp, ddl.hpp, script.hpp @ develop 0bdb394) --------
-- Actor (0xC0): flags +0x10, actorAsset +0x30, components +0x68, componentCount u16 +0x70, name +0xB0
-- Asset: assetId +0x08, name +0x10, nameOffset u16 +0x18
-- ComponentPointer { ComponentInfo *type; Component *instance } (0x10)
-- ComponentInfo: prius_info.size +0x58, name +0x60, size i32 +0x78, id u32 +0x7C, prius (DDLTypeInfo*)
--   +0xC8, parent_count u8 +0xE6, prius_behavior u8 +0xE7 (0 ReadOnly, 1 Local, 2 ReadWrite)
-- Component: vtable +0, ddlPriusData +0x08, actor +0x10, handle +0x1C
-- ScriptAction: instanceUid +0x48, graphUid +0x50, plugs +0x58 (ScriptPlugs 0x28: zone +0x1C, owner +0x24)
P.TEMPLATE_FLAG = 4
P.BEHAVIOR = { [0] = "ReadOnly", [1] = "Local", [2] = "ReadWrite" }

function P.actor_info(actor)
  local a = read(actor, 0xC0)
  if not a or #a < 0xC0 then return nil end
  local info = { flags = u32(a, 0x11), asset = ptr64(a, 0x31), comps = ptr64(a, 0x69), ncomp = u16(a, 0x71),
                 name = cstr(ptr64(a, 0xB1)) }
  if info.asset then
    local ab = read(info.asset, 0x20)
    if ab and #ab >= 0x1A then
      info.asset_id = hex64(ab, 9)
      local full = cstr(ptr64(ab, 0x11))
      local off = u16(ab, 0x19) or 0
      info.asset_name = full and (off > 1 and off < #full and full:sub(off + 1) or full) or nil
    end
  end
  info.template = info.flags and (info.flags & P.TEMPLATE_FLAG) ~= 0
  return info
end

-- every component of an actor: class, instance, handle, ddlPriusData, size, prius type / size / behaviour
function P.components_of(actor)
  local a = P.actor_info(actor)
  if not a or not valid_ptr(a.comps) or not a.ncomp or a.ncomp < 1 or a.ncomp > 64 then return nil, a end
  local list = read(a.comps, a.ncomp * 0x10)
  if not list then return nil, a end
  local out = {}
  for k = 0, a.ncomp - 1 do
    local ti, inst = ptr64(list, k * 0x10 + 1), ptr64(list, k * 0x10 + 9)
    local e = { info = ti, inst = inst }
    local ib = valid_ptr(ti) and read(ti, 0xE8)
    if ib and #ib >= 0xE8 then
      e.class = cstr(ptr64(ib, 0x61))
      e.size = s32(ib, 0x79)
      e.id = u32(ib, 0x7D)
      e.prius_type = ptr64(ib, 0xC9)
      e.prius_size = s32(ib, 0x59)
      e.behavior = P.BEHAVIOR[ib[0xE8]] or tostring(ib[0xE8])
    end
    local cb = valid_ptr(inst) and read(inst, 0x20)
    if cb and #cb >= 0x20 then e.ddl = hex64(cb, 9); e.handle = u32(cb, 0x1D) end
    out[#out + 1] = e
  end
  return out, a
end

-- a handle's actor pointer (through one of its components), or nil
function P.actor_ptr(handle)
  local okn, names = pcall(rivet.components, handle)
  if not okn or type(names) ~= "table" then return nil end
  for k, n in ipairs(names) do
    if k > 4 then break end              -- dev 10.21: your log: a long component list ran past the frame budget
    local ok, c = pcall(rivet.component, handle, tostring(n))
    if ok and type(c) == "table" and c.address then
      local b = read(tonumber(c.address, 16), 0x18)
      local a = b and ptr64(b, 0x11)
      if valid_ptr(a) then return a, names end
    end
  end
  return nil, names
end

-- one line about an actor handle: uid, name, actor asset, Template flag, classes
function P.describe(handle)
  handle = math.tointeger(tonumber(handle)) or handle
  if not handle or handle == 0 then return "none" end
  local oku, uid = pcall(rivet.uid, handle)
  local nm
  if rivet.name then local okn, n = pcall(rivet.name, handle); if okn then nm = n end end
  local actor, names = P.actor_ptr(handle)
  local a = actor and P.actor_info(actor)
  local cls = {}
  for k, n in ipairs(type(names) == "table" and names or {}) do if k <= 14 then cls[#cls + 1] = tostring(n) end end
  return string.format("handle %s uid %s name %s asset %s %s%s classes %s", tostring(handle), tostring(oku and uid),
      tostring(nm or (a and a.name)), tostring(a and a.asset_id), tostring(a and a.asset_name),
      (a and a.template) and " TEMPLATE" or "", #cls > 0 and table.concat(cls, ",") or "?"), a
end

-- ---- the level index ----------------------------------------------------------------------------
local function pause()
  if coroutine.isyieldable() and clock() - P.t0 > P.SLICE then coroutine.yield(); P.t0 = clock() end
end
P.pause = pause

-- a call that rivet_hook's frame budget may stop: tried again on the next frames (3 times)
local function guarded(fn, ...)
  local ok, a, b, c
  for _ = 1, 3 do
    ok, a, b, c = pcall(fn, ...)
    if ok then return a, b, c end
    if not tostring(a):find("budget", 1, true) or not coroutine.isyieldable() then error(a, 0) end
    coroutine.yield(); P.t0 = clock()
  end
  log("a step was stopped by the frame budget three times; skipped")
  return nil
end
P.guarded = guarded

-- pointer offsets (beyond the vtable +0 and the actor +0x10) whose target is readable
local function readable_pointers(b, from)
  local out = {}
  for off = from or 0x18, #b - 8, 8 do
    local p = ptr64(b, off + 1)
    if valid_ptr(p) and read(p, 8) then out[#out + 1] = { off = off, p = p } end
  end
  return out
end
P.readable_pointers = readable_pointers

function P.index(why)
  local lvl = { nodes = {}, order = {}, why = why, probes = 0, spawns = 0, sweeps = 0, spawned_assets = {},
                id = (P.lvl and P.lvl.id or 0) + 1 }
  local okl, list = pcall(rivet.script_nodes, P.NODE_CLASS, P.INDEX_LIMIT)
  if not okl or type(list) ~= "table" then log("index: the spawner nodes cannot be listed:", tostring(list)); return end
  local n, matched, mismatch, nospawner, sizes, ptr_hist = 0, 0, 0, 0, {}, {}
  local function one(node)
    local c = rcall(rivet.component, node.actor, P.NODE_CLASS)
    local addr = type(c) == "table" and c.handle == node.component and c.address and tonumber(c.address, 16)
    local hb = addr and read(addr + P.HANDLE_AT, 4)
    local want = hb and u32(hb, 1)
    local s = rcall(rivet.component, node.actor, P.SPAWNER_CLASS)
    if not (type(s) == "table" and s.address) then nospawner = nospawner + 1
    elseif s.handle ~= want then mismatch = mismatch + 1
    else
      matched = matched + 1
      local saddr = tonumber(s.address, 16)
      local ssize = math.min(P.READ_MAX, (s.size and s.size > 0) and s.size or 0x200)
      local snap = read(saddr, ssize)
      sizes[tostring(s.size)] = (sizes[tostring(s.size)] or 0) + 1
      local ptrs = snap and readable_pointers(snap) or {}
      for _, e in ipairs(ptrs) do local k = string.format("+0x%X", e.off); ptr_hist[k] = (ptr_hist[k] or 0) + 1 end
      local rec = { uid = node.uid, actor = node.actor, component = node.component, addr = addr, handle = want,
                    saddr = saddr, ssize = ssize, snap = snap, nptr = #ptrs }
      lvl.nodes[want] = rec
      lvl.order[#lvl.order + 1] = want
    end
  end
  for _, node in ipairs(list) do
    pause()
    if node.class == P.NODE_CLASS and node.actor then n = n + 1; guarded(one, node) end
  end
  P.lvl = lvl
  local sz, hist = {}, {}
  for k, v in pairs(sizes) do sz[#sz + 1] = k .. " x" .. v end
  table.sort(sz)
  for k, v in pairs(ptr_hist) do hist[#hist + 1] = { k = k, v = v } end
  table.sort(hist, function(a, b) if a.v ~= b.v then return a.v > b.v end return a.k < b.k end)
  local ht = {}
  for i = 1, math.min(16, #hist) do ht[#ht + 1] = hist[i].k .. " x" .. hist[i].v end
  log(string.format("index %d (%s): %d node(s); Spawner handle == node +0x%X for %d, another handle %d, no Spawner %d; Spawner sizes %s; readable pointers at %s",
      lvl.id, tostring(why), n, P.HANDLE_AT, matched, mismatch, nospawner, #sz > 0 and table.concat(sz, ", ") or "-",
      #ht > 0 and table.concat(ht, ", ") or "no offset"))
  -- the first deep probes: nodes whose Spawner holds a pointer first (the likeliest to lead to the lists)
  local pick = {}
  for _, h in ipairs(lvl.order) do if lvl.nodes[h].nptr > 0 then pick[#pick + 1] = h end end
  for _, h in ipairs(lvl.order) do if lvl.nodes[h].nptr == 0 then pick[#pick + 1] = h end end
  for i = 1, math.min(P.INDEX_PROBES, #pick) do guarded(P.probe, lvl.nodes[pick[i]], "index") end
end

-- ---- the deep probe -----------------------------------------------------------------------------
-- 8-byte values worth asking rivet.find_uid: not 0, not -1, not a pointer, not two equal floats
local function uid_candidate(h)
  if not h or h == "0000000000000000" or h == "FFFFFFFFFFFFFFFF" then return false end
  if h:sub(1, 4) == "0000" then return false end           -- small numbers and user-space pointers
  if h:sub(1, 8) == h:sub(9, 16) then return false end      -- two equal u32 / floats
  if h:sub(1, 8) == "FFFFFFFF" then return false end
  return true
end
P.uid_candidate = uid_candidate

function P.uid_search(blocks, lvl, skip)
  local asked, hits, seen = 0, 0, {}
  for _, h in ipairs(skip or {}) do seen[tostring(h):upper()] = true end
  for _, blk in ipairs(blocks) do
    for off = 0, #blk.b - 8, 8 do
      local h = hex64(blk.b, off + 1)
      if uid_candidate(h) and not seen[h] and asked < P.UID_CALLS then
        seen[h] = true
        asked = asked + 1
        pause()
        local handle = rcall(rivet.find_uid, h)
        if handle then
          hits = hits + 1
          local text, a = P.describe(handle)
          local match = ""
          if a and a.asset_id and lvl and lvl.spawned_assets[a.asset_id] then
            match = " - SAME ACTOR ASSET AS SPAWNED " .. lvl.spawned_assets[a.asset_id]
          end
          log(string.format("UID HIT %s+0x%X = %s -> %s%s", blk.path, off, h, text, match))
        end
      end
    end
  end
  return asked, hits
end

function P.probe(rec, why)
  local lvl = P.lvl
  local kind = (why == "index") and "index" or "change"
  if not rec or P.spent[kind] >= P.SESSION_PROBES[kind] then return end
  P.spent[kind] = P.spent[kind] + 1
  if lvl then lvl.probes = lvl.probes + 1; if kind == "change" then lvl.change_probes = (lvl.change_probes or 0) + 1 end end
  local tag = string.format("probe %s node %s", tostring(why), tostring(rec.uid))
  log(string.format("%s: node component %s at %X, Spawner handle %X at %X (%d bytes read)", tag, tostring(rec.component),
      rec.addr or 0, rec.handle or 0, rec.saddr or 0, rec.ssize or 0))
  -- the actor's components and their type data
  local node = rec.addr and read(rec.addr, 0x80)
  local actor = node and ptr64(node, 0x11)
  if valid_ptr(actor) then
    local comps, a = P.components_of(actor)
    if a then
      log(string.format("%s: actor %X flags %s asset %s %s name %s, %s component(s)", tag, actor, tostring(a.flags),
          tostring(a.asset_id), tostring(a.asset_name), tostring(a.name), tostring(a.ncomp)))
    end
    for _, e in ipairs(comps or {}) do
      log(string.format("%s: component %s handle %s inst %X ddlPriusData %s | class size %s id %s prius type %s prius size %s %s",
          tag, tostring(e.class), e.handle and string.format("%X", e.handle) or "?", e.inst or 0, tostring(e.ddl),
          tostring(e.size), e.id and string.format("%08X", e.id) or "?", e.prius_type and string.format("%X", e.prius_type) or "none",
          tostring(e.prius_size), tostring(e.behavior)))
    end
  end
  -- what rivet_hook knows about the node's wiring (outputs and variables)
  if rivet.script_node then
    local ok, t = pcall(rivet.script_node, rec.component, false)
    if ok and type(t) == "table" then
      local parts = {}
      for _, k in ipairs({ "graph_uid", "zone", "connections_in" }) do if t[k] ~= nil then parts[#parts + 1] = k .. "=" .. tostring(t[k]) end end
      local outs = {}
      for _, o in ipairs(type(t.outputs) == "table" and t.outputs or {}) do
        if type(o) == "table" then outs[#outs + 1] = tostring(o.plug_name or o.plug) .. "->" .. tostring(o.target_class or o.target) end
        if #outs >= 8 then break end
      end
      local vars = {}
      for _, v in ipairs(type(t.vars) == "table" and t.vars or {}) do
        if type(v) == "table" then
          local val = v.value
          if type(val) == "table" then      -- dev 10.21: an actors var: its handles, group flag, count and uid
            local hs = {}
            for i = 1, math.min(4, #val) do hs[i] = tostring(val[i]) end
            val = string.format("{%s}%s count %s uid %s", table.concat(hs, ","), val.group and " group" or "", tostring(val.count), tostring(val.uid))
          end
          vars[#vars + 1] = tostring(v.plug_name or v.plug) .. ":" .. tostring(v.type) .. "=" .. tostring(val)
        end
        if #vars >= 8 then break end
      end
      log(string.format("%s: script_node %s; outputs %s; vars %s", tag, table.concat(parts, " "),
          #outs > 0 and table.concat(outs, ", ") or "-", #vars > 0 and table.concat(vars, ", ") or "-"))
    end
  end
  -- the bytes: node, Spawner, plugs, one pointer away
  local blocks = {}
  if node then P.dump(tag .. " node", node); blocks[#blocks + 1] = { path = "node", b = node } end
  local sp = rec.saddr and read(rec.saddr, rec.ssize or 0x200)
  if sp then P.dump(tag .. " Spawner", sp); blocks[#blocks + 1] = { path = "Spawner", b = sp } end
  if node then
    local plugs = ptr64(node, 0x59)
    local pb = valid_ptr(plugs) and read(plugs, 0x28)
    if pb then P.dump(string.format("%s plugs at %X", tag, plugs), pb) end
  end
  local followed, seen = 0, { [rec.addr or 0] = true, [rec.saddr or 0] = true, [actor or 0] = true }
  local second = {}
  for _, src in ipairs({ { "node", node, 0x60 }, { "Spawner", sp, 0x48 } }) do
    if src[2] then
      for _, e in ipairs(readable_pointers(src[2], src[3])) do
        if not seen[e.p] and followed < 12 then
          seen[e.p] = true
          followed = followed + 1
          pause()
          local b = read(e.p, 0x100)
          if b then
            local path = string.format("%s+0x%X->%X", src[1], e.off, e.p)
            P.dump(tag .. " " .. path, b)
            blocks[#blocks + 1] = { path = path, b = b }
            for _, q in ipairs(readable_pointers(b, 0)) do second[#second + 1] = { path = path .. "+0x" .. string.format("%X", q.off), p = q.p } end
          end
        end
      end
    end
  end
  -- two pointers away: searched for uids, not dumped (only their hits are logged)
  local n2 = 0
  for _, e in ipairs(second) do
    if not seen[e.p] and n2 < 16 then
      seen[e.p] = true; n2 = n2 + 1
      pause()
      local b = read(e.p, 0x80)
      if b then blocks[#blocks + 1] = { path = e.path .. "->" .. string.format("%X", e.p), b = b } end
    end
  end
  -- the node's own uid (+0x48) and graph uid (+0x50) are not asked: they name the node itself
  local skip = { tostring(rec.uid) }
  if node then skip[2] = hex64(node, 0x49); skip[3] = hex64(node, 0x51) end
  local asked, hits = P.uid_search(blocks, lvl, skip)
  log(string.format("%s: %d block(s) searched (%d one pointer away, %d two away), %d value(s) asked rivet.find_uid, %d loaded actor(s) found",
      tag, #blocks, followed, n2, asked, hits))
end

-- what changed in a Spawner since the last read: "+0x0C8 a6000000->e2001234 ..." (8-byte steps)
function P.diff(old, new)
  local out = {}
  if not (old and new) then return out end
  for off = 0, math.min(#old, #new) - 8, 8 do
    local a, b = hex64(old, off + 1), hex64(new, off + 1)
    if a ~= b then out[#out + 1] = string.format("+0x%03X %s->%s", off, a, b) end
  end
  return out
end

function P.sweep()
  local lvl = P.lvl
  if not lvl then return end
  lvl.sweeps = lvl.sweeps + 1
  local changed = 0
  for _, h in ipairs(lvl.order) do
    pause()
    local rec = lvl.nodes[h]
    local now = guarded(read, rec.saddr, rec.ssize)
    local d = P.diff(rec.snap, now)
    if #d > 0 then
      changed = changed + 1
      if changed <= 8 then
        local shown = {}
        for i = 1, math.min(12, #d) do shown[i] = d[i] end
        log(string.format("sweep %d: Spawner of node %s changed at %d place(s): %s", lvl.sweeps, tostring(rec.uid), #d, table.concat(shown, " ")))
      end
      rec.snap = now
      if (lvl.change_probes or 0) < P.CHANGE_PROBES and not rec.probed then rec.probed = true; guarded(P.probe, rec, "changed") end
    end
  end
  log(string.format("sweep %d: %d of %d Spawner(s) changed since the last read", lvl.sweeps, changed, #lvl.order))
end

-- ---- events ---------------------------------------------------------------------------------------
function P.on_spawn(f, ev)
  local lvl = P.lvl
  if not lvl then return end
  lvl.spawns = lvl.spawns + 1
  local h = math.tointeger(tonumber(f.SpawnedHandle)) or f.SpawnedHandle
  if lvl.spawns <= P.SPAWN_LOG then
    local text, a = P.describe(h)
    if a and a.asset_id then lvl.spawned_assets[a.asset_id] = tostring(a.asset_name or h) end
    local loc = math.tointeger(tonumber(f.SpawnLocation))
    local okl, lid = false, nil
    if loc and loc ~= 0 then okl, lid = pcall(rivet.uid, loc) end
    local fac = math.tointeger(tonumber(f.SpawnFactory))
    log(string.format("spawn %d: index %s location %s (uid %s); spawned %s", lvl.spawns, tostring(f.SpawnIndex), tostring(loc),
        tostring(okl and lid), text))
    if fac and fac ~= 0 then log(string.format("spawn %d: SpawnFactory %s", lvl.spawns, (P.describe(fac)))) end
  end
  if lvl.sweeps < P.SWEEPS_PER_LEVEL and (P.sweep_at == nil) and P.frame - (P.last_sweep or -10000) >= P.SWEEP_GAP then
    P.sweep_at = P.frame + 30
  end
end

function P.on_spawner_event(kind, f)
  local lvl = P.lvl
  local h = math.tointeger(tonumber(f.SpawnerComponentHandle))
  local rec = lvl and h and lvl.nodes[h]
  if not rec then return end
  if (lvl.events or 0) < 6 then
    lvl.events = (lvl.events or 0) + 1
    local now = read(rec.saddr, rec.ssize)
    local d = P.diff(rec.snap, now)
    local shown = {}
    for i = 1, math.min(12, #d) do shown[i] = d[i] end
    log(string.format("%s: SpawnerComponentHandle %X = node %s (its +0x%X); Spawner changed at %d place(s) since the index%s%s",
        kind, h, tostring(rec.uid), P.HANDLE_AT, #d, #shown > 0 and ": " or "", table.concat(shown, " ")))
    rec.snap = now or rec.snap
  end
  if not rec.probed and (lvl.change_probes or 0) < P.CHANGE_PROBES then
    rec.probed = true
    P.queue[#P.queue + 1] = function() guarded(P.probe, rec, kind) end
  end
end

function P.schedule(why)
  P.lvl = nil
  P.job = nil
  P.queue = {}
  P.sweep_at = nil
  P.index_at = P.frame + P.INDEX_DELAY
  P.index_why = why
end

local function run(fn)
  P.job = coroutine.create(fn)
end

function P.on_frame()
  P.frame = P.frame + 1
  P.t0 = clock()
  if P.job then
    local ok, err = coroutine.resume(P.job)
    if not ok then
      P.job = nil
      if tostring(err):find("budget", 1, true) then log("a step ran past the frame budget; it is dropped") else log("RANDO-ERROR", tostring(err)) end
    elseif coroutine.status(P.job) == "dead" then P.job = nil end
    return
  end
  local okr, ready = pcall(rivet.scene_ready)
  if okr and ready == false then return end
  if P.index_at and P.frame >= P.index_at then
    P.index_at = nil
    local why = P.index_why
    run(function() P.index(why) end)
    return
  end
  if #P.queue > 0 then run(table.remove(P.queue, 1)); return end
  if P.sweep_at and P.frame >= P.sweep_at then
    P.sweep_at = nil
    P.last_sweep = P.frame
    run(P.sweep)
  end
end

-- ---- wiring (rivet.on_event directly: this works whatever the randomizer's switches are) ------------
-- dev 10.21: the events come through the spawner layer's listeners (16_rando_spawners SP.listen): rivet_hook
-- allows 64 event callbacks in all and your dev 10.20 log hit that limit (PlanetChanged / Checkpoint lost)
if not P.subscribed then
  P.subscribed = true
  local SPL = RANDO_SPAWNERS
  if SPL and SPL.listen then
    SPL.listen("SpawnerSpawnEvent", P.on_spawn)
    SPL.listen("SpawnerStartedEvent", function(f) P.on_spawner_event("started", f) end)
    SPL.listen("SpawnerStoppedEvent", function(f) P.on_spawner_event("stopped", f) end)
    SPL.listen("LevelLoadedEvent", function() P.schedule("level loaded") end)
    SPL.listen("PlanetChangedEvent", function(f) if f.NewPlanetName then P.schedule("planet " .. tostring(f.NewPlanetName)) end end)
    SPL.listen("Checkpoint", function(cp) if cp.loaded then P.schedule("checkpoint loaded") end end)
  else
    log("16_rando_spawners.lua (with SP.listen) is missing: no events")
  end
  pcall(rivet.on_frame, P.on_frame)
end
P.schedule("scripts loaded")
log("v1 loaded: read-only spawner evidence (index after each load, spawned actors, changed Spawners, deep probes); remove the file to turn it off")
end)

-- ==== section: spawnproof (dev(spawnproof).lua) =====================================================================
DBG.section("spawnproof", function()
-- ---- dev(spawnproof).lua ----
-- DEVELOPER TOOL - not part of a release. SPAWN PROOF v6 (dev 10.26): controlled enemy replacements on Zurkon,
-- to prove (or disprove) in your game the mechanism the Enemy / Boss / Chaos Randomizers will use.
--
-- dev 10.27: ITS RESULT (round37: 6/6 factories, 20/20 spawns replaced) is now the Enemy Randomizer itself
-- (16_rando_spawners.lua section SP.V). This file STANDS DOWN - reads and writes nothing - while the Enemy Randomizer
-- is ON (both would write the same factory variables); with it OFF it runs as before.
--
-- WHAT YOUR DEV 10.24 LOG SHOWED (tests/data/round35_rivet.log, real game, v7 helper, SceneManager found):
--   * The arena's enemies are spawned by SunsetSpawnerFactory nodes (the SpawnerSpawnEvent's SpawnFactory). Each
--     factory node has its own script variables: "Templates" (3990217346 = rivet.hash "Templates"), "Locations"
--     (2501629366), sometimes "InitialCount" (2429945776), and itself (3368780241).
--   * Templates IS the enemy: the 11 arena factories of challenge A1 held 3 Templates values, and every factory
--     always spawned the same kind - Templates 1097446 -> enm_pirate_robot_sh (factories 1097948/49/53/57),
--     1097451 -> enm_pirate_robot_me (1097946/54/56), 1097452 -> enm_pirate_bladeball (1097947/51/52/55). The spawn's
--     SpawnLocation equals the factory's Locations value (1097957: 1097478 both).
--   * v4 never armed because it only swapped SpawnerScriptAction variables (Template / Factories); the factories
--     the Factories variables point at are not the ones the events name, and most factory spawns tie to no node.
-- v6 (dev 10.26, your dev 10.25 log round36): v5 armed a factory that had already spawned its 4 enemies and never
-- spawned again (each arena wave has its own factories). v6 only arms factories that have NOT spawned yet, all the
-- fresh factories of one enemy kind at once (one experiment = one kind -> one other kind), each verified on its own.
-- v5 added the FACTORY TEMPLATES ROUTE: it lists the level's SunsetSpawnerFactory nodes, reads each one's Templates
-- variable, learns from every factory spawn which enemy each Templates value makes, then writes ANOTHER learned
-- enemy Templates value (same role, another kind) into ONE factory's Templates variable (checked, read back), and
-- verifies the next spawn of every factory that uses that variable. Put back on the next level / checkpoint load.
--
-- WHY v3 DID NOTHING (your dev 10.23 log, tests/data/round34_rivet.log, real game): the planet fix worked ("level
-- reset (planet Zurkon): ON ZURKON - active", and the randomizer itself said scarstu), but the game folder still had
-- rando_give.dll v6: "no script variables: rando_give.dll is v6, v7 is needed". v7 was only in
-- rando_give_source/dev_build and had to be copied by hand; that one log line was the only sign. Since dev 10.24 the
-- kit's own rando_give.dll IS v7 (it ran in your game in round32), and v4 says it ON SCREEN, on every Zurkon level,
-- whenever it cannot work ("SPAWNPROOF BLOCKED: ...").
--
-- WHY v2 DID NOTHING AT ALL (your dev 10.22 log, tests/data/round33_rivet.log, real game): it loaded ("v2 loaded")
-- and then wrote not one more line. It only acted where RANDO.state.current_planet == "scarstu". The companion
-- started late, so every event waited in 10_rando_runtime's buffer of 500; the buffer filled on NefCity and the
-- PlanetChangedEvent to Zurkon was DROPPED ("replaying 500 event(s)", then only "RANDO-PLANET NefCity", and every
-- checkpoint on Zurkon logged "on nefarious_city"). v2 believed it was on NefCity and stayed silent, so the
-- Factories experiment never ran. v3:
--   * subscribes to PlanetChangedEvent and SpawnerSpawnEvent ITSELF (rivet.on_event, not buffered by the seed),
--     and decides "on Zurkon" from the event's own planet name (the randomizer's state only as a fallback);
--   * never stays silent: every level change logs where it thinks it is and why, and spawns it ignores are counted
--     and reported ("inactive: ...");
--   * shows ARMED and VERIFY on screen, so what you SEE in the game can be matched with the log.
-- (The kit's buffer was fixed too: planet / level / checkpoint / mission / item events are never dropped.)
--
-- WHY v1 NEVER ARMED (your dev 10.21 log, tests/data/round32_rivet.log, real game):
--   * v1 learned a template only from a node's "Template" variable. The Battleplex nodes that spawn ENEMIES have
--     none: their one variable is "Factories" (838143302 = rivet.hash "Factories", the DDL's SpawnerPrius
--     FactoryGroup), holding a SunsetSpawnerFactory node (handles 1087129..1087143 on Zurkon; the SpawnerSpawnEvent
--     SpawnFactory field names the same kind of actor). Their Spawner component says the same: +0x48 = the factory
--     handle, +0x50 (template) and +0x58 (location) = 0. The 104 nodes that do have a Template variable spawned
--     only rift portals (anomaly_portal_*). So "0 regular-enemy template(s) learned" in every scan.
--   * v1's jobs died on "ran past the 8 ms frame budget" (lines 101/133/272/400) during the fight: a budget error
--     outside a pcall ended the job and lost the spawns it was matching.
--   * v1 logged its first 12 spawns per level (the pub's bots and portals) and nothing of the challenges.
--
-- WHAT v2 DOES (only on Zurkon, only in memory, never saved, at most MAX_SWAPS per session):
--   1. Lists the level's SpawnerScriptAction nodes; reads each node's variable plugs (node +0x58 -> ScriptPlugs) and
--      its Spawner component (handle == node +0x60). A node's SLOT is its Template variable ("template") or, when it
--      has none, its Factories variable ("factory").
--   2. Ties every spawn to its node by the node's LastSpawn variable OR by the Spawner's slot list (+0x9C count,
--      +0xDC entries of 12 bytes { spawned handle, location handle, time }: real bytes of 9 nodes in your log).
--      A spawn with a SpawnFactory and no node is still learned for that factory.
--   3. Learns per slot value what it really spawned (actor name, bot family, role) and logs the first 40
--      enemy / boss spawns of each level in full, with each new factory's own variables (rivet.script_node).
--   4. ARM: a node whose slot holds ONE actor (not a group), whose variable no other node shares, whose value was
--      learned to spawn an enemy (or a boss), gets another learned value of the SAME kind and role that spawned
--      another actor. Written: the variable (uid +0x00, actors
--      +0x10; generation, type and value checked right before, read back after) and, if it holds the old value,
--      the Spawner's cached copy (+0x48 factory, +0x50 template). Only nodes not seen spawning on this level.
--   5. VERIFY on that node's next spawn: REPLACEMENT SPAWNED / ORIGINAL SPAWNED / SOMETHING ELSE.
--   6. PUT BACK when the node's Spawner stops, or on a level change (only what still holds what was written).
--   Every unit of work is guarded: a frame-budget error yields and retries on the next frame instead of ending it.
-- Every line starts with "RANDO-SPAWNPROOF". Remove this file and nothing of it runs.
-- (dev(spawnproof).lua's own kit stamp: dev(debug).lua carries one for all)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["spawnproof"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_SPAWNPROOF = RANDO_SPAWNPROOF or {}
local P = RANDO_SPAWNPROOF
P.version = 6
P.frame = P.frame or 0
P.ENABLED = true
P.PLANET = "scarstu"            -- Zurkon (Zurkie's Battleplex): replayable fights, nothing of the story
P.SCAN_EVERY = 120              -- frames between two listings of the level's nodes
P.NODE_LIMIT = 512
P.MAX_SWAPS = 4                 -- per session
P.MAX_ACTIVE = 2                -- armed at the same time
P.HELPER_MIN = 7                -- rando_give.dll v7 publishes the SceneManager
P.MB_SCENE = 0x128
P.SCENE_VARS = 0x75A0
P.VAR_SIZE = 0x40
P.VAR_TYPE_ACTORS = 5
P.GROUP_BIT = 0x80000000
P.SLICE = 0.0015
P.LEARN_LOG = 40                -- enemy / boss spawns logged in full per level
P.OTHER_LOG = 6                 -- other spawns (portals, props, NPCs) logged per level
P.FACTORY_LOG = 12              -- factories described per level
P.ROLES = { enemy = true, boss = true }
-- the Spawner component (432 bytes), measured on 9 nodes of your dev 10.21 log
P.SP_READ_AT, P.SP_READ_LEN = 0x40, 0x160
P.SP_FACTORY, P.SP_TEMPLATE, P.SP_LOCATION = 0x48, 0x50, 0x58
P.SP_COUNT, P.SP_SLOTS, P.SP_STRIDE, P.SP_SLOT_MAX = 0x9C, 0xDC, 12, 15

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNPROOF", ...) end
local function say(text) if RANDO and RANDO.say then pcall(RANDO.say, text, { type = "center", duration = 6 }) end end
P.log = log
local function clock() return (os and os.clock and os.clock()) or 0 end

-- ---- the engine's string hash (rivet_hook script_signal.cpp: reflected CRC-32, start 0xEDB88320) ----
local CRC = {}
for i = 0, 255 do
  local c = i
  for _ = 1, 8 do if c & 1 == 1 then c = (c >> 1) ~ 0xEDB88320 else c = c >> 1 end end
  CRC[i] = c
end
function P.hash(text)
  local c = 0xEDB88320
  for k = 1, #text do c = (c >> 8) ~ CRC[(text:byte(k) ~ c) & 0xFF] end
  return c
end
P.PLUG_TEMPLATE = P.hash("Template")      -- 1835115251
P.PLUG_LASTSPAWN = P.hash("LastSpawn")    -- 406637480
P.PLUG_LOCATION = P.hash("Location")      -- 2761897147
P.PLUG_FACTORIES = P.hash("Factories")    -- 838143302 (your dev 10.21 log: the arena's enemy nodes)
P.PLUG_TEMPLATES = P.hash("Templates")    -- 3990217346 (your dev 10.24 log: a SunsetSpawnerFactory's enemy)
P.PLUG_LOCATIONS = P.hash("Locations")    -- 2501629366
P.FACTORY_CLASS = "SunsetSpawnerFactoryScriptAction"
P.AFTER_LOG = 6                 -- spawns of an armed factory logged after its VERIFY
P.PLUG_NAMES = {}
for _, n in ipairs({ "Template", "LastSpawn", "Location", "Factories", "MaxAlive", "NumSpawns", "OnSpawned", "OnAllSpawned",
                    "Templates", "Locations", "InitialCount" }) do
  P.PLUG_NAMES[P.hash(n)] = n
end
local function plug_name(h) return P.PLUG_NAMES[h] or tostring(h) end

-- ---- bytes ---------------------------------------------------------------------------------------
local function bytes_of(text)
  local t = {}
  for x in tostring(text or ""):gmatch("%x%x") do t[#t + 1] = tonumber(x, 16) end
  return t
end
local function u16(b, i) if not b[i + 1] then return nil end return b[i] + b[i + 1] * 0x100 end
local function u32(b, i)
  if not b[i + 3] then return nil end
  return b[i] + b[i + 1] * 0x100 + b[i + 2] * 0x10000 + b[i + 3] * 0x1000000
end
local function hex64(b, i)
  if not b[i + 7] then return nil end
  return string.format("%02X%02X%02X%02X%02X%02X%02X%02X", b[i + 7], b[i + 6], b[i + 5], b[i + 4], b[i + 3], b[i + 2], b[i + 1], b[i])
end
local function ptr64(b, i)
  local h = hex64(b, i)
  if not h or h:sub(1, 1):match("[89A-F]") then return nil end
  return tonumber(h, 16)
end
local function valid_ptr(p) return p ~= nil and p > 0x10000 and p < 0x7FFFFFFFFFFF and p % 8 == 0 end
local function le(hex16) local t = {} for k = 15, 1, -2 do t[#t + 1] = hex16:sub(k, k + 1) end return table.concat(t, " ") end
local function le32(v) return string.format("%02X %02X %02X %02X", v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF) end
P.bytes_of, P.u32, P.hex64, P.le = bytes_of, u32, hex64, le

local function read(addr, len)
  if not (addr and addr > 0x10000) then return nil end
  local ok, text = pcall(rivet.read, string.format("%X", addr), len)
  if not ok or not text then return nil end
  local b = bytes_of(text)
  if #b < len then return nil end
  return b
end
P.read = read

-- one unit of work: a frame-budget error yields (the job goes on next frame) and retries, up to 3 times
local function guard(fn, ...)
  for _ = 1, 3 do
    local res = table.pack(pcall(fn, ...))
    if res[1] then return table.unpack(res, 2, res.n) end
    local err = tostring(res[2])
    if not err:find("frame budget", 1, true) then error(err, 0) end
    P.budget_hits = (P.budget_hits or 0) + 1
    if coroutine.isyieldable() then coroutine.yield() else return nil end
  end
  return nil
end
P.guard = guard
local function pace(t0)
  if clock() - t0 > P.SLICE and coroutine.isyieldable() then coroutine.yield(); return clock() end
  return t0
end

-- ---- the SceneManager and its script variables ------------------------------------------------------
function P.scene()
  local rr = RANDO_REAL
  local n = rr and rr.native
  if not (n and n.addr) then return nil, "rando_give.dll is not answering" end
  local hb = read(n.addr, 0x10)
  local ver = hb and u32(hb, 9)
  if not ver or ver < P.HELPER_MIN then return nil, "rando_give.dll is v" .. tostring(ver) .. ", v" .. P.HELPER_MIN .. " is needed (copy the kit's)" end
  local mb = read(n.addr + P.MB_SCENE, 0x0C)
  local scene, sigs = mb and ptr64(mb, 1), mb and u32(mb, 9)
  if not valid_ptr(scene) then return nil, "rando_give.dll found no SceneManager (signature matched " .. tostring(sigs) .. "x, exactly 1 needed)" end
  local sb = read(scene + P.SCENE_VARS, 0x20)
  local base, max = sb and ptr64(sb, 1), sb and u32(sb, 0x1D)
  if not (valid_ptr(base) and max and max > 0 and max < 0x100000) then
    return nil, string.format("SceneManager %X: no script variable array (%s, max %s)", scene, tostring(base), tostring(max))
  end
  return { scene = scene, base = base, max = max, sigs = sigs }
end

-- one variable: nil and why, or { addr, uid, actors, type, gen, single } (checked against the plug's generation)
function P.var(sc, idx, gen)
  if not (sc and idx and gen) or gen == 0 or idx >= sc.max then return nil, "no such variable" end
  local addr = sc.base + idx * P.VAR_SIZE
  local b = read(addr, P.VAR_SIZE)
  if not b then return nil, "unreadable" end
  local v = { addr = addr, uid = hex64(b, 1), actors = u32(b, 0x11), type = u16(b, 0x35), gen = u16(b, 0x37) }
  if v.gen ~= gen then return nil, string.format("generation %s, the plug says %s", tostring(v.gen), tostring(gen)) end
  v.single = v.type == P.VAR_TYPE_ACTORS and v.actors ~= 0 and (v.actors & P.GROUP_BIT) == 0
  return v
end

-- a node's variable plugs: { spawner (+0x60), uid, vars = { [plug] = { idx, gen } }, order = { plug... } }
function P.plugs_of(addr)
  local nb = read(addr, 0x80)
  if not nb then return nil, "node unreadable" end
  local plugs = ptr64(nb, 0x59)
  if not valid_ptr(plugs) then return nil, "no plug block" end
  local hb = read(plugs, 0x28)
  if not hb then return nil, "plug block unreadable" end
  local var_ptr, n = ptr64(hb, 9), hb[0x1B]
  local out = { spawner = u32(nb, 0x61), uid = hex64(nb, 0x49), vars = {}, order = {}, nvars = n or 0 }
  if not n or n == 0 then return out end
  if not (var_ptr and var_ptr > 0x10000) or n > 32 then return nil, "variable plugs unreadable" end
  local vb = read(var_ptr, n * 8)
  if not vb then return nil, "variable plugs unreadable" end
  for k = 0, n - 1 do
    local plug = u32(vb, k * 8 + 1)
    out.vars[plug] = { idx = u16(vb, k * 8 + 5), gen = u16(vb, k * 8 + 7) }
    out.order[#out.order + 1] = plug
  end
  return out
end

-- the Spawner component's cached factory / template / location and its spawn slots
function P.spawner_state(saddr)
  local b = saddr and read(saddr + P.SP_READ_AT, P.SP_READ_LEN)
  if not b then return nil end
  local at = function(off) return u32(b, off - P.SP_READ_AT + 1) end
  local st = { factory = at(P.SP_FACTORY), template = at(P.SP_TEMPLATE), location = at(P.SP_LOCATION), count = at(P.SP_COUNT), slots = {} }
  local n = math.min(st.count or 0, P.SP_SLOT_MAX)
  for i = 0, n - 1 do
    local h = at(P.SP_SLOTS + i * P.SP_STRIDE)
    if h and h ~= 0 then st.slots[#st.slots + 1] = { spawned = h, location = at(P.SP_SLOTS + i * P.SP_STRIDE + 4) } end
  end
  return st
end

-- ---- actors --------------------------------------------------------------------------------------
function P.actor(h)
  if not h or h == 0 then return nil end
  local a = { handle = h }
  if rivet.name then local ok, n = pcall(rivet.name, h); if ok then a.name = n end end
  local oku, uid = pcall(rivet.uid, h); a.uid = oku and uid or nil
  local SPL = RANDO_SPAWNERS
  if SPL and SPL.classify_actor then
    local okc, fam, cls = pcall(SPL.classify_actor, h, true)
    if okc and fam then a.family, a.class, a.role = fam, cls, SPL.ROLE_OF_FAMILY and SPL.ROLE_OF_FAMILY[fam] end
  end
  return a
end
local function who(a)
  if not a then return "none" end
  return string.format("%s (handle %s, %s/%s)", tostring(a.name), tostring(a.handle), tostring(a.family), tostring(a.class))
end
P.who = who
local function short(name)
  local n = tostring(name):match("([^\\]+)$") or tostring(name)
  return (n:gsub("%.actor$", ""):gsub("%.a$", ""))
end
P.short = short
local function norm_uid(u)
  if type(u) ~= "string" or not u:match("^%x+$") or #u > 16 then return nil end
  return string.rep("0", 16 - #u) .. u:upper()
end

-- a factory actor, said once per level: its classes and its own node's variables (rivet.script_node)
function P.describe_factory(lvl, fac)
  if not fac or fac == 0 or lvl.described[fac] then return end
  lvl.described[fac] = true
  if lvl.ndescribed >= P.FACTORY_LOG then return end
  lvl.ndescribed = lvl.ndescribed + 1
  local okl, names = pcall(rivet.components, fac)
  local classes = (okl and type(names) == "table") and table.concat(names, ",", 1, math.min(#names, 6)) or "?"
  local vars = {}
  for _, cls in ipairs({ "SunsetSpawnerFactoryScriptAction", "SpawnerFactoryScriptAction" }) do
    local okc, c = pcall(rivet.component, fac, cls)
    if okc and type(c) == "table" and c.handle and rivet.script_node then
      local okn, t = pcall(rivet.script_node, c.handle, false)
      if okn and type(t) == "table" then
        for _, v in ipairs(type(t.vars) == "table" and t.vars or {}) do
          local val = v.value
          if type(val) == "table" then
            local hs = {}
            for i = 1, math.min(4, #val) do hs[i] = tostring(val[i]) end
            val = string.format("{%s}%s", table.concat(hs, ","), val.group and " group" or "")
          end
          vars[#vars + 1] = tostring(v.plug_name or plug_name(v.plug or 0)) .. ":" .. tostring(v.type) .. "=" .. tostring(val)
          if #vars >= 8 then break end
        end
        vars[#vars + 1] = "outputs " .. tostring(#(t.outputs or {}))
      end
      break
    end
  end
  log(string.format("factory %s: classes %s; node variables %s", tostring(fac), classes, #vars > 0 and table.concat(vars, ", ") or "-"))
end

-- ---- the level --------------------------------------------------------------------------------------
-- where you are: the last PlanetChangedEvent this file saw itself (not buffered), else the randomizer's state
P.ZURKON_EVENT_NAME = "Zurkon"
local function state_planet()
  local s = RANDO and RANDO.state
  return s and s.current_planet
end
local function planet()
  if P.event_planet then return P.event_planet == P.ZURKON_EVENT_NAME and P.PLANET or ("event:" .. P.event_planet) end
  return state_planet()
end
P.planet = planet
function P.where()
  return string.format("event planet %s, randomizer state %s", tostring(P.event_planet), tostring(state_planet()))
end

P.swaps = P.swaps or 0
P.armed = P.armed or {}
P.spawn_queue = {}

function P.reset(why)
  for _, A in ipairs(P.armed) do
    if not A.restored then
      P.put_back(A, "level changed: " .. tostring(why))
      if not A.verified then P.swaps = math.max(0, P.swaps - 1) end
    end
  end
  if P.lvl and P.lvl.scans > 0 then P.summary() end
  P.armed = {}
  P.lvl = { nodes = {}, order = {}, scans = 0, learned = { template = {}, factory = {}, ftemplate = {} }, logged = 0, other = 0,
            factories = {}, forder = {}, fvar_users = {},
            described = {}, ndescribed = 0, stopped = {}, why = why, untied = 0, ties = 0, ignored = 0 }
  log(string.format("level reset (%s): %s (%s)", tostring(why), planet() == P.PLANET and "ON ZURKON - active" or "not Zurkon - inactive", P.where()))
  P.spawn_queue = {}
  P.next_scan = P.frame + P.SCAN_EVERY
end


-- one new node: plugs, Spawner, slot
function P.read_node(node)
  local okc, c = pcall(rivet.component, node.actor, "SpawnerScriptAction")
  local addr = okc and type(c) == "table" and c.handle == node.component and c.address and tonumber(c.address, 16)
  local pl = addr and P.plugs_of(addr)
  local rec = { component = node.component, actor = node.actor, uid = node.uid, addr = addr, plugs = pl }
  if pl then
    rec.spawner, rec.last = pl.spawner, pl.vars[P.PLUG_LASTSPAWN]
    if pl.vars[P.PLUG_TEMPLATE] then
      rec.slot = { kind = "template", var = pl.vars[P.PLUG_TEMPLATE], plug = P.PLUG_TEMPLATE, cache = P.SP_TEMPLATE }
    elseif pl.vars[P.PLUG_FACTORIES] then
      rec.slot = { kind = "factory", var = pl.vars[P.PLUG_FACTORIES], plug = P.PLUG_FACTORIES, cache = P.SP_FACTORY }
    end
    local oks, s = pcall(rivet.component, node.actor, "Spawner")
    if oks and type(s) == "table" and s.handle == pl.spawner and s.address then rec.saddr = tonumber(s.address, 16) end
  end
  return rec
end

function P.scan()
  local lvl = P.lvl
  if not lvl then return end
  local sc, why = P.scene()
  if not sc then
    if not lvl.blocked_said then
      lvl.blocked_said = true
      log("BLOCKED: no script variables:", why)
      say("SPAWNPROOF BLOCKED: " .. tostring(why))
    end
    return
  end
  if not P.scene_logged then
    P.scene_logged = true
    log(string.format("SceneManager %X (signature matched %s x), script variables at %X, max %d", sc.scene, tostring(sc.sigs), sc.base, sc.max))
  end
  local list = guard(function()
    local ok, l = pcall(rivet.script_nodes, "SpawnerScriptAction", P.NODE_LIMIT)
    if ok and type(l) == "table" then return l end
    if not ok then error(l, 0) end
  end)
  if type(list) ~= "table" then return end
  lvl.scans = lvl.scans + 1
  local new, t0 = 0, clock()
  for _, node in ipairs(list) do
    if node.component and not lvl.nodes[node.component] then
      local rec = guard(P.read_node, node)
      if rec then
        lvl.nodes[node.component] = rec
        lvl.order[#lvl.order + 1] = node.component
        new = new + 1
      end
      t0 = pace(t0)
    end
  end
  if new > 0 then
    local users, kinds = {}, { template = 0, factory = 0, none = 0 }
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      if r.slot then users[r.slot.var.idx] = (users[r.slot.var.idx] or 0) + 1 end
    end
    local single, groups, shared, last, sp = 0, 0, 0, 0, 0
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      kinds[r.slot and r.slot.kind or "none"] = kinds[r.slot and r.slot.kind or "none"] + 1
      if r.last then last = last + 1 end
      if r.saddr then sp = sp + 1 end
      if r.slot then
        r.shared = users[r.slot.var.idx] > 1
        if r.shared then shared = shared + 1 end
        local v = guard(P.var, sc, r.slot.var.idx, r.slot.var.gen)
        if v and v.single then single = single + 1 elseif v and v.actors ~= 0 then groups = groups + 1 end
      end
      t0 = pace(t0)
    end
    log(string.format("scan %d on %s: %d node(s) (%d new): %d Template, %d Factories, %d neither; slots holding one actor %d, groups %d, shared %d; %d with LastSpawn, %d Spawner(s) read",
        lvl.scans, tostring(planet()), #lvl.order, new, kinds.template, kinds.factory, kinds.none, single, groups, shared, last, sp))
  end
  P.scan_factories(sc)
end

-- v5: every SunsetSpawnerFactory node of the level and its Templates variable (also the ones not spawned yet)
function P.scan_factories(sc)
  local lvl = P.lvl
  local list = guard(function()
    local ok, l = pcall(rivet.script_nodes, P.FACTORY_CLASS, P.NODE_LIMIT)
    if ok and type(l) == "table" then return l end
    if not ok then error(l, 0) end
  end)
  if type(list) ~= "table" then return end
  local before, t0 = #lvl.forder, clock()
  for _, node in ipairs(list) do
    if node.actor and lvl.factories[node.actor] == nil then guard(P.factory_rec, lvl, node.actor) end
    t0 = pace(t0)
  end
  if #lvl.forder > before then
    local values, nvals = {}, 0
    for _, fac in ipairs(lvl.forder) do
      local fr = lvl.factories[fac]
      local v = fr and guard(P.var, sc, fr.slot.var.idx, fr.slot.var.gen)
      if v and v.single then
        if not values[v.actors] then nvals = nvals + 1; values[v.actors] = 0 end
        values[v.actors] = values[v.actors] + 1
      end
    end
    local parts = {}
    for val, n in pairs(values) do parts[#parts + 1] = string.format("%d x%d", val, n) end
    table.sort(parts)
    log(string.format("factories on %s: %d with a Templates variable (%d new); %d Templates value(s): %s", tostring(planet()), #lvl.forder,
        #lvl.forder - before, nvals, table.concat(parts, ", ", 1, math.min(#parts, 12))))
  end
end

-- the node that made each spawn: its LastSpawn variable (one 64-byte read a node) first; the Spawner's slot list
-- (one read of its component) only for spawns still not found
function P.tie(sc, wanted)
  local lvl, found, t0 = P.lvl, {}, clock()
  local left = 0
  for _ in pairs(wanted) do left = left + 1 end
  for pass = 1, 2 do
    for _, k in ipairs(lvl.order) do
      if left == 0 then return found end
      local r = lvl.nodes[k]
      guard(function()
        if pass == 1 and r.last then
          local lv = P.var(sc, r.last.idx, r.last.gen)
          if lv and lv.actors and wanted[lv.actors] and not found[lv.actors] then found[lv.actors] = { rec = r, via = "LastSpawn" }; left = left - 1 end
        elseif pass == 2 and r.saddr then
          local st = P.spawner_state(r.saddr)
          r.state = st
          for _, s in ipairs(st and st.slots or {}) do
            if wanted[s.spawned] and not found[s.spawned] then found[s.spawned] = { rec = r, via = "Spawner slot" }; left = left - 1 end
          end
        end
      end)
      t0 = pace(t0)
    end
  end
  return found
end

-- what a value made: never overwritten with nil (an actor already gone answers nil); two kinds = MIXED
local function note(x, a)
  if a.name then
    if x.name and x.name ~= a.name then x.mixed = true end
    x.name = a.name
  end
  if a.role then x.role, x.family, x.class = a.role, a.family, a.class end
  x.count = (x.count or 0) + 1
end
P.note = note

-- one SunsetSpawnerFactory node (the actor the SpawnerSpawnEvent's SpawnFactory names): its Templates variable
function P.factory_rec(lvl, fac)
  if not fac or fac == 0 then return nil end
  local fr = lvl.factories[fac]
  if fr ~= nil then return fr or nil end
  local okc, c = pcall(rivet.component, fac, P.FACTORY_CLASS)
  local addr = okc and type(c) == "table" and c.address and tonumber(c.address, 16)
  local pl = addr and P.plugs_of(addr)
  local tv = pl and pl.vars[P.PLUG_TEMPLATES]
  if not tv then lvl.factories[fac] = false; return nil end
  fr = { uid = "factory " .. tostring(fac), fac = fac, addr = addr, plugs = pl, component = c.handle,
         slot = { kind = "ftemplate", var = tv, plug = P.PLUG_TEMPLATES, cache = 0 } }
  lvl.factories[fac] = fr
  lvl.forder[#lvl.forder + 1] = fac
  lvl.fvar_users[tv.idx] = (lvl.fvar_users[tv.idx] or 0) + 1
  return fr
end

-- the armed record whose variable this factory uses (factories can share one Templates variable)
function P.armed_of_factory(fr)
  for _, A in ipairs(P.armed) do
    if not A.restored and A.slot.kind == "ftemplate" and A.slot.var.idx == fr.slot.var.idx then return A end
  end
  return nil
end

function P.learn(batch)
  local lvl = P.lvl
  local sc = P.scene()
  if not (lvl and sc) then return end
  local wanted = {}
  for _, e in ipairs(batch) do wanted[e.h] = e end
  local found = P.tie(sc, wanted)
  local t0 = clock()
  for _, e in ipairs(batch) do
    guard(function()
      local a = P.actor(e.h)
      local t = found[e.h]
      local r = t and t.rec
      local interesting = a and P.ROLES[a.role or ""]
      local kind, value, v
      if r and r.slot then
        v = P.var(sc, r.slot.var.idx, r.slot.var.gen)
        kind = r.slot.kind
        if kind == "factory" and e.fac and e.fac ~= 0 then value = e.fac          -- the factory the game used
        elseif v and v.single then value = v.actors
        elseif r.state then value = r.state[kind] end                             -- the Spawner's cached copy
      elseif e.fac and e.fac ~= 0 then
        kind, value = "factory", e.fac
      end
      if r then lvl.ties = lvl.ties + 1; r.spawned = (r.spawned or 0) + 1 else lvl.untied = lvl.untied + 1 end
      local mine = r and P.armed_of(r)
      if kind and value and value ~= 0 and a and a.name and not mine then
        local L = lvl.learned[kind]
        local x = L[value] or { handle = value, kind = kind, count = 0 }
        if v and v.single and v.actors == value then x.uid = v.uid end
        if not x.uid and kind == "factory" then local oku, u = pcall(rivet.uid, value); x.uid = oku and norm_uid(u) or nil end
        note(x, a)
        L[value] = x
      end
      if kind == "factory" then P.describe_factory(lvl, value) end
      -- v5: the factory's own Templates variable
      local fnote, fA = "", nil
      local fr = e.fac and e.fac ~= 0 and P.factory_rec(lvl, e.fac)
      if fr then
        fr.spawned = (fr.spawned or 0) + 1
        local fv = P.var(sc, fr.slot.var.idx, fr.slot.var.gen)
        fA = P.armed_of_factory(fr)
        if fv and fv.single then
          fnote = string.format("; factory Templates = %d", fv.actors)
          if a and not fA then
            local x = lvl.learned.ftemplate[fv.actors] or { handle = fv.actors, kind = "ftemplate", count = 0 }
            x.uid = fv.uid
            note(x, a)
            lvl.learned.ftemplate[fv.actors] = x
          end
        elseif fv then
          fnote = string.format("; factory Templates variable %08X (not one actor)", fv.actors or 0)
        end
      end
      local say = (interesting and lvl.logged < P.LEARN_LOG) or (not interesting and lvl.other < P.OTHER_LOG)
      if mine then say = true end
      if fA then
        fA.after = (fA.after or 0) + 1
        say = say or fA.after <= P.AFTER_LOG
      end
      if say then
        if interesting then lvl.logged = lvl.logged + 1 else lvl.other = lvl.other + 1 end
        log(string.format("spawn %s (SpawnFactory %s, location %s): %s; slot %s = %s%s%s; spawned %s%s",
            tostring(e.h), tostring(e.fac), tostring(e.loc),
            r and string.format("node %s via %s", tostring(r.uid), t.via) or "no node",
            kind or "none", tostring(value), v and (v.single and "" or string.format(" (variable %08X)", v.actors or 0)) or "",
            fnote, who(a), fA and string.format(" [ARMED factory variable, spawn %d since]", fA.after) or ""))
      end
      if mine and not mine.verified then P.verify(mine, a, e) end
      if fA and not fA.verified then P.verify(fA, a, e) end
    end)
    t0 = pace(t0)
  end
end

function P.armed_of(r)
  for _, A in ipairs(P.armed) do if A.rec == r and not A.restored then return A end end
  return nil
end

-- ---- arm, verify, put back ------------------------------------------------------------------------------
function P.try_arm()
  local lvl = P.lvl
  if not (P.ENABLED and lvl) or P.swaps >= P.MAX_SWAPS or planet() ~= P.PLANET then return end
  local active = 0
  for _, A in ipairs(P.armed) do if not A.restored then active = active + 1 end end
  if active >= P.MAX_ACTIVE then return end
  local sc = P.scene()
  if not sc then return end
  local pool = { template = {}, factory = {}, ftemplate = {} }
  local counts = {}
  for kind, L in pairs(lvl.learned) do
    for _, x in pairs(L) do
      if P.ROLES[x.role or ""] and not x.mixed then
        pool[kind][#pool[kind] + 1] = x
        counts[#counts + 1] = kind .. " " .. tostring(x.handle) .. "=" .. tostring(x.name):match("([^\\]+)$")
      end
    end
    table.sort(pool[kind], function(a, b) return a.handle < b.handle end)
  end
  local why = string.format("%d template(s), %d factory(ies), %d factory Templates value(s) learned spawning an enemy or boss on this level%s",
      #pool.template, #pool.factory, #pool.ftemplate, #counts > 0 and (" (" .. table.concat(counts, ", ", 1, math.min(#counts, 8)) .. ")") or "")
  if why ~= lvl.waiting_said then lvl.waiting_said = why; log("learned: " .. why) end
  -- v5: the factory Templates route first (the one your dev 10.24 log points at)
  if P.try_arm_factory(sc, pool.ftemplate) then return end
  if #pool.template < 2 and #pool.factory < 2 then return end
  local best
  local t0 = clock()
  for _, k in ipairs(lvl.order) do
    local r = lvl.nodes[k]
    if r.slot and not r.shared and (r.spawned or 0) == 0 and not lvl.stopped[r.spawner or -1] and not P.armed_of(r) and not r.tried
        and #pool[r.slot.kind] >= 2 then
      local v = guard(P.var, sc, r.slot.var.idx, r.slot.var.gen)
      local orig = v and v.single and lvl.learned[r.slot.kind][v.actors]
      if orig and P.ROLES[orig.role or ""] and not orig.mixed then
        for _, rep in ipairs(pool[r.slot.kind]) do
          if rep.handle ~= v.actors and rep.name ~= orig.name and rep.role == orig.role and (rep.uid or v.uid == "0000000000000000") then
            best = { r = r, v = v, orig = orig, rep = rep }
            break
          end
        end
      end
    end
    if best then break end
    t0 = pace(t0)
  end
  if best then P.arm(sc, best.r, best.v, best.orig, best.rep) end
end

-- dev 10.26 (your dev 10.25 log, round36): v5 armed factory 1109878 AFTER its 4 spawns, and it never spawned again:
-- in the arena every wave has its own factories, each spawning once per wave. So a spent factory is never chosen now.
-- One EXPERIMENT = one enemy kind -> one other kind: every factory NOT YET SPAWNED on this level whose Templates holds
-- the original (up to P.EXP_FACTORIES) gets the replacement's value; each verifies on its own first spawn.
P.EXP_FACTORIES = 8
P.MAX_EXPERIMENTS = 3
function P.try_arm_factory(sc, pool)
  local lvl = P.lvl
  for _, A in ipairs(P.armed) do
    if not A.restored and A.slot.kind == "ftemplate" then return true end     -- one experiment at a time
  end
  if (P.experiments or 0) >= P.MAX_EXPERIMENTS or #pool < 2 then return false end
  -- the original kind with the most fresh factories, and a replacement of the same role and another kind
  local fresh_by_value = {}
  for _, fac in ipairs(lvl.forder) do
    local fr = lvl.factories[fac]
    if fr and not fr.tried and (fr.spawned or 0) == 0 then
      local v = guard(P.var, sc, fr.slot.var.idx, fr.slot.var.gen)
      if v and v.single then
        local list = fresh_by_value[v.actors] or {}
        list[#list + 1] = { fr = fr, v = v }
        fresh_by_value[v.actors] = list
      end
    end
  end
  local best
  for value, list in pairs(fresh_by_value) do
    local orig = lvl.learned.ftemplate[value]
    if orig and P.ROLES[orig.role or ""] and not orig.mixed then
      for _, x in ipairs(pool) do
        if x.handle ~= value and x.name ~= orig.name and x.role == orig.role and (x.uid or list[1].v.uid == "0000000000000000") then
          if not best or #list > #best.list then best = { orig = orig, rep = x, list = list } end
          break
        end
      end
    end
  end
  if not best then
    local why = "no factory that has not spawned yet holds a learned enemy"
    if why ~= lvl.fwait_said then lvl.fwait_said = why; log("factory route waiting: " .. why) end
    return false
  end
  P.experiments = (P.experiments or 0) + 1
  local n = math.min(#best.list, P.EXP_FACTORIES)
  local facs = {}
  for i = 1, n do facs[i] = tostring(best.list[i].fr.fac) end
  log(string.format("EXPERIMENT %d: %s -> %s on %d factory(ies) that have not spawned yet: %s", P.experiments,
      tostring(best.orig.name), tostring(best.rep.name), n, table.concat(facs, ", ")))
  P.quiet_arm = 0
  for i = 1, n do P.arm(sc, best.list[i].fr, best.list[i].v, best.orig, best.rep) end
  return true
end

function P.arm(sc, r, v, orig, rep)
  r.tried = true
  local slot = r.slot
  local now = P.var(sc, slot.var.idx, slot.var.gen)
  if not (now and now.actors == v.actors and now.uid == v.uid) then log("not armed: the variable changed while it was checked"); return end
  local new_uid = (now.uid == "0000000000000000") and now.uid or rep.uid
  local okw1 = pcall(rivet.write, string.format("%X", now.addr), le(new_uid))
  local okw2 = pcall(rivet.write, string.format("%X", now.addr + 0x10), le32(rep.handle))
  local back = P.var(sc, slot.var.idx, slot.var.gen)
  local cache = "no Spawner"
  local cache_written = false
  if r.saddr then
    local cb = read(r.saddr + slot.cache, 4)
    local cur = cb and u32(cb, 1)
    if cur == v.actors then
      pcall(rivet.write, string.format("%X", r.saddr + slot.cache), le32(rep.handle))
      local cb2 = read(r.saddr + slot.cache, 4)
      cache_written = cb2 and u32(cb2, 1) == rep.handle
      cache = string.format("Spawner +0x%X %s -> %s %s", slot.cache, tostring(cur), tostring(rep.handle), cache_written and "OK" or "FAILED")
    else
      cache = string.format("Spawner +0x%X holds %s (not activated yet): left alone", slot.cache, tostring(cur))
    end
  end
  if slot.kind ~= "ftemplate" then P.swaps = P.swaps + 1 end
  local function copy(t) local c = {} for k, x in pairs(t) do c[k] = x end return c end
  local A = { rec = r, slot = slot, orig = copy(orig), rep = copy(rep), orig_uid = v.uid, orig_handle = v.actors, new_uid = new_uid,
              cache_written = cache_written, frame = P.frame, spawned_before = r.spawned or 0 }
  P.armed[#P.armed + 1] = A
  local ok = okw1 and okw2 and back and back.uid == new_uid and back.actors == rep.handle
  log(string.format("ARMED %d/%d node %s (Spawner %X, %s, spawned %d time(s) so far): %s variable %d at %X: %s -> %s; read back %s; %s",
      P.swaps, P.MAX_SWAPS, tostring(r.uid), r.spawner or 0, slot.kind, A.spawned_before, plug_name(slot.plug), slot.var.idx, now.addr,
      who(orig), who(rep), ok and "OK" or "FAILED", cache))
  if ok and (slot.kind ~= "ftemplate" or (P.quiet_arm or 0) == 0) then
    P.quiet_arm = (P.quiet_arm or 0) + 1
    say(string.format("SPAWNPROOF ARMED: %s should now come as %s", short(orig.name), short(rep.name)))
  end
  if not ok then A.verified = true; P.put_back(A, "the write did not read back") end
end

function P.verify(A, a, e)
  A.verified = true
  local verdict
  if a and a.name == A.rep.name then verdict = "REPLACEMENT SPAWNED"
  elseif a and a.name == A.orig.name then verdict = "ORIGINAL SPAWNED (the write had no effect on this spawn)"
  else verdict = "SOMETHING ELSE SPAWNED" end
  log(string.format("VERIFY node %s (%s, SpawnFactory %s): requested %s; original %s; spawned %s: %s", tostring(A.rec.uid), A.slot.kind,
      tostring(e and e.fac), who(A.rep), who(A.orig), who(a), verdict))
  A.verdict = verdict
  P.said_verdicts = (P.said_verdicts or 0) + 1
  if P.said_verdicts <= 3 then
    say("SPAWNPROOF: " .. verdict:match("^[A-Z ]+"):gsub("%s+$", "") .. " (" .. (a and a.name and short(a.name) or "?") .. ")")
  end
  P.verdicts = P.verdicts or {}
  P.verdicts[#P.verdicts + 1] = verdict
  -- a factory that ignored the write is put back at once, so another (fresh) factory can be tried in this fight
  if A.slot.kind == "ftemplate" and not verdict:find("REPLACEMENT", 1, true) then P.put_back(A, "not replaced") end
end

function P.put_back(A, why)
  if not A or A.restored then return end
  A.restored = true
  local sc = P.scene()
  local v = sc and P.var(sc, A.slot.var.idx, A.slot.var.gen)
  local parts = {}
  if v and v.uid == A.new_uid and v.actors == A.rep.handle then
    pcall(rivet.write, string.format("%X", v.addr), le(A.orig_uid))
    pcall(rivet.write, string.format("%X", v.addr + 0x10), le32(A.orig_handle))
    local back = P.var(sc, A.slot.var.idx, A.slot.var.gen)
    parts[#parts + 1] = "variable " .. ((back and back.actors == A.orig_handle and back.uid == A.orig_uid) and "OK" or "FAILED")
  else
    parts[#parts + 1] = "variable skipped (it no longer holds what was written)"
  end
  if A.cache_written and A.rec.saddr then
    local cb = read(A.rec.saddr + A.slot.cache, 4)
    if cb and u32(cb, 1) == A.rep.handle then
      pcall(rivet.write, string.format("%X", A.rec.saddr + A.slot.cache), le32(A.orig_handle))
      parts[#parts + 1] = "Spawner copy put back"
    else
      parts[#parts + 1] = "Spawner copy changed by the game: left alone"
    end
  end
  log(string.format("put back (%s): node %s %s = %s: %s", tostring(why), tostring(A.rec.uid), A.slot.kind, tostring(A.orig_handle), table.concat(parts, "; ")))
  if A.slot.kind == "ftemplate" and P.said_putback ~= P.experiments then
    P.said_putback = P.experiments
    say("SPAWNPROOF: put back (" .. tostring(why) .. ")")
  end
end

function P.summary()
  local lvl = P.lvl
  local L = {}
  for kind, t in pairs(lvl.learned) do
    for _, x in pairs(t) do
      L[#L + 1] = string.format("%s %s x%d %s/%s %s%s", kind, tostring(x.handle), x.count, tostring(x.family), tostring(x.role),
          tostring(x.name):match("([^\\]+)$") or "?", x.mixed and " (MIXED)" or "")
      if #L >= 16 then break end
    end
  end
  log(string.format("level summary (%s): %d node(s), %d spawn(s) tied, %d not tied, %d budget retries; learned: %s; verdicts: %s",
      tostring(lvl.why), #lvl.order, lvl.ties, lvl.untied, P.budget_hits or 0, #L > 0 and table.concat(L, " | ") or "-",
      P.verdicts and table.concat(P.verdicts, " | ") or "-"))
end

-- ---- events (through the spawner layer: no rivet callback of its own) ------------------------------------
function P.on_spawn(f)
  local h = math.tointeger(tonumber(f.SpawnedHandle))
  if not (h and P.lvl) then return end
  if P.seen_spawn[h] then return end                        -- direct and buffered deliveries of the same spawn
  P.seen_spawn[h] = true
  if planet() ~= P.PLANET then
    P.lvl.ignored = P.lvl.ignored + 1
    if P.lvl.ignored == 1 or P.lvl.ignored == 50 then
      log(string.format("inactive: %d spawn(s) ignored on this level - not Zurkon (%s)", P.lvl.ignored, P.where()))
    end
    return
  end
  if #P.spawn_queue < 256 then
    P.spawn_queue[#P.spawn_queue + 1] = { h = h, fac = math.tointeger(tonumber(f.SpawnFactory)), loc = math.tointeger(tonumber(f.SpawnLocation)) }
  end
end
P.seen_spawn = P.seen_spawn or {}
function P.on_planet(f)
  if f.NewPlanetName then
    P.event_planet = tostring(f.NewPlanetName)
    P.seen_spawn = {}
    P.reset("planet " .. P.event_planet)
  end
end
function P.on_stopped(f)
  local h = math.tointeger(tonumber(f.SpawnerComponentHandle))
  if not (h and P.lvl) then return end
  P.lvl.stopped[h] = true
  for _, A in ipairs(P.armed) do
    if not A.restored and A.rec.spawner == h then
      log(string.format("node %s's Spawner %X stopped (%d frame(s) after arming; %s)", tostring(A.rec.uid), h,
          P.frame - A.frame, A.verdict or "no spawn of it was seen"))
      P.put_back(A, "its Spawner stopped")
    end
  end
end

function P.start(fn)
  P.job_fn, P.job_restarts = fn, 0
  P.job = coroutine.create(fn)
end

function P.on_frame()
  P.frame = P.frame + 1
  local V = RANDO_SPAWNERS and RANDO_SPAWNERS.V
  if V and V.enabled and V.enabled() then
    if not P.stood_down then
      P.stood_down = true
      for _, A in ipairs(P.armed) do if not A.restored then P.put_back(A, "the Enemy Randomizer is on") end end
      P.job = nil
      log("standing down: the Enemy Randomizer is ON (it uses this experiment's method); nothing of spawnproof runs")
    end
    return
  end
  if P.stood_down then P.stood_down = nil; log("the Enemy Randomizer is OFF: spawnproof runs again") end
  if P.job then
    local ok, err = coroutine.resume(P.job)
    if not ok then
      -- the budget can also run out outside every guard: the job starts again (at most twice), nothing is lost
      if tostring(err):find("frame budget", 1, true) and (P.job_restarts or 0) < 2 then
        P.job_restarts = (P.job_restarts or 0) + 1
        P.budget_hits = (P.budget_hits or 0) + 1
        P.job = coroutine.create(P.job_fn)
      else
        P.job = nil; log("RANDO-ERROR", tostring(err))
      end
    elseif coroutine.status(P.job) == "dead" then P.job = nil end
    return
  end
  if not P.lvl or planet() ~= P.PLANET then return end      -- nothing is listed or read anywhere else
  local okr, ready = pcall(rivet.scene_ready)
  if okr and ready == false then return end
  if P.lvl.scans > 0 and #P.spawn_queue > 0 then
    local batch = P.spawn_queue
    P.spawn_queue = {}
    P.start(function() guard(P.learn, batch); guard(P.try_arm) end)
    return
  end
  if P.frame >= (P.next_scan or 0) or (P.lvl.scans == 0 and #P.spawn_queue > 0) then
    P.next_scan = P.frame + P.SCAN_EVERY
    P.start(function() guard(P.scan); guard(P.try_arm) end)
  end
end

if not P.subscribed then
  P.subscribed = true
  local SPL = RANDO_SPAWNERS
  -- dev 10.23: planet and spawns straight from rivet (2 of rivet_hook's 64 event callbacks): the spawner layer's
  -- events wait in the randomizer's buffer until the seed is ready, and that buffer once dropped the planet
  local function direct(class, fn)
    local ok, err = pcall(rivet.on_event, class, function(ev) local okf, e = pcall(fn, ev.fields or {}); if not okf then log("RANDO-ERROR", class, tostring(e)) end end)
    if not ok then log("cannot subscribe", class, tostring(err), "- using the spawner layer's (buffered) copy") end
    return ok
  end
  P.direct = { planet = direct("PlanetChangedEvent", P.on_planet), spawn = direct("SpawnerSpawnEvent", P.on_spawn) }
  if SPL and SPL.listen then
    SPL.listen("SpawnerSpawnEvent", P.on_spawn)            -- a second copy is ignored (P.seen_spawn)
    SPL.listen("SpawnerStoppedEvent", P.on_stopped)
    SPL.listen("LevelLoadedEvent", function() P.reset("level loaded") end)
    if not P.direct.planet then SPL.listen("PlanetChangedEvent", P.on_planet) end
    SPL.listen("Checkpoint", function(cp) if cp.loaded then P.reset("checkpoint loaded") end end)
  else
    log("16_rando_spawners.lua (with SP.listen) is missing: nothing runs")
    P.ENABLED = false
  end
  pcall(rivet.on_frame, P.on_frame)
end
P.reset("scripts loaded")
local hash_ok = (not rivet.hash) or (pcall(rivet.hash, "Factories") and rivet.hash("Factories") == P.PLUG_FACTORIES)
log(string.format("v6 loaded (factory Templates route, fresh factories): Template and Factories replacements on Zurkon (%s, at most %d); plugs Template %d Factories %d LastSpawn %d%s; own events: planet %s, spawns %s",
    P.ENABLED and "on" or "off", P.MAX_SWAPS, P.PLUG_TEMPLATE, P.PLUG_FACTORIES, P.PLUG_LASTSPAWN, hash_ok and "" or " - rivet.hash DISAGREES, nothing will match",
    P.direct and P.direct.planet and "yes" or "NO", P.direct and P.direct.spawn and "yes" or "NO"))
end)

DBG.log("dev(debug).lua loaded - sections on:", (function() local t = {} for k, v in pairs(DBG.ran) do if v then t[#t + 1] = k end end table.sort(t) return table.concat(t, ", ") end)())
