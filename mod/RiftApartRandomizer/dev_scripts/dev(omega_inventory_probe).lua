-- DEVELOPER TOOL - not part of a release. Safe Omega inventory discovery (dev(debug).lua holds it too).
-- Copy this file to GAME_FOLDER/scripts/ for one diagnostic run, then remove it.
-- It only inspects the live hero's component class names and metadata. No game state is mutated,
-- and event ItemHandle values are never treated as scene-actor handles.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(omega_inventory_probe)"] = "10.0.35"   -- the kit check (10_rando_runtime.lua)
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
