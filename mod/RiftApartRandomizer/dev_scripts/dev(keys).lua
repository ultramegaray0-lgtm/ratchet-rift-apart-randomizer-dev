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
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(keys)"] = "10.0.39"   -- the kit check (10_rando_runtime.lua)
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
