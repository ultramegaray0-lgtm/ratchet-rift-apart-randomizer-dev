-- Rift Apart Randomizer dev 10.27: ENEMY RANDOMIZER (regular enemies). OPTIONAL.
--
-- In the game: the - key turns it ON / OFF (key_enemies; remembered in the save, kept over a New Game).
-- Ctrl+- shows what it changed on this level. The setting enemy_randomizer in 04_rando_settings.lua only decides
-- the start for a save that never used the key.
--
-- What it does (dev 10.27, the method your game proved in round37): before a spawner runs, the enemy template in its
-- script variable is replaced by another regular enemy's template that is loaded on this level - a SunsetSpawnerFactory's
-- "Templates" (the arena waves: proven), a SpawnerScriptAction's "Template" (one actor) or its actor GROUP (robomutt /
-- thug waves: not yet seen working in the game - verified on the first spawn and switched off for the session if the
-- game ignores it). The encounter's own spawner spawns, counts and completes them, so doors, objectives, waves and the
-- story advance as before. Walkers become walkers, flyers flyers, turrets turrets. It never touches boss-tier enemies
-- (large bots, anything with a health bar), story bosses, friendly bots, NPCs, mounts or props, and never an enemy
-- that is not spawned by a spawner (enemies placed in the level). Every change is put back on a checkpoint load, a
-- level change, the - key, and when a changed encounter looks stuck or was retried 5 times (16_rando_spawners.lua,
-- section SP.V). Needs rando_give.dll v7 (the kit's) in the game folder; it says so on screen if it cannot work.
--
-- Needs 16_rando_spawners.lua. Removing this file only removes the enemy randomizer.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["enemy"] = "10.0.18"   -- the kit check (10_rando_runtime.lua)

RANDO_ENEMY = RANDO_ENEMY or {}
local E = RANDO_ENEMY
local R = RANDO
local SP = RANDO_SPAWNERS

local function log(...) pcall(rivet.log, "[rando]", "RANDO-ENEMY", ...) end

if not (R and R.config) then return end
if not SP then
  log("16_rando_spawners.lua is not installed: the enemy randomizer stays off")
  return
end

E.client = SP.register({ name = "enemy", role = "enemy", label = "Enemy Randomizer", state_key = "enemy_rando",
                         config_key = "enemy_randomizer", unique = false,
                         route = (R.config.enemy_route ~= "census") and "vars" or nil })

function E.enabled() return SP.enabled(E.client) end
function E.set(on, why) return SP.set(E.client, on, why) end
function E.toggle(why) return SP.toggle(E.client, why) end

function E.status_text()
  if not E.enabled() then return nil end
  if E.client.route ~= "vars" then
    local st = SP.client_status(E.client)
    return string.format("enemies ON (%d changed here, %d known)", st.slots, st.learned)
  end
  local st = SP.V.status()
  return string.format("enemies ON (%d spawner(s) changed here, %d enemy kind(s) known)", st.changed, st.known)
end

function E.key()
  if not (RANDO_SEED and R.state) then
    R.say("Randomizer: the seed is still being prepared", { type = "corner", duration = 3 }); return
  end
  if R.ctrl_down() and E.client.route ~= "vars" then
    local st = SP.client_status(E.client)
    R.say(string.format("Enemy Randomizer %s: %d enemy slot(s) changed in %d encounter(s) here", E.enabled() and "ON" or "OFF",
                        st.slots, st.encounters),
          { type = "corner", sub = string.format("%d regular enemy type(s) learned, %d encounter(s) kept original", st.learned, st.blocked),
            duration = 6 })
    return
  end
  if R.ctrl_down() then
    local st = SP.V.status()
    -- dev 10.29: what happened to this level's enemy spawns, first
    R.say(string.format("Enemy Randomizer %s: %d of %d enemy spawn(s) here were replaced", E.enabled() and "ON" or "OFF",
                        st.replaced, st.spawns),
          { type = "corner", sub = string.format("%d spawner(s) changed now (%d factory, %d node, %d group); %d kind(s) here%s",
                                                 st.changed, st.factory, st.template, st.group, st.kinds,
                                                 st.top_reason and ("; most kept: " .. st.top_reason) or ""), duration = 7 })
    return
  end
  E.toggle(R.key("key_enemies"))
end
R.bind_key(R.config.key_enemies, E.key, "key_enemies")
log("installed (" .. (E.enabled() and "ON" or "OFF") .. " until the save says otherwise) - " .. R.key("key_enemies") ..
    " turns it on / off, " .. R.key("key_enemies", true) .. " shows what it changed")
