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
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(debug)"] = "10.0.28"   -- the kit check (10_rando_runtime.lua)

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
    if not pid then say("[DEBUG] press HOME first to choose a planet", { type = "corner", duration = 4 }); return end
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
