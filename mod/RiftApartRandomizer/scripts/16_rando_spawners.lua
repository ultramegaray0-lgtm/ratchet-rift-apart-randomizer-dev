-- Rift Apart Randomizer dev 10.12: the spawner layer shared by enemy.lua and boss.lua (rivet_hook, Lua 5.4).
--
-- OPTIONAL. This file does nothing by itself: it only works for the two features that register with
-- it (enemy.lua: regular enemies, boss.lua: boss-tier enemies). Without it, both say so in rivet.log
-- and stay off; without them, it never reads or writes anything. Removing any of the three files
-- never touches the rest of the randomizer (10_rando_runtime.lua lists them as optional).
--
-- HOW AN ENEMY IS CHANGED (and why progression keeps working)
--   The game's combat encounters spawn their enemies with SpawnerScriptAction nodes in the level's
--   scripts (neptuwunium/rivet DDL, SpawnerScriptActionPrius: Templates, SpawnLocations, NumSpawns,
--   MaxSimultaneousSpawns, OnNumDeadTrigger, ...). The node keeps its own count of what it spawned and
--   what died, puts its spawns into its actor group and fires its outputs ("all dead", "num dead")
--   that open doors, finish objectives and start the next wave. The randomizer changes ONLY the
--   actor template ids in the node's Templates list, in memory, before the node runs. It never
--   deletes an enemy, never spawns one itself, never fires a node output and never writes a mission or
--   objective. The encounter's own node spawns the new enemy at the original spawn points, counts its
--   death like the original's and completes the encounter itself: one completion, at the right time,
--   from the game's own logic. A multi-enemy encounter completes when the node's own count says so.
--
-- WHAT IS NOT KNOWN UNTIL IT IS SEEN IN YOUR GAME (so nothing is guessed)
--   * Where Templates sits in a live node: found per node by a signature of the DDL layout (three
--     dynamic arrays 24 bytes apart, the eight flag bytes after them, sane counts), never assumed.
--     dev 10.17: it is in the node's Prius (rivet.component(...).prius), read at FactoryGroup +8 and
--     checked with that signature; the instance (too small in your game) is only a fallback.
--     A node that does not match is left alone (RANDO-SPAWNERS says why).
--   * What an actor template is: learned when the game itself spawns it. The spawned actor is asked
--     for the bot components of the DDL (SP.FAMILY_CLASSES): a turret, a flyer, a swarmer, a ground
--     bot, a large bot, a story boss, a friendly or a mount. Only templates learned this way are ever
--     used or replaced, and only by one of the same family (a flyer for a flyer, a turret for a
--     turret). Learned templates are kept in the save (state.spawn_learned), so the pool grows as you play.
--   * Story bosses (BossBot* components, the Seekerpede) and friendly bots are never touched.
--
-- SAFETY NETS (each one only ever puts an encounter BACK to its original enemies)
--   * a changed spawner that starts and spawns nothing within SP.SPAWN_TIMEOUT seconds;
--   * a changed spawner whose enemies stay alive SP.STUCK_SECONDS seconds without a death;
--   * a checkpoint loaded SP.DEATH_LIMIT times while a changed encounter was running (deaths, reloads);
--   * a replacement that turns out to be another family than expected;
--   * story boss areas (checkpoints named in SP.BOSS_ZONES): every change is put back while you are there.
--   Such a spawner is put back at once and kept original for this seed (state.spawn_blocked).
--   Spawners already running are never changed; switching a feature off puts its spawners back at once.
--
-- dev 10.13 CHAOS (chaos.lua) is a PRIORITY client without guards: while it is ON it owns every slot
-- (the Enemy and Boss Randomizers keep their own ON/OFF but change nothing), it chooses its own
-- replacements (client.assign), and none of the safety nets above apply to the slots it changed:
-- no story boss area put-back, no timeouts, no retries limit, no family check, no "not started yet"
-- rule. What stays for every client is code integrity: the node must still be the same live instance,
-- the slot must hold what was written, a write is read back, refused writes are not repeated, and a
-- Templates list two nodes share is not written. When Chaos is switched OFF its slots go back to their
-- originals and the Enemy / Boss Randomizers plan again from their own settings.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["16_rando_spawners"] = "10.0.12"   -- the kit check (10_rando_runtime.lua)

RANDO_SPAWNERS = RANDO_SPAWNERS or {}
local SP = RANDO_SPAWNERS
local R = RANDO

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNERS", ...) end
local function S() return RANDO and RANDO.state end
local function SEED() return RANDO_SEED end
local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) end end
local function changed() if RANDO and RANDO.mark_changed then RANDO.mark_changed() end end
local function hexaddr(n) return string.format("%X", n) end
local function history(line) if RANDO and RANDO.history then pcall(RANDO.history, line) end end
local function clock() return (os and os.clock and os.clock()) or 0 end
SP.log = log

SP.NODE_CLASS = "SpawnerScriptAction"
SP.HEADER = 0x100                 -- node bytes searched for the layout
SP.PREFERRED_X = 0x50             -- AddToInventoryAction's first field is at +0x50 in your game (round 13 probe: ItemConfig +0x58)
SP.MAX_TEMPLATES = 16
SP.SCAN_LIMIT = 512               -- spawner nodes listed per level
SP.CHECK_PER_FRAME = 2            -- nodes read per frame (rivet_hook's frame budget is shared)
SP.SLICE_SECONDS = 0.002
SP.RESCAN_DELAY = 90              -- frames after a load before the level's spawners are read
SP.SPAWN_TIMEOUT = 20             -- seconds
SP.STUCK_SECONDS = 180
SP.DEATH_LIMIT = 3
SP.LEARN_CAP = 600
SP.BLOCK_CAP = 300
SP.BOSS_ZONES = { "BOSS", "FINALE", "HEAVY_FIGHT", "CHASE" }
SP.BUDGET_SECONDS = 0.003         -- writes per frame stop after this long; the rest follows next frame
SP.CENSUS_RETRIES = 5             -- dev 10.17: a census stopped by the frame budget is started again this often

-- the bot components of the DDL, most specific first: class, family, role. role: "enemy" (enemy.lua),
-- "boss" (boss.lua), "story_boss" / "friendly" / "never" (nobody touches them). Classes whose purpose is
-- not clear from the DDL are "never".
SP.FAMILY_CLASSES = {
  { "BossBotCordelionNefarious", "story_boss", "story_boss" }, { "BossBotNefariousBlimp", "story_boss", "story_boss" },
  { "BossBotNefariousFinale", "story_boss", "story_boss" }, { "BossBotUnderwaterBaseJuice", "story_boss", "story_boss" },
  { "BossBotZordoomMonster", "story_boss", "story_boss" }, { "GameBotSargassoCentipedeBoss", "story_boss", "story_boss" },
  { "BossBase", "story_boss", "story_boss" },
  { "GameBotClankLemming", "friendly", "friendly" }, { "GameBotShooterSheep", "friendly", "friendly" },
  { "GameBotShooterTestDummy", "friendly", "friendly" }, { "GameBotShooterNoFiring", "friendly", "friendly" },
  { "GameBotShooterJetPackNoFiring", "friendly", "friendly" }, { "NPCInfobot", "friendly", "friendly" },
  { "GameBotMountBeast", "mount", "never" }, { "GameBotMountBeetle", "mount", "never" },
  { "GameBotMountFlyer", "mount", "never" }, { "GameBotMountKit", "mount", "never" },
  { "GameBotPufferFish", "hazard", "never" }, { "GameBotPoolShark", "unclear", "never" },
  { "GameBotMrFunGuy", "unclear", "never" }, { "GameBotTelepathipus", "unclear", "never" },
  { "GameBotGrunthor", "large", "boss" }, { "GameBotMeleeLarge", "large", "boss" }, { "GameBotTankBase", "large", "boss" },
  { "GameBotDoom", "large", "boss" }, { "GameBotMangler", "large", "boss" },
  { "GameBotShooterArmoredTransport", "large", "boss" },
  { "GameBotShooterTurret", "turret", "enemy" },
  { "GameBotMeleeSwarmerGroundFlyer", "flyer", "enemy" }, { "GameBotMeleeFlier", "flyer", "enemy" },
  { "GameBotShooterNymphFlyer", "flyer", "enemy" }, { "GameBotShooterHeli", "flyer", "enemy" },
  { "GameBotShooterJetPack", "flyer", "enemy" }, { "GameBotDarterBat", "flyer", "enemy" },
  { "GameBotShooterBlargSaucer", "flyer", "enemy" }, { "GameBotShooterBlargBomber", "flyer", "enemy" },
  { "GameBotMeleeSwarmerBurrower", "swarmer", "enemy" }, { "GameBotMeleeSwarmerJumper", "swarmer", "enemy" },
  { "GameBotMeleeSwarmer", "swarmer", "enemy" }, { "GameBotAmoeboid", "swarmer", "enemy" },
  { "GameBotShooterExtermibot", "ground", "enemy" }, { "GameBotShooterConstructorBot", "ground", "enemy" },
  { "GameBotShooterMrsZurkonMinion", "ground", "enemy" }, { "GameBotMeleeBase", "ground", "enemy" },
  { "GameBotShooterBase", "ground", "enemy" }, { "GameBotShooter", "ground", "enemy" },
}
SP.ROLE_OF_FAMILY = {}
for _, e in ipairs(SP.FAMILY_CLASSES) do SP.ROLE_OF_FAMILY[e[2]] = SP.ROLE_OF_FAMILY[e[2]] or e[3] end

-- session state (a new Lua VM starts empty; what must outlive it is in RANDO.state)
SP.clients = SP.clients or {}
SP.client_order = SP.client_order or {}
SP.frame = SP.frame or 0
SP.level = nil                    -- the census of the loaded level
SP.spawned_by = {}                -- spawned actor handle -> { uid, tid }
SP.session = SP.session or { choice = {} }
SP.retries = {}                   -- uid -> checkpoint loads while its changed encounter ran
SP.zone = nil                     -- the story boss zone you are in (a checkpoint name), or nil
SP.stats = { applied = 0, reverted = 0, blocked = 0 }
SP.written = {}                   -- slot address -> { uid, orig, cur, owner, expect }: what this session wrote
SP.started_handles = {}           -- spawner handle -> frame it started (also before the census has read it)
SP.revert_pending = {}            -- client name -> why: its slots are being put back (over a few frames if many)

-- ---------------------------------------------------------------------------------------------
-- small helpers
-- ---------------------------------------------------------------------------------------------
local HEXB = {}
for i = 0, 255 do
  local hi, lo = string.format("%02X", i), string.format("%02x", i)
  local ch = string.char(i)
  HEXB[hi] = ch; HEXB[lo] = ch; HEXB[hi:sub(1, 1) .. lo:sub(2, 2)] = ch; HEXB[lo:sub(1, 1) .. hi:sub(2, 2)] = ch
end
local function bytes_of(text)
  local hex = (text or ""):gsub("[^%x]", "")
  if #hex % 2 == 1 then hex = hex:sub(1, #hex - 1) end
  if #hex == 0 then return {} end
  return { (hex:gsub("%x%x", HEXB)):byte(1, -1) }
end
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
  if not h or h:sub(1, 1):match("[89A-F]") then return nil end    -- above 2^63: not a user-space pointer
  return tonumber(h, 16)
end
local function le_hex(hex)
  local t = {}
  for k = 15, 1, -2 do t[#t + 1] = hex:sub(k, k + 1) end
  return table.concat(t, " ")
end
local function valid_ptr(p) return p ~= nil and p > 0x10000 and p < 0x7FFFFFFFFFFF and p % 8 == 0 end
local function read_bytes(addr, len)
  local ok, text = pcall(rivet.read, hexaddr(addr), len)
  if not ok or not text then return nil end
  return bytes_of(text)
end
local function read_id(addr)
  local b = read_bytes(addr, 8)
  return b and hex64(b, 1)
end
SP.bytes_of, SP.hex64, SP.le_hex = bytes_of, hex64, le_hex

-- FNV-1a, 32 bit: the same text gives the same number in every game and in the tests
function SP.hash(text)
  local h = 0x811C9DC5
  for i = 1, #text do h = ((h ~ text:byte(i)) * 0x01000193) & 0xFFFFFFFF end
  return h
end
-- rendezvous ranking: adding a candidate changes a pick only if the new one wins, so a pool that
-- grows while you play keeps most encounters as they were
function SP.rank(key, candidates)
  local scored = {}
  for _, c in ipairs(candidates) do scored[#scored + 1] = { c = c, h = SP.hash(key .. "|" .. c) } end
  table.sort(scored, function(a, b) if a.h ~= b.h then return a.h > b.h end return a.c < b.c end)
  local out = {}
  for i, e in ipairs(scored) do out[i] = e.c end
  return out
end
local function seed_key() local s = SEED(); return (s and (tostring(s.seed) .. "/" .. tostring(s.fingerprint))) or "no-seed" end
local function sorted_keys(t)
  local k = {}
  for key in pairs(t) do k[#k + 1] = key end
  table.sort(k, function(a, b) return tostring(a) < tostring(b) end)
  return k
end
local function count(t) local n = 0; for _ in pairs(t or {}) do n = n + 1 end; return n end

-- ---------------------------------------------------------------------------------------------
-- clients (enemy.lua, boss.lua) and their switches
-- ---------------------------------------------------------------------------------------------
-- client = { name = "enemy", role = "enemy", label = "Enemy Randomizer", state_key = "enemy_rando",
--            config_key = "enemy_randomizer", unique = false }
function SP.register(client)
  if SP.clients[client.name] then return SP.clients[client.name] end
  SP.clients[client.name] = client
  SP.client_order[#SP.client_order + 1] = client.name
  table.sort(SP.client_order)
  local what = (client.role == "boss") and "boss-tier enemies" or (client.role == "any") and
               "every enemy and boss, priority, no guards" or "regular enemies"
  log(client.label, "is installed (", what, ")")
  return client
end
-- dev 10.13: the priority client (Chaos) when it is ON, else nil
function SP.priority_client()
  for _, name in ipairs(SP.client_order) do
    local c = SP.clients[name]
    if c.priority and SP.enabled(c) then return c end
  end
  return nil
end
-- does this client's work get the safety nets? (Chaos: guards = false)
local function guarded_name(name)
  local c = name and SP.clients[name]
  return c == nil or c.guards ~= false
end
SP.guarded_name = guarded_name
function SP.client_for_role(role)
  for _, name in ipairs(SP.client_order) do
    local c = SP.clients[name]
    if c.role == role then return c end
  end
  return nil
end
-- ON / OFF: the save's choice, else the setting (enemy_randomizer / boss_randomizer, false by default)
function SP.enabled(client)
  if type(client) == "string" then client = SP.clients[client] end
  if not client then return false end
  local cfg = R and R.config or {}
  if cfg.spawner_runtime == false then return false end
  local s = S()
  local v = s and s[client.state_key]
  if v == nil then v = cfg[client.config_key] == true end
  return v == true
end
function SP.any_enabled()
  for _, name in ipairs(SP.client_order) do if SP.enabled(SP.clients[name]) then return true end end
  return false
end

function SP.set(client, on, why)
  if type(client) == "string" then client = SP.clients[client] end
  local s = S()
  if not (client and s) then return false end
  on = on == true
  if SP.enabled(client) == on then return false end
  s[client.state_key] = on
  SP.session.choice[client.state_key] = on        -- this session's choice outlives a later restore
  changed()
  history(string.format("[%s %s] (%s)", client.label:upper(), on and "ON" or "OFF", tostring(why)))
  if on then
    log(client.label, "ON (" .. tostring(why) .. ")")
    if SP.level and SP.level.done then SP.plan("switched on") else SP.schedule_scan("switched on", 1) end
  else
    SP.revert_pending[client.name] = "switched off"
    local n = SP.continue_reverts()
    log(client.label, "OFF (" .. tostring(why) .. "):", n, "spawner slot(s) put back to their original enemies" ..
        (next(SP.revert_pending) and " (the rest over the next frames)" or ""))
    if not SP.any_enabled() then SP.job = nil else SP.replan = true end   -- the others plan again (dev 10.13)
  end
  return true
end
function SP.toggle(client, why)
  if type(client) == "string" then client = SP.clients[client] end
  if not client then return false end
  local on = not SP.enabled(client)
  SP.set(client, on, why)
  local sub = on and "takes effect for encounters that have not started yet" or "every encounter has its original enemies again"
  say(client.label .. ": " .. (on and "ON" or "OFF"), { type = "center", sub = sub, duration = 5 })
  return on
end

-- after the companion's restore: a choice made this session wins; what this session learned is kept
function SP.after_restore(live)
  local s = S()
  if not s then return end
  for k, v in pairs(SP.session.choice) do s[k] = v end
  if type(live) == "table" and live ~= s then
    for _, k in ipairs({ "spawn_learned", "spawn_blocked" }) do
      if type(live[k]) == "table" and next(live[k]) ~= nil then
        s[k] = s[k] or {}
        for key, v in pairs(live[k]) do if s[k][key] == nil then s[k][key] = v end end
      end
    end
  end
  for _, name in ipairs(SP.client_order) do
    local c = SP.clients[name]
    if c.after_restore then pcall(c.after_restore, live) end
  end
  -- a feature the restored save has off: whatever this session changed for it goes back
  for _, name in ipairs(SP.client_order) do
    if not SP.enabled(SP.clients[name]) then SP.revert_pending[name] = "off in the restored save" end
  end
  if next(SP.revert_pending) then SP.continue_reverts() end
  if not SP.any_enabled() then SP.job = nil else SP.replan = true end
end
-- kept over a New Game: the switches and what was learned about the game (not about the run)
SP.KEEP_OVER_NEW_GAME = { "enemy_rando", "boss_rando", "spawn_learned", "spawn_blocked" }

-- ---------------------------------------------------------------------------------------------
-- learning: what an actor template is
-- ---------------------------------------------------------------------------------------------
-- read: the save's table or an empty one (reading never adds anything to the save); write: created then
local EMPTY = setmetatable({}, { __newindex = function() error("read-only") end })
local function learned_t(write)
  local s = S(); if not s then return EMPTY end
  if write then s.spawn_learned = s.spawn_learned or {} end
  return s.spawn_learned or EMPTY
end
local function blocked_t(write)
  local s = S(); if not s then return EMPTY end
  if write then s.spawn_blocked = s.spawn_blocked or {} end
  return s.spawn_blocked or EMPTY
end
-- "family" or "family|hb" (a health bar was shown for it: boss tier)
function SP.family_of(tid)
  local v = learned_t()[tid]
  if type(v) ~= "string" then return nil, false end
  local fam, hb = v:match("^([%w_]+)(|?h?b?)$")
  return fam, hb == "|hb"
end
function SP.role_of(tid)
  local fam, hb = SP.family_of(tid)
  if not fam then return nil end
  local role = SP.ROLE_OF_FAMILY[fam] or "never"
  if role == "enemy" and hb then role = "boss" end     -- a regular bot with its own health bar is boss tier
  return role, fam, hb
end
-- the pool key: a replacement must share it (same tier, same movement family)
function SP.pool_key(tid)
  local role, fam = SP.role_of(tid)
  if role ~= "enemy" and role ~= "boss" then return nil end
  return role .. ":" .. fam, role
end

-- the bot components of a spawned actor (its first class of SP.FAMILY_CLASSES)
SP.CLASS_SUFFIXES = { "", "Prius" }
SP.unclassified_logged = SP.unclassified_logged or {}
function SP.classify_actor(handle)
  if handle == nil then return nil end
  -- dev 10.17: one rivet.components call lists the actor's classes (instead of ~90 failing lookups)
  local okl, names = pcall(rivet.components, handle)
  if okl and type(names) == "table" and #names > 0 then
    local have = {}
    for _, n in ipairs(names) do
      have[tostring(n)] = true
      if tostring(n):sub(-5) == "Prius" then have[tostring(n):sub(1, -6)] = true end
    end
    for _, e in ipairs(SP.FAMILY_CLASSES) do if have[e[1]] then return e[2], e[1] end end
    -- not one class of the table: said once per class list, so the next log shows what bots really are
    local bots = {}
    for _, n in ipairs(names) do
      local t = tostring(n)
      if t:find("Bot", 1, true) or t:find("Boss", 1, true) or t:find("NPC", 1, true) then bots[#bots + 1] = t end
    end
    local key = table.concat(bots, ",")
    if #bots > 0 and not SP.unclassified_logged[key] and count(SP.unclassified_logged) < 20 then
      SP.unclassified_logged[key] = true
      log("spawned actor not classified (left alone):", key)
    end
    if #bots > 0 then return nil end
  end
  for _, e in ipairs(SP.FAMILY_CLASSES) do
    for _, suffix in ipairs(SP.CLASS_SUFFIXES) do
      local ok, c = pcall(rivet.component, handle, e[1] .. suffix)
      if ok and type(c) == "table" and c.address then return e[2], e[1] end
    end
  end
  return nil
end
function SP.learn(tid, family, why)
  local L = learned_t(true)
  local old = L[tid]
  local hb = type(old) == "string" and old:find("|hb", 1, true) ~= nil
  local v = family .. (hb and "|hb" or "")
  if old == v then return false end
  if old == nil and count(L) >= SP.LEARN_CAP then return false end
  L[tid] = v
  changed()
  SP.replan = true                  -- idle spawners of the loaded level may use it now
  log("learned", tid, "=", family, "(" .. tostring(why) .. ")")
  return true
end
function SP.learn_health_bar(tid)
  local L = learned_t(true)
  local old = L[tid]
  if type(old) ~= "string" or old:find("|hb", 1, true) then return false end
  L[tid] = old .. "|hb"
  changed()
  SP.replan = true
  log("learned", tid, "shows a health bar: boss tier from now on")
  return true
end

-- ---------------------------------------------------------------------------------------------
-- the census: the level's spawner nodes, their Templates found by the layout's signature
-- ---------------------------------------------------------------------------------------------
-- dynamic array header { pointer, count, capacity } at byte i (1-based)
local function array_at(b, i)
  local p, n, cap = ptr64(b, i), u32(b, i + 8), u32(b, i + 12)
  if n == nil or cap == nil then return nil end
  if n > 64 or (cap ~= 0 and cap < n) or cap > 0x10000 then return nil end
  if n > 0 and not valid_ptr(p) then return nil end
  return { ptr = p, count = n }
end
-- SpawnerScriptActionPrius (rivet DDL): FactoryGroup +8, FactorySelectionMethod +24, Templates +32,
-- TemplateSelectionMethod +48, SpawnLocations +56, LocationSelectionMethod +72, 8 bools +76..83,
-- NumSpawns +108, MaxSimultaneousSpawns +112, MaxActivations +128. x = where FactoryGroup is (offset).
function SP.layout_at(b, x)
  local i = x + 1
  if not b[i + 127] then return nil end
  local fac, tpl, loc = array_at(b, i), array_at(b, i + 24), array_at(b, i + 48)
  if not (fac and tpl and loc) then return nil end
  if tpl.count < 1 or tpl.count > SP.MAX_TEMPLATES then return nil end
  if b[i + 16] > 15 or b[i + 40] > 15 then return nil end                    -- the two selection enums
  for k = 68, 75 do if b[i + k] > 1 then return nil end end                  -- InViewValidate .. RandomizeT
  local num, maxsim, maxact = s32(b, i + 100), s32(b, i + 104), s32(b, i + 120)
  if not (num and maxsim and maxact) then return nil end
  if num < -1 or num > 10000 or maxsim < -1 or maxsim > 10000 or maxact < -1 or maxact > 10000 then return nil end
  return { x = x, templates = tpl, locations = loc, factories = fac.count, num_spawns = num, max_alive = maxsim }
end
-- the one x that matches; nil and the reason otherwise. Mostly-zero bytes can make a place 24 bytes off
-- look like the list too, so when several match, the one with spawn locations and no factories (an
-- ordinary spawner) wins; if that does not decide it, SP.PREFERRED_X among them; else nothing is used.
function SP.find_layout(b)
  local cands = {}
  for x = 0x08, SP.HEADER - 0x88, 8 do
    local l = SP.layout_at(b, x)
    if l then cands[#cands + 1] = l end
  end
  if #cands == 0 then return nil, "no Templates list found" end
  if #cands == 1 then return cands[1] end
  local ordinary = {}
  for _, l in ipairs(cands) do if l.locations.count >= 1 and l.factories == 0 then ordinary[#ordinary + 1] = l end end
  if #ordinary == 1 then return ordinary[1] end
  for _, l in ipairs(#ordinary > 1 and ordinary or {}) do if l.x == SP.PREFERRED_X then return l end end
  return nil, #cands .. " places look like the spawner's fields"
end

function SP.still_valid(rec)
  local ok, c = pcall(rivet.component, rec.actor, SP.NODE_CLASS)
  return ok and type(c) == "table" and c.handle == rec.component and tonumber(c.address, 16) == rec.addr
end

-- dev 10.17: where the SpawnerScriptActionPrius fields really are. rivet_hook's rivet.component gives
-- `prius` = the component's Prius data (Component.ddlPriusData -> holder { vtable, count, data } ->
-- data), separate from the instance, and `size` = the class's instance size. 10.12-10.16 searched
-- only the instance's first min(0x100, size) bytes and needed 0x88: in your game every node failed
-- ("cannot read the node", rivet.log of 2026-11-17: 0 nodes read in 32 censuses), so nothing was
-- ever learned or changed. Now the Prius is read at the DDL's own offsets (FactoryGroup +8); the
-- instance search stays only for a node rivet gives no Prius for.
SP.PRIUS_X = 0x08                 -- FactoryGroup's offset in SpawnerScriptActionPrius (rivet DDL)
SP.PRIUS_READ = 0x90              -- bytes of the Prius read: through MaxActivations (+128) and OnNumDeadTrigger
local function read_ids(ptr, n)
  if n < 1 then return {} end
  local b = read_bytes(ptr, n * 8)
  if not b or #b < n * 8 then return nil end
  local out = {}
  for k = 1, n do out[k] = hex64(b, (k - 1) * 8 + 1) end
  return out
end

-- one node -> a record, or nil and why
function SP.read_node(node)
  local okc, c = pcall(rivet.component, node.actor, node.class)
  if not (okc and type(c) == "table" and c.handle == node.component and c.address) then return nil, "instance not reachable" end
  local addr = tonumber(c.address, 16)
  if not valid_ptr(addr) then return nil, "no address" end
  local lay, why, where
  local pr = c.prius and tonumber(c.prius, 16)
  if valid_ptr(pr) then
    local need = SP.PRIUS_X + 0x80
    local plen = SP.PRIUS_READ
    if c.prius_size and c.prius_size > 0 and c.prius_size < plen then plen = c.prius_size end
    local pb = read_bytes(pr, plen)
    if not pb or #pb < need then why = "cannot read the Prius (" .. tostring(c.prius_size) .. " bytes)"
    else
      lay = SP.layout_at(pb, SP.PRIUS_X)
      if lay then where = "prius" else why = "the Prius does not hold the spawner's fields at +8" end
    end
  end
  if not lay then
    -- no Prius from rivet (older rivet_hook, the simulator's old nodes): the instance, never past its size
    local len = math.min(SP.HEADER, (c.size and c.size > 0) and c.size or SP.HEADER)
    if len < 0x88 then return nil, why or ("no Prius and the instance is only " .. tostring(c.size) .. " bytes") end
    local b = read_bytes(addr, len)
    if not b or #b < 0x88 then return nil, why or "cannot read the node" end
    local why2
    lay, why2 = SP.find_layout(b)
    if not lay then return nil, why and (why .. "; instance: " .. tostring(why2)) or why2 end
    where = "instance"
  end
  local t = lay.templates
  local tb = read_bytes(t.ptr, t.count * 8)
  if not tb or #tb < t.count * 8 then return nil, "cannot read the Templates list" end
  local rec = { uid = node.uid, component = node.component, actor = node.actor, addr = addr, x = lay.x, where = where,
                tptr = t.ptr, count = t.count, slots = {}, max_alive = lay.max_alive, num_spawns = lay.num_spawns,
                spawned = 0, alive = {}, alive_n = 0 }
  -- the spawn points' actor ids: a SpawnerSpawnEvent names its SpawnLocation, which finds the node when the
  -- event carries no sender (fallback only; never used to change anything)
  local l = lay.locations
  if l and l.count >= 1 and l.count <= 32 then rec.locs = read_ids(l.ptr, l.count) end
  for k = 1, t.count do
    local id = hex64(tb, (k - 1) * 8 + 1)
    if not id or id == "0000000000000000" then return nil, "an empty template" end
    rec.slots[k] = { addr = t.ptr + (k - 1) * 8, orig = id, cur = id }
  end
  return rec
end

function SP.schedule_scan(why, delay)
  if not SP.any_enabled() then return end
  SP.scan_at = SP.frame + (delay or SP.RESCAN_DELAY)
  SP.scan_why = why
end

-- the census runs as a job, a slice per frame
local function census(job)
  local okl, list = pcall(rivet.script_nodes, SP.NODE_CLASS, SP.SCAN_LIMIT)
  if not okl or type(list) ~= "table" then
    if tostring(list):find("budget", 1, true) then error(list, 0) end      -- dev 10.17: SP.tick starts it again
    log("the level's spawner nodes cannot be listed:", tostring(list))
    return
  end
  coroutine.yield()
  local lvl = { nodes = {}, order = {}, slots_by_addr = {}, skipped = {}, loc_index = {}, done = false, id = (SP.level_id or 0) + 1 }
  SP.level_id = lvl.id
  local n_in_slice, t0 = 0, clock()
  for _, node in ipairs(list) do
    if node.class == SP.NODE_CLASS and node.uid and not lvl.nodes[node.uid] then
      local rec, why = SP.read_node(node)
      if rec then
        -- a Templates list two nodes share is never changed (one write would change both encounters)
        for _, sl in ipairs(rec.slots) do
          local a = sl.addr
          if lvl.slots_by_addr[a] then
            sl.shared = true; rec.shared = true
            local other = lvl.nodes[lvl.slots_by_addr[a]]
            if other then other.shared = true; for _, o in ipairs(other.slots) do if o.addr == a then o.shared = true end end end
          else lvl.slots_by_addr[a] = rec.uid end
          -- a slot this session changed before a reload that kept the node: its original is remembered
          local w = SP.written[a]
          if w then
            if w.uid == rec.uid and w.cur == sl.cur then sl.orig, sl.owner, sl.expect = w.orig, w.owner, w.expect
            else SP.written[a] = nil end
          end
        end
        -- started before the census read it (an encounter at the load's checkpoint): never changed now
        local st = SP.started_handles[rec.component] or SP.started_handles[rec.actor]
        if st then rec.started = st.frame; rec.stopped = st.stopped end
        lvl.nodes[rec.uid] = rec
        lvl.order[#lvl.order + 1] = rec.uid
        -- dev 10.17: spawn point id -> node uid (false when two nodes share the point: not a lead)
        for _, id in ipairs(rec.locs or {}) do
          if id ~= "0000000000000000" then
            local prev = lvl.loc_index[id]
            if prev == nil then lvl.loc_index[id] = rec.uid elseif prev ~= rec.uid then lvl.loc_index[id] = false end
          end
        end
      else
        lvl.skipped[#lvl.skipped + 1] = tostring(node.uid) .. ": " .. tostring(why)
      end
      n_in_slice = n_in_slice + 1
      if n_in_slice >= SP.CHECK_PER_FRAME or clock() - t0 > SP.SLICE_SECONDS then
        coroutine.yield(); n_in_slice, t0 = 0, clock()
      end
    end
  end
  table.sort(lvl.order, function(a, b) return tostring(a) < tostring(b) end)
  lvl.done = true
  SP.level = lvl
  local tids = {}
  for _, uid in ipairs(lvl.order) do for _, sl in ipairs(lvl.nodes[uid].slots) do tids[sl.orig] = true end end
  lvl.templates = tids
  local layouts = {}
  for _, uid in ipairs(lvl.order) do
    local r = lvl.nodes[uid]
    local k = string.format("%s+0x%X", r.where == "prius" and "prius " or "", r.x)
    layouts[k] = (layouts[k] or 0) + 1
  end
  local lay = {}
  for _, k in ipairs(sorted_keys(layouts)) do lay[#lay + 1] = string.format("%s x%d", k, layouts[k]) end
  log(string.format("census %d (%s): %d spawner node(s) read, %d template(s), %d skipped%s", lvl.id, tostring(job.why),
      #lvl.order, count(tids), #lvl.skipped, #lay > 0 and (" - layout " .. table.concat(lay, ", ")) or ""))
  for i = 1, math.min(5, #lvl.skipped) do log("  skipped", lvl.skipped[i]) end
  for _, name in ipairs(SP.client_order) do
    local c = SP.clients[name]
    if c.on_census then
      local ok, err = pcall(c.on_census, lvl)
      if not ok then log("RANDO-ERROR", name, "census hook:", tostring(err)) end
    end
  end
  SP.plan("census " .. lvl.id)
  -- dev 10.13: forget writes in nodes that are gone (another planet's), so the record never grows
  local n_in, t1 = 0, clock()
  for _, a in ipairs(sorted_keys(SP.written)) do
    if not lvl.slots_by_addr[a] then
      local w = SP.written[a]
      if w and not SP.still_valid({ actor = w.actor, component = w.component, addr = w.node }) then SP.written[a] = nil end
      n_in = n_in + 1
      if n_in >= 8 or clock() - t1 > SP.SLICE_SECONDS then coroutine.yield(); n_in, t1 = 0, clock() end
    end
  end
end

function SP.start_scan(why)
  SP.scan_at = nil
  if not SP.any_enabled() then return end
  local job = { why = why }
  job.co = coroutine.create(function() census(job) end)
  SP.job = job
end

-- ---------------------------------------------------------------------------------------------
-- writing and putting back
-- ---------------------------------------------------------------------------------------------
-- one slot to `id`; checks the node is still the same live instance and the slot still holds what
-- we believe. Returns true, or false and why.
function SP.write_slot(rec, sl, id, why)
  if sl.cur == id then return true end
  if not SP.still_valid(rec) then return false, "the node is gone (the level reloaded)" end
  local now = read_id(sl.addr)
  if now ~= sl.cur then return false, "the slot holds " .. tostring(now) .. ", not " .. tostring(sl.cur) end
  local ok, err = pcall(rivet.write, hexaddr(sl.addr), le_hex(id))
  if not ok then return false, "write refused: " .. tostring(err) end
  local back = read_id(sl.addr)
  if back ~= id then
    pcall(rivet.write, hexaddr(sl.addr), le_hex(sl.cur))
    return false, "read back " .. tostring(back)
  end
  sl.cur = id
  if id == sl.orig then SP.written[sl.addr] = nil
  else SP.written[sl.addr] = { uid = rec.uid, orig = sl.orig, cur = id, actor = rec.actor, component = rec.component,
                                node = rec.addr } end
  return true
end

function SP.revert_rec(rec, why, only_owner)
  local n = 0
  for _, sl in ipairs(rec.slots) do
    if sl.cur ~= sl.orig and (only_owner == nil or sl.owner == only_owner) then
      local ok, err = SP.write_slot(rec, sl, sl.orig, why)
      if ok then n = n + 1; sl.owner = nil
      else log("could not put back", rec.uid, "slot", tostring(sl.addr), "-", tostring(err)) end
    end
  end
  if n > 0 then SP.stats.reverted = SP.stats.reverted + n end
  return n
end
function SP.revert_client(client, why, deadline)
  if not client then return 0, true end
  local lvl = SP.level
  local n = 0
  if lvl then
    for _, uid in ipairs(lvl.order) do
      if n > 0 and deadline and clock() > deadline then return n, false end
      n = n + SP.revert_rec(lvl.nodes[uid], why, client.name)
    end
  end
  local m, done = SP.revert_written(client.name, why, deadline)
  return n + m, done
end
-- the pending put-backs, within the frame budget; returns the slots put back now
function SP.continue_reverts()
  local total = 0
  local deadline = clock() + SP.BUDGET_SECONDS
  for _, name in ipairs(sorted_keys(SP.revert_pending)) do
    local n, done = SP.revert_client(SP.clients[name], SP.revert_pending[name], deadline)
    total = total + n
    if done then SP.revert_pending[name] = nil else break end
  end
  return total
end
-- slots written in nodes the current census does not hold (it is being read again after a load):
-- put back from what this session wrote, if the node is still the same and still holds our write
function SP.revert_written(owner, why, deadline)
  local n = 0
  for _, a in ipairs(sorted_keys(SP.written)) do
    if n > 0 and deadline and clock() > deadline then return n, false end
    local w = SP.written[a]
    if owner == nil or w.owner == owner then
      if SP.still_valid({ actor = w.actor, component = w.component, addr = w.node }) and read_id(a) == w.cur then
        local ok = pcall(rivet.write, hexaddr(a), le_hex(w.orig))
        if ok and read_id(a) == w.orig then n = n + 1 end
      end
      SP.written[a] = nil
    end
  end
  if n > 0 then SP.stats.reverted = SP.stats.reverted + n; log(n, "slot(s) of an earlier census put back:", tostring(why)) end
  return n, true
end
-- the guarded clients' slots only (a story boss area does not touch Chaos)
function SP.revert_guarded(why)
  local n = 0
  for _, name in ipairs(SP.client_order) do
    if guarded_name(name) then n = n + (SP.revert_client(SP.clients[name], why)) end
  end
  if n > 0 then log(n, "slot(s) put back:", why) end
  return n
end
function SP.revert_all(why)
  local lvl = SP.level
  local n = 0
  if lvl then for _, uid in ipairs(lvl.order) do n = n + SP.revert_rec(lvl.nodes[uid], why) end end
  n = n + SP.revert_written(nil, why)
  if n > 0 then log(n, "slot(s) put back:", why) end
  return n
end
-- a spawner that must keep its original enemies for this seed
function SP.block(rec, why)
  local B = blocked_t(true)
  if B[rec.uid] == nil and count(B) < SP.BLOCK_CAP then B[rec.uid] = why; changed() end
  rec.blocked = why
  local n = SP.revert_rec(rec, why)
  SP.stats.blocked = SP.stats.blocked + 1
  log("encounter", rec.uid, "put back to its original enemies and kept so:", why, "(" .. n .. " slot(s))")
  history("[SPAWNER KEPT ORIGINAL] " .. tostring(rec.uid) .. ": " .. why)
  return n
end
function SP.is_blocked(rec) return rec.blocked ~= nil or blocked_t()[rec.uid] ~= nil end

-- ---------------------------------------------------------------------------------------------
-- the plan: which slot gets which template
-- ---------------------------------------------------------------------------------------------
-- may this spawner be changed now? (idle: not started since the level was read, not blocked)
function SP.idle(rec) return rec.started == nil and not SP.is_blocked(rec) end

-- the pools of the loaded level: pool key -> sorted template ids (learned, of a role a client owns)
function SP.pools(lvl)
  local pools = {}
  for tid in pairs(lvl.templates or {}) do
    local key = SP.pool_key(tid)
    if key then pools[key] = pools[key] or {}; table.insert(pools[key], tid) end
  end
  for _, p in pairs(pools) do table.sort(p) end
  return pools
end

-- unique clients (boss.lua): one permutation of each pool, so no boss tier enemy appears twice where it
-- appeared once; free clients (enemy.lua): each slot its own pick
function SP.permutation(key, pool)
  local order = SP.rank(seed_key() .. "|perm|" .. key, pool)
  local map = {}
  local n = #order
  for i, tid in ipairs(order) do map[tid] = order[(i % n) + 1] end
  return map
end

function SP.plan(why)
  local lvl = SP.level
  if not (lvl and lvl.done) then return 0 end
  local pools = SP.pools(lvl)
  local perms = {}
  local applied, kept, wrong, writes = 0, 0, 0, 0
  local deadline = clock() + SP.BUDGET_SECONDS
  -- dev 10.13: a priority client (Chaos) chooses every slot itself; the others wait
  local prio = SP.priority_client()
  local prio_picks
  if prio then
    local list = {}
    for _, uid in ipairs(lvl.order) do
      for i, sl in ipairs(lvl.nodes[uid].slots) do
        if not sl.shared and not sl.failed then list[#list + 1] = { uid = uid, i = i, orig = sl.orig } end
      end
    end
    local ok, picks = pcall(prio.assign, lvl, list)
    if not ok then log("RANDO-ERROR", prio.name, "assign:", tostring(picks)); picks = {} end
    prio_picks = picks or {}
  end
  for _, uid in ipairs(lvl.order) do
    -- after the first write, the budget decides; the rest next frame (the plan is the same, so a
    -- slot already done is passed over without a write)
    if writes > 0 and clock() > deadline then SP.replan = true; break end
    local rec = lvl.nodes[uid]
    for i, sl in ipairs(rec.slots) do
      local key, role, owner, pick
      if prio then
        pick = prio_picks[uid .. "#" .. i]
        if pick == sl.orig then pick = nil end
        owner = pick and prio or nil
        key = pick and "chaos" or nil
      else
        key, role = SP.pool_key(sl.orig)
        owner = role and SP.client_for_role(role)
      end
      -- a slot changed by a client that is off now, or that belongs to another client now: back
      if sl.cur ~= sl.orig and not sl.failed and (not owner or sl.owner ~= owner.name or not SP.enabled(owner)) then
        writes = writes + 1
        local ok, err = SP.write_slot(rec, sl, sl.orig, "owner changed")
        if ok then sl.owner = nil; wrong = wrong + 1
        else
          sl.failed = true
          log("slot of", uid, "could not be put back:", tostring(err), "- the level is read again")
          SP.schedule_scan("a node changed under the randomizer", 30)
        end
      end
      if not prio and owner and SP.enabled(owner) and not sl.shared and not sl.failed and SP.idle(rec) and not SP.zone then
        local pool = pools[key] or {}
        if #pool >= 2 then
          if owner.unique then
            perms[key] = perms[key] or SP.permutation(key, pool)
            pick = perms[key][sl.orig]
          else
            local others = {}
            for _, t in ipairs(pool) do if t ~= sl.orig then others[#others + 1] = t end end
            pick = SP.rank(seed_key() .. "|" .. tostring(uid) .. "|" .. i, others)[1]
          end
        end
      elseif not prio then
        owner = nil
      end
      if owner and not sl.failed then
        if pick and pick ~= sl.cur then
          writes = writes + 1
          local ok, err = SP.write_slot(rec, sl, pick, owner.name)
          if ok then
            sl.owner = (pick ~= sl.orig) and owner.name or nil
            sl.expect = (pick ~= sl.orig) and key or nil
            local w = SP.written[sl.addr]
            if w then w.owner, w.expect = sl.owner, sl.expect end
            applied = applied + 1
          else
            sl.failed = true          -- not tried again until the level is read again
            log("slot of", uid, "not changed:", tostring(err)); kept = kept + 1
          end
        elseif not pick then kept = kept + 1 end
      end
    end
  end
  SP.stats.applied = SP.stats.applied + applied
  if applied > 0 or wrong > 0 then
    local parts = {}
    if prio then parts[1] = prio.name .. " (priority, " .. tostring(prio.pool_size or "?") .. " template(s))"
    else for _, k in ipairs(sorted_keys(pools)) do parts[#parts + 1] = k .. "=" .. #pools[k] end end
    log(string.format("plan (%s): %d slot(s) changed, %d put back, %d left original | pools %s", tostring(why), applied,
        wrong, kept, #parts > 0 and table.concat(parts, " ") or "none learned yet"))
  end
  return applied
end
SP.seed_key = seed_key
SP.sorted_keys = sorted_keys

-- what a client changed in the loaded level (for its status line)
function SP.client_status(client)
  local lvl = SP.level
  local slots, nodes = 0, 0
  if lvl then
    for _, uid in ipairs(lvl.order) do
      local n = 0
      for _, sl in ipairs(lvl.nodes[uid].slots) do if sl.owner == client.name then n = n + 1 end end
      if n > 0 then slots = slots + n; nodes = nodes + 1 end
    end
  end
  local role_learned = 0
  for tid in pairs(learned_t()) do local r = SP.role_of(tid); if r == client.role then role_learned = role_learned + 1 end end
  return { slots = slots, encounters = nodes, learned = role_learned, blocked = count(blocked_t()) }
end

-- ---------------------------------------------------------------------------------------------
-- the game's events
-- ---------------------------------------------------------------------------------------------
local function rec_by_handle(h)
  local lvl = SP.level
  if not (lvl and h ~= nil) then return nil end
  h = math.tointeger(tonumber(h)) or h
  for _, uid in ipairs(lvl.order) do
    local rec = lvl.nodes[uid]
    if rec.component == h or rec.actor == h then return rec end
  end
  return nil
end
SP.rec_by_handle = rec_by_handle
local function changed_rec(rec)
  for _, sl in ipairs(rec.slots) do if sl.cur ~= sl.orig then return true end end
  return false
end
SP.changed_rec = changed_rec
-- every changed slot of this node belongs to a client with safety nets (not Chaos)
function SP.guarded_rec(rec)
  for _, sl in ipairs(rec.slots) do
    if sl.cur ~= sl.orig and not guarded_name(sl.owner) then return false end
  end
  return true
end
local function distinct_cur(rec)
  local one
  for _, sl in ipairs(rec.slots) do
    if one and sl.cur ~= one then return nil end
    one = sl.cur
  end
  return one
end

-- dev 10.17: the event's sender comes from ev.sender when its fields carry no SenderHandle
local function sender_of(f, ev) return f.SenderHandle or (type(ev) == "table" and ev.sender) or nil end
-- the node of a spawn: its sender, else its SpawnLocation's actor id in one node's SpawnLocations
local function rec_of_spawn(f, ev)
  local rec = rec_by_handle(sender_of(f, ev))
  if rec then return rec end
  local lvl = SP.level
  local loc = math.tointeger(tonumber(f.SpawnLocation))
  if not (lvl and loc and loc ~= 0 and rivet.uid) then return nil end
  local ok, id = pcall(rivet.uid, loc)
  if not ok or type(id) ~= "string" then return nil end
  local uid = lvl.loc_index[id:upper()]
  return uid and lvl.nodes[uid] or nil
end
SP.rec_of_spawn = rec_of_spawn

function SP.on_started(f, ev)
  local h = f.SpawnerComponentHandle or sender_of(f, ev)
  h = math.tointeger(tonumber(h)) or h
  if h ~= nil then SP.started_handles[h] = { frame = SP.frame } end
  local rec = rec_by_handle(h)
  if not rec then return end
  rec.started = rec.started or SP.frame
  rec.last_activity = SP.frame
  rec.stopped = nil
  rec.started_cp = SP.cp_hash
end
function SP.on_stopped(f, ev)
  local h = f.SpawnerComponentHandle or sender_of(f, ev)
  h = math.tointeger(tonumber(h)) or h
  if h ~= nil and SP.started_handles[h] then SP.started_handles[h].stopped = SP.frame end
  local rec = rec_by_handle(h)
  if rec then rec.stopped = SP.frame; rec.last_activity = SP.frame end
end
function SP.on_spawn(f, ev)
  local rec = rec_of_spawn(f, ev)
  if not rec then return end
  local h = math.tointeger(tonumber(f.SpawnedHandle)) or f.SpawnedHandle
  rec.started = rec.started or SP.frame
  rec.spawned = rec.spawned + 1
  rec.last_activity = SP.frame
  if h ~= nil and not rec.alive[h] then rec.alive[h] = true; rec.alive_n = rec.alive_n + 1 end
  local tid = (not rec.shared) and distinct_cur(rec) or nil
  if h ~= nil then SP.spawned_by[h] = { uid = rec.uid, tid = tid } end
  if not tid then return end
  -- asking an actor for its components costs up to ~90 calls: once per template (unchanged spawner)
  -- and once per changed spawner (the check of its replacement)
  local is_changed = changed_rec(rec)
  if is_changed then
    if rec.verified then return end
    rec.verified = true
  elseif SP.family_of(tid) then return end
  local fam = SP.classify_actor(h)
  if not fam then return end
  local unguarded = false
  for _, sl in ipairs(rec.slots) do if sl.owner and not guarded_name(sl.owner) then unguarded = true end end
  if is_changed and unguarded then
    SP.learn(tid, fam, "spawned by " .. tostring(rec.uid) .. " (chaos)")     -- learned, never put back
  elseif is_changed then
    -- a replacement: it must be what the plan expected
    local expect
    for _, sl in ipairs(rec.slots) do if sl.expect then expect = sl.expect end end
    local known = SP.family_of(tid)
    if known and known ~= fam then
      SP.learn(tid, fam, "spawned by " .. tostring(rec.uid))
      SP.block(rec, "the replacement turned out to be a " .. fam .. ", not a " .. tostring(expect))
    end
  else
    SP.learn(tid, fam, "spawned by " .. tostring(rec.uid))
  end
end
function SP.on_death(f, ev)
  local s = sender_of(f, ev)
  local h = math.tointeger(tonumber(s)) or s
  local who = h ~= nil and SP.spawned_by[h]
  if not who then return end
  SP.spawned_by[h] = nil
  local lvl = SP.level
  local rec = lvl and lvl.nodes[who.uid]
  if rec and rec.alive[h] then rec.alive[h] = nil; rec.alive_n = rec.alive_n - 1; rec.last_activity = SP.frame end
end
function SP.on_health_bar(f, ev)
  if f.IsFriendly == true then return end
  local s = sender_of(f, ev)
  local h = math.tointeger(tonumber(s)) or s
  local who = h ~= nil and SP.spawned_by[h]
  if not (who and who.tid) then return end
  SP.learn_health_bar(who.tid)
end
function SP.on_boss_phase(f)
  log("boss phase change (", tostring(f.SenderHandle), ") - nothing of the randomizer reacts to it")
end

-- 14_rando_travel.lua calls this for every CheckpointTriggeredEvent
function SP.on_checkpoint(cp)
  if type(cp) ~= "table" then return end
  local name = cp.name and tostring(cp.name):upper() or nil
  local was = SP.zone
  SP.zone = nil
  if name then for _, z in ipairs(SP.BOSS_ZONES) do if name:find(z, 1, true) then SP.zone = cp.name end end end
  SP.cp_hash = cp.hash
  if not SP.any_enabled() then return end
  if SP.zone and not was then
    local n = SP.revert_guarded("story boss area " .. tostring(SP.zone))
    log("story boss area", tostring(SP.zone), "- every change put back (" .. n .. " slot(s)) while you are there")
  end
  if cp.loaded then
    -- a load at a checkpoint: a death, a reload or a trip. A changed encounter that was running when
    -- it came counts one retry; too many and it keeps its original enemies.
    local lvl = SP.level
    if lvl then
      for _, uid in ipairs(lvl.order) do
        local rec = lvl.nodes[uid]
        if rec.started and not rec.stopped and changed_rec(rec) and SP.guarded_rec(rec) then
          SP.retries[uid] = (SP.retries[uid] or 0) + 1
          if SP.retries[uid] >= SP.DEATH_LIMIT then
            SP.block(rec, "the checkpoint was loaded " .. SP.retries[uid] .. " times while it ran")
            say("Randomizer: an encounter you retried " .. SP.retries[uid] .. " times has its original enemies now",
                { type = "corner", duration = 6 })
          end
        end
      end
    end
    SP.level = nil                    -- the load may have made the nodes anew
    SP.spawned_by, SP.started_handles = {}, {}
    SP.schedule_scan("checkpoint loaded")
  elseif was and not SP.zone and SP.level then
    SP.plan("left the story boss area")
  end
end

-- ---------------------------------------------------------------------------------------------
-- the frame (10_rando_runtime.lua calls it)
-- ---------------------------------------------------------------------------------------------
function SP.tick(frame, ready)
  SP.frame = frame
  if ready and next(SP.revert_pending) then SP.continue_reverts() end
  if not SP.any_enabled() then
    SP.job = nil
    if not next(SP.revert_pending) then SP.level = nil end
    return
  end
  if not ready then return end
  if SP.job then
    local ok, err = coroutine.resume(SP.job.co)
    if not ok then
      SP.job = nil
      -- dev 10.17: a frame that ran past rivet_hook's budget is a bad frame, not a broken level: the
      -- census starts again shortly (10.16 dropped it until the next checkpoint or planet)
      SP.census_retries = (SP.census_retries or 0) + 1
      if tostring(err):find("budget", 1, true) and SP.census_retries <= SP.CENSUS_RETRIES then
        log("census interrupted by the frame budget - reading again (" .. SP.census_retries .. "/" .. SP.CENSUS_RETRIES .. ")")
        SP.schedule_scan(SP.scan_why or "after a frame budget overrun", 20)
      else
        log("RANDO-ERROR census:", tostring(err))
      end
    elseif coroutine.status(SP.job.co) == "dead" then SP.job = nil; SP.census_retries = 0 end
    return
  end
  if (SP.scan_at and frame >= SP.scan_at) or (SP.level == nil and SP.scan_at == nil) then
    SP.start_scan(SP.scan_why or "the level is loaded")
    return
  end
  if SP.replan and SP.level then SP.replan = nil; SP.plan("learned while playing") end
  if frame % 60 ~= 0 or not SP.level then return end
  -- watchdogs: they only ever put an encounter back
  local lvl = SP.level
  for _, uid in ipairs(lvl.order) do
    local rec = lvl.nodes[uid]
    if changed_rec(rec) and rec.started and not SP.is_blocked(rec) and SP.guarded_rec(rec) then
      if rec.spawned == 0 and not rec.stopped and frame - rec.started > SP.SPAWN_TIMEOUT * 60 then
        SP.block(rec, "it started and spawned nothing for " .. SP.SPAWN_TIMEOUT .. " s")
      elseif rec.alive_n > 0 and frame - (rec.last_activity or rec.started) > SP.STUCK_SECONDS * 60 then
        SP.block(rec, "its enemies stayed alive " .. SP.STUCK_SECONDS .. " s without a death")
        say("Randomizer: an encounter looked stuck - it has its original enemies now (load the last checkpoint if an enemy cannot be reached)",
            { type = "corner", duration = 8 })
      end
    end
  end
end

-- a planet change or a level load: read the spawners again
function SP.on_level(why)
  SP.level = nil
  SP.census_retries = 0
  SP.spawned_by, SP.started_handles = {}, {}
  SP.schedule_scan(why)
end

-- ---------------------------------------------------------------------------------------------
-- subscriptions (once per VM; RANDO.subscribe retries a class the game does not know yet)
-- ---------------------------------------------------------------------------------------------
if not SP.subscribed then
  SP.subscribed = true
  local sub = (R and R.subscribe) or function(class, fn) pcall(rivet.on_event, class, function(ev) pcall(fn, ev) end) end
  -- `always`: a spawner's start and stop are noted even while both are off (no read, no write), so
  -- an encounter already running when a feature is switched on is never changed
  local function on(class, fn, always)
    sub(class, function(ev)
      if not always and not SP.any_enabled() then return end
      local ok, err = pcall(fn, ev.fields or {}, ev)
      if not ok then log("RANDO-ERROR", class, tostring(err)) end
    end)
  end
  on("SpawnerStartedEvent", SP.on_started, true)
  on("SpawnerStoppedEvent", SP.on_stopped, true)
  on("SpawnerSpawnEvent", SP.on_spawn)
  on("BotDeathCompleteEvent", SP.on_death)
  on("HealthBarShowEvent", SP.on_health_bar)
  on("BossPhaseChangeEvent", SP.on_boss_phase)
  on("LevelLoadedEvent", function() SP.on_level("level loaded") end)
  on("PlanetChangedEvent", function(f) if f.NewPlanetName then SP.on_level("planet " .. tostring(f.NewPlanetName)) end end)
end

log("spawner layer loaded (" .. SP.NODE_CLASS .. " Templates; families " .. #SP.FAMILY_CLASSES .. " bot classes)")
