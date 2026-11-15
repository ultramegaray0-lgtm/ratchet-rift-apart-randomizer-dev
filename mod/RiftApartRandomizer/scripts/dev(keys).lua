-- DEVELOPER TOOL - not part of a release. The developer keys. A release answers only the player's
-- key (0, 10_rando_runtime.lua); with this file installed these work too, and on-screen messages
-- mention them (RANDO_DEV_KEYS):
--   ;  (F9)   status line              Ctrl+; twice  open the planet you were last sent back from
--   ]  (F6)   next hub destination     Ctrl+]        go there
--   [  (F5)   cancel the automatic return after a finished destination
--             Ctrl+[ twice  finish the current destination by hand
--   /         start the story of the planet you are on (hub)
--   '  (F12)  campaign director: travel to the next visit (experimental mission orders only)
-- The F keys in brackets work as well while legacy_f_keys = true. Key names are settings
-- (key_status, key_hub, key_hub_return, key_story, key_campaign in 04_rando_settings.lua).
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(keys)"] = "10.0.9"   -- the kit check (10_rando_runtime.lua)

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
