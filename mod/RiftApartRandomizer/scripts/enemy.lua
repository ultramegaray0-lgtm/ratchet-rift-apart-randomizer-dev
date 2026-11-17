-- Rift Apart Randomizer dev 10.12: ENEMY RANDOMIZER (regular enemies). OPTIONAL, OFF by default.
--
-- In the game: the - key turns it ON / OFF (key_enemies; remembered in the save, kept over a New Game).
-- Ctrl+- shows what it changed on this planet. The setting enemy_randomizer = true in
-- 04_rando_settings.lua only decides the start for a save that never used the key.
--
-- What it does: the regular enemies of the game's combat encounters (turrets, flyers, swarmers, ground
-- bots) are replaced by other regular enemies of the same family that this planet's own encounters
-- use. The encounter's own spawner node spawns, counts and completes them, so doors, objectives,
-- waves and the story advance exactly as before (16_rando_spawners.lua explains how). It never
-- touches boss-tier enemies (boss.lua does), story bosses, friendly bots, mounts or anything that
-- is not spawned by an encounter's spawner node.
--
-- Needs 16_rando_spawners.lua. Removing this file only removes the enemy randomizer.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["enemy"] = "10.0.12"   -- the kit check (10_rando_runtime.lua)

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
                         config_key = "enemy_randomizer", unique = false })

function E.enabled() return SP.enabled(E.client) end
function E.set(on, why) return SP.set(E.client, on, why) end
function E.toggle(why) return SP.toggle(E.client, why) end

function E.status_text()
  if not E.enabled() then return nil end
  local st = SP.client_status(E.client)
  return string.format("enemies ON (%d changed here, %d known)", st.slots, st.learned)
end

function E.key()
  if not (RANDO_SEED and R.state) then
    R.say("Randomizer: the seed is still being prepared", { type = "corner", duration = 3 }); return
  end
  if R.ctrl_down() then
    local st = SP.client_status(E.client)
    R.say(string.format("Enemy Randomizer %s: %d enemy slot(s) changed in %d encounter(s) here", E.enabled() and "ON" or "OFF",
                        st.slots, st.encounters),
          { type = "corner", sub = string.format("%d regular enemy type(s) learned, %d encounter(s) kept original", st.learned, st.blocked),
            duration = 6 })
    return
  end
  E.toggle(R.key("key_enemies"))
end
R.bind_key(R.config.key_enemies, E.key, "key_enemies")
log("installed (" .. (E.enabled() and "ON" or "OFF") .. " until the save says otherwise) - " .. R.key("key_enemies") ..
    " turns it on / off, " .. R.key("key_enemies", true) .. " shows what it changed")
