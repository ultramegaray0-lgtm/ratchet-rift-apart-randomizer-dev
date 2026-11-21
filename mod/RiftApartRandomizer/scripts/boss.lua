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
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["boss"] = "10.0.25"   -- the kit check (10_rando_runtime.lua)

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

-- dev 10.29: the Boss Randomizer runs on the variable route too (16_rando_spawners.lua SP.V, the same engine as the
-- Enemy Randomizer): a spawner whose original enemy is BOSS TIER (a large bot, or a kind that showed a health bar)
-- gets another boss-tier kind of the same movement group loaded on the same level. Story bosses (the 8 below; their
-- bot classes are "story_boss") are never touched, nor anything in a story boss area. enemy_route = "census" or
-- boss_route = "census" keeps the old census route (the 10.12-10.19 tests).
local route = (R.config.enemy_route ~= "census" and R.config.boss_route ~= "census") and "vars" or nil
B.client = SP.register({ name = "boss", role = "boss", label = "Boss Randomizer", state_key = "boss_rando",
                         config_key = "boss_randomizer", unique = true, route = route })

function B.enabled() return SP.enabled(B.client) end
function B.set(on, why) return SP.set(B.client, on, why) end
function B.toggle(why) return SP.toggle(B.client, why) end

function B.status_text()
  if not B.enabled() then return nil end
  if B.client.route == "vars" then
    local n = 0
    for _, A in ipairs(SP.V.lvl and SP.V.lvl.arms or {}) do if not A.restored and A.role == "boss" then n = n + 1 end end
    return string.format("bosses ON (%d boss spawner(s) changed here)", n)
  end
  local st = SP.client_status(B.client)
  return string.format("bosses ON (%d changed here, %d known)", st.slots, st.learned)
end

function B.key()
  if not (RANDO_SEED and R.state) then
    R.say("Randomizer: the seed is still being prepared", { type = "corner", duration = 3 }); return
  end
  if R.ctrl_down() and B.client.route == "vars" then
    local n, kinds = 0, {}
    for _, A in ipairs(SP.V.lvl and SP.V.lvl.arms or {}) do if not A.restored and A.role == "boss" then n = n + 1 end end
    for _, T in pairs(SP.V.lvl and SP.V.lvl.tpl or {}) do
      local g, role = SP.V.group_of(T)
      if g and role == "boss" then kinds[SP.V.short(T.name)] = true end
    end
    local k = 0
    for _ in pairs(kinds) do k = k + 1 end
    R.say(string.format("Boss Randomizer %s: %d boss spawner(s) changed here", B.enabled() and "ON" or "OFF", n),
          { type = "corner", sub = string.format("%d boss-tier kind(s) loaded here (2 are needed to swap); the %d story bosses stay as they are; combat: %s",
                                                 k, #B.STORY, SP.V.compat_mode()), duration = 6 })
    return
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
-- dev 10.30: boss-tier swaps go through the same combat compatibility as regular enemies (16_rando_spawners.lua): with
-- enemy_compat = "verified" (the default) a boss-tier pair needs in-game evidence that the replacement dies. No real
-- log has shown a boss-tier swap yet (round40: "0 boss spawner(s) changed here"), so none is verified and the Boss
-- Randomizer changes nothing until a "trial" round proves a pair.
-- dev 10.31: with enemy_compat = "all" boss-tier kinds swap among themselves without proof (watched like the rest).
if B.client.route == "vars" then
  if SP.V.all_mode() then
    log("combat compatibility: all - boss-tier enemies swap among themselves (watched; story bosses stay)")
  else
    log("combat compatibility: " .. SP.V.compat_mode() .. " - a boss-tier swap needs in-game proof that the replacement dies "
        .. "(no real log has one yet; a pair a trial round verified is kept in the save)")
  end
end
