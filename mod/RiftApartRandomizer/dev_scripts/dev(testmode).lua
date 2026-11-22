-- DEVELOPER TOOL - not part of a release. Randomizer TEST MODE: shortcuts that fake progress on a
-- spare save. Everything done with them is marked [TEST] in the history and the status line.
--   F10            a story mission on the current planet (or the first one not done)
--   F11            pick up one Gold Bolt on the current planet
--   Ctrl+F10 x2    reset this seed's randomizer progress (press twice within 5 seconds)
--   Ctrl+'  (Ctrl+F12 with legacy_f_keys)   the mission lab: read every mission's state (read only)
--   Ctrl+F11       the mission lab: start / complete / replay a mission on this spare save
-- Delete this file for normal play.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(testmode)"] = "10.0.26"   -- the kit check (10_rando_runtime.lua)
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
