-- Rift Apart Randomizer dev 10.12: BOSS RANDOMIZER (boss-tier enemies). OPTIONAL, OFF by default.
--
-- In the game: the = key turns it ON / OFF (key_bosses; remembered in the save, kept over a New Game).
-- Ctrl+= shows what it changed on this planet. The setting boss_randomizer = true in
-- 04_rando_settings.lua only decides the start for a save that never used the key.
--
-- What it does: boss-tier enemies that the game's encounters spawn with a spawner node (large bots
-- such as Grunthors, tanks, Manglers and armored transports, and any spawned enemy the game gives its
-- own boss health bar) are shuffled among the boss-tier enemies of the same planet and family. Each
-- planet's boss-tier enemies are permuted, never multiplied: a boss that appeared once still appears
-- once, as another boss. The encounter's spawner node spawns it, its health bar and death are its
-- own, and the node completes the encounter (16_rando_spawners.lua explains why progression holds).
--
-- STORY BOSSES ARE LEFT UNCHANGED. Their fights are not spawner encounters: each boss is its own
-- component (BossBot*, GameBotSargassoCentipedeBoss) driven by script actions written for it
-- (BossChaseControllerScriptAction, BossCentipedeGetPilotActorScriptAction, FinaleBoss*ScriptAction,
-- BossAttackVolumeSetupScriptAction, ...), with an arena, phases, health bar and defeat cutscene built
-- around that one boss. Swapping one in place of another would leave those scripts waiting for a boss
-- that is not there, so - as the request allows - these encounters keep their original boss (E.STORY).
-- Any spawned actor that turns out to be one of them is never used or replaced, and their areas
-- (checkpoints with BOSS / FINALE / HEAVY_FIGHT / CHASE in the name) put every change back while you
-- are there, so the adds of a story boss fight are the game's own too.
--
-- Needs 16_rando_spawners.lua. Removing this file only removes the boss randomizer; regular enemies
-- (enemy.lua) never become bosses and bosses never become regular enemies.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["boss"] = "10.0.18"   -- the kit check (10_rando_runtime.lua)

RANDO_BOSS = RANDO_BOSS or {}
local B = RANDO_BOSS
local R = RANDO
local SP = RANDO_SPAWNERS

local function log(...) pcall(rivet.log, "[rando]", "RANDO-BOSS", ...) end

-- the campaign's story bosses (03_rando_campaign.lua's segments), all kept as they are
B.STORY = {
  { boss = "Nefarious City: the blimp and the heavy fight", why = "BossBotNefariousBlimp; scripted shifts between planets" },
  { boss = "Sargasso: Seekerpede", why = "GameBotSargassoCentipedeBoss; BossCentipedeGetPilotActorScriptAction" },
  { boss = "Zurkie's: Francois (arena)", why = "the arena's own scripted fight" },
  { boss = "Torren IV: the Fixer (chase)", why = "BossChaseControllerScriptAction" },
  { boss = "Cordelion: the Cordelion boss", why = "BossBotCordelionNefarious; shield and telekinesis managers" },
  { boss = "Viceron: the Zordoom Prison warden", why = "BossBotZordoomMonster" },
  { boss = "the Juice boss", why = "BossBotUnderwaterBaseJuice" },
  { boss = "the finale: Emperor Nefarious", why = "BossBotNefariousFinale; FinaleBoss*ScriptAction phases" },
}

if not (R and R.config) then return end
if not SP then
  log("16_rando_spawners.lua is not installed: the boss randomizer stays off")
  return
end

B.client = SP.register({ name = "boss", role = "boss", label = "Boss Randomizer", state_key = "boss_rando",
                         config_key = "boss_randomizer", unique = true })

function B.enabled() return SP.enabled(B.client) end
function B.set(on, why) return SP.set(B.client, on, why) end
function B.toggle(why) return SP.toggle(B.client, why) end

function B.status_text()
  if not B.enabled() then return nil end
  local st = SP.client_status(B.client)
  return string.format("bosses ON (%d changed here, %d known)", st.slots, st.learned)
end

function B.key()
  if not (RANDO_SEED and R.state) then
    R.say("Randomizer: the seed is still being prepared", { type = "corner", duration = 3 }); return
  end
  if R.ctrl_down() then
    local st = SP.client_status(B.client)
    R.say(string.format("Boss Randomizer %s: %d boss slot(s) changed in %d encounter(s) here", B.enabled() and "ON" or "OFF",
                        st.slots, st.encounters),
          { type = "corner", sub = string.format("%d boss-tier type(s) learned; the %d story bosses stay as they are", st.learned, #B.STORY),
            duration = 6 })
    return
  end
  B.toggle(R.key("key_bosses"))
end
R.bind_key(R.config.key_bosses, B.key, "key_bosses")
log("installed (" .. (B.enabled() and "ON" or "OFF") .. " until the save says otherwise) - " .. R.key("key_bosses") ..
    " turns it on / off, " .. R.key("key_bosses", true) .. " shows what it changed; " .. #B.STORY ..
    " story boss fights are kept as they are")
